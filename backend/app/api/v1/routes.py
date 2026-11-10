import base64
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.models.database import get_db, Transaction, SavedBiller, User
from app.schemas.voice import (
    ProcessVoiceCommandRequest,
    ProcessVoiceCommandResponse,
    VoiceEntities,
    FraudCheck
)
from app.schemas.transaction import (
    TransactionConfirmRequest,
    TransactionConfirmResponse,
    AccountBalanceResponse,
    AccountDetails
)
from app.services.gnani_stt import gnani_stt
from app.services.gnani_tts import gnani_tts
from app.services.evon_llm import evon_engine
from app.services.banking import banking_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1")


class UpdateLanguageRequest(BaseModel):
    preferred_lang: str  # hi, en, mr, bn


@router.post("/voice/process-command", response_model=ProcessVoiceCommandResponse)
async def process_voice_command(
    session_id: Optional[str] = Form("sess_default"),
    user_id: str = Form("usr_9921"),
    lang: Optional[str] = Form("hi"),
    audio: Optional[UploadFile] = File(None),
    text_override: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """Processes incoming spoken Hindi/vernacular audio or text command in specified language."""
    active_lang = lang if lang in ["hi", "en", "mr", "bn"] else "hi"
    transcript = ""

    # Priority 1: Direct text override (for testing or keyboard fallback)
    if text_override and text_override.strip():
        transcript = text_override.strip()
    elif audio:
        audio_bytes = await audio.read()
        transcript = await gnani_stt.transcribe(audio_bytes, lang=active_lang)
    else:
        # Default fallback for testing
        from app.services.gnani_stt import DEFAULT_TRANSCRIPTS
        transcript = DEFAULT_TRANSCRIPTS.get(active_lang, DEFAULT_TRANSCRIPTS["hi"])

    # Analyze intent and scam indicators with Evon v3.3
    analysis = await evon_engine.analyze_intent_and_safety(transcript, lang=active_lang)

    intent = analysis.get("intent", "UNKNOWN")
    entities_dict = analysis.get("entities")
    entities = entities_dict if isinstance(entities_dict, VoiceEntities) else VoiceEntities(**entities_dict)
    fraud_check = analysis.get("fraud_check", FraudCheck())
    confirmation_message = analysis.get("confirmation_message", "")
    requires_confirmation = analysis.get("requires_confirmation", False)
    state = analysis.get("state", "IDLE")

    transaction_token = None

    # If it is a valid utility payment or P2P transfer requiring confirmation
    if requires_confirmation and not fraud_check.is_flagged:
        recipient = entities.biller_name or entities.recipient_name or "Unknown"
        amount = entities.amount or 0.0

        tx = await banking_service.create_draft_transaction(
            db=db,
            user_id=user_id,
            recipient_name=recipient,
            amount=amount,
            intent_type=intent,
            fraud_risk_level=fraud_check.risk_level
        )
        transaction_token = tx.id

    # Synthesize vernacular spoken feedback via Gnani Timbre v3.0 in active language
    audio_base64 = await gnani_tts.synthesize(confirmation_message, lang=active_lang)

    return ProcessVoiceCommandResponse(
        transcription=transcript,
        lang=active_lang,
        intent=intent,
        entities=entities,
        fraud_check=fraud_check,
        confirmation_message=confirmation_message,
        audio_base64=audio_base64,
        requires_confirmation=requires_confirmation,
        transaction_token=transaction_token,
        state=state
    )


@router.post("/voice/process-command-json", response_model=ProcessVoiceCommandResponse)
async def process_voice_command_json(
    payload: ProcessVoiceCommandRequest,
    db: AsyncSession = Depends(get_db)
):
    """JSON variant of voice command processing with language support."""
    active_lang = payload.lang if payload.lang in ["hi", "en", "mr", "bn"] else "hi"
    transcript = ""

    if payload.text_override and payload.text_override.strip():
        transcript = payload.text_override.strip()
    elif payload.audio_base64:
        try:
            audio_bytes = base64.b64decode(payload.audio_base64)
            transcript = await gnani_stt.transcribe(audio_bytes, lang=active_lang)
        except Exception:
            from app.services.gnani_stt import DEFAULT_TRANSCRIPTS
            transcript = DEFAULT_TRANSCRIPTS.get(active_lang, DEFAULT_TRANSCRIPTS["hi"])
    else:
        from app.services.gnani_stt import DEFAULT_TRANSCRIPTS
        transcript = DEFAULT_TRANSCRIPTS.get(active_lang, DEFAULT_TRANSCRIPTS["hi"])

    analysis = await evon_engine.analyze_intent_and_safety(transcript, lang=active_lang)
    intent = analysis.get("intent", "UNKNOWN")
    entities_dict = analysis.get("entities")
    entities = entities_dict if isinstance(entities_dict, VoiceEntities) else VoiceEntities(**entities_dict)
    fraud_check = analysis.get("fraud_check", FraudCheck())
    confirmation_message = analysis.get("confirmation_message", "")
    requires_confirmation = analysis.get("requires_confirmation", False)
    state = analysis.get("state", "IDLE")

    transaction_token = None
    if requires_confirmation and not fraud_check.is_flagged:
        recipient = entities.biller_name or entities.recipient_name or "Unknown"
        amount = entities.amount or 0.0

        tx = await banking_service.create_draft_transaction(
            db=db,
            user_id=payload.user_id,
            recipient_name=recipient,
            amount=amount,
            intent_type=intent,
            fraud_risk_level=fraud_check.risk_level
        )
        transaction_token = tx.id

    audio_base64 = await gnani_tts.synthesize(confirmation_message, lang=active_lang)

    return ProcessVoiceCommandResponse(
        transcription=transcript,
        lang=active_lang,
        intent=intent,
        entities=entities,
        fraud_check=fraud_check,
        confirmation_message=confirmation_message,
        audio_base64=audio_base64,
        requires_confirmation=requires_confirmation,
        transaction_token=transaction_token,
        state=state
    )


@router.post("/transaction/confirm", response_model=TransactionConfirmResponse)
async def confirm_transaction(
    payload: TransactionConfirmRequest,
    db: AsyncSession = Depends(get_db)
):
    """Confirms and settles a drafted transaction token in active language."""
    active_lang = payload.lang if payload.lang in ["hi", "en", "mr", "bn"] else "hi"
    res = await banking_service.confirm_transaction(
        db=db,
        token=payload.transaction_token,
        confirmation=payload.user_confirmation,
        auth_method=payload.auth_method or "BIOMETRIC_PASS",
        lang=active_lang
    )

    audio_base64 = await gnani_tts.synthesize(res["receipt_message"], lang=active_lang)

    return TransactionConfirmResponse(
        status=res["status"],
        reference_id=res["reference_id"],
        receipt_message=res["receipt_message"],
        audio_base64=audio_base64
    )


@router.put("/account/{user_id}/language")
async def update_user_language(
    user_id: str,
    payload: UpdateLanguageRequest,
    db: AsyncSession = Depends(get_db)
):
    """Updates user's preferred language."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    user.preferred_lang = payload.preferred_lang
    await db.commit()
    return {"status": "SUCCESS", "user_id": user_id, "preferred_lang": user.preferred_lang}


@router.get("/account/{user_id}/balance", response_model=AccountBalanceResponse)
async def get_account_balance(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Fetches user balance and primary linked account."""
    acc = await banking_service.get_user_balance(db, user_id)
    if not acc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} account not found"
        )

    return AccountBalanceResponse(
        user_id=user_id,
        primary_account=AccountDetails(
            bank_name=acc["bank_name"],
            account_mask=acc["account_mask"],
            balance=acc["balance"],
            upi_id=acc["upi_id"]
        )
    )


@router.get("/account/{user_id}/billers")
async def get_user_billers(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Fetches list of registered utilities and last bill amounts."""
    result = await db.execute(
        select(SavedBiller).where(SavedBiller.user_id == user_id)
    )
    billers = result.scalars().all()
    return [
        {
            "id": b.id,
            "category": b.category,
            "biller_name": b.biller_name,
            "consumer_number": b.consumer_number,
            "last_bill_amount": b.last_bill_amount
        }
        for b in billers
    ]


@router.get("/account/{user_id}/transactions")
async def get_user_transactions(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Fetches transaction history."""
    result = await db.execute(
        select(Transaction).where(Transaction.user_id == user_id).order_by(Transaction.created_at.desc())
    )
    txs = result.scalars().all()
    return [
        {
            "id": t.id,
            "recipient_name": t.recipient_name,
            "amount": t.amount,
            "intent_type": t.intent_type,
            "fraud_risk_level": t.fraud_risk_level,
            "status": t.status,
            "reference_id": t.reference_id,
            "created_at": t.created_at.isoformat() if t.created_at else None
        }
        for t in txs
    ]
