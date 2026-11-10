# सारथी पे (Sarthi Pay)

> **आसान और सुरक्षित आवाज़ी बैंकिंग** — Accessible, Voice-First Banking & Utility Payment Assistant for Senior Citizens in India.

Built with **Gnani.ai Speech Engines (Streaming STT & Timbre v3.0 Expressive Indic TTS)**, **Indic LLM (Evon v3.3)**, **FastAPI**, and **Next.js**.

---

## 🌟 Key Features

1. **Multilingual Vernacular Support (Indic + English):**
   - Seamless one-tap language switching for **Hindi (`hi` - हिंदी)**, **English (`en`)**, **Marathi (`mr` - मराठी)**, and **Bengali (`bn` - বাংলা)**.
   - Dynamic localization of all speech recognition prompts, spoken audio synthesis, safety warnings, and UI components.
   - Language preferences persisted in SQLite per user account.

2. **Elderly-First Accessibility (Design & UX):**
   - **Central Voice Orb (160px diameter):** High-visibility pulsing button reacting to mic input and state transitions.
   - **Large Typography & High Contrast:** Base font $\ge$ 20px, high-contrast dark charcoal on warm ivory (`#FAF7F2`), zero advertising clutter.
   - **Zero Ambiguity:** One primary action per stage, with a persistent emergency abort button (*रद्द करें*).

2. **Proactive Scam & Fraud Guardrails:**
   - Real-time detection of urgency keywords (*"तुरंत भेजो"*, *"खाता बंद हो जाएगा"*), bank impersonation (*"बैंक मैनेजर"*), and lottery scams.
   - Automatically intercepts and blocks unauthorized payment drafts with an urgent spoken warning and high-contrast alert card.
   - Two-step explicit confirmation before any fund movement.

3. **Core Financial Workflows:**
   - **Utility Bill Fetch & Pay:** Spoken bill retrieval (e.g., Mahavitaran Electricity, Gas, Water) and verbal confirmation.
   - **Account Balance Inquiry:** Instant spoken account balance read-out.
   - **P2P Transfers:** Transfer to saved family contacts (e.g., Suresh) with unverified contact safety checks.

---

## 🛠️ Project Structure

```
gnani_ai/
├── backend/
│   ├── app/
│   │   ├── api/v1/routes.py       # API Endpoints (voice commands, confirm, balance)
│   │   ├── core/config.py         # App settings & API keys
│   │   ├── models/database.py     # SQLite async ledger & seed accounts
│   │   ├── schemas/               # Pydantic v2 schemas
│   │   └── services/
│   │       ├── gnani_stt.py       # Gnani.ai Streaming STT connector
│   │       ├── gnani_tts.py       # Gnani Timbre v3.0 Expressive TTS
│   │       ├── evon_llm.py        # Evon v3.3 reasoning & scam interceptor
│   │       └── banking.py         # Mock BBPS & Core Banking engine
│   ├── tests/test_api.py          # Pytest automated test suite
│   ├── test_voice_loop.py         # Phase 1 CLI benchmark script (5 test cases)
│   ├── requirements.txt           # Python dependencies
│   └── .env.example               # Environment variables
├── frontend/
│   ├── app/
│   │   ├── page.tsx               # Accessible Senior-Friendly Voice UI
│   │   ├── layout.tsx             # Root layout & accessibility metadata
│   │   └── globals.css            # High-contrast palette & animations
│   └── package.json               # Next.js 16 + React 19 + Tailwind CSS
└── sarthi_pay_project_files/       # Project specifications, PRD, TRD, Architecture
```

---

## 🚀 Running the Project

### 1. Backend (FastAPI)

```bash
# Navigate to backend directory
cd backend

# Activate Python virtual environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Run the API server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation will be available at: `http://localhost:8000/docs`

### 2. Frontend (Next.js)

```bash
# Navigate to frontend directory
cd frontend

# Start development server
pnpm dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🧪 Running Tests & Phase 1 Validation

### Run the Phase 1 CLI Benchmark Loop
```bash
python backend/test_voice_loop.py
```
This runs all 5 benchmark test cases:
1. Standard Utility Bill Payment (`PAY_UTILITY` $\rightarrow$ LOW risk)
2. Account Balance Inquiry (`CHECK_BALANCE` $\rightarrow$ LOW risk)
3. Adversarial Test: Bank Manager Impersonation Scam (`SEND_MONEY_P2P` $\rightarrow$ **HIGH risk / BLOCKED**)
4. P2P Transfer to Saved Contact (`SEND_MONEY_P2P` $\rightarrow$ LOW risk)
5. Adversarial Test: Lottery / Prize Scam (`SEND_MONEY_P2P` $\rightarrow$ **HIGH risk / BLOCKED**)

### Run Pytest Test Suite
```bash
pytest -c backend/pytest.ini backend/tests
```

"# Sarthi-Pay" 
