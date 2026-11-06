"""Offline frequency vocabulary and reviewed gateway exceptions.

These words are deliberately disclosed in prose. A private name or technical
term with the same spelling is ambiguous and must be registered as sensitive.
Entries are exact forms, not prefixes, and do not apply to code. wordfreq's
packaged data is CC BY-SA 4.0; see docs/THIRD_PARTY_DATA.md for attribution.
"""

import unicodedata
import re
from functools import lru_cache

from wordfreq import available_languages, read_cBpack

from secure_gateway.engine.natural_languages import tokenize
from secure_gateway.gateway_indic_vocabulary import INDIC_WORDS
from secure_gateway.gateway_name_vocabulary import NAME_WORDS
from secure_gateway.gateway_household_vocabulary import HOUSEHOLD_WORDS



@lru_cache(maxsize=17)
def ordinary_words(language: str) -> frozenset[str]:
    """Packaged frequency data, with no network and no cross-language fallback.

    Frequency is an ordinary-vocabulary cue,
    not proof that a word is safe. Forced spans always override this set.
    Keep only the selected bins instead of retaining full frequency tables.
    """
    path = available_languages().get(language)
    words = set(GENERAL_WORDS.get(language, ())) | set(INDIC_WORDS.get(language, ())) | set(HOUSEHOLD_WORDS.get(language, ()))
    if path:
        bins = read_cBpack(path)
        # Case-free scripts have no reliable capitalization cue for names, so
        # require a higher frequency. Exact sensitive rules still take priority.
        cutoff = 550 if language in {"en", "es", "fr", "pt", "de", "id", "tr", "ru"} else 500
        for bucket in bins[:cutoff + 1]:
            words.update(unicodedata.normalize("NFC", word).casefold() for word in bucket
                         if word and all(char.isalpha() or unicodedata.category(char).startswith("M")
                                         or char in "’'\u200c\u200d" for char in word))
    elif language not in INDIC_WORDS:
        raise ValueError("Packaged ordinary vocabulary is missing for " + language)
    return frozenset(words)

GENERAL_WORDS = {
    "en": "please tell time meeting meetings start starts begin begins today tomorrow work store tea weather walk together friend list going explain how make nice check call",
    "ko": "오늘 내일 회의 시간 시 시작 시작하는지 알려주세요 퇴근 후 가게 들러서 필요한 물건 살게요 차 한 잔 만드는 방법 설명해 주세요 날씨 좋으니 함께 공원 걸어가요 목록 확인하고 친구 전화할게요",
    "es": "por favor dime qué hora empieza empezar reunión hoy tienda después trabajo puedes explicar cómo preparar taza té hace buen tiempo podemos caminar juntos mañana revisaré lista llamaré amigo",
    "fr": "dis moi quelle heure commence réunion je vais magasin après travail aujourd’hui peux tu expliquer comment préparer tasse thé il fait beau nous pouvons marcher ensemble demain vérifierai liste appellerai ami",
    "pt": "por favor diga horas começa reunião hoje vou loja depois trabalho pode explicar como preparar xícara chá tempo está bom podemos caminhar juntos amanhã verificar lista ligar amigo",
    "de": "bitte sag mir wann treffen beginnt heute gehe ich nach arbeit laden kannst du erklären wie man eine tasse tee zubereitet wetter ist schön wir können zusammen spazieren gehen morgen prüfe liste rufe meinen freund an",
    "id": "tolong beri tahu kapan rapat dimulai hari ini saya pergi toko setelah bekerja bisakah kamu menjelaskan cara membuat secangkir teh cuacanya bagus kita bisa berjalan bersama besok akan memeriksa daftar menelepon teman",
    "tr": "lütfen toplantının toplantı saat kaçta başladığını başla söyle bugün işten sonra mağazaya gideceğim bir fincan çayın nasıl hazırlandığını açıklayabilir misin hava güzel birlikte yürüyebiliriz yarın listeyi kontrol edip arkadaşımı arayacağım",
    "ru": "пожалуйста скажи сколько начинается встреча сегодня после работы я пойду магазин можешь объяснить как приготовить чашку чая погода хорошая мы можем погулять вместе завтра проверю список позвоню другу",
    "hi": "कृपया बताएं बैठक कितने बजे शुरू होती आज काम बाद मैं दुकान जाऊँगा क्या आप बता सकते हैं एक कप चाय कैसे बनाते मौसम अच्छा हम साथ चल कल सूची देखूँगा अपने दोस्त फोन करूँगा",
    "mr": "कृपया बैठक किती वाजता सुरू होते ते सांगा आज कामानंतर मी दुकानात जाईन एक कप चहा कसा बनवायचा सांगू शकता का हवामान छान आहे आपण एकत्र फिरू शकतो उद्या यादी तपासेन मित्राला फोन करेन",
    "bn": "দয়া করে বলুন সভা কখন শুরু হবে আজ কাজের পরে আমি দোকানে যাব এক কাপ চা কীভাবে বানাতে হয় বুঝিয়ে বলবেন আবহাওয়া ভালো আমরা একসঙ্গে হাঁটতে পারি আগামীকাল তালিকা দেখে বন্ধুকে ফোন করব",
    "ur": "براہ کرم بتائیں اجلاس کتنے بجے شروع ہوگا آج کام بعد میں دکان جاؤں گا کیا آپ بتا سکتے ہیں ایک کپ چائے کیسے بناتے موسم اچھا ہم اکٹھے چل کل فہرست دیکھ کر اپنے دوست فون کروں",
    "te": "సమావేశం ఎప్పుడు మొదలవుతుందో చెప్పండి ఈ రోజు పని తర్వాత నేను దుకాణానికి వెళ్తాను ఒక కప్పు టీ ఎలా తయారు చేయాలో వివరించగలరా వాతావరణం బాగుంది మనం కలిసి నడవవచ్చు రేపు జాబితా చూసి నా స్నేహితుడికి ఫోన్ చేస్తాను",
    "ar": "من فضلك أخبرني متى يبدأ الاجتماع اليوم سأذهب إلى المتجر بعد العمل هل يمكنك شرح طريقة إعداد كوب الشاي الطقس جميل يمكننا المشي معا معاً غدا غداً سأراجع القائمة أتصل بصديقي",
    "zh": "请 告诉 我 会议 几点 开始 今天 下班 后 要 去 商店 你 能 解释 一下 怎么 泡 一杯 茶 吗 天气 很好 我们 可以 一起 散步 明天 会 检查 清单 给 朋友 打电话",
    "ja": "会議 何時 始まる か 教え て く ださい 今日 仕事 後 店 行き お茶 入れ 方 説明 もらえ 天気 良い ので 一緒 散歩 でき 明日 一覧 確認 し 友達 電話 し ます",
}


def select_gateway_language(text: str, fallback: str) -> str:
    """Select among scripts with shared alphabets only when evidence is clear.

    Scores use whole lexical words, not substring matches. Ambiguous and short
    inputs keep the existing conservative detector's selection.
    """
    groups = {"en": ("en", "es", "fr", "pt", "de", "id", "tr"),
              "hi": ("hi", "mr"), "ar": ("ar", "ur")}
    choices = groups.get(fallback)
    if choices is None:
        return fallback
    words = [unicodedata.normalize("NFC", chunk.text).casefold()
             for chunk in tokenize(text, fallback) if chunk.is_word]
    scores = sorted(((sum(word in ordinary_words(lang) for word in words), lang)
                     for lang in choices), reverse=True)
    if scores[0][0] >= 2 and scores[0][0] > scores[1][0]:
        return scores[0][1]
    return fallback

ADDITIONAL_WORDS = {
    "en": "book books home house help find found left can could want need read learn ask question answer show give use open close day morning evening family school food water where when why what how",
    "ko": "집 책 도움 찾아 찾다 찾기 찾아줘 찾아주세요 두고 온 있어 도와줘 도와주세요 학교 가족 아침 저녁 음식 물 무엇 어디 언제 왜 어떻게",
    "es": "libro libros casa hogar ayudar ayuda ayudarme encontrar encuentra encontraré dejé puedes quiero necesito leer aprender pregunta respuesta familia escuela comida agua dónde cuándo por qué cómo",
    "fr": "livre livres maison chez aide aider aiderai retrouver trouve trouver laissé laissée peux aider à école famille repas eau où quand pourquoi quoi comment m’ aide j’ ai",
    "pt": "livro livros casa ajuda ajudar encontrar encontra deixei deixou você podem posso precisa família escola comida água onde quando porque como",
    "de": "buch bücher zuhause hause haus helfen hilfe finden finde gelassen habe kannst können frage antwort familie schule essen wasser wo wann warum was wie",
    "id": "buku rumah bantu membantu bantuan menemukan temukan tertinggal tinggal bisa dapat tolong ingin perlu baca belajar tanya jawab keluarga sekolah makanan air mana kapan mengapa bagaimana",
    "tr": "kitap kitabı kitaplar kitapçı ev evde yardım yardımcı bulmak bul bulmama bıraktığım edebilir edebilir misin aile okul yemek su nerede ne zaman neden nasıl",
    "ru": "книга книгу книги дом дома домой помощь помочь помоги поможешь найти оставил оставила можешь семья школа еда вода где когда почему что как мыть помыть вымыть почистить убрать",
    "hi": "किताब किताबें घर मदद ढूँढ़ने ढूंढने खोजने छोड़ी हुई मेरी आपके परिवार विद्यालय भोजन पानी कहाँ कब क्यों क्या कैसे",
    "mr": "पुस्तक पुस्तके घर घरी मदत शोधायला शोधणे ठेवलेले तुम्ही मला कराल कुटुंब शाळा जेवण पाणी कुठे कधी का कसे",
    "bn": "বই বইটি বাড়ি বাড়িতে সাহায্য খুঁজে পেতে ফেলে আসা তুমি কি আমাকে করবে পরিবার স্কুল খাবার পানি কোথায় কখন কেন কীভাবে",
    "ur": "کتاب کتابیں گھر مدد ڈھونڈنے تلاش چھوڑی ہوئی میری آپ سکتے خاندان اسکول کھانا پانی کہاں کب کیوں کیا کیسے",
    "te": "పుస్తకం పుస్తకాన్ని పుస్తకాలు ఇల్లు ఇంట్లో సహాయం కనుగొనడానికి వదిలిన నాకు చేయగలవా కుటుంబం పాఠశాల ఆహారం నీరు ఎక్కడ ఎప్పుడు ఎందుకు ఎలా",
    "ar": "كتاب الكتاب كتب المنزل البيت مساعدة مساعدتي العثور تركته يمكنك أسرة مدرسة طعام ماء أين متى لماذا ماذا كيف",
    "zh": "书 本书 那本书 书本 家 家里 家中 帮 帮助 找到 找 留在 帮我 你 能 我 的 那 本 吗 学校 家人 食物 水 哪里 什么时候 为什么 怎么",
    "ja": "本 本屋 家 自宅 手伝っ 手伝う 手伝っ て くれ ます か 探す 探し 置い 置く 来 き た を の 友達 学校 食事 水 どこ いつ なぜ どう",
}

GENERAL_WORDS = {
    language: frozenset((words + " " + ADDITIONAL_WORDS.get(language, "")).split())
    for language, words in GENERAL_WORDS.items()
}

# Reviewed domain markers are protected even when statistically frequent.
# This is a starter denylist, not exhaustive industry/PII classification.
DOMAIN_WORDS = {
    "en": "secret private password credential token confidential internal cancer insulin diabetes chemotherapy surgery diagnosis patient bank credit mortgage securitization pharmacokinetics electroplating bitcoin amazon apple tesla encryption merger acquisition oncology leukemia atherosclerosis underwriting actuarial derivatives collateral liquidity solvency immunotherapy radiotherapy bioreactor chromatography lithography etching metallurgy polymerase genome sequencing amortization bankruptcy",
    "ko": "암 인슐린 당뇨 은행 신용 담보 약물동태학 자산유동화 전기도금",
    "es": "cáncer insulina diabetes banco crédito hipoteca titulización farmacocinética galvanoplastia",
    "fr": "cancer insuline diabète banque crédit hypothèque titrisation pharmacocinétique galvanoplastie",
    "pt": "câncer insulina diabetes banco crédito hipoteca securitização farmacocinética galvanoplastia",
    "de": "krebs insulin diabetes bank kredit hypothek verbriefung pharmakokinetik galvanotechnik",
    "id": "kanker insulin diabetes bank kredit hipotek sekuritisasi farmakokinetik elektroplating",
    "tr": "kanser insülin diyabet banka kredi ipotek menkul kıymetleştirme farmakokinetik elektrokaplama",
    "ru": "рак инсулин диабет банк кредит ипотека секьюритизация фармакокинетика гальванопокрытие",
    "hi": "कैंसर इंसुलिन मधुमेह बैंक ऋण प्रतिभूतिकरण",
    "mr": "कर्करोग इन्सुलिन मधुमेह बँक कर्ज प्रतिभूतिकरण",
    "bn": "ক্যান্সার ইনসুলিন ডায়াবেটিস ব্যাংক ঋণ সিকিউরিটাইজেশন",
    "ur": "سرطان انسولین ذیابیطس بینک قرض سیکیورٹائزیشن",
    "te": "నీలం క్యాన్సర్ ఇన్సులిన్ మధుమేహం బ్యాంకు రుణం సెక్యూరిటైజేషన్",
    "ar": "سرطان الأنسولين السكري بنك ائتمان التوريق",
    "zh": "北京 上海 广州 深圳 癌症 胰岛素 糖尿病 银行 信贷 抵押 证券化 电镀",
    "ja": "東京 大阪 京都 横浜 名古屋 癌 がん インスリン 糖尿病 銀行 信用 住宅ローン 資産証券化 薬物動態学 電気めっき 証券化 めっき",
}
DOMAIN_WORDS = {language: frozenset(words.split()) for language, words in DOMAIN_WORDS.items()}
ENGLISH_NAMES = frozenset("john james maria mary michael robert patricia jennifer linda elizabeth david william richard joseph thomas charles daniel matthew anthony mark donald steven paul andrew joshua kevin brian george edward ronald timothy jason jeffrey ryan jacob gary nicholas eric jonathan stephen larry justin scott brandon benjamin samuel frank gregory raymond alexander patrick jack dennis jerry tyler aaron henry douglas peter adam nathan zachary walter kyle harold carl jeremy keith roger gerald ethan arthur terry lawrence sean christian austin joe albert jesse alan ralph eugene russell vincent philip billy johnny bradley johnson washington smith garcia martinez rodriguez hernandez lopez gonzalez wilson anderson thompson jackson harris clark lewis robinson walker young allen king wright susan jessica sarah karen nancy lisa betty margaret sandra ashley kimberly emily donna michelle carol amanda dorothy melissa deborah stephanie rebecca sharon laura cynthia kathleen amy angela shirley anna brenda pamela nicole samantha katherine christine debra rachel catherine carolyn janet ruth heather diane virginia julie joyce victoria olivia kelly christina lauren joan evelyn judith megan cheryl andrea hannah jacqueline martha gloria teresa ann sara madison frances kathryn janice jean abigail alice judy sophia grace denise amber doris marilyn danielle beverly isabella theresa diana natalie brittany charlotte marie kayla alexis lori".split())


def domain_terms(text: str, language: str) -> set[str]:
    private = DOMAIN_WORDS.get(language, frozenset()) | NAME_WORDS.get(language, frozenset())
    if language == "en":
        private = private | ENGLISH_NAMES
    terms = {chunk.text for chunk in tokenize(text, language)
             if unicodedata.normalize("NFC", chunk.text).casefold() in private}
    if language == "en":
        for chunk in tokenize(text, language):
            word = unicodedata.normalize("NFC", chunk.text).casefold()
            if word.endswith(("'s", "’s")) and word[:-2] in private:
                terms.add(chunk.text)
            if any(word.endswith(suffix) and word[:-len(suffix)] in private
                   for suffix in ("s", "es", "ing", "ed")):
                terms.add(chunk.text)
    if language == "ar":
        for chunk in tokenize(text, language):
            word = unicodedata.normalize("NFC", chunk.text)
            if any(word.startswith(prefix) and word[len(prefix):] in private
                   for prefix in ("وال", "بال", "لل", "ال", "و", "ف", "ب", "ل", "ك")):
                terms.add(chunk.text)
    if language in {"zh", "ja", "ko"}:
        for word in private:
            for form in {word, unicodedata.normalize("NFD", word)}:
                terms.update(match.group() for match in re.finditer(re.escape(form), text))
    return terms


def reviewed_inflections(text: str, language: str) -> set[str]:
    """Allow case/plural forms only when a reviewed ordinary root is known.

    Do not infer roots for arbitrary unknown names or technical compounds.
    """
    suffixes = {
        "mr": ("ांमध्ये", "ांवर", "ांच्या", "ांची", "ांचा", "ांचे", "ामध्ये", "ावर", "ाच्या", "ाची", "ाचा", "ाचे", "मध्ये", "वर", "च्या", "ची", "चा", "चे", "ावी", "ावा", "ावे"),
        "te": ("లలో", "లను", "లతో", "లకి", "లకు", "లో", "లోని", "లను", "లు", "తో", "ను", "ని", "కు", "కి", "గా"),
    }.get(language, ())
    if not suffixes:
        return set()
    roots = (INDIC_WORDS.get(language, frozenset()) | HOUSEHOLD_WORDS.get(language, frozenset())) - NAME_WORDS.get(language, frozenset()) - DOMAIN_WORDS.get(language, frozenset())
    return {chunk.text for chunk in tokenize(text, language)
            if any(chunk.text.endswith(suffix) and chunk.text[:-len(suffix)] in roots for suffix in suffixes)}
