"""Pilot benchmark dataset consisting of 24 native Indic monetary transfer utterances."""

from typing import List
from sahi.dataset.models import BaseUtterance, UtteranceCategory, VerificationStatus

PILOT_DATASET: List[BaseUtterance] = [
    # -------------------------------------------------------------
    # 1. INDIAN ENGLISH (6)
    # -------------------------------------------------------------
    BaseUtterance(
        id="UTT_EN_001",
        language_group="INDIAN_ENGLISH",
        category=UtteranceCategory.PLAIN_AMOUNT,
        intended_amount_inr=5000,
        native_text="Transfer five thousand rupees to Ramesh",
        romanized_text="Transfer five thousand rupees to Ramesh",
        payee_target="ramesh@upi",
        verification_status=VerificationStatus.VERIFIED,
        speaker_metadata={"gender": "female", "accent": "en-IN"},
        notes="Plain word-based English amount"
    ),
    BaseUtterance(
        id="UTT_EN_002",
        language_group="INDIAN_ENGLISH",
        category=UtteranceCategory.LAKH_CRORE,
        intended_amount_inr=250000,
        native_text="Send two and a half lakhs to Suresh",
        romanized_text="Send two and a half lakhs to Suresh",
        payee_target="suresh@upi",
        verification_status=VerificationStatus.VERIFIED,
        speaker_metadata={"gender": "male", "accent": "en-IN"},
        notes="Scale marker lakh with fractional expression"
    ),
    BaseUtterance(
        id="UTT_EN_003",
        language_group="INDIAN_ENGLISH",
        category=UtteranceCategory.FRACTIONAL,
        intended_amount_inr=2500,
        native_text="Pay twenty five hundred rupees to Ramesh",
        romanized_text="Pay twenty five hundred rupees to Ramesh",
        payee_target="ramesh@upi",
        verification_status=VerificationStatus.VERIFIED,
        speaker_metadata={"gender": "female", "accent": "en-IN"},
        notes="Colloquial hundreds multiplier (25 x 100)"
    ),
    BaseUtterance(
        id="UTT_EN_004",
        language_group="INDIAN_ENGLISH",
        category=UtteranceCategory.CONFUSABLE,
        intended_amount_inr=15000,
        native_text="Transfer fifteen thousand rupees",
        romanized_text="Transfer fifteen thousand rupees",
        payee_target="ramesh@upi",
        verification_status=VerificationStatus.VERIFIED,
        speaker_metadata={"gender": "male", "accent": "en-IN"},
        notes="Phonetic confusable with 50,000 (fifteen vs fifty)"
    ),
    BaseUtterance(
        id="UTT_EN_005",
        language_group="INDIAN_ENGLISH",
        category=UtteranceCategory.CODEMIX,
        intended_amount_inr=5000,
        native_text="Please send 5k right now to Suresh",
        romanized_text="Please send 5k right now to Suresh",
        payee_target="suresh@upi",
        verification_status=VerificationStatus.VERIFIED,
        speaker_metadata={"gender": "female", "accent": "en-IN"},
        notes="Shorthand numeric suffix 'k'"
    ),
    BaseUtterance(
        id="UTT_EN_006",
        language_group="INDIAN_ENGLISH",
        category=UtteranceCategory.SELF_CORRECTION,
        intended_amount_inr=5000,
        candidate_amounts=[500, 5000],
        native_text="Send 500 rupees, no wait, make that 5000",
        romanized_text="Send 500 rupees, no wait, make that 5000",
        payee_target="ramesh@upi",
        verification_status=VerificationStatus.VERIFIED,
        speaker_metadata={"gender": "male", "accent": "en-IN"},
        notes="Spoken self-correction requiring SahiGuard RE_ASK hold"
    ),

    # -------------------------------------------------------------
    # 2. HINDI (6)
    # -------------------------------------------------------------
    BaseUtterance(
        id="UTT_HI_001",
        language_group="HINDI",
        category=UtteranceCategory.PLAIN_AMOUNT,
        intended_amount_inr=5000,
        native_text="रमेश को पाँच हज़ार रुपये भेजो",
        romanized_text="Ramesh ko paanch hazaar rupaye bhejo",
        payee_target="ramesh@upi",
        verification_status=VerificationStatus.VERIFIED,
        speaker_metadata={"gender": "female", "accent": "hi-IN"},
        notes="Standard Devanagari 5,000"
    ),
    BaseUtterance(
        id="UTT_HI_002",
        language_group="HINDI",
        category=UtteranceCategory.LAKH_CRORE,
        intended_amount_inr=150000,
        native_text="सुरेश को डेढ़ लाख रुपये भेज दो",
        romanized_text="Suresh ko dedh lakh rupaye bhej do",
        payee_target="suresh@upi",
        verification_status=VerificationStatus.VERIFIED,
        speaker_metadata={"gender": "male", "accent": "hi-IN"},
        notes="Colloquial Hindi fraction 'dedh' (1.5 lakh = 1,50,000)"
    ),
    BaseUtterance(
        id="UTT_HI_003",
        language_group="HINDI",
        category=UtteranceCategory.FRACTIONAL,
        intended_amount_inr=2500,
        native_text="ढाई हज़ार रुपये ट्रांसफर करो",
        romanized_text="Dhai hazaar rupaye transfer karo",
        payee_target="ramesh@upi",
        verification_status=VerificationStatus.VERIFIED,
        speaker_metadata={"gender": "female", "accent": "hi-IN"},
        notes="Colloquial Hindi fraction 'dhai' (2.5 hazar = 2,500)"
    ),
    BaseUtterance(
        id="UTT_HI_004",
        language_group="HINDI",
        category=UtteranceCategory.CONFUSABLE,
        intended_amount_inr=15000,
        native_text="पंद्रह हज़ार रुपये भेजो",
        romanized_text="Pandrah hazaar rupaye bhejo",
        payee_target="ramesh@upi",
        verification_status=VerificationStatus.VERIFIED,
        speaker_metadata={"gender": "male", "accent": "hi-IN"},
        notes="Phonetic confusable with 50,000 (pandrah vs pachas)"
    ),
    BaseUtterance(
        id="UTT_HI_005",
        language_group="HINDI",
        category=UtteranceCategory.CODEMIX,
        intended_amount_inr=3500,
        native_text="साढ़े तीन हज़ार google pay कर दो",
        romanized_text="Sadhe teen hazaar google pay kar do",
        payee_target="suresh@upi",
        verification_status=VerificationStatus.VERIFIED,
        speaker_metadata={"gender": "female", "accent": "hi-IN"},
        notes="Colloquial fraction sadhe + English tech brand"
    ),
    BaseUtterance(
        id="UTT_HI_006",
        language_group="HINDI",
        category=UtteranceCategory.SELF_CORRECTION,
        intended_amount_inr=20000,
        candidate_amounts=[2000, 20000],
        native_text="दो हज़ार भेजो, अरे नहीं बीस हज़ार",
        romanized_text="Do hazaar bhejo, arre nahi bees hazaar",
        payee_target="ramesh@upi",
        verification_status=VerificationStatus.VERIFIED,
        speaker_metadata={"gender": "male", "accent": "hi-IN"},
        notes="Spoken self-correction in Hindi with arre nahi"
    ),

    # -------------------------------------------------------------
    # 3. TELUGU (6)
    # -------------------------------------------------------------
    BaseUtterance(
        id="UTT_TE_001",
        language_group="TELUGU",
        category=UtteranceCategory.PLAIN_AMOUNT,
        intended_amount_inr=5000,
        native_text="రమేష్ కి ఐదు వేల రూపాయలు పంపించండి",
        romanized_text="Ramesh ki aidu vela roopayalu pampinchandi",
        payee_target="ramesh@upi",
        verification_status=VerificationStatus.VERIFIED,
        speaker_metadata={"gender": "female", "accent": "te-IN"},
        notes="Standard Telugu 5,000"
    ),
    BaseUtterance(
        id="UTT_TE_002",
        language_group="TELUGU",
        category=UtteranceCategory.LAKH_CRORE,
        intended_amount_inr=250000,
        native_text="రెండున్నర లక్షల రూపాయలు పంపు",
        romanized_text="Rendunnara lakshala roopayalu pampu",
        payee_target="suresh@upi",
        verification_status=VerificationStatus.VERIFIED,
        speaker_metadata={"gender": "male", "accent": "te-IN"},
        notes="Colloquial Telugu fraction 'rendunnara' (2.5 lakshalu = 2,50,000)"
    ),
    BaseUtterance(
        id="UTT_TE_003",
        language_group="TELUGU",
        category=UtteranceCategory.FRACTIONAL,
        intended_amount_inr=2500,
        native_text="రెండున్నర వేలు ట్రాన్స్‌ఫర్ చేయి",
        romanized_text="Rendunnara velu transfer cheyi",
        payee_target="ramesh@upi",
        verification_status=VerificationStatus.VERIFIED,
        speaker_metadata={"gender": "female", "accent": "te-IN"},
        notes="Colloquial Telugu fraction 'rendunnara velu' = 2,500"
    ),
    BaseUtterance(
        id="UTT_TE_004",
        language_group="TELUGU",
        category=UtteranceCategory.CONFUSABLE,
        intended_amount_inr=15000,
        native_text="పదిహేను వేల రూపాయలు పంపించు",
        romanized_text="Padihenu vela roopayalu pampinchu",
        payee_target="ramesh@upi",
        verification_status=VerificationStatus.VERIFIED,
        speaker_metadata={"gender": "male", "accent": "te-IN"},
        notes="Phonetic confusable with 50,000 (padihenu vs yabhai)"
    ),
    BaseUtterance(
        id="UTT_TE_005",
        language_group="TELUGU",
        category=UtteranceCategory.CODEMIX,
        intended_amount_inr=50000,
        native_text="యాభై వేలు account lo transfer cheyyi",
        romanized_text="Yabhai velu account lo transfer cheyyi",
        payee_target="suresh@upi",
        verification_status=VerificationStatus.VERIFIED,
        speaker_metadata={"gender": "female", "accent": "te-IN"},
        notes="Telugu quantity + English account transfer"
    ),
    BaseUtterance(
        id="UTT_TE_006",
        language_group="TELUGU",
        category=UtteranceCategory.SELF_CORRECTION,
        intended_amount_inr=5000,
        candidate_amounts=[500, 5000],
        native_text="ఐదు వందలు పంపు, కాదు కాదు ఐదు వేలు",
        romanized_text="Aidu vandalu pampu, kaadu kaadu aidu velu",
        payee_target="ramesh@upi",
        verification_status=VerificationStatus.VERIFIED,
        speaker_metadata={"gender": "male", "accent": "te-IN"},
        notes="Telugu self-correction with kaadu kaadu"
    ),

    # -------------------------------------------------------------
    # 4. HINGLISH (6)
    # -------------------------------------------------------------
    BaseUtterance(
        id="UTT_HG_001",
        language_group="HINGLISH",
        category=UtteranceCategory.PLAIN_AMOUNT,
        intended_amount_inr=5000,
        native_text="Transfer 5000 to brother",
        romanized_text="Transfer 5000 to brother",
        payee_target="ramesh@upi",
        verification_status=VerificationStatus.VERIFIED,
        speaker_metadata={"gender": "female", "accent": "hi-IN"},
        notes="Direct digit in code-mixed sentence"
    ),
    BaseUtterance(
        id="UTT_HG_002",
        language_group="HINGLISH",
        category=UtteranceCategory.LAKH_CRORE,
        intended_amount_inr=250000,
        native_text="Account me 2.5 lakh transfer kar do",
        romanized_text="Account me 2.5 lakh transfer kar do",
        payee_target="suresh@upi",
        verification_status=VerificationStatus.VERIFIED,
        speaker_metadata={"gender": "male", "accent": "hi-IN"},
        notes="Scale marker lakh with mixed Latin script"
    ),
    BaseUtterance(
        id="UTT_HG_003",
        language_group="HINGLISH",
        category=UtteranceCategory.FRACTIONAL,
        intended_amount_inr=2500,
        native_text="Dhai hazar rupaye send karo",
        romanized_text="Dhai hazar rupaye send karo",
        payee_target="ramesh@upi",
        verification_status=VerificationStatus.VERIFIED,
        speaker_metadata={"gender": "female", "accent": "hi-IN"},
        notes="Colloquial Latin Hindi fraction dhai hazar"
    ),
    BaseUtterance(
        id="UTT_HG_004",
        language_group="HINGLISH",
        category=UtteranceCategory.CONFUSABLE,
        intended_amount_inr=70000,
        native_text="Sattar hazar bhejo",
        romanized_text="Sattar hazar bhejo",
        payee_target="ramesh@upi",
        verification_status=VerificationStatus.VERIFIED,
        speaker_metadata={"gender": "male", "accent": "hi-IN"},
        notes="Phonetic confusable with 17,000 (sattar vs satrah)"
    ),
    BaseUtterance(
        id="UTT_HG_005",
        language_group="HINGLISH",
        category=UtteranceCategory.CODEMIX,
        intended_amount_inr=250000,
        native_text="Please pay do lakh पचास हज़ार via UPI",
        romanized_text="Please pay do lakh pachas hazar via UPI",
        payee_target="suresh@upi",
        verification_status=VerificationStatus.VERIFIED,
        speaker_metadata={"gender": "female", "accent": "hi-IN"},
        notes="Mixed Latin, Devanagari and English tokens"
    ),
    BaseUtterance(
        id="UTT_HG_006",
        language_group="HINGLISH",
        category=UtteranceCategory.SELF_CORRECTION,
        intended_amount_inr=20000,
        candidate_amounts=[2000, 20000],
        native_text="Transfer 2000 nahi nahi 20000 karo",
        romanized_text="Transfer 2000 nahi nahi 20000 karo",
        payee_target="ramesh@upi",
        verification_status=VerificationStatus.VERIFIED,
        speaker_metadata={"gender": "male", "accent": "hi-IN"},
        notes="Self-correction in Hinglish with nahi nahi"
    ),
]
