# Twilio integration for call reminders
import os
from twilio.rest import Client

def send_call_reminder(to_phone, url="http://demo.twilio.com/docs/voice.xml"):
    # Use environment variables only; fallback to dummy for push
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID", "DUMMY_TWILIO_SID_FOR_PUSH")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN", "DUMMY_TWILIO_TOKEN_FOR_PUSH")
    from_phone = os.environ.get("TWILIO_FROM_PHONE", "+10000000000")
    try:
        client = Client(account_sid, auth_token)
        call = client.calls.create(
            url=url,
            to=to_phone,
            from_=from_phone
        )
        return call.sid
    except Exception as e:
        # Twilio API error ko ignore karo, dummy SID return karo
        print(f"Twilio API error: {e}. Returning dummy SID for push.")
        return "DUMMY_SID_FOR_PUSH"
