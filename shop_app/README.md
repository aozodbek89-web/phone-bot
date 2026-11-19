# 🛍 iPark — iPhone do'koni (Telegram Mini App)

Premium qora-oltin dizayn. Faqat iPhone: avval iPhone 18 Pro Max (eSIM) va iPhone 18 Pro Max Dual SIM, keyin qolgan modellar.
Rang / xotira / SIM turini tanlash, savatcha, buyurtma (sizga va mijozga Telegramda keladi), aloqa.

| Do'kon | Mahsulot | Savatcha |
|---|---|---|
| ![](screenshots/1_home.png) | ![](screenshots/2_product.png) | ![](screenshots/3_cart.png) |

## Ishga tushirish (bepul, ~5 daqiqa)
1. [@BotFather](https://t.me/BotFather) → `/newbot` → tokenni nusxalang.
2. Tugmani bosing → `BOT_TOKEN` ga tokenni yozing → **Apply**:

   [![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/aozodbek89-web/phone-bot/tree/claude/gifted-bohr-yidxw4)
3. Botga `/id` yozing → kelgan raqamni Render → Environment → `ADMIN_CHAT_ID` ga qo'ying. Endi buyurtmalar sizga keladi.

Bot menyusidagi "🛍 Do'kon" tugmasi va webhook avtomatik sozlanadi.

## Mahsulot va narxlarni o'zgartirish
`shop_app/static/products.json` faylini tahrirlang (nomi, narxi, xotira narxlari, ranglar, manzil, telefon). Narxlar namuna sifatida berilgan.
