"""SMS provider abstraction for KrishiBondhu."""

import os
from typing import Dict
from app.core.logging import get_logger

logger = get_logger("sms_provider")

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
        logger.info("Mock SMS", to=phone, message=message)
        return {"success": True, "provider": "mock", "phone": phone, "message": message}


class NexmoSMSProvider(SMSProviderBase):
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_url = "https://rest.nexmo.com/sms/send"

    async def send(self, phone: str, message: str) -> Dict:
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    data={
                        "api_key": self.api_key,
                        "api_secret": self.api_secret,
                        "to": phone,
                        "from": "KrishiBondhu",
                        "text": message,
                    }
                )
                response.raise_for_status()
                data = response.json()

                if data.get("messages", [{}])[0].get("status") == "OK":
                    return {"success": True, "provider": "nexmo", "phone": phone, "message": message}
                else:
                    return {"success": False, "provider": "nexmo", "error": data}
        except Exception as e:
            logger.error("Nexmo SMS error", error=str(e))
            return {"success": False, "provider": "nexmo", "error": str(e)}


def get_sms_provider() -> SMSProviderBase:
    if SMS_PROVIDER == "nexmo":
        return NexmoSMSProvider(
            api_key=os.getenv("NEXMO_API_KEY", ""),
            api_secret=os.getenv("NEXMO_API_SECRET", "")
        )
    return MockSMSProvider()
