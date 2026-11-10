from typing import Optional, Dict, Any
from pydantic import BaseModel


class TransactionConfirmRequest(BaseModel):
    transaction_token: str
    user_confirmation: str  # CONFIRMED or CANCELLED
    lang: Optional[str] = "hi"  # hi, en, mr, bn
    auth_method: Optional[str] = "BIOMETRIC_PASS"  # BIOMETRIC_PASS, PIN


class TransactionConfirmResponse(BaseModel):
    status: str  # SUCCESS, CANCELLED, FAILED, BLOCKED
    reference_id: Optional[str] = None
    receipt_message: str
    audio_base64: Optional[str] = None


class AccountDetails(BaseModel):
    bank_name: str
    account_mask: str
    balance: float
    upi_id: Optional[str] = None


class AccountBalanceResponse(BaseModel):
    user_id: str
    primary_account: AccountDetails

