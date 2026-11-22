"""Numerical constants, multipliers, and word mappings across Hindi, Telugu, and English."""

ENGLISH_SCALES = {
    "k": 1_000,
    "thousand": 1_000,
    "thousands": 1_000,
    "hundred": 100,
    "hundreds": 100,
    "lakh": 100_000,
    "lakhs": 100_000,
    "lac": 100_000,
    "lacs": 100_000,
    "crore": 10_000_000,
    "crores": 10_000_000,
}

HINDI_SCALES = {
    # Hindi Latin
    "sau": 100,
    "so": 100,
    "hazar": 1_000,
    "hazaar": 1_000,
    "lakh": 100_000,
    "karod": 10_000_000,
    "crore": 10_000_000,

    # Hindi Devanagari
    "सौ": 100,
    "हज़ार": 1_000,
    "हजार": 1_000,
    "लाख": 100_000,
    "करोड़": 10_000_000,
}

TELUGU_SCALES = {
    # Telugu Latin
    "vanda": 100,
    "vandalu": 100,
    "vela": 1_000,
    "velu": 1_000,
    "veylu": 1_000,
    "laksha": 100_000,
    "lakshalu": 100_000,
    "koti": 10_000_000,
    "kotlu": 10_000_000,

    # Telugu Script
    "వంద": 100,
    "వందలు": 100,
    "వేలు": 1_000,
    "వేల": 1_000,
    "లక్ష": 100_000,
    "లక్షలు": 100_000,
    "కోటి": 10_000_000,
    "కోట్లు": 10_000_000,
}

ALL_SCALES = {**ENGLISH_SCALES, **HINDI_SCALES, **TELUGU_SCALES}

# English Units (1-99)
ENGLISH_UNITS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90
}

# Hindi Numbers (Devanagari) - purely units and tens 1-99
HINDI_DEVANAGARI = {
    "शून्य": 0, "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पाँच": 5, "पांच": 5,
    "छह": 6, "सात": 7, "आठ": 8, "नौ": 9, "दस": 10,
    "ग्यारह": 11, "बारह": 12, "तेरह": 13, "चौदह": 14, "पंद्रह": 15, "पन्द्रह": 15,
    "सोलह": 16, "सत्रह": 17, "अट्ठारह": 18, "उन्नीस": 19, "बीस": 20,
    "इक्कीस": 21, "बाईस": 22, "तेईस": 23, "चौबीस": 24, "पचीस": 25, "पच्चीस": 25,
    "छब्बीस": 26, "सत्ताईस": 27, "अट्ठाईस": 28, "उनतीस": 29, "तीस": 30,
    "इकत्तीस": 31, "बत्तीस": 32, "तैंतीस": 33, "चौंतीस": 34, "पैंतीस": 35,
    "छत्तीस": 36, "सैंतीस": 37, "अड़तीस": 38, "उनतालीस": 39, "चालीस": 40,
    "इकतालीस": 41, "बयालीस": 42, "तैंतालीस": 43, "चवालीस": 44, "पैंतालीस": 45,
    "छियालीस": 46, "सैंतालीस": 47, "अड़तालीस": 48, "उनचास": 49, "पचास": 50,
    "इक्यावन": 51, "बावन": 52, "तिरेपन": 53, "चौवन": 54, "पचपन": 55,
    "छप्पन": 56, "सत्तावन": 57, "अट्ठावन": 58, "उनसठ": 59, "साठ": 60,
    "इकसठ": 61, "बासठ": 62, "तिरेसठ": 63, "चौंसठ": 64, "पैंसठ": 65,
    "छियासठ": 66, "सरसठ": 67, "अड़सठ": 68, "उनहत्तर": 69, "सत्तर": 70,
    "इकहत्तर": 71, "बहत्तर": 72, "तिहत्तर": 73, "चौहत्तर": 74, "पचहत्तर": 75,
    "छिहत्तर": 76, "सतहत्तर": 77, "अठहत्तर": 78, "उनासी": 79, "अस्सी": 80,
    "इक्यासी": 81, "बयासी": 82, "तिरासी": 83, "चौरासी": 84, "पचासी": 85,
    "छियासी": 86, "सत्तासी": 87, "अट्ठासी": 88, "नवासी": 89, "नब्बे": 90,
    "इक्यानवे": 91, "बानवे": 92, "तिरानवे": 93, "चौरानवे": 94, "पंचानवे": 95,
    "छियानवे": 96, "सत्तानवे": 97, "अट्ठानवे": 98, "निन्यानवे": 99
}

# Hindi Numbers (Latin Transliteration)
HINDI_LATIN = {
    "ek": 1, "do": 2, "teen": 3, "char": 4, "chaar": 4, "panch": 5, "paanch": 5,
    "che": 6, "chhe": 6, "chheh": 6, "saat": 7, "aath": 8, "nau": 9, "das": 10,
    "gyarah": 11, "barah": 12, "terah": 13, "chaudah": 14, "pandrah": 15,
    "solah": 16, "satrah": 17, "atharah": 18, "unnees": 19, "bees": 20,
    "ikkees": 21, "baees": 22, "teees": 23, "chaubees": 24, "pachees": 25, "pachchees": 25,
    "tees": 30, "paintis": 35, "chalis": 40, "pachas": 50, "saath": 60,
    "sattar": 70, "assi": 80, "nabbe": 90
}

# Telugu Numbers (Telugu Script)
TELUGU_SCRIPT = {
    "సున్నా": 0, "ఒకటి": 1, "ఒక": 1, "రెండు": 2, "మూడు": 3, "నాలుగు": 4,
    "ఐదు": 5, "ఆరు": 6, "ఏడు": 7, "ఎనిమిది": 8, "తొమ్మిది": 9, "పది": 10,
    "పదకొండు": 11, "పన్నెండు": 12, "పదమూడు": 13, "పద్నాలుగు": 14, "పదిహేను": 15,
    "పదహారు": 16, "పదిహేడు": 17, "పద్దెనిమిది": 18, "పంతొమ్మిది": 19, "ఇరవై": 20,
    "ఇరవై ఐదు": 25, "ముప్పై": 30, "ముప్పై ఐదు": 35, "నలభై": 40, "యాభై": 50,
    "అరవై": 60, "డెబ్బై": 70, "ఎనభై": 80, "తొంభై": 90
}

# Telugu Numbers (Latin Transliteration)
TELUGU_LATIN = {
    "sunna": 0, "okati": 1, "oka": 1, "rendu": 2, "moodu": 3, "nalugu": 4,
    "aidu": 5, "aaru": 6, "yedu": 7, "edu": 7, "enimidi": 8, "tommidi": 9, "padi": 10,
    "padakondu": 11, "pannendu": 12, "padamoodu": 13, "padnalugu": 14, "padihenu": 15,
    "padaharu": 16, "padihedu": 17, "paddenimidi": 18, "pantommidi": 19, "iravai": 20,
    "iravai aidu": 25, "muppai": 30, "nalabhai": 40, "yabhai": 50, "aabhai": 50,
    "aravai": 60, "debbai": 70, "enabhai": 80, "tombhai": 90
}

COLLOQUIAL_FRACTIONS_HINDI = {
    "dedh": 1.5, "derh": 1.5, "dhai": 2.5, "adhai": 2.5, "dhaiya": 2.5,
    "aadha": 0.5, "adha": 0.5, "डेढ़": 1.5, "ढाई": 2.5, "आधा": 0.5
}

COLLOQUIAL_FRACTIONS_TELUGU = {
    "rendunnara": 2.5, "moodunnara": 3.5, "nalugunnara": 4.5, "aidunnara": 5.5,
    "sagam": 0.5, "ara": 0.5, "రెండున్నర": 2.5, "మూడున్నర": 3.5,
    "నాలుగున్నర": 4.5, "సగం": 0.5, "అర": 0.5
}

SELF_CORRECTION_PHRASES = [
    "no wait", "not that", "sorry", "wait no", "cancel that",
    "actually", "instead of", "make that",
    "arre nahi", "nahi nahi", "nahi", "galat bol diya",
    "kadu", "kadu kadu", "ledu ledu", "sorry cheppanu", "marichipoyanu"
]

CURRENCY_WORDS = {
    "rupee", "rupees", "rs", "inr", "rupaye", "rupya", "roopayalu", "roopayilu", "roopayee",
    "రూపాయలు", "రూపాయి", "రुपये", "रुपया", "रू"
}
