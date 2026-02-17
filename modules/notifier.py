def notify_job_found(job):
    import asyncio
    import os
    from telegram import Bot
    from dotenv import load_dotenv
    load_dotenv()

    token   = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    # Escape special chars that break Telegram Markdown
    def esc(text):
        if not text:
            return "N/A"
        for ch in ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']:
            text = text.replace(ch, f'\\{ch}')
        return text

    msg = (
        f"🚀 *New Job Found\\!*\n\n"
        f"🏢 *Company:* {esc(job.get('company', ''))}\n"
        f"💼 *Role:* {esc(job.get('job_title', ''))}\n"
        f"🌍 *Location:* {esc(job.get('country', ''))}\n"
        f"📡 *Source:* {esc(job.get('source', ''))}\n"
        f"✈️ *Visa:* {esc(job.get('visa_sponsorship', ''))}\n"
        f"🔗 [Apply Here]({job.get('job_url', '')})"
    )

    async def _send():
        bot = Bot(token=token)
        await bot.send_message(chat_id=chat_id, text=msg, parse_mode='MarkdownV2')

    asyncio.run(_send())