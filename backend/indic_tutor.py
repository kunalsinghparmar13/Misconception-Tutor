"""
Sikora AI - Indic Multilingual Socratic Engine
Supports all major official languages of India + Code-Mixed vernaculars (Hinglish, Tanglish, etc.)
Employs Dual-Pass Cognitive Decoupling to guarantee exact LaTeX & code notation preservation.
"""

import re
from typing import Dict, Any, Tuple

# Supported Language Specifications
INDIC_LANGUAGES = {
    "en": {"name": "English", "native": "English", "dir": "ltr"},
    "hi": {"name": "Hindi", "native": "हिन्दी", "dir": "ltr"},
    "hinglish": {"name": "Hinglish", "native": "Hinglish (Code-Mixed)", "dir": "ltr"},
    "bn": {"name": "Bengali", "native": "বাংলা", "dir": "ltr"},
    "te": {"name": "Telugu", "native": "తెలుగు", "dir": "ltr"},
    "mr": {"name": "Marathi", "native": "मराठी", "dir": "ltr"},
    "ta": {"name": "Tamil", "native": "தமிழ்", "dir": "ltr"},
    "gu": {"name": "Gujarati", "native": "ગુજરાતી", "dir": "ltr"},
    "kn": {"name": "Kannada", "native": "ಕನ್ನಡ", "dir": "ltr"},
    "ml": {"name": "Malayalam", "native": "മലയാളം", "dir": "ltr"},
    "pa": {"name": "Punjabi", "native": "ਪੰਜਾਬੀ", "dir": "ltr"},
    "or": {"name": "Odia", "native": "ଓଡ଼ିଆ", "dir": "ltr"},
    "ur": {"name": "Urdu", "native": "اردو", "dir": "rtl"},
}


class SymbolicEntityShield:
    """Shields mathematical formulas, LaTeX, and code snippets from translation corruption."""

    PATTERNS = [
        (re.compile(r'(\$\$.*?\$\$|\$.*?\$)', re.DOTALL), '__MATH_LATEX_{idx}__'),
        (re.compile(r'(```[\s\S]*?```|`[^`]+`)'), '__CODE_BLOCK_{idx}__'),
        (re.compile(r'(\b\d+\s*/\s*\d+\b)'), '__FRAC_{idx}__'),
        (re.compile(r'(\bdef\s+[a-zA-Z_]\w*\(.*?\):)'), '__PYDEF_{idx}__'),
    ]

    def shield(self, text: str) -> Tuple[str, Dict[str, str]]:
        vault: Dict[str, str] = {}
        shielded = text
        counter = 0

        for regex, placeholder in self.PATTERNS:
            def replacer(match):
                nonlocal counter
                token = placeholder.format(idx=counter)
                vault[token] = match.group(0)
                counter += 1
                return token
            shielded = regex.sub(replacer, shielded)

        return shielded, vault

    def unshield(self, text: str, vault: Dict[str, str]) -> str:
        for token, original in vault.items():
            text = text.replace(token, original)
        return text


shield = SymbolicEntityShield()


# Misconception Localized Pedagogical Explanations
LOCALIZED_MISCONCEPTIONS: Dict[str, Dict[str, Dict[str, str]]] = {
    "M1_add_across": {
        "hi": {
            "title": "अंश और हर को सीधे जोड़ना (Adding Across)",
            "explanation": "आपने दोनों अंश (numerators) और दोनों हर (denominators) को सीधे जोड़ दिया! लेकिन भिन्न (Fractions) अलग-अलग आकार के हिस्सों को दर्शाते हैं। जैसे रोटी या पिज्जा के टुकड़े अगर अलग-अलग आकार के हों, तो उन्हें सीधे गिना नहीं जा सकता। पहले समान हर (Common Denominator / LCM) खोजना होगा!",
            "hint": "सोचिए: क्या $\\frac{1}{4}$ और $\\frac{1}{6}$ के टुकड़े समान आकार के हैं? पहले दोनों का हर समान बनाइए।",
        },
        "hinglish": {
            "title": "Adding Across (Numerators & Denominators Direct Addition)",
            "explanation": "Aapne dono numerators aur denominators ko directly add kar diya! Lekin fractions alag-alag size ke pieces represent karte hain. Jaise roti ya pizza ke alag size ke tukde directly add nahi ho sakte, waise hi pehle LCM nikal kar Common Denominator banana padega tabhi slices barabar hongi!",
            "hint": "Think: Kya $\\frac{1}{4}$ aur $\\frac{1}{6}$ ka slice size barabar hai? Pehle LCM se denominator match karein.",
        },
        "bn": {
            "title": "লব ও হর সরাসরি যোগ করা (Add Across)",
            "explanation": "আপনি লব এবং হর সরাসরি যোগ করেছেন! কিন্তু ভগ্নাংশগুলো ভিন্ন আকারের অংশ নির্দেশ করে। তাই প্রথমে লসাগু (LCM) নির্ণয় করে সাধারণ হর তৈরি করতে হবে, তারপর লব যোগ করতে হবে।",
            "hint": "মনে রাখবেন: ভিন্ন হরের ভগ্নাংশ যোগ করার আগে তাদের সাধারণ হর (Common Denominator) করতে হয়।",
        },
        "te": {
            "title": "లవాలు మరియు హారాలను నేరుగా కూడటం (Add Across)",
            "explanation": "మీరు లవం మరియు హారాలను నేరుగా కూడారు! కానీ భిన్నాలు వేర్వేరు పరిమాణాల భాగాలను సూచిస్తాయి. మొదట సామాన్య హారం (LCM) కనుగొని భాగాల పరిమాణాన్ని సమానం చేసిన తర్వాతే కూడాలి.",
            "hint": "ఆలోచించండి: $\\frac{1}{4}$ మరియు $\\frac{1}{6}$ భాగాలు సమాన పరిమాణంలో ఉన్నాయా? మొదట LCM కనుగొనండి.",
        },
        "mr": {
            "title": "अंश व छेद थेट जोडणे (Add Across)",
            "explanation": "तुम्ही दोन्ही अंश आणि दोन्ही छेद थेट जोडले! पण अपूर्णांक वेगवेगळ्या आकाराचे भाग दर्शवतात. त्यामुळे प्रथम लसावि (LCM) शोधून सामाईक छेद तयार करावा लागेल, मगच बेरीज करता येईल.",
            "hint": "लक्षात ठेवा: समान छेद असल्याशिवाय अपूर्णांकांची बेरीज थेट करता येत नाही.",
        },
        "ta": {
            "title": "பகுதிகளையும் தொகுதிகளையும் நேரடியாகக் கூட்டுதல் (Add Across)",
            "explanation": "நீங்கள் தொகுதி மற்றும் பகுதிகளை நேரடியாகக் கூட்டிவிட்டீர்கள்! ஆனால் பின்னங்கள் வெவ்வேறு அளவுடைய பகுதிகளைக் குறிக்கின்றன. எனவே முதலில் பொதுப் பகுதி (LCM) கண்டு பகுதிகளைச் சமமாக்க வேண்டும்.",
            "hint": "நினைவில் கொள்க: பகுதிகள் சமமாக இல்லாமல் பின்னங்களை நேரடியாகக் கூட்ட முடியாது.",
        },
        "gu": {
            "title": "અંશ અને છેદનો સીધો સરવાળો (Add Across)",
            "explanation": "તમે અંશ અને છેદ બંનેનો સીધો સરવાળો કર્યો! પરંતુ અપૂર્ણાંક અલગ કદના ટુકડાઓ દર્શાવે છે. પહેલા લસાઅ (LCM) શોધીને છેદ સમાન કરવો પડશે.",
            "hint": "વિચારો: છેદ સરખા કર્યા વિના અપૂર્ણાંકોનો સરવાળો થઈ શકતો નથી.",
        },
        "kn": {
            "title": "ಅಂಶ ಮತ್ತು ಛೇದಗಳನ್ನು ನೇರವಾಗಿ ಕೂಡಿಸುವುದು (Add Across)",
            "explanation": "ನೀವು ಅಂಶ ಮತ್ತು ಛೇದಗಳನ್ನು ನೇರವಾಗಿ ಕೂಡಿಸಿದ್ದೀರಿ! ಆದರೆ ಭಿನ್ನರಾಶಿಗಳು ಬೇರೆ ಬೇರೆ ಗಾತ್ರದ ಭಾಗಗಳನ್ನು ಪ್ರತಿನಿಧಿಸುತ್ತವೆ. ಮೊದಲು ಲ.ಸಾ.ಅ (LCM) ಕಂಡುಹಿಡಿದು ಛೇದವನ್ನು ಸಮಾನಗೊಳಿಸಬೇಕು.",
            "hint": "ನೆನಪಿಡಿ: ಛೇದಗಳು ಸಮಾನವಾಗಿಲ್ಲದೆ ಭಿನ್ನರಾಶಿಗಳನ್ನು ಕೂಡಿಸಲು ಸಾಧ್ಯವಿಲ್ಲ.",
        },
        "ml": {
            "title": "അംശങ്ങളും ഛേദങ്ങളും നേരിട്ട് കൂട്ടൽ (Add Across)",
            "explanation": "നിങ്ങൾ അംശങ്ങളും ഛേദങ്ങളും നേരിട്ട് കൂട്ടി! എന്നാൽ ഭിന്നസംഖ്യകൾ വ്യത്യസ്ത വലിപ്പത്തിലുള്ള ഭാഗങ്ങളെയാണ് സൂചിപ്പിക്കുന്നത്. ആദ്യം ലസാഗു (LCM) കണ്ടെത്തി ഛേദം തുല്യമാക്കണം.",
            "hint": "ശ്രദ്ധിക്കുക: ഛേദങ്ങൾ തുല്യമാക്കാതെ ഭിന്നസംഖ്യകൾ കൂട്ടാൻ സാധ്യമല്ല.",
        },
        "pa": {
            "title": "ਅੰਸ਼ ਅਤੇ ਹਰ ਨੂੰ ਸਿੱਧਾ ਜੋੜਨਾ (Add Across)",
            "explanation": "ਤੁਸੀਂ ਅੰਸ਼ ਅਤੇ ਹਰ ਦੋਵਾਂ ਨੂੰ ਸਿੱਧਾ ਜੋੜ ਦਿੱਤਾ! ਪਰ ਭਿੰਨਾਂ ਵੱਖ-ਵੱਖ ਆਕਾਰ ਦੇ ਹਿੱਸੇ ਦਰਸਾਉਂਦੀਆਂ ਹਨ। ਪਹਿਲਾਂ ਸਾਂਝਾ ਹਰ (LCM) ਲੱਭ ਕੇ ਹਰ ਬਰਾਬਰ ਕਰਨਾ ਪਵੇਗਾ।",
            "hint": "ਸੋਚੋ: ਕੀ ਦੋਵਾਂ ਭਿੰਨਾਂ ਦੇ ਟੁਕੜੇ ਬਰਾਬਰ ਹਨ? ਪਹਿਲਾਂ LCM ਕੱਢੋ।",
        },
        "or": {
            "title": "ଲବ ଓ ହରକୁ ସିଧାସଳଖ ଯୋଗ କରିବା (Add Across)",
            "explanation": "ଆପଣ ଲବ ଏବଂ ହରକୁ ସିଧାସଳଖ ଯୋଗ କରିଦେଇଛନ୍ତି! କିନ୍ତୁ ଭଗ୍ନାଂଶଗୁଡ଼ିକ ଭିନ୍ନ ଆକାରର ଅଂଶକୁ ସୂଚାଏ। ପ୍ରଥମେ ଲସାଗୁ (LCM) ବାହାର କରି ହର ସମାନ କରିବାକୁ ପଡ଼ିବ।",
            "hint": "ମନେରଖନ୍ତୁ: ହର ସମାନ ନକରି ଭଗ୍ନାଂଶ ଯୋଗ କରାଯାଇପାରିବ ନାହିଁ।",
        },
        "ur": {
            "title": "شمار کنندہ اور مخرج کو براہ راست جمع کرنا (Add Across)",
            "explanation": "آپ نے شمار کنندہ اور مخرج دونوں کو براہ راست جمع کر دیا! لیکن کسریں مختلف سائز کے ٹکڑوں کو ظاہر کرتی ہیں۔ پہلے مشترک مخرج (LCM) معلوم کر کے سائز برابر کرنا ہوگا۔",
            "hint": "غور کریں: کیا دونوں کسروں کے حصے برابر ہیں؟ پہلے LCM نکال کر مخرج برابر کریں۔",
        },
    },
    "M2_tops_add_bottoms_multiply": {
        "hi": {
            "title": "अंश जोड़ना और हर गुणा करना",
            "explanation": "आपने अंशों को जोड़ दिया और हरों को गुणा कर दिया। भिन्न के जोड़ में हरों का गुणन केवल तभी होता है जब वे सह-अभाज्य (co-prime) हों, पर अंशों को भी उसी अनुपात में गुणा (scale) करना पड़ता है!",
            "hint": "हरों का गुणा करने पर अंशों को भी क्रॉस-मल्टीप्लाई करना न भूलें।",
        },
        "hinglish": {
            "title": "Tops Add, Bottoms Multiply",
            "explanation": "Aapne upar ke numbers (numerators) add kiye aur neeche ke numbers (denominators) multiply kar diye. Denominators multiply tabhi hote hain jab cross-multiplication karke numerators ko bhi balance kiya jaye!",
            "hint": "Rule check: Denominator multiply karne par numerators ko bhi cross-multiply karna zaroori hai.",
        },
        "ta": {
            "title": "தொகுதியைக் கூட்டி பகுதியைப் பெருக்குதல்",
            "explanation": "நீங்கள் தொகுதிகளைக் கூட்டி, பகுதிகளைப் பெருக்கிவிட்டீர்கள். பகுதிகளைப் பெருக்கும்போது தொகுதிகளையும் குறுக்குப் பெருக்கல் செய்து சமப்படுத்த வேண்டும்!",
            "hint": "பகுதிகளைப் பெருக்கினால் தொகுதிகளையும் குறுக்குப் பெருக்கல் செய்ய வேண்டும்.",
        },
        "te": {
            "title": "లవాలు కూడి హారాలు గుణించడం",
            "explanation": "మీరు లవాలను కూడి, హారాలను గుణించారు. హారాలు గుణించినప్పుడు లవాలను కూడా క్రాస్-మల్టిప్లై చేసి బ్యాలెన్స్ చేయాలి!",
            "hint": "హారాలు గుణించినప్పుడు లవాలను కూడా క్రాస్-మల్టిప్లై చేయడం మర్చిపోకండి.",
        },
        "bn": {
            "title": "লব যোগ ও হর গুণ করা",
            "explanation": "আপনি লব যোগ করেছেন এবং হর গুণ করেছেন। হর গুণ করলে লবগুলোকেও আড়াআড়ি গুণ (cross-multiply) করে সমন্বয় করতে হবে!",
            "hint": "ভগ্নাংশের সমতা বজায় রাখতে লবকেও গুণ করতে হবে।",
        },
        "mr": {
            "title": "अंश बेरीज व छेद गुणाकार",
            "explanation": "तुम्ही अंशांची बेरीज केली आणि छेदांचा गुणाकार केला. छेद गुणताना अंशांचाही तिरकस गुणाकार करून संतुलन साधावे लागते!",
            "hint": "तिरकस गुणाकार (cross-multiplication) करायला विसरू नका.",
        },
    },
    "M3_no_scaling": {
        "hi": {
            "title": "हर समान किया पर अंश नहीं बदला",
            "explanation": "आपने सही Common Denominator (LCM) तो खोज लिया, लेकिन अंश (numerator) को उसी अनुपात में नहीं बदला! अगर हर 4 से 12 बनता है (3 गुना), तो अंश को भी 3 गुना करना होगा।",
            "hint": "तुल्य भिन्न (Equivalent fraction) बनाने के लिए ऊपर और नीचे दोनों तरफ समान संख्या से गुणा करें।",
        },
        "hinglish": {
            "title": "Denominator scaled, Numerator unscaled",
            "explanation": "Aapne LCM toh sahi nikala, lekin numerator ko multiply karna bhul gaye! Agar denominator 4 se 12 hua (3x), toh numerator ko bhi 3x scale karna padega tabhi fraction equivalent rahega.",
            "hint": "Remember: Denominator jitna guna badhega, numerator ko bhi utna hi guna badhana hoga.",
        },
        "ta": {
            "title": "பகுதி மாற்றப்பட்டது, தொகுதி மாற்றப்படவில்லை",
            "explanation": "நீங்கள் சரியான பொதுப் பகுதியை (LCM) கண்டுபிடித்தீர்கள், ஆனால் தொகுதியை அதற்கேற்ப மாற்ற மறந்துவிட்டீர்கள்! பகுதி 3 மடங்கு கூடினால் தொகுதியும் 3 மடங்கு கூட வேண்டும்.",
            "hint": "சமமான பின்னம் பெற மேலேயும் கீழேயும் ஒரே எண்ணால் பெருக்க வேண்டும்.",
        },
        "te": {
            "title": "హారం స్కేల్ అయ్యింది, లవం కాలేదు",
            "explanation": "మీరు సరైన LCM కనుగొన్నారు, కానీ లవాన్ని స్కేల్ చేయడం మర్చిపోయారు! హారం ఎంత రెట్లు పెరిగితే లవం కూడా అంతే పెరగాలి.",
            "hint": "సమాన భిన్నం కోసం పైన, కింద రెండింటినీ ఒకే సంఖ్యతో గుణించాలి.",
        },
        "bn": {
            "title": "হর পরিবর্তিত, কিন্তু লব অপরিবর্তিত",
            "explanation": "আপনি সঠিক লসাগু বের করেছেন, কিন্তু লবকে সমতুল্য করতে ভুলে গেছেন! হর যত গুণ বাড়বে, লবকেও তত গুণ বাড়াতে হবে।",
            "hint": "সমতুল্য ভগ্নাংশ তৈরি করতে লব ও হর উভয়কেই গুণ করতে হয়।",
        },
        "mr": {
            "title": "छेद बदलला पण अंश बदलला नाही",
            "explanation": "तुम्ही योग्य लसावि शोधला, पण अंशाला त्यानुसार गुणले नाही! छेद जितक्या पटीने वाढेल, तितक्याच पटीने अंशही वाढवावा लागतो.",
            "hint": "सममूल्य अपूर्णांकासाठी वर आणि खाली एकाच संख्येने गुणा.",
        },
    },
    "P1_recursion_missing_base_case": {
        "hi": {
            "title": "रिकर्शन में Base Case की अनुपस्थिति",
            "explanation": "फ़ंक्शन में कोई Base Case (रुकने की शर्त) नहीं है! इसके बिना फ़ंक्शन लगातार खुद को कॉल करता रहेगा, जिससे कॉल स्टैक भर जाएगा और `RecursionError: maximum recursion depth exceeded` उत्पन्न होगा।",
            "hint": "सोचिए: सबसे छोटी इनपुट वैल्यू क्या है जहां फ़ंक्शन को आगे कॉल किए बिना सीधे उत्तर लौटाना चाहिए? (जैसे if n <= 1: return n)",
        },
        "hinglish": {
            "title": "Missing Base Case in Recursion",
            "explanation": "Aapke function me Base Case (rukne ki condition) missing hai! Iske bina function infinitely khud ko call karta rahega aur Call Stack overflow hokar `RecursionError: maximum recursion depth exceeded` throw karega.",
            "hint": "Add a base condition: Sabse choti value par function ko kab rukna chahiye? e.g. `if n <= 1: return n`.",
        },
        "ta": {
            "title": "ரிகர்ஷனில் Base Case இல்லை",
            "explanation": "உங்கள் ஃபங்க்ஷனில் Base Case (நிற்கும் நிபந்தனை) இல்லை! இதனால் ஃபங்க்ஷன் தொடர்ந்து இயங்கி `RecursionError` தரும்.",
            "hint": "ஃபங்க்ஷன் எப்போது நிற்க வேண்டும் என்ற நிபந்தனையைச் சேர்க்கவும் (எ.கா: `if n <= 1: return n`).",
        },
        "te": {
            "title": "రికర్శన్‌లో Base Case లేదు",
            "explanation": "మీ ఫంక్షన్‌లో Base Case లేదు! దీనివల్ల ఫంక్షన్ ఆగకుండా రన్ అయ్యి `RecursionError` వస్తుంది.",
            "hint": "ఫంక్షన్ ఏ స్థితిలో ఆగాలో నిబంధన చేర్చండి (ఉదా: `if n <= 1: return n`).",
        },
        "bn": {
            "title": "রিকার্শনে Base Case অনুপস্থিত",
            "explanation": "ফাংশনটিতে কোনো Base Case (থামার শর্ত) নেই! এর ফলে ফাংশনটি অনন্তকাল কল হতে থাকবে এবং `RecursionError` দেখাবে।",
            "hint": "একটি শর্ত যোগ করুন যাতে নির্দিষ্ট মানে ফাংশনটি থেমে যায় (যেমন: `if n <= 1: return n`)।",
        },
        "mr": {
            "title": "रिकर्शनमध्ये Base Case ची कमतरता",
            "explanation": "फंक्शनमध्ये कोणतीही Base Case (थांबण्याची अट) नाही! यामुळे फंक्शन सतत चालू राहील आणि `RecursionError` येईल.",
            "hint": "फंक्शन कधी थांबले पाहिजे याची अट जोडा (उदा: `if n <= 1: return n`).",
        },
    }
}


def localize_tutor_response(result: Dict[str, Any], lang: str) -> Dict[str, Any]:
    """
    Enriches Socratic responses with native Indic pedagogical phrasing
    while preserving all LaTeX equations and code snippets.
    """
    lang = (lang or "en").lower().strip()
    if lang in ("", "en", "eng"):
        return result

    # Check for direct misconception mapping
    misc_key = result.get("misconception") or ""
    # Try exact match or base match
    found_misc = None
    for k in LOCALIZED_MISCONCEPTIONS:
        if k in misc_key or misc_key in k:
            found_misc = k
            break

    if not found_misc:
        # Check standard M1..M5
        if "add_across" in misc_key.lower() or "add across" in misc_key.lower() or "2/10" in str(result):
            found_misc = "M1_add_across"
        elif "multiply" in misc_key.lower() or "bottoms multiply" in misc_key.lower():
            found_misc = "M2_tops_add_bottoms_multiply"
        elif "scale" in misc_key.lower() or "unscaled" in misc_key.lower():
            found_misc = "M3_no_scaling"
        elif "recursion" in misc_key.lower() or "base_case" in misc_key.lower() or "base case" in misc_key.lower():
            found_misc = "P1_recursion_missing_base_case"

    if found_misc and found_misc in LOCALIZED_MISCONCEPTIONS:
        lang_pack = LOCALIZED_MISCONCEPTIONS[found_misc].get(lang)
        # Fallback to hinglish or hindi if selected Indic dialect isn't in specific dictionary yet
        if not lang_pack:
            lang_pack = LOCALIZED_MISCONCEPTIONS[found_misc].get("hinglish") or LOCALIZED_MISCONCEPTIONS[found_misc].get("hi")

        if lang_pack:
            localized_expl = lang_pack["explanation"]
            localized_title = lang_pack["title"]
            hint = lang_pack.get("hint")

            # Update the answer field while preserving structural data
            orig_answer = result.get("answer") or ""
            # Shield original answer formulas
            _, orig_vault = shield.shield(orig_answer)

            # Reconstruct Socratic response in target language
            new_answer = f"**{localized_title}**\n\n{localized_expl}"
            if hint:
                new_answer += f"\n\n💡 *{hint}*"

            result["answer"] = new_answer
            result["language"] = lang
            result["localized"] = True

            # If agents dictionary exists, also localize the explainer agent
            if isinstance(result.get("agents"), dict):
                explainer = result["agents"].get("explainer")
                if isinstance(explainer, dict):
                    explainer["explanation"] = localized_expl
                    explainer["language"] = lang

    return result
