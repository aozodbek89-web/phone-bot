"""Telefon do'koni Telegram Mini App: sahifa + buyurtma API + Telegram bot."""
import asyncio
import hashlib
import hmac
import json
import logging
import os
from pathlib import Path
from urllib.parse import parse_qsl

from aiohttp import ClientSession, ClientTimeout, web

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("shop")

STATIC = Path(__file__).parent / "static"
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "").strip()
PUBLIC_URL = (os.getenv("PUBLIC_URL") or os.getenv("RENDER_EXTERNAL_URL") or "").strip().rstrip("/")
PORT = int(os.getenv("PORT", "8080"))
SECRET = hashlib.sha256(("wh" + BOT_TOKEN).encode()).hexdigest()[:40]
session: ClientSession | None = None


def catalog() -> dict:
    return json.loads((STATIC / "products.json").read_text("utf-8"))


def money(n: int) -> str:
    return f"{n:,}".replace(",", " ") + " so'm"


def check_init_data(init_data: str) -> dict | None:
    """Telegram WebApp initData imzosini tekshiradi, foydalanuvchini qaytaradi."""
    try:
        data = dict(parse_qsl(init_data, strict_parsing=True))
        got = data.pop("hash")
        check = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
        key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(hmac.new(key, check.encode(), hashlib.sha256).hexdigest(), got):
            return None
        return json.loads(data.get("user", "{}"))
    except Exception:  # noqa: BLE001
        return None


async def tg(method: str, **params):
    if not BOT_TOKEN:
        return {}
    async with session.post(f"https://api.telegram.org/bot{BOT_TOKEN}/{method}", json=params) as r:
        data = await r.json()
        if not data.get("ok"):
            log.warning("Telegram %s: %s", method, data)
        return data


# ---------------- Buyurtma ----------------
async def order(request: web.Request) -> web.Response:
    body = await request.json()
    user = check_init_data(body.get("initData", "")) if BOT_TOKEN else {"id": 0, "first_name": "Test"}
    if user is None:
        return web.json_response({"ok": False, "error": "Iltimos, ilovani Telegram ichida oching"}, status=403)
    cat = catalog()
    items = {p["id"]: p for p in cat["products"]}
    sims = dict(cat["sims"])
    lines, total = [], 0
    for it in body.get("items", [])[:50]:
        p = items.get(str(it.get("id")))
        if not p:
            continue
        mem = dict(p["mem"])
        m = str(it.get("mem", p["mem"][0][0]))
        sim = p.get("sim") or str(it.get("sim", "eSIM"))
        color = next((c["n"] for c in p["colors"] if c["n"] == it.get("color")), p["colors"][0]["n"])
        if m not in mem or sim not in sims:
            continue
        price = p["price"] + mem[m] + (0 if p.get("sim") else sims[sim])
        qty = max(1, min(int(it.get("qty", 1)), 20))
        total += price * qty
        lines.append(f"• {p['name']} {m}, {color}, {sim} × {qty} — {money(price * qty)}")
    if not lines:
        return web.json_response({"ok": False, "error": "Savatcha bo'sh"}, status=400)
    name = str(body.get("name", ""))[:80]
    phone = str(body.get("phone", ""))[:30]
    comment = str(body.get("comment", ""))[:300]
    delivery = "🚚 Yetkazib berish" if body.get("delivery") else "🏬 Do'kondan olib ketish"
    uname = f"@{user['username']}" if user.get("username") else user.get("first_name", "")
    text = (f"🛒 YANGI BUYURTMA\n\n{chr(10).join(lines)}\n\n💰 Jami: {money(total)}\n\n"
            f"👤 {name} ({uname})\n📞 {phone}\n{delivery}" + (f"\n💬 {comment}" if comment else ""))
    if ADMIN_CHAT_ID:
        await tg("sendMessage", chat_id=ADMIN_CHAT_ID, text=text)
    if user.get("id"):
        await tg("sendMessage", chat_id=user["id"],
                 text=f"✅ Buyurtmangiz qabul qilindi!\n\n{chr(10).join(lines)}\n\n💰 Jami: {money(total)}\n\n"
                      "Tez orada operatorimiz siz bilan bog'lanadi. Rahmat! 🙏")
    return web.json_response({"ok": True, "total": total})


# ---------------- Bot ----------------
async def handle_update(upd: dict):
    msg = upd.get("message") or {}
    chat = msg.get("chat", {}).get("id")
    text = msg.get("text", "")
    if not chat:
        return
    if text.startswith("/id"):
        await tg("sendMessage", chat_id=chat, text=f"Sizning chat ID: {chat}\n\nBuni Render'da ADMIN_CHAT_ID ga yozing — buyurtmalar shu yerga keladi.")
        return
    shop = catalog()["shop"]
    name = msg.get("from", {}).get("first_name", "")
    kb = {"inline_keyboard": [[{"text": "🛍 Do'konni ochish", "web_app": {"url": PUBLIC_URL}}]]} if PUBLIC_URL else None
    await tg("sendMessage", chat_id=chat,
             text=f"Assalomu alaykum, {name}! 👋\n\n✨ {shop['name']} — {shop['tagline']}.\n\n"
                  "📱 iPhone 18 Pro Max, Dual SIM va boshqa modellar — rasmiy kafolat bilan.\n"
                  f"📍 {shop['address']}\n📞 {shop['phone']}",
             **({"reply_markup": kb} if kb else {}))


async def webhook(request: web.Request) -> web.Response:
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != SECRET:
        return web.Response(status=403)
    asyncio.create_task(handle_update(await request.json()))
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
            log.warning("Polling: %s", e)
            await asyncio.sleep(5)


async def on_start(app: web.Application):
    global session
    session = ClientSession(timeout=ClientTimeout(total=30))
    if not BOT_TOKEN:
        log.warning("BOT_TOKEN yo'q — faqat sahifa ishlaydi.")
        return
    await tg("setMyCommands", commands=[{"command": "start", "description": "Do'konni ochish"},
                                        {"command": "id", "description": "Chat ID ni bilish"}])
    if PUBLIC_URL:
        await tg("setWebhook", url=f"{PUBLIC_URL}/tg/webhook", secret_token=SECRET, allowed_updates=["message"])
        await tg("setChatMenuButton", menu_button={"type": "web_app", "text": "🛍 Do'kon", "web_app": {"url": PUBLIC_URL}})
    else:
        await tg("deleteWebhook")
        app["poller"] = asyncio.create_task(polling())


async def on_stop(app: web.Application):
    if "poller" in app:
        app["poller"].cancel()
    await session.close()


def nocache(name):
    async def h(_r):
        return web.FileResponse(STATIC / name, headers={"Cache-Control": "no-cache"})
    return h


def make_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", nocache("index.html"))
    app.router.add_get("/products.json", nocache("products.json"))
    app.router.add_get("/health", lambda _r: web.Response(text="ok"))
    app.router.add_post("/api/order", order)
    app.router.add_post("/tg/webhook", webhook)
    app.on_startup.append(on_start)
    app.on_cleanup.append(on_stop)
    return app


if __name__ == "__main__":
    web.run_app(make_app(), port=PORT)
