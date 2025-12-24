#!/usr/bin/env python3
import os, asyncio, getpass
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

api_id  = int(os.environ['TELEGRAM_API_ID'])
api_hash= os.environ['TELEGRAM_API_HASH']
phone   = os.environ['TELEGRAM_PHONE']
sess    = 'state/telegram.user.session'  # session dédiée UTILISATEUR

async def main():
    client = TelegramClient(sess, api_id, api_hash)
    await client.connect()

    if not await client.is_user_authorized():
        print(f">>> Envoi du code à {phone}")
        await client.send_code_request(phone)
        code = input("Code reçu (SMS/Telegram) : ").strip()
        try:
            await client.sign_in(phone=phone, code=code)
        except SessionPasswordNeededError:
            pwd = os.environ.get("TELEGRAM_2FA_PASSWORD") or getpass.getpass("Mot de passe 2FA : ")
            await client.sign_in(password=pwd)

    me = await client.get_me()
    print(">>> Connecté comme:", me.username or me.id, "| bot =", bool(me.bot))
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
