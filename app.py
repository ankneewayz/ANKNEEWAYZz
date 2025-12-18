import os
from typing import Optional
from fastapi import FastAPI, Request
import httpx

# ---- Telegram Bot Token ----
TELEGRAM_BOT_TOKEN = "7943648773:AAGEZaetLa6Cm4nB7W2ARKuEkPKJIB_cmo0"
TELEGRAM_API_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# ---- OSINT APIs ----
OSINT_COMMANDS = {
    "/num": "https://zero-api-number-info.vercel.app/api?number={query}&key=zero",
    "/ifsc": "https://ab-ifscinfoapi.vercel.app/info?ifsc={query}",
    "/mail": "https://ab-mailinfoapi.vercel.app/info?mail={query}",
    "/numtoname": "https://ab-number-to-name.vercel.app/info?number={query}",
    "/numbasic": "https://ab-calltraceapi.vercel.app/info?number={query}"
}

# ---- FastAPI App ----
app = FastAPI()

# ---- Memory: Track First Message Users ----
FIRST_USERS = set()

# ---- Telegram Sender ----
async def tg_send(method: str, payload: dict) -> dict:
    url = f"{TELEGRAM_API_BASE}/{method}"
    async with httpx.AsyncClient() as client:
        r = await client.post(url, json=payload, timeout=30.0)
        try:
            return r.json()
        except Exception:
            return {"ok": False, "status_code": r.status_code, "text": r.text}

# ---- OSINT Handler ----
async def handle_osint_search(chat_id: int, query: str, api_url: str, command: str):
    url = api_url.format(query=query)
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, timeout=20.0)
            data = r.json() if "application/json" in r.headers.get("content-type", "") else r.text

            emoji_map = {
                "/num": "🇮🇳 IND Number Info",
                "/ifsc": "🏦 IFSC Bank Info",
                "/mail": "✉️ Mail Info",
                "/numtoname": "📝 Number → Name",
                "/numbasic": "🔢 Number → Basic Info"
            }

            title = emoji_map.get(command, "ℹ️ Result")

            formatted = (
                f"📌 *{title}*\n\n"
                f"```\n{data}\n```\n"
                f"⚡ Powered by ArC OSINT"
            )

            await tg_send(
                "sendMessage",
                {
                    "chat_id": chat_id,
                    "text": formatted,
                    "parse_mode": "Markdown"
                }
            )

        except Exception as e:
            await tg_send("sendMessage", {"chat_id": chat_id, "text": f"❌ Error: {e}"})


# ---- Webhook ----
@app.post("/api/webhook")
async def webhook(request: Request):
    update = await request.json()
    message = update.get("message") or update.get("edited_message")
    if not message:
        return {"ok": True}

    chat_id = message["chat"]["id"]
    text = (message.get("text") or "").strip()
    if not text:
        return {"ok": True}

    # ---- First Message Logic ----
    if chat_id not in FIRST_USERS:
        FIRST_USERS.add(chat_id)

        await tg_send(
            "sendVideo",
            {
                "chat_id": chat_id,
                "video": "homelander.mp4",  # <-- replace with your OSINT intro video
                "caption": (
                    "🕵️ *Welcome to ArC OSINT Bot*\n\n"
                    "Advanced Open-Source Intelligence tools at your fingertips.\n"
                    "Phone • Bank • Email • Identity Lookup\n\n"
                    "Type /start to see all commands
   🚀"
   "by @ankneewayz"
                ),
                "parse_mode": "Markdown"
            }
        )

    lc = text.lower()
    parts = lc.split()

    async def reply(msg: str):
        return await tg_send("sendMessage", {"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})

    # ---- /start ----
    if lc.startswith("/start"):
        await reply(
            "👋 *ArC OSINT Bot Ready*\n\n"
            "📌 *Available Commands*\n"
            "/num <number> – 🇮🇳 Number Info\n"
            "/ifsc <code> – 🏦 Bank Details\n"
            "/mail <email> – ✉️ Email Lookup\n"
            "/numtoname <number> – 📝 Name Finder\n"
            "/numbasic <number> – 🔢 CallTrace\n\n"
            "Example:\n`/num 919876543210`\n\n"
            "⚡ Fast • Private • Reliable"
        )
        return {"ok": True}

    # ---- OSINT Commands ----
    command = parts[0]
    query = " ".join(parts[1:]).strip()

    if command in OSINT_COMMANDS:
        if not query:
            await reply(f"❌ Missing input.\nExample:\n`{command} 919876543210`")
        else:
            await handle_osint_search(chat_id, query, OSINT_COMMANDS[command], command)
        return {"ok": True}

    # ---- Fallback ----
    await reply("❌ Unknown command.\nType /start to view options.")
    return {"ok": True}