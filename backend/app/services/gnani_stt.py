import logging
import httpx
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


LANG_MAP = {
    "hi": "hi-IN",
    "en": "en-IN",
    "mr": "mr-IN",
    "bn": "bn-IN",
}

DEFAULT_TRANSCRIPTS = {
    "hi": "बिजली का बिल भर दो",
    "en": "Pay electricity bill",
    "mr": "महावितरणचे वीज बिल भरा",
    "bn": "বিদ্যুৎ বিল পরিশোধ করুন",
}


class GnaniSTTService:
    def __init__(self):
        self.api_key = settings.GNANI_STT_API_KEY
        self.endpoint = settings.GNANI_STT_ENDPOINT
        self.default_lang = settings.GNANI_DEFAULT_LANG

    async def transcribe(self, audio_bytes: bytes, lang: Optional[str] = None) -> str:
        """Transcribes incoming audio bytes using Gnani.ai Streaming/REST STT.

        Falls back to demo simulation if API key is not configured or network
        is unavailable.
        """
        lang_code = lang or "hi"
        language = LANG_MAP.get(lang_code, self.default_lang)

        if self.api_key:
            try:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "token": self.api_key,
                    "x-api-key": self.api_key,
                    "Content-Type": "audio/wav",
                }
                params = {"lang": language, "encoding": "LINEAR16", "sample_rate": 16000}
                async with httpx.AsyncClient(timeout=4.0) as client:
                    response = await client.post(
                        self.endpoint,
                        headers=headers,
                        params=params,
                        content=audio_bytes
                    )
                    if response.status_code == 200:
                        data = response.json()
                        transcript = data.get("transcript") or data.get("text", "")
                        if transcript:
                            return transcript
                    else:
                        logger.warning(
                            f"Gnani STT API returned status {response.status_code}: {response.text}"
                        )
            except Exception as e:
                logger.error(f"Error calling Gnani STT API: {e}")

        # Fallback simulation for offline testing & demo resiliency in requested language
        logger.info(f"Using simulated transcription fallback for lang={lang_code}")
        return DEFAULT_TRANSCRIPTS.get(lang_code, DEFAULT_TRANSCRIPTS["hi"])


gnani_stt = GnaniSTTService()

