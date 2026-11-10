from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class FraudCheck(BaseModel):
    is_flagged: bool = False
    risk_level: str = "LOW"  # LOW, MEDIUM, HIGH
    reason: Optional[str] = None


class VoiceEntities(BaseModel):
    utility_type: Optional[str] = None  # ELECTRICITY, GAS, WATER, MOBILE
    biller_name: Optional[str] = None
    recipient_name: Optional[str] = None
    phone_number: Optional[str] = None
    amount: Optional[float] = None


class ProcessVoiceCommandRequest(BaseModel):
    session_id: Optional[str] = "sess_default"
    user_id: str = "usr_9921"
    lang: Optional[str] = "hi"  # hi, en, mr, bn
    audio_base64: Optional[str] = None
    text_override: Optional[str] = None  # Facilitates testing/text input fallback


class ProcessVoiceCommandResponse(BaseModel):
    transcription: str
    lang: str = "hi"
    intent: str  # PAY_UTILITY, SEND_MONEY_P2P, CHECK_BALANCE, UNKNOWN
    entities: VoiceEntities
    fraud_check: FraudCheck
    confirmation_message: str
    audio_base64: Optional[str] = None
    requires_confirmation: bool = False
    transaction_token: Optional[str] = None
    state: str = "IDLE"  # IDLE, CONFIRMATION, FRAUD_ALERT, SUCCESS, FAILED

