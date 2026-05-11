import os
import requests
from anthropic import Anthropic
from twilio.rest import Client
from datetime import datetime, timezone, timedelta

client = Anthropic()

NL_OFFSET = timedelta(hours=2)  # Zomertijd UTC+2

def convert_to_nl_time(date_str, time_str):
    try:
        if not time_str or time_str in ("All Day", "Tentative"):
            return time_str or "?"
        dt_str = f"{date_str} {time_str}"
        dt_utc = datetime.strptime(dt_str, "%Y-%m-%d %I:%M%p")
        dt_nl = dt_utc + NL_OFFSET
        return dt_nl.strftime("%H:%M")
    except:
        return time_str or "?"

def get_news_today():
    try:
        response = requests.get(
            "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
            timeout=10
        )
        events = response.json()
        today = datetime.utcnow().strftime("%Y-%m-%d")
        high_impact = [
            e for e in events
            if e.get("impact") == "High"
            and e.get("date", "").startswith(today)
            and any(c in e.get("country", "") for c in ["USD", "EUR", "GBP", "JPY"])
        ]
        if not high_impact:
            return "Geen high-impact nieuws vandaag voor deze pairs."
        lines = []
        for e in high_impact:
            nl_time = convert_to_nl_time(e.get("date", "")[:10], e.get("time", ""))
            lines.append(f"- {e['country']} | {e['title']} | {nl_time}")
        return "\n".join(lines)
    except:
        return "Nieuwsdata niet beschikbaar."

def get_week_events():
    try:
        response = requests.get(
            "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
            timeout=10
        )
        events = response.json()
        red_events = [
            e for e in events
            if e.get("impact") == "High"
            and any(c in e.get("country", "") for c in ["USD", "EUR", "GBP", "JPY"])
        ]
        if not red_events:
            return "Geen red folder events deze week."

        from collections import defaultdict
        by_day = defaultdict(list)
        for e in red_events:
            date_str = e.get("date", "")[:10]
            nl_time = convert_to_nl_time(date_str, e.get("time", ""))
            by_day[date_str].append(f"  {e['country']} | {e['title']} | {nl_time}")

        lines = []
        for date in sorted(by_day.keys()):
            try:
                day_label = datetime.strptime(date, "%Y-%m-%d").strftime("%A %d %b")
            except:
                day_label = date
            lines.append(f"📅 *{day_label}*")
            lines.extend(by_day[date])
        return "\n".join(lines)
    except Exception as ex:
        return f"Weekoverzicht niet beschikbaar: {ex}"

news = get_news_today()
is_monday = datetime.utcnow().weekday() == 0

prompt = f"""
Je bent een professionele forex analist. Vandaag is het {datetime.utcnow().strftime('%A %d %B %Y')}.

High-impact nieuws vandaag:
{news}

Geef een korte fundamentele bias voor deze drie pairs:
- GBP/JPY
- USD/JPY
- EUR/USD

Per pair: bullish, bearish of neutraal, met één zin uitleg.
Houd het beknopt en geschikt voor WhatsApp.
"""

message = client.messages.create(
    model="claude-opus-4-5",
    max_tokens=500,
    messages=[{"role": "user", "content": prompt}]
)

bias_text = message.content[0].text
date_label = datetime.utcnow().strftime('%d %b %Y')

whatsapp_message = f"🌍 *Forex Bias — {date_label}*\n\n{bias_text}\n\n_Automatisch gegenereerd om 08:00_"

if is_monday:
    week_events = get_week_events()
    whatsapp_message += f"\n\n────────────────\n📊 *Red Folder Events Deze Week*\n\n{week_events}"

twilio_client = Client(
    os.environ["TWILIO_ACCOUNT_SID"],
    os.environ["TWILIO_AUTH_TOKEN"]
)

twilio_client.messages.create(
    from_=os.environ["TWILIO_WHATSAPP_FROM"],
    to=os.environ["TWILIO_WHATSAPP_TO"],
    body=whatsapp_message
)

print("Bias verstuurd!")
