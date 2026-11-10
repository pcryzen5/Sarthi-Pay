import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.models.database import init_db


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    await init_db()


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "Evon v3.3" in data["indic_llm"]


@pytest.mark.asyncio
async def test_get_account_balance():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/account/usr_9921/balance")
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "usr_9921"
        assert data["primary_account"]["bank_name"] == "State Bank of India"
        assert data["primary_account"]["balance"] > 0


@pytest.mark.asyncio
async def test_process_voice_command_utility():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/voice/process-command",
            data={
                "user_id": "usr_9921",
                "session_id": "sess_test",
                "lang": "hi",
                "text_override": "बिजली का बिल भर देना महावितरण वाला"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "PAY_UTILITY"
        assert data["entities"]["biller_name"] == "Mahavitaran"
        assert data["fraud_check"]["risk_level"] == "LOW"
        assert data["requires_confirmation"] is True
        assert data["transaction_token"] is not None
        assert data["transaction_token"].startswith("txn_draft_")


@pytest.mark.asyncio
async def test_multilingual_commands():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. English
        en_res = await client.post(
            "/api/v1/voice/process-command",
            data={
                "user_id": "usr_9921",
                "session_id": "sess_test",
                "lang": "en",
                "text_override": "Pay electricity bill"
            }
        )
        assert en_res.status_code == 200
        en_data = en_res.json()
        assert en_data["intent"] == "PAY_UTILITY"
        assert "electricity bill" in en_data["confirmation_message"].lower()

        # 2. Marathi
        mr_res = await client.post(
            "/api/v1/voice/process-command",
            data={
                "user_id": "usr_9921",
                "session_id": "sess_test",
                "lang": "mr",
                "text_override": "खात्यात किती पैसे शिल्लक आहेत"
            }
        )
        assert mr_res.status_code == 200
        mr_data = mr_res.json()
        assert mr_data["intent"] == "CHECK_BALANCE"
        assert "शिल्लक" in mr_data["confirmation_message"]

        # 3. Bengali Scam Intercept
        bn_res = await client.post(
            "/api/v1/voice/process-command",
            data={
                "user_id": "usr_9921",
                "session_id": "sess_test",
                "lang": "bn",
                "text_override": "অবিলম্বে ১০,০০০ টাকা পাঠান, ব্যাঙ্ক ম্যানেজার বলছেন"
            }
        )
        assert bn_res.status_code == 200
        bn_data = bn_res.json()
        assert bn_data["fraud_check"]["is_flagged"] is True
        assert bn_data["fraud_check"]["risk_level"] == "HIGH"
        assert "থামুন" in bn_data["confirmation_message"]


@pytest.mark.asyncio
async def test_process_voice_command_scam_intercept():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/voice/process-command",
            data={
                "user_id": "usr_9921",
                "session_id": "sess_test",
                "lang": "hi",
                "text_override": "जल्दी से 10,000 रुपये 9820055443 पर भेजो, बैंक मैनेजर का कॉल आया है"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["fraud_check"]["is_flagged"] is True
        assert data["fraud_check"]["risk_level"] == "HIGH"
        assert data["requires_confirmation"] is False
        assert data["transaction_token"] is None
        assert data["state"] == "FRAUD_ALERT"


@pytest.mark.asyncio
async def test_transaction_confirmation_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Draft transaction
        cmd_res = await client.post(
            "/api/v1/voice/process-command",
            data={
                "user_id": "usr_9921",
                "session_id": "sess_test",
                "lang": "hi",
                "text_override": "सुरेश को 200 रुपये भेज दो चाय के"
            }
        )
        draft_token = cmd_res.json()["transaction_token"]
        assert draft_token is not None

        # 2. Confirm transaction
        confirm_res = await client.post(
            "/api/v1/transaction/confirm",
            json={
                "transaction_token": draft_token,
                "user_confirmation": "CONFIRMED",
                "lang": "hi",
                "auth_method": "BIOMETRIC_PASS"
            }
        )
        assert confirm_res.status_code == 200
        confirm_data = confirm_res.json()
        assert confirm_data["status"] == "SUCCESS"
        assert confirm_data["reference_id"].startswith("UPI/")
