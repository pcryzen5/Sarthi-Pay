from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    DATABASE_URL: str = "sqlite+aiosqlite:///./sarthi_pay.db"

    # Gnani.ai STT & TTS
    GNANI_STT_API_KEY: str = ""
    GNANI_STT_ENDPOINT: str = "https://api.gnani.ai/asr/v1/stream"
    GNANI_TTS_API_KEY: str = ""
    GNANI_TTS_ENDPOINT: str = "https://api.gnani.ai/tts/v3/synthesize"
    GNANI_DEFAULT_LANG: str = "hi-IN"
    GNANI_TIMBRE_VOICE: str = "expressive_hindi_female_1"

    # Indic LLM (Evon v3.3)
    HUGGINGFACE_API_KEY: str = ""
    EVON_API_URL: str = "https://api-inference.huggingface.co/models/gnani-ai/evon-v3.3"
    EVON_MODEL_NAME: str = "gnani-ai/evon-v3.3"

    # Simulation & Test Fallbacks
    ENABLE_FALLBACK_SIMULATION: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

