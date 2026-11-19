# 📚 Manga Telegram Mini App

Telegram ichida ochiladigan manga o'qish ilovasi (manba: MangaDex, minglab manga).

**Imkoniyatlar:** mashhur va yangi mangalar · qidiruv · janr bo'yicha filtr · O'zbek / Русский / English tili ·
bob o'qish (HD yoki trafik tejovchi rejim) · sevimlilar ❤️ · "Davom ettirish" va o'qish tarixi · Telegram mavzusiga moslashadi.

## Ishga tushirish (3 qadam, ~5 daqiqa, bepul)

1. **Bot tokenini oling:** Telegramda [@BotFather](https://t.me/BotFather) → `/newbot` → nom bering → tokenni nusxalang.
2. **Render.com ga joylang:** quyidagi tugmani bosing, GitHub orqali kiring, `BOT_TOKEN` maydoniga tokenni qo'ying va **Apply** bosing.

   [![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/aozodbek89-web/phone-bot/tree/claude/gifted-bohr-yidxw4)

3. 2–3 daqiqa kuting. Tamom! Botingizga kirib `/start` bosing yoki pastdagi **📚 Manga** tugmasini bosing.

Server o'zi avtomatik: webhook'ni o'rnatadi, bot menyusiga "📚 Manga" tugmasini qo'shadi, `/start` buyrug'ini sozlaydi.
Hech qanday URL'ni qo'lda yozish shart emas.

> ℹ️ Render bepul tarifida server 15 daqiqa ishlatilmasa "uxlaydi" — keyingi birinchi ochilish ~30–50 soniya olishi mumkin, keyin tez ishlaydi.

## Kompyuterda sinash (ixtiyoriy)
```
pip install -r manga_app/requirements.txt
BOT_TOKEN=... PUBLIC_URL=https://sizning-https-manzil python manga_app/server.py
```
