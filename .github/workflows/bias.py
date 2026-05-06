import os
import requests
from anthropic import Anthropic
from twilio.rest import Client
from datetime import datetime

client = Anthropic()

def get_news():
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

news = get_news()

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

whatsapp_message = f"🌍 *Forex Bias — {datetime.utcnow().strftime('%d %b %Y')}*\n\n{bias_text}\n\n_Automatisch gegenereerd om 08:00_"

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
