"""SMS provider abstraction for KrishiBondhu."""

import os
from typing import Dict

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

SMS_PROVIDER = os.getenv("SMS_PROVIDER", "mock")


class SMSProviderBase:
    async def send(self, phone: str, message: str) -> Dict:
        raise NotImplementedError("SMS provider must implement send().")


class MockSMSProvider(SMSProviderBase):
    async def send(self, phone: str, message: str) -> Dict:
        print(f"[MOCK SMS] To={phone} Message={message}")
        return {"success": True, "provider": "mock", "phone": phone, "message": message}


class NexmoSMSProvider(SMSProviderBase):
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret

    async def send(self, phone: str, message: str) -> Dict:
        # Replace with actual Nexmo/Vonage integration if enabled
        print(f"[NEXMO SMS] To={phone} Message={message}")
        return {"success": True, "provider": "nexmo", "phone": phone, "message": message}


def get_sms_provider() -> SMSProviderBase:
    if SMS_PROVIDER == "nexmo":
        return NexmoSMSProvider(
            api_key=os.getenv("NEXMO_API_KEY", ""),
            api_secret=os.getenv("NEXMO_API_SECRET", "")
        )
    return MockSMSProvider()
