"""Manga Telegram Mini App: static sahifa + MangaDex proxy + Telegram bot (webhook/polling)."""
import asyncio
import hashlib
import logging
import os
import time
from pathlib import Path
from urllib.parse import urlparse

from aiohttp import ClientSession, ClientTimeout, web

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("manga")

STATIC = Path(__file__).parent / "static"
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
PUBLIC_URL = (os.getenv("PUBLIC_URL") or os.getenv("RENDER_EXTERNAL_URL") or "").strip().rstrip("/")
PORT = int(os.getenv("PORT", "8080"))
MD_API = os.getenv("MD_API", "https://api.mangadex.org")
UA = "MangaMiniApp/1.0 (+telegram mini app)"
ALLOWED_API = ("manga", "chapter", "at-home/server/", "cover")
SECRET = hashlib.sha256(("wh" + BOT_TOKEN).encode()).hexdigest()[:40]

_cache: dict[str, tuple[float, int, bytes]] = {}
session: ClientSession | None = None


# ---------------- MangaDex proxy ----------------
async def api_proxy(request: web.Request) -> web.Response:
    path = request.match_info["path"]
    if ".." in path or not path.startswith(ALLOWED_API):
        return web.json_response({"error": "not allowed"}, status=404)
    url = f"{MD_API}/{path}"
    if request.query_string:
        url += "?" + request.query_string
    now = time.time()
    hit = _cache.get(url)
    if hit and hit[0] > now:
        return web.Response(body=hit[2], status=hit[1], content_type="application/json")
    try:
        async with session.get(url, headers={"User-Agent": UA}) as r:
            body = await r.read()
            status = r.status
    except Exception as e:  # noqa: BLE001
        log.warning("API xato %s: %s", url, e)
        return web.json_response({"error": "upstream"}, status=502)
    if status == 200:
        if len(_cache) > 800:
            _cache.clear()
        ttl = 60 if path.startswith("at-home") else 300
        _cache[url] = (now + ttl, status, body)
    return web.Response(body=body, status=status, content_type="application/json")


def _img_allowed(u: str) -> bool:
    p = urlparse(u)
    h = (p.hostname or "").lower()
    return p.scheme == "https" and (h == "uploads.mangadex.org" or h.endswith(".mangadex.network"))


async def img_proxy(request: web.Request) -> web.StreamResponse:
    u = request.query.get("u", "")
    if not _img_allowed(u):
        return web.Response(status=400, text="bad url")
    try:
        async with session.get(u, headers={"User-Agent": UA}) as r:
            if r.status != 200:
                return web.Response(status=r.status)
            resp = web.StreamResponse(headers={
                "Content-Type": r.headers.get("Content-Type", "image/jpeg"),
                "Cache-Control": "public, max-age=604800, immutable",
            })
            await resp.prepare(request)
            async for chunk in r.content.iter_chunked(65536):
                await resp.write(chunk)
            await resp.write_eof()
            return resp
    except (asyncio.CancelledError, ConnectionResetError):
        raise
    except Exception as e:  # noqa: BLE001
        log.warning("Rasm xato %s: %s", u, e)
        return web.Response(status=502)


# ---------------- Telegram bot ----------------
async def tg(method: str, **params):
    async with session.post(f"https://api.telegram.org/bot{BOT_TOKEN}/{method}", json=params) as r:
        data = await r.json()
        if not data.get("ok"):
            log.warning("Telegram %s: %s", method, data)
        return data


async def handle_update(upd: dict):
    msg = upd.get("message") or {}
    chat = msg.get("chat", {}).get("id")
    if not chat:
        return
    name = msg.get("from", {}).get("first_name", "")
    text = (f"Assalomu alaykum, {name}! 👋\n\n📚 Minglab manga sizni kutmoqda.\n"
            "Pastdagi tugmani bosib o'qishni boshlang!")
    kb = None
    if PUBLIC_URL:
        kb = {"inline_keyboard": [[{"text": "📖 Mangalarni ochish", "web_app": {"url": PUBLIC_URL}}]]}
    await tg("sendMessage", chat_id=chat, text=text, **({"reply_markup": kb} if kb else {}))


async def webhook(request: web.Request) -> web.Response:
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != SECRET:
        return web.Response(status=403)
    upd = await request.json()
    asyncio.create_task(handle_update(upd))
    return web.Response(text="ok")


async def polling():
    offset = 0
    while True:
        try:
            data = await tg("getUpdates", offset=offset, timeout=30)
            for u in data.get("result", []):
                offset = u["update_id"] + 1
                asyncio.create_task(handle_update(u))
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001
            log.warning("Polling xato: %s", e)
            await asyncio.sleep(5)


async def setup_bot(app: web.Application):
    if not BOT_TOKEN:
        log.warning("BOT_TOKEN berilmagan — faqat mini ilova ishlaydi.")
        return
    await tg("setMyCommands", commands=[{"command": "start", "description": "Mangalarni ochish"}])
    if PUBLIC_URL:
        await tg("setWebhook", url=f"{PUBLIC_URL}/tg/webhook", secret_token=SECRET,
                 allowed_updates=["message"])
        await tg("setChatMenuButton", menu_button={
            "type": "web_app", "text": "📚 Manga", "web_app": {"url": PUBLIC_URL}})
        log.info("Bot webhook rejimida: %s", PUBLIC_URL)
    else:
        await tg("deleteWebhook")
        app["poller"] = asyncio.create_task(polling())
        log.info("Bot polling rejimida (PUBLIC_URL yo'q).")


# ---------------- App ----------------
async def on_start(app: web.Application):
    global session
    session = ClientSession(timeout=ClientTimeout(total=40))
    await setup_bot(app)


async def on_stop(app: web.Application):
    if "poller" in app:
        app["poller"].cancel()
    await session.close()


async def index(_request):
    return web.FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})


def make_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/health", lambda _r: web.Response(text="ok"))
    app.router.add_get("/api/md/{path:.+}", api_proxy)
    app.router.add_get("/img", img_proxy)
    app.router.add_post("/tg/webhook", webhook)
    app.on_startup.append(on_start)
    app.on_cleanup.append(on_stop)
    return app


if __name__ == "__main__":
    web.run_app(make_app(), port=PORT)
