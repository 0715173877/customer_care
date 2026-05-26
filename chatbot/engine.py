"""
Chatbot Engine - Core AI/robot brain for Kalton Investment Money Transfer Services.
Bilingual (English & Swahili) with optional Google Gemini AI integration.
Falls back to rule-based matching when no GEMINI_API_KEY is configured.
"""

import re
import os
import random
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Swahili Responses
# ---------------------------------------------------------------------------

SWAHILI_RESPONSES = {
    'greeting': [
        "Habari! Karibu Kalton Investment - Huduma za Uhamisho wa Pesa. Nikusaidie vipi?",
        "Hujambo! Asante kwa kuchagua Kalton Investment. Je, nikusaidie?",
        "Shikamoo! Mimi ni msaidizi wako pepe katika Kalton Investment.",
    ],
    'goodbye': [
        "Asante kwa kutumia Kalton Investment! Kuwa na siku njema!",
        "Kwaheri! Tupo tayari kukusaidia wakati wowote.",
        "Kwaheri ya kuonana! Tutakusaidia saa 24/7.",
    ],
    'send_money': [
        "Ninaweza kukusaidia kutuma pesa! Tafadhali nambie jina la mpokeaji na kiasi unachotaka kutuma.",
        "Hebu nikusaidie na uhamisho wako wa pesa. Unamtuma nani na kiasi gani?",
        "Ili kuanza uhamisho, nahitaji jina kamili la mpokeaji, kiasi, na nchi inayotumwa.",
    ],
    'track_transfer': [
        "Naweza kukusaidia kufuatilia uhamisho wako! Tafadhali toa namba yako ya kumbukumbu.",
        "Wacha niangalie hali ya uhamisho wako. Una namba ya kumbukumbu?",
        "Nitaangalia hali ya uhamisho wako mara moja. Je, una namba ya kumbukumbu?",
    ],
    'exchange_rate': [
        "Naweza kukupa bei za sasa za ubadilishaji fedha! Ungependa kubadilisha fedha gani?",
        "Wacha niangalie bei za sasa za ubadilishaji. Ungependa kubadilisha sarafu gani?",
    ],
    'transfer_fees': [
        "Ada zetu za uhamisho ni wazi na zinashindana. Ada hutegemea kiasi na nchi inayotumwa.",
        "Naweza kukuelezea ada zote! Gharama inategemea kiasi na mahali unapotuma.",
    ],
    'transfer_limits': [
        "Vikomo vya uhamisho: Akaunti za kawaida hadi $1,000 kwa siku. Akaunti zilizothibitishwa hadi $10,000 kwa siku.",
        "Vikomo: Hazijathibitishwa hadi $1,000/siku. Zilizothibitishwa hadi $10,000/siku. Kiasi cha chini ni $10.",
    ],
    'recipient_info': [
        "Ili kuongeza mpokeaji, nahitaji jina lake kamili na maelezo ya akaunti ya benki au namba ya simu.",
        "Kuongeza mpokeaji ni rahisi! Utahitaji jina kamili, benki au mkoba wa simu, na nchi.",
    ],
    'account_verification': [
        "Uthibitisho husaidia kuongeza vikomo vyako. Utahitaji kitambulisho halali na uthibitisho wa anwani.",
        "Ili kuthibitisha akaunti yako, tafadhali wasilisha pasipoti/kitambulisho na bili ya umeme.",
    ],
    'complaint': [
        "Samahani sana kwa uzoefu wako. Hebu nikuunganishe na mtaalamu atakayesuluhisha hili.",
        "Samahani kusikia hayo. Nitapeleka hili kwa timu yetu ya huduma kwa wateja.",
    ],
    'hours_location': [
        "Kalton Investment inapatikana saa 24/7 mtandaoni! Msaada wa simu: Jumatatu-Ijumaa 8:00-20:00, Jumamosi 9:00-17:00.",
        "Tunafunguliwa Jumatatu-Ijumaa 8:00-20:00, Jumamosi 9:00-17:00. Tovuti: https://kalton-investment.com.",
    ],
    'feedback': [
        "Asante kwa maoni yako! Tunathamini kusikia kutoka kwa wateja wetu.",
        "Maoni yako yanatusaidia kuboresha huduma zetu. Asante!",
    ],
    'cancel_transfer': [
        "Naweza kukusaidia kughairi uhamisho. Unaweza kughairiwa tu kama haujachakatwa. Una namba ya kumbukumbu?",
        "Ili kughairi, nahitaji namba ya kumbukumbu. Uhamisho ukishakamilika hauwezi kutenguliwa.",
    ],
    'promotions': [
        "Tuna matangazo! Wateja wapya wanapata ada sifuri kwa uhamisho wa kwanza. Pia mpango wa rufaa - mwalike rafiki na nyote wawili mtapata $10!",
        "Watuma wageni wanafurahia uhamisho bila ada hadi $500. Mpango wa rufaa unakupa $10 kila mmoja!",
    ],
    'security': [
        "Usalama wako ni kipaumbele chetu. Tunatumia usimbaji fiche wa 256-bit SSL, uthibitisho wa hatua mbili, na ufuatiliaji wa ulaghai.",
        "Uhamisho wote umeimbwa na kufuatiliwa 24/7. Pia tunatoa uthibitisho wa hatua mbili kwa ulinzi wa ziada.",
    ],
    'unknown': [
        "Samahani, sikuelewa vizuri. Ninaweza kusaidia na: kutuma pesa, kufuatilia uhamisho, bei za ubadilishaji, ada, vikomo, na uthibitisho wa akaunti.",
        "Samahani, sikukamata vizuri. Jaribu kuuliza kuhusu 'tuma pesa', 'fuatilia uhamisho', 'bei za ubadilishaji', au 'ada'.",
    ],
}


# ---------------------------------------------------------------------------
# English Responses
# ---------------------------------------------------------------------------

ENGLISH_RESPONSES = {
    'greeting': [
        "Hello! Welcome to Kalton Investment Money Transfer Services. How can I assist you today?",
        "Hi there! Thank you for choosing Kalton Investment. How may I help you?",
        "Greetings! I'm your virtual assistant for Kalton Investment. What can I do for you?",
    ],
    'goodbye': [
        "Thank you for choosing Kalton Investment! Have a wonderful day!",
        "Goodbye! Feel free to reach out anytime for your money transfer needs.",
        "Take care! We're here 24/7 if you need any assistance with transfers.",
    ],
    'send_money': [
        "I'd be happy to help you send money! Please provide the recipient's name and the amount.",
        "Let me assist you with your money transfer. Could you tell me who you're sending to and how much?",
        "To start a transfer, I'll need the recipient's full name, amount, and destination country.",
    ],
    'track_transfer': [
        "I can help you track your transfer! Please provide your transaction reference number.",
        "Let me look up your transfer status. Could you share your reference number?",
        "I'll check the status right away. Do you have your reference number handy?",
    ],
    'exchange_rate': [
        "I can check our current exchange rates! Which currencies are you looking to convert?",
        "Let me get the latest rates. Which currency pair are you interested in?",
    ],
    'transfer_fees': [
        "Our transfer fees are transparent and competitive. The fee depends on the amount and destination country.",
        "I can explain our fee structure! The cost varies based on amount and where you're sending to.",
    ],
    'transfer_limits': [
        "Basic accounts: up to $1,000/day. Verified accounts: up to $10,000/day. Minimum: $10.",
        "Transfer limits: Unverified up to $1,000/day. Verified up to $10,000/day. Monthly limit: $50,000.",
    ],
    'recipient_info': [
        "To add a recipient, I'll need their full name, bank account or mobile money details, and their relationship to you.",
        "Adding a recipient is easy! You'll need their full name, bank/mobile wallet info, and country.",
    ],
    'account_verification': [
        "Verification helps increase your transfer limits and ensure security. You'll need a valid government ID and proof of address.",
        "To verify your account, please submit your passport/national ID and a utility bill or bank statement.",
    ],
    'complaint': [
        "I'm very sorry about your experience. Let me connect you with a specialist who can resolve this immediately.",
        "Sorry to hear that. I'll escalate this to our customer service team who will assist you personally.",
    ],
    'hours_location': [
        "Kalton Investment is available 24/7 online! Phone support: Mon-Fri 8AM-8PM, Sat 9AM-5PM. Visit kalton-investment.com.",
        "We're open Mon-Fri 8AM-8PM, Sat 9AM-5PM. You can send money anytime via our website.",
    ],
    'feedback': [
        "Thank you for your feedback! We at Kalton Investment value hearing from our customers.",
        "Your feedback helps us improve our services. Thank you!",
    ],
    'cancel_transfer': [
        "I can help you cancel a transfer. It can only be cancelled if not yet processed. Do you have your reference number?",
        "To cancel, I need your reference number. Once processed, transfers cannot be reversed.",
    ],
    'promotions': [
        "Exciting promos! New customers get zero fees on their first transfer. Plus our Refer-a-Friend program - both of you get $10!",
        "First-time senders enjoy fee-free transfers up to $500. Refer a friend and both get $10 each!",
    ],
    'security': [
        "Your security is our top priority. We use 256-bit SSL encryption, two-factor authentication, and fraud monitoring 24/7.",
        "All transfers are encrypted and monitored 24/7. We also offer two-factor authentication for extra protection.",
    ],
    'unknown': [
        "I didn't quite understand. I can help with: sending money, tracking transfers, exchange rates, fees, limits, and account verification.",
        "Sorry, I didn't catch that. Try asking about 'send money', 'track transfer', 'exchange rates', or 'fees'.",
    ],
}


# ---------------------------------------------------------------------------
# Intent Patterns
# ---------------------------------------------------------------------------

INTENT_PATTERNS = {
    'greeting': [
        r'\b(hi|hello|hey|good\s*(morning|afternoon|evening)|howdy|greetings)\b',
        r"\b(what'?s\s*up|sup|yo)\b",
        r'\b(habari|hujambo|jambo|shikamoo|marahaba|salama|mambo|vipi|sema)\b',
    ],
    'goodbye': [
        r'\b(bye|goodbye|see\s*you|talk\s*to\s*you\s*late?r?|have\s*a\s*great\s*day)\b',
        r"\b(end\s*chat|that'?s\s*all|i'?m\s*done)\b",
        r'\b(kwaheri|baadaye|tuonane|nimekamilisha|nimesha)\b',
    ],
    'send_money': [
        r'\b(send|transfer|remit|wire)\b.*\b(money|cash|funds|payment|remittance)\b',
        r'\b((want|like|need|would)\s*to\s*(send|transfer))\b',
        r'\b(tuma|hamisha|uhamisho)\b.*\b(pesa|fedha|hela)\b',
        r'\b(nataka\s*kutuma|naomba\s*kutuma|nahitaji\s*kutuma)\b.*\b(pesa|fedha|hela)\b',
    ],
    'track_transfer': [
        r'\b(track|trace|status|where|check)\b.*\b(transfer|transaction|payment)\b',
        r'\b(reference\s*number|tracking\s*number|transfer\s*status)\b',
        r'\b(fuatilia|angalia\s*hali|uko\s*wapi|status|tafuta)\b.*\b(transfer|uhamisho)\b',
    ],
    'exchange_rate': [
        r'\b(exchange\s*rate|conversion|forex|currency\s*rate|current\s*rate)\b',
        r'\b(how\s*much\s+is|usd\s*to\s*|eur\s*to\s*|gbp\s*to\s*)\b',
        r'\b(rates?|exchange)\b',
        r'\b(kiwango\s+cha\s+ubadilishaji|bei\s+ya\s+fedha|bei\s+za\s+fedha|bei\s+za\s+ubadilishaji)\b',
    ],
    'transfer_fees': [
        r'\b(fees?|charges?|cost|commission|service\s*charge)\b',
        r'\b(how\s*much\s*(does\s*it\s*cost|is\s*the\s*fee)|transfer\s*fee)\b',
        r'\b(ada|gharama|tozo|bei|ada\s+ya\s+uhamisho|gharama\s+ya\s+kutuma)\b',
    ],
    'transfer_limits': [
        r'\b(limit|maximum|minimum|max|min)\b',
        r'\b(how\s*much\s*can\s*i\s*send|daily\s*limit|monthly\s*limit|transfer\s*limit)\b',
        r'\b(kiwango\s+cha\s+juu|kiwango\s+cha\s+chini|naweza\s+kutuma\s+kiasi\s+gani)\b',
    ],
    'recipient_info': [
        r'\b(recipient|receiver|beneficiary|payee)\b',
        r'\b(add\s*recipient|new\s*recipient|manage\s*recipient)\b',
        r'\b(mpokeaji|mnufaika|mpokea\s+pesa|ongeza\s+mpokeaji)\b',
    ],
    'account_verification': [
        r'\b(verify|verification|kyc|identity)\b.*\b(account|id|card|passport|document)\b',
        r'\b(thibitisha|uhakiki|kitambulisho|pasipoti|hati)\b',
    ],
    'complaint': [
        r'\b(complaint|unhappy|dissatisfied|frustrated|angry|upset)\b',
        r'\b(speak\s*to\s*manager|escalate|terrible\s*service)\b',
        r'\b(malalamiko|nina\s+hasira|nina\s+shida|huduma\s+mbaya)\b',
    ],
    'hours_location': [
        r'\b(hours|open|close|location|address|office|branch|where\s+are\s+you|directions)\b',
        r'\b(saa\s+za\s+kazi|mahali|anuani|ofisi|tawi|wako\s+wapi|saa\s+gani)\b',
    ],
    'feedback': [
        r'\b(feedback|suggestion|review|rating|opinion)\b',
        r'\b(i\s+love|i\s+like|great\s+service|excellent)\b',
        r'\b(maoni|mapendekezo|tathmini|huduma\s+nzuri)\b',
    ],
    'cancel_transfer': [
        r'\b(cancel\s+transfer|stop\s+transfer|reverse|undo|cancel\s+transaction|cancel\s+payment)\b',
        r'\b(ghairi\s+uhamisho|sitisha|batilisha|ghairi|ahirisha\s+transfer)\b',
    ],
    'promotions': [
        r'\b(promo|promotion|discount|offer|bonus|coupon|referral|refer\s+a\s+friend|deals|special\s+offer)\b',
        r'\b(punguzo|ofaa|bonasi|promo|zawadi|mpango\s+maalum|mwalika\s+rafiki)\b',
    ],
    'security': [
        r'\b(security|safe|secure|fraud|scam|protect|privacy|data\s+protection)\b',
        r'\b(usalama|ulinzi|hifadhi|ulanguzi|faragha|salama|imelindwa)\b',
    ],
}


# ---------------------------------------------------------------------------
# Language Detection
# ---------------------------------------------------------------------------

SWAHILI_WORDS = {
    'habari', 'hujambo', 'sijambo', 'jambo', 'shikamoo', 'marahaba',
    'ndiyo', 'hapana', 'tafadhali', 'asante', 'karibu', 'vizuri',
    'safi', 'kwaheri', 'pole', 'samahani', 'sio', 'hakuna', 'sawa',
    'vipi', 'mambo', 'sema', 'nzuri', 'mbaya', 'nini', 'lini',
    'wapi', 'nani', 'jinsi', 'sana', 'kidogo', 'kabisa', 'bado',
    'tena', 'pia', 'lakini', 'tuma', 'pesa', 'hela', 'fedha',
    'uhamisho', 'ghairi', 'ada', 'bei', 'kiasi', 'akaunti',
    'mpokeaji', 'usalama', 'ulinzi', 'thibitisha', 'uhakiki',
    'kitambulisho', 'malalamiko', 'maoni', 'fuatilia', 'angalia',
    'saa', 'siku', 'leo', 'kesho', 'jana', 'nataka', 'nahitaji',
    'naomba', 'nina', 'niko', 'nime', 'huduma', 'msaada',
    'familia', 'kazi', 'rafiki',
}


def detect_language(message):
    """Detect if message is Swahili ('sw') or English ('en')."""
    message_lower = message.lower().strip()
    if not message_lower:
        return 'en'

    words = re.findall(r'\b[a-zA-Z]+\b', message_lower)
    sw_score = sum(3 for w in words if w in SWAHILI_WORDS)

    # Swahili grammar particles (strong indicators)
    if re.search(r'\b(kwa|ya|za|wa|la|cha|vya|mwa|pa|na)\b', message_lower):
        sw_score += 2

    return 'sw' if sw_score >= len(words) * 0.3 else 'en'


# ---------------------------------------------------------------------------
# AI Integration (Google Gemini)
# ---------------------------------------------------------------------------

AI_SYSTEM_PROMPT = """You are a friendly, professional customer care assistant for Kalton Investment, a money transfer service in Tanzania. 

## LANGUAGE RULES
- Detect if the customer speaks English or Swahili. Respond in the same language.
- If mixed (e.g. "hello, nina shida"), respond in Swahili.

## KNOWLEDGE
- Company: Kalton Investment - Money Transfer Services - https://kalton-investment.com
- Hours: Mon-Fri 8AM-8PM, Sat 9AM-5PM (online 24/7)
- Transfer limits: Basic $1,000/day, Verified $10,000/day, Minimum $10
- Fees: 2-3% of transfer amount, no hidden charges
- Verification: Government ID + proof of address
- Promotions: First transfer fee-free, Refer-a-friend ($10 each)
- Security: 256-bit SSL, two-factor auth, fraud monitoring 24/7

## CONSTRAINTS
- Keep responses concise (2-3 sentences max).
- Do NOT make up specific exchange rates.
- Be empathetic with complaints.
- Offer to connect to a human agent for complex issues."""


def is_ai_available():
    """Check if Gemini AI is configured."""
    if os.environ.get('GEMINI_API_KEY', ''):
        return True
    try:
        from django.conf import settings
        return bool(getattr(settings, 'GEMINI_API_KEY', ''))
    except Exception:
        return False


def get_gemini_api_key():
    """Get Gemini API key from env or Django settings."""
    api_key = os.environ.get('GEMINI_API_KEY', '')
    if api_key:
        return api_key
    try:
        from django.conf import settings
        return getattr(settings, 'GEMINI_API_KEY', '')
    except Exception:
        return ''


def call_gemini(system_prompt, conversation_history):
    """Call Google Gemini API. Returns None on error or if unavailable."""
    try:
        api_key = get_gemini_api_key()
        if not api_key:
            return None

        from google import genai

        client = genai.Client(api_key=api_key)
        contents = [system_prompt]
        for entry in conversation_history:
            contents.append(entry.get('content', ''))

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=contents,
        )

        if response and response.text:
            return response.text.strip()

    except ImportError:
        logger.warning("google-genai not installed. Using fallback engine.")
    except Exception as e:
        logger.error(f"Gemini API error: {e}")

    return None


# ---------------------------------------------------------------------------
# Intent Matching
# ---------------------------------------------------------------------------

def match_intent(message):
    """Match a user message to an intent. Returns intent name or 'unknown'."""
    message_lower = message.lower().strip()

    for intent_name, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, message_lower):
                return intent_name
    return 'unknown'


def get_response(intent_name, language='en'):
    """Get a random response for the matched intent in the detected language."""
    responses = SWAHILI_RESPONSES if language == 'sw' else ENGLISH_RESPONSES
    return random.choice(responses.get(intent_name, responses['unknown']))


# ---------------------------------------------------------------------------
# Conversation Memory (simple session-based)
# ---------------------------------------------------------------------------

class ConversationMemory:
    """Stores conversation context per session."""

    def __init__(self):
        self.sessions = {}

    def get_or_create(self, session_id):
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                'history': [],
                'last_intent': None,
                'language': 'en',
                'collected_info': {},
                'created_at': datetime.now(),
            }
        return self.sessions[session_id]

    def add_message(self, session_id, role, content, intent=None):
        session = self.get_or_create(session_id)
        session['history'].append({
            'role': role,
            'content': content,
            'intent': intent,
            'timestamp': datetime.now().isoformat(),
        })
        if intent:
            session['last_intent'] = intent

    def set_language(self, session_id, language):
        session = self.get_or_create(session_id)
        session['language'] = language

    def get_language(self, session_id):
        session = self.get_or_create(session_id)
        return session['language']

    def clear(self, session_id):
        if session_id in self.sessions:
            del self.sessions[session_id]


memory = ConversationMemory()


# ---------------------------------------------------------------------------
# ChatbotEngine - Main Class
# ---------------------------------------------------------------------------

class ChatbotEngine:
    """
    Bilingual chatbot engine for Kalton Investment.
    Uses Google Gemini AI when GEMINI_API_KEY is configured.
    Falls back to rule-based matching otherwise.
    """

    def __init__(self):
        self.conversation_context = {}

    def get_response(self, message, session_id=None, use_ai=None):
        """
        Main method: process a user message and return a response.

        Args:
            message: The user's message string.
            session_id: Optional session ID for conversation continuity.
            use_ai: Force AI on/off. If None, auto-detect based on API key.

        Returns:
            Dict with 'response', 'intent', 'language' keys.
        """
        if session_id is None:
            session_id = 'default'

        # Detect language
        language = detect_language(message)
        memory.set_language(session_id, language)

        # Match intent
        intent_name = match_intent(message)
        memory.add_message(session_id, 'user', message, intent=intent_name)

        # Determine if AI should be used
        if use_ai is None:
            use_ai = is_ai_available()

        response_text = None

        if use_ai:
            # Try AI first
            history = memory.get_or_create(session_id)['history']
            response_text = call_gemini(AI_SYSTEM_PROMPT, history)

        if not response_text:
            # Fallback to rule-based
            response_text = get_response(intent_name, language)

        # Store bot response
        memory.add_message(session_id, 'bot', response_text, intent=intent_name)

        return {
            'response': response_text,
            'intent': intent_name,
            'language': language,
        }

    def reset_session(self, session_id):
        """Reset a conversation session."""
        memory.clear(session_id)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

engine = ChatbotEngine()
