import datetime
from typing import AsyncGenerator
from sqlalchemy import (
    Column,
    String,
    Float,
    DateTime,
    ForeignKey,
    Boolean,
    text,
)
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import declarative_base, relationship
from app.core.config import settings

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    phone_number = Column(String, unique=True, nullable=False)
    preferred_lang = Column(String, default="hi")
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")
    billers = relationship("SavedBiller", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    contacts = relationship("SavedContact", back_populates="user", cascade="all, delete-orphan")


class Account(Base):
    __tablename__ = "accounts"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    bank_name = Column(String, nullable=False)
    account_number_mask = Column(String, nullable=False)
    balance = Column(Float, nullable=False, default=0.0)
    upi_id = Column(String, unique=True, nullable=True)

    user = relationship("User", back_populates="accounts")


class SavedBiller(Base):
    __tablename__ = "saved_billers"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    category = Column(String, nullable=False)  # ELECTRICITY, GAS, WATER, MOBILE
    biller_name = Column(String, nullable=False)  # e.g. Mahavitaran, Adani Gas
    consumer_number = Column(String, nullable=False)
    last_bill_amount = Column(Float, nullable=True, default=0.0)

    user = relationship("User", back_populates="billers")


class SavedContact(Base):
    __tablename__ = "saved_contacts"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)  # e.g., Suresh, Ramesh son
    phone_number = Column(String, nullable=False)
    upi_id = Column(String, nullable=True)
    is_trusted = Column(Boolean, default=True)

    user = relationship("User", back_populates="contacts")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    recipient_name = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    intent_type = Column(String, nullable=False)  # PAY_UTILITY, SEND_MONEY_P2P, CHECK_BALANCE
    fraud_risk_level = Column(String, nullable=False, default="LOW")  # LOW, MEDIUM, HIGH
    status = Column(String, nullable=False, default="DRAFT")  # DRAFT, CONFIRMED, FAILED, BLOCKED
    reference_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    user = relationship("User", back_populates="transactions")


# Engine & Session Setup
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed initial test data (Ramesh Uncle - usr_9921)
    async with AsyncSessionLocal() as session:
        existing_user = await session.get(User, "usr_9921")
        if not existing_user:
            user = User(
                id="usr_9921",
                full_name="Ramesh Sharma",
                phone_number="+919820011223",
                preferred_lang="hi"
            )
            session.add(user)

            account = Account(
                id="acc_01",
                user_id="usr_9921",
                bank_name="State Bank of India",
                account_number_mask="******3412",
                balance=24850.50,
                upi_id="ramesh@sbi"
            )
            session.add(account)

            biller = SavedBiller(
                id="bil_01",
                user_id="usr_9921",
                category="ELECTRICITY",
                biller_name="Mahavitaran",
                consumer_number="049012345678",
                last_bill_amount=1240.00
            )
            session.add(biller)

            biller_gas = SavedBiller(
                id="bil_02",
                user_id="usr_9921",
                category="GAS",
                biller_name="Adani Gas",
                consumer_number="89102456",
                last_bill_amount=680.00
            )
            session.add(biller_gas)

            biller_water = SavedBiller(
                id="bil_03",
                user_id="usr_9921",
                category="WATER",
                biller_name="Municipal Water Board",
                consumer_number="WTR-98214",
                last_bill_amount=350.00
            )
            session.add(biller_water)

            contact = SavedContact(
                id="con_01",
                user_id="usr_9921",
                name="Suresh",
                phone_number="+919820055443",
                upi_id="suresh@oksbi",
                is_trusted=True
            )
            session.add(contact)

            # Seed a sample historical transaction for Ramesh Uncle
            past_tx = Transaction(
                id="txn_past_001",
                user_id="usr_9921",
                recipient_name="Mahavitaran",
                amount=1180.00,
                intent_type="PAY_UTILITY",
                fraud_risk_level="LOW",
                status="CONFIRMED",
                reference_id="UPI/20261015/849201124"
            )
            session.add(past_tx)

            await session.commit()
