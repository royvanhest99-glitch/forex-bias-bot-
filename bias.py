import os
import requests
from anthropic import Anthropic
from twilio.rest import Client
from datetime import datetime
import pytz

client = Anthropic()

NL_TZ = pytz.timezone("Europe/Amsterdam")

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
            lines.append(f"- {e['country']} | {e['title']} om {e.get('time', '?')}")
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

        # Groepeer per dag
        from collections import defaultdict
        by_day = defaultdict(list)
        for e in red_events:
            date_str = e.get("date", "")[:10]
            time_str = e.get("time", "")
            # Converteer naar NL tijd
            try:
                if time_str and time_str != "All Day" and time_str != "Tentative":
                    dt_str = f"{date_str} {time_str}"
                    dt_utc = datetime.strptime(dt_str, "%Y-%m-%d %I:%M%p")
                    dt_utc = pytz.utc.localize(dt_utc)
                    dt_nl = dt_utc.astimezone(NL_TZ)
                    nl_time = dt_nl.strftime("%H:%M")
                else:
                    nl_time = time_str or "?"
            except:
                nl_time = time_str or "?"
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
