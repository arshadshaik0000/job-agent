# modules/notifier.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from telegram import Bot
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

async def _send(text):
    """Internal async send."""
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode='Markdown')
    except Exception as e:
        print(f"❌ Telegram error: {e}")

def send_message(text):
    """Send a plain message to Telegram."""
    asyncio.run(_send(text))

def notify_job_found(job):
    """Send detailed job alert to Telegram."""
    company  = job.get('company', 'Unknown')
    title    = job.get('job_title', 'Unknown')
    location = job.get('location', job.get('country', ''))
    country  = job.get('country', '')
    url      = job.get('job_url', '')
    source   = job.get('source', 'unknown').capitalize()
    posted   = job.get('date_posted', '')
    visa     = job.get('visa_sponsorship', 'unknown')

    # Visa display
    if visa == 'sponsored':
        visa_line = "✈️ *Visa:* Sponsorship Available ✅"
    elif 'india' in country.lower():
        visa_line = "✈️ *Visa:* Not Required (India) 🇮🇳"
    else:
        visa_line = "✈️ *Visa:* Unknown"

    # Date display
    date_line = f"📅 *Posted:* {posted}" if posted else "📅 *Posted:* Not available"

    message = f"""
🚀 *New Job Found!*

🏢 *Company:* {company}
💼 *Role:* {title}
🌍 *Location:* {location}
🗺 *Country:* {country}
{visa_line}
{date_line}
📡 *Source:* {source}
🔗 [Apply Here]({url})
"""
    send_message(message)

if __name__ == "__main__":
    send_message("🧪 Notifier module working!")
    print("✅ Notifier tested!")