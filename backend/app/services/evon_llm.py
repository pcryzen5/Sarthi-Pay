import re
import json
import logging
from typing import Dict, Any, List, Optional
import httpx
from app.core.config import settings
from app.schemas.voice import VoiceEntities, FraudCheck

logger = logging.getLogger(__name__)

# Multilingual scam keywords
SCAM_URGENCY_KEYWORDS = [
    # Hindi
    "तुरंत", "जल्दी", "अभी", "खाता बंद", "खाता ब्लॉक", "खाता सीज", "अकाउंट ब्लॉक", "बिजली कट",
    # English
    "immediately", "urgent", "account blocked", "account suspended", "cutoff", "hurry", "expire today",
    # Marathi
    "ताबडतोब", "लगेच", "आत्ता", "खाते बंद", "खाते ब्लॉक", "वीज खंडित",
    # Bengali
    "অবিলম্বে", "জরুরি", "তাড়াতাড়ি", "অ্যাকাউন্ট বন্ধ", "অ্যাকাউন্ট ব্লক", "লাইন কাটা"
]

SCAM_IMPERSONATION_KEYWORDS = [
    # Hindi
    "बैंक अधिकारी", "बैंक मैनेजर", "आरबीआई", "कस्टमर केयर", "kyc अपडेट", "केवाईसी",
    # English
    "bank manager", "bank officer", "rbi", "kyc", "customer care", "police",
    # Marathi
    "बँक अधिकारी", "बँक मॅनेजर", "केवायसी", "कस्टमर केअर",
    # Bengali
    "ব্যাঙ্ক ম্যানেজার", "ব্যাঙ্ক অফিসার", "কেওয়াইসি", "কাস্টমার কেয়ার"
]

SCAM_LOTTERY_KEYWORDS = [
    # Hindi
    "लॉटरी", "लोटरी", "इनाम", "टैक्स भरने", "प्राइज", "कैशबैक", "विजेता",
    # English
    "lottery", "prize", "winner", "cashback", "lucky draw", "reward money",
    # Marathi
    "लॉटरी", "बक्षीस", "प्रायझ", "कॅशबॅक", "विजेता",
    # Bengali
    "লটারি", "পুরস্কার", "প্রাইজ", "ক্যাশব্যাক", "বিজয়ী"
]

MESSAGES = {
    "hi": {
        "balance": "आपके बैंक खाते में वर्तमान शेष राशि ₹{balance:,.2f} है।",
        "bill_confirm": "आपके {biller} बिजली बिल के ₹{amount:,.2f} बाकी हैं। क्या मैं इसे भर दूं? बोलिए 'हाँ' या 'ना'।",
        "p2p_confirm": "{recipient} को ₹{amount:,.2f} भेजने के लिए पुष्टि करें। क्या मैं पैसे भेज दूं?",
        "fraud_lead": "रुकिए! {reason} कृपया किसी पारिवारिक सदस्य से बात करें और कोई पैसा न भेजें।",
        "fraud_impersonation": "बैंक या अधिकारी कभी व्यक्तिगत नंबर पर तुरंत पैसे भेजने का दबाव नहीं बनाते। यह धोखाधड़ी (Scam) हो सकती है।",
        "fraud_lottery": "लॉटरी या इनाम का झांसा देकर पैसे मांगना धोखाधड़ी (Fraud) है।",
        "fraud_unknown": "अपरिचित नंबर पर तुरंत पैसे भेजने की मांग संदिग्ध है।",
        "unknown_contact": "यह नंबर आपकी संपर्क सूची में नहीं है।",
        "cancel": "भुगतान रद्द कर दिया गया।",
        "success": "₹{amount:,.2f} का भुगतान सफल रहा।",
        "unknown": "माफ़ कीजिए, मैं समझ नहीं पाया। आप बिजली बिल भरने, पैसे भेजने या बैलेंस जानने के लिए बोल सकते हैं。"
    },
    "en": {
        "balance": "The current available balance in your bank account is ₹{balance:,.2f}.",
        "bill_confirm": "Your {biller} electricity bill of ₹{amount:,.2f} is due. Shall I pay it? Say 'Yes' or 'No'.",
        "p2p_confirm": "Please confirm transferring ₹{amount:,.2f} to {recipient}. Shall I proceed?",
        "fraud_lead": "Wait! {reason} Please consult a trusted family member and do not transfer money.",
        "fraud_impersonation": "Banks and officials never ask for immediate transfers to personal numbers. This appears to be a scam.",
        "fraud_lottery": "Demanding advance fees or taxes for lottery winnings is a known fraud tactic.",
        "fraud_unknown": "Urgent transfer requests to unrecognized numbers are suspicious.",
        "unknown_contact": "This number is not in your trusted contacts.",
        "cancel": "Payment has been cancelled.",
        "success": "Payment of ₹{amount:,.2f} was successful.",
        "unknown": "I am sorry, I did not catch that. You can say 'pay electricity bill', 'check balance', or 'send money'."
    },
    "mr": {
        "balance": "तुमच्या बँक खात्यात सध्या ₹{balance:,.2f} शिल्लक आहेत.",
        "bill_confirm": "तुमचे {biller} वीज बिल ₹{amount:,.2f} भरायचे बाकी आहे. मी भरू का? 'हो' किंवा 'नाही' बोला.",
        "p2p_confirm": "{recipient} ला ₹{amount:,.2f} पाठवण्यासाठी पुष्टी करा. मी पैसे पाठवू का?",
        "fraud_lead": "थांबा! {reason} कृपया कुटुंबातील सदस्याशी बोला आणि पैसे पाठवू नका.",
        "fraud_impersonation": "बँक किंवा अधिकारी वैयक्तिक नंबरवर पैसे पाठवण्यास सांगत नाहीत. ही फसवणूक (Scam) असू शकते.",
        "fraud_lottery": "लॉटरी किंवा बक्षीसाच्या नावाखाली पैसे मागणे फसवणूक आहे.",
        "fraud_unknown": "अनोळखी नंबरवर तातडीने पैसे पाठवण्याची मागणी संशयास्पद आहे.",
        "unknown_contact": "हा नंबर तुमच्या संपर्क यादीत नाही.",
        "cancel": "पेमेंट रद्द केले आहे.",
        "success": "₹{amount:,.2f} चे पेमेंट यशस्वी झाले.",
        "unknown": "माफ करा, मला समजले नाही. तुम्ही वीज बिल भरण्यासाठी, पैसे पाठवण्यासाठी किंवा शिल्लक तपासण्यासाठी बोलू शकता."
    },
    "bn": {
        "balance": "আপনার ব্যাঙ্ক অ্যাকাউন্টে বর্তমান ব্যালেন্স ₹{balance:,.2f}।",
        "bill_confirm": "আপনার {biller} বিদ্যুৎ বিলের ₹{amount:,.2f} বকেয়া আছে। আমি কি এটি পরিশোধ করব? 'হ্যাঁ' অথবা 'না' বলুন।",
        "p2p_confirm": "{recipient}-কে ₹{amount:,.2f} পাঠানোর জন্য নিশ্চিত করুন। আমি কি টাকা পাঠাব?",
        "fraud_lead": "থামুন! {reason} অনুগ্রহ করে পরিবারের কোনো সদস্যের সাথে কথা বলুন এবং টাকা পাঠাবেন না।",
        "fraud_impersonation": "ব্যাঙ্ক বা আধিকারিকরা কখনো ব্যক্তিগত নম্বরে দ্রুত টাকা পাঠাতে বলেন না। এটি একটি প্রতারণা (Scam) হতে পারে।",
        "fraud_lottery": "লটারি বা পুরস্কারের নামে অগ্রিম ফি চাওয়া প্রতারণা।",
        "fraud_unknown": "অচেনা নম্বরে জরুরি ভিত্তিতে টাকা পাঠানোর অনুরোধ সন্দেহজনক।",
        "unknown_contact": "এই নম্বরটি আপনার পরিচিত তালিকায় নেই।",
        "cancel": "পেমেন্ট বাতিল করা হয়েছে।",
        "success": "₹{amount:,.2f} পেমেন্ট সফল হয়েছে।",
        "unknown": "দুঃখিত, আমি বুঝতে পারিনি। আপনি বিদ্যুৎ বিল দিতে, টাকা পাঠাতে বা ব্যালেন্স জানতে বলতে পারেন।"
    }
}


class EvonReasoningEngine:
    def __init__(self):
        self.api_key = settings.HUGGINGFACE_API_KEY
        self.api_url = settings.EVON_API_URL

    async def analyze_intent_and_safety(
        self,
        transcript: str,
        lang: str = "hi",
        saved_contacts: List[str] = None
    ) -> Dict[str, Any]:
        """Analyzes transcribed Indic/English speech for intent, entities, and scam risk."""
        lang_code = lang if lang in MESSAGES else "hi"
        msgs = MESSAGES[lang_code]
        transcript_clean = transcript.strip().lower()
        saved_contacts = saved_contacts or ["suresh", "सुरेश", "सुरेश", "সুরেশ", "ramesh", "रमेश", "রমেশ"]

        # 1. Proactive Scam Guardrail Interceptor
        fraud_check = self._evaluate_fraud_risk(transcript_clean, saved_contacts, lang_code)

        # 2. Extract Intent & Entities
        intent_data = await self._extract_intent_and_entities(transcript, lang_code)

        # If fraud check detected high risk, override intent state
        if fraud_check.is_flagged:
            intent_data["fraud_check"] = fraud_check
            intent_data["requires_confirmation"] = False
            intent_data["confirmation_message"] = msgs["fraud_lead"].format(reason=fraud_check.reason)
            intent_data["state"] = "FRAUD_ALERT"
            return intent_data

        intent_data["fraud_check"] = fraud_check
        return intent_data

    def _evaluate_fraud_risk(self, text: str, saved_contacts: List[str], lang_code: str) -> FraudCheck:
        """Evaluates fraud risk according to SECURITY.md specification across languages."""
        msgs = MESSAGES.get(lang_code, MESSAGES["hi"])

        has_urgency = any(kw in text for kw in SCAM_URGENCY_KEYWORDS)
        has_impersonation = any(kw in text for kw in SCAM_IMPERSONATION_KEYWORDS)
        has_lottery = any(kw in text for kw in SCAM_LOTTERY_KEYWORDS)

        phone_match = re.search(r"\b[6-9]\d{9}\b", text) or re.search(r"\b98\d{8}\b", text)
        is_unknown_number = False
        if phone_match:
            number = phone_match.group(0)
            if number not in saved_contacts:
                is_unknown_number = True

        if has_impersonation and has_urgency:
            return FraudCheck(
                is_flagged=True,
                risk_level="HIGH",
                reason=msgs["fraud_impersonation"]
            )

        if has_lottery:
            return FraudCheck(
                is_flagged=True,
                risk_level="HIGH",
                reason=msgs["fraud_lottery"]
            )

        if has_urgency and is_unknown_number:
            return FraudCheck(
                is_flagged=True,
                risk_level="HIGH",
                reason=msgs["fraud_unknown"]
            )

        if is_unknown_number:
            return FraudCheck(
                is_flagged=False,
                risk_level="MEDIUM",
                reason=msgs["unknown_contact"]
            )

        return FraudCheck(is_flagged=False, risk_level="LOW", reason=None)

    async def _extract_intent_and_entities(self, text: str, lang_code: str) -> Dict[str, Any]:
        """Extracts financial intent and entities for Hindi, English, Marathi, Bengali."""
        msgs = MESSAGES.get(lang_code, MESSAGES["hi"])
        lower = text.lower()

        # Check Balance Intent Keywords across languages
        balance_kws = [
            "बैलेंस", "balance", "कितना पैसा", "खाते में", "kitna balance",
            "check balance", "how much money", "account balance",
            "शिल्लक", "किती पैसे", "खात्यात", "बॅलन्स",
            "ব্যালেন্স", "কত টাকা", "অ্যাকাউন্টে"
        ]
        if any(w in lower for w in balance_kws):
            return {
                "intent": "CHECK_BALANCE",
                "entities": VoiceEntities(),
                "requires_confirmation": False,
                "confirmation_message": msgs["balance"].format(balance=24850.50),
                "state": "SPEAKING"
            }

        # Utility Payment Intent Keywords
        utility_kws = [
            "बिजली", "बिल", "bill", "mahavitaran", "महावितरण", "light bill", "electricity", "पानी", "गैस",
            "pay bill", "water", "gas",
            "वीज", "लाईट बिल", "महावितरणचे", "पाणी", "गॅस",
            "বিদ্যুৎ", "কারেন্ট", "বিল", "ইলেকট্রিসিটি", "জল", "গ্যাস"
        ]
        if any(w in lower for w in utility_kws):
            utility_type = "ELECTRICITY"
            biller_name = "Mahavitaran"
            amount = 1240.00

            if any(w in lower for w in ["गैस", "gas", "गॅस", "গ্যাস", "adani"]):
                utility_type = "GAS"
                biller_name = "Adani Gas"
                amount = 680.00
            elif any(w in lower for w in ["पानी", "water", "पाणी", "জল", "water board"]):
                utility_type = "WATER"
                biller_name = "Municipal Water Board"
                amount = 350.00

            amt_match = re.search(r"(\d+)\s*(रुपये|rupees|rs|₹|টাকা)?", text)
            if amt_match:
                try:
                    val = float(amt_match.group(1))
                    if val > 50:
                        amount = val
                except ValueError:
                    pass

            return {
                "intent": "PAY_UTILITY",
                "entities": VoiceEntities(
                    utility_type=utility_type,
                    biller_name=biller_name,
                    amount=amount
                ),
                "requires_confirmation": True,
                "confirmation_message": msgs["bill_confirm"].format(biller=biller_name, amount=amount),
                "state": "CONFIRMATION"
            }

        # P2P Transfer Intent Keywords
        p2p_kws = [
            "भेजो", "send", "डाल दो", "ट्रांसफर", "रुपये", "pay",
            "transfer", "send money",
            "पाठवा", "पैसे पाठव", "द्या",
            "পাঠাও", "পাঠিয়ে দাও", "টাকা পাঠাও"
        ]
        if any(w in lower for w in p2p_kws):
            recipient = "Suresh"
            amount = 200.00

            amt_match = re.search(r"(\d+)\s*(रुपये|rupees|rs|₹|টাকা)?", text)
            if amt_match:
                try:
                    amount = float(amt_match.group(1))
                except ValueError:
                    pass

            if any(name in text or name in lower for name in ["सुरेश", "suresh", "সুরেশ"]):
                recipient = "Suresh"
            elif any(name in text or name in lower for name in ["रमेश", "ramesh", "রমেশ"]):
                recipient = "Ramesh"

            return {
                "intent": "SEND_MONEY_P2P",
                "entities": VoiceEntities(
                    recipient_name=recipient,
                    amount=amount
                ),
                "requires_confirmation": True,
                "confirmation_message": msgs["p2p_confirm"].format(recipient=recipient, amount=amount),
                "state": "CONFIRMATION"
            }

        # Default / Fallback
        return {
            "intent": "UNKNOWN",
            "entities": VoiceEntities(),
            "requires_confirmation": False,
            "confirmation_message": msgs["unknown"],
            "state": "IDLE"
        }

    def get_localized_message(self, key: str, lang_code: str, **kwargs) -> str:
        """Helper to get a localized string for transactions and receipts."""
        lang = lang_code if lang_code in MESSAGES else "hi"
        template = MESSAGES[lang].get(key, MESSAGES["hi"].get(key, ""))
        return template.format(**kwargs) if kwargs else template


evon_engine = EvonReasoningEngine()
