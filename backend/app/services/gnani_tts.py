import io
import math
import wave
import struct
import base64
import logging
import httpx
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


TTS_LANG_MAP = {
    "hi": ("hi-IN", "expressive_hindi_female_1"),
    "en": ("en-IN", "expressive_english_female_1"),
    "mr": ("mr-IN", "expressive_marathi_female_1"),
    "bn": ("bn-IN", "expressive_bengali_female_1"),
}


class GnaniTTSService:
    def __init__(self):
        self.api_key = settings.GNANI_TTS_API_KEY
        self.endpoint = settings.GNANI_TTS_ENDPOINT
        self.default_lang = settings.GNANI_DEFAULT_LANG
        self.voice = settings.GNANI_TIMBRE_VOICE

    async def synthesize(self, text: str, lang: Optional[str] = None) -> str:
        """Synthesizes text using Gnani.ai Timbre v3.0 Expressive Indic TTS.

        Returns a base64 encoded audio string (WAV/MP3).
        """
        lang_code = lang or "hi"
        language, default_voice = TTS_LANG_MAP.get(lang_code, (self.default_lang, self.voice))
        voice = default_voice

        if self.api_key:
            try:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "token": self.api_key,
                    "x-api-key": self.api_key,
                    "Content-Type": "application/json",
                }
                payload = {
                    "text": text,
                    "language": language,
                    "voice": voice,
                    "format": "wav",
                    "sample_rate": 24000
                }
                async with httpx.AsyncClient(timeout=4.0) as client:
                    response = await client.post(
                        self.endpoint,
                        headers=headers,
                        json=payload
                    )
                    if response.status_code == 200:
                        content_type = response.headers.get("content-type", "")
                        if "audio" in content_type or "octet-stream" in content_type:
                            return base64.b64encode(response.content).decode("utf-8")
                        else:
                            data = response.json()
                            audio_val = data.get("audio_base64") or data.get("audio") or data.get("audio_content")
                            if audio_val:
                                return audio_val
                    else:
                        logger.warning(
                            f"Gnani TTS API returned status {response.status_code}: {response.text}"
                        )
            except Exception as e:
                logger.error(f"Error calling Gnani TTS API: {e}")

        # Fallback synthesizer: generates an accessible melodic confirmation chime (16-bit PCM WAV)
        return self._generate_fallback_wav(text)

    def _generate_fallback_wav(self, text: str) -> str:
        """Generates a pleasant, valid PCM WAV sound cue for offline/demo operation."""
        sample_rate = 24000
        duration_sec = 0.8  # Short auditory cue
        num_samples = int(sample_rate * duration_sec)

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)

            # Generate warm major chord chime (523.25 Hz C5, 659.25 Hz E5)
            frames = bytearray()
            for i in range(num_samples):
                t = i / sample_rate
                # Exponential decay envelope
                envelope = math.exp(-3.5 * t)
                # Harmonic mix
                val = 0.6 * math.sin(2 * math.pi * 523.25 * t) + 0.4 * math.sin(2 * math.pi * 659.25 * t)
                sample = int(val * envelope * 16000)
                # Clamp sample to 16-bit signed range
                sample = max(-32768, min(32767, sample))
                frames.extend(struct.pack("<h", sample))

            wav_file.writeframes(frames)

        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode("utf-8")


gnani_tts = GnaniTTSService()

