import uuid
import datetime
from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.database import User, Account, SavedBiller, Transaction, SavedContact
from app.services.evon_llm import evon_engine


class MockBankingService:
    @staticmethod
    async def get_user_balance(db: AsyncSession, user_id: str) -> Optional[Dict[str, Any]]:
        result = await db.execute(
            select(Account).where(Account.user_id == user_id)
        )
        account = result.scalars().first()
        if not account:
            return None

        return {
            "bank_name": account.bank_name,
            "account_mask": account.account_number_mask,
            "balance": account.balance,
            "upi_id": account.upi_id
        }

    @staticmethod
    async def get_bill_due(db: AsyncSession, user_id: str, category: str = "ELECTRICITY") -> Optional[SavedBiller]:
        result = await db.execute(
            select(SavedBiller).where(
                SavedBiller.user_id == user_id,
                SavedBiller.category == category
            )
        )
        return result.scalars().first()

    @staticmethod
    async def create_draft_transaction(
        db: AsyncSession,
        user_id: str,
        recipient_name: str,
        amount: float,
        intent_type: str,
        fraud_risk_level: str = "LOW"
    ) -> Transaction:
        token = f"txn_draft_{uuid.uuid4().hex[:8]}"
        tx = Transaction(
            id=token,
            user_id=user_id,
            recipient_name=recipient_name,
            amount=amount,
            intent_type=intent_type,
            fraud_risk_level=fraud_risk_level,
            status="DRAFT"
        )
        db.add(tx)
        await db.commit()
        await db.refresh(tx)
        return tx

    @staticmethod
    async def confirm_transaction(
        db: AsyncSession,
        token: str,
        confirmation: str,
        auth_method: str = "BIOMETRIC_PASS",
        lang: str = "hi"
    ) -> Dict[str, Any]:
        result = await db.execute(
            select(Transaction).where(Transaction.id == token)
        )
        tx = result.scalars().first()
        if not tx:
            return {
                "status": "FAILED",
                "receipt_message": evon_engine.get_localized_message("unknown", lang),
                "reference_id": None
            }

        if confirmation.upper() != "CONFIRMED":
            tx.status = "CANCELLED"
            await db.commit()
            return {
                "status": "CANCELLED",
                "receipt_message": evon_engine.get_localized_message("cancel", lang),
                "reference_id": None
            }

        # Deduct balance from primary account
        acc_result = await db.execute(
            select(Account).where(Account.user_id == tx.user_id)
        )
        account = acc_result.scalars().first()
        if account:
            if account.balance >= tx.amount:
                account.balance -= tx.amount
            else:
                tx.status = "FAILED"
                await db.commit()
                return {
                    "status": "FAILED",
                    "receipt_message": "Insufficient funds / खाते में पर्याप्त शेष राशि नहीं है।",
                    "reference_id": None
                }

        today_str = datetime.date.today().strftime("%Y%m%d")
        ref_id = f"UPI/{today_str}/{uuid.uuid4().int % 1000000000:09d}"

        tx.status = "CONFIRMED"
        tx.reference_id = ref_id
        await db.commit()

        receipt_msg = evon_engine.get_localized_message("success", lang, amount=tx.amount)

        return {
            "status": "SUCCESS",
            "receipt_message": receipt_msg,
            "reference_id": ref_id
        }


banking_service = MockBankingService()

