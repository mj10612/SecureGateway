"""Public instruction operators for recognizing task-bearing language.

Provenance: independently authored from general linguistic knowledge of common
imperatives, infinitives, inflections, sequencing, and negative instructions.
No evaluation examples, repository fixtures, or existing vocabulary were used.
These words describe operations; they are not privacy classifications.

This intentionally incomplete lexicon is neither a grammar nor an exhaustive
list of instructions. Spelling variants, dialects, inflections, and compounds
may be absent; membership alone cannot determine the meaning of a sentence.
Multiword entries preserve ordinary internal spaces. All entries use NFC.
"""

from functools import lru_cache
import re
import unicodedata

from secure_gateway.engine.natural_languages import tokenize
from secure_gateway.gateway_workflow_vocabulary import WORKFLOW_OPERATIONS, WORKFLOW_RELATIONS

TASK_OPERATORS: dict[str, frozenset[str]] = {
    "en": frozenset(
        {
            "summarize", "summarise", "compare", "contrast", "group",
            "classify", "categorize", "categorise", "sort", "organize",
            "organise", "arrange", "plan", "outline", "prioritize",
            "include", "add", "keep", "retain", "preserve", "maintain",
            "exclude", "remove", "delete", "omit", "discard", "filter",
            "recommend", "suggest", "propose", "advise", "explain",
            "describe", "clarify", "analyze", "analyse", "review",
            "evaluate", "select", "choose", "combine", "merge",
            "separate", "split", "first", "then", "next", "finally",
            "before", "after", "without", "do not", "don't", "never",
            "allow", "permit", "avoid", "without permission",
        }
    ),
    "ko": frozenset(
        {
            "요약해", "요약하세요", "요약해줘", "요약하라", "비교해",
            "비교하세요", "비교해줘", "대조해", "묶어", "분류해",
            "분류하세요", "정렬해", "정리해", "정리하세요", "배열해",
            "계획해", "계획하세요", "포함해", "포함하세요", "넣어",
            "추가해", "남겨", "유지해", "유지하세요", "보존해",
            "제외해", "제외하세요", "빼", "빼줘", "제거해", "삭제해",
            "생략해", "버려", "추천해", "추천하세요", "제안해",
            "제안하세요", "설명해", "설명하세요", "알려줘", "풀어써",
            "분석해", "검토해", "선택해", "합쳐", "나눠", "먼저",
            "다음에", "그런 다음", "마지막으로", "하지 마",
            "하지 마세요", "없이", "허락 없이", "허용해", "금지해",
        }
    ),
    "es": frozenset(
        {
            "resume", "resumir", "resuma", "compara", "comparar",
            "compare", "contrasta", "agrupa", "agrupar", "clasifica",
            "clasificar", "categoriza", "ordena", "ordenar", "organiza",
            "organizar", "planifica", "planificar", "incluye", "incluir",
            "incluya", "añade", "añadir", "conserva", "conservar",
            "mantén", "mantener", "guarda", "excluye", "excluir",
            "excluya", "elimina", "eliminar", "quita", "quitar", "omite",
            "omitir", "descarta", "recomienda", "recomendar", "sugiere",
            "sugerir", "propone", "proponer", "explica", "explicar",
            "explique", "aclara", "primero", "luego", "después",
            "finalmente", "no", "sin", "evita", "permite", "no hagas",
            "sin permiso",
        }
    ),
    "fr": frozenset(
        {
            "résume", "résumer", "résumez", "compare", "comparer",
            "comparez", "regroupe", "regrouper", "classe", "classer",
            "trie", "trier", "organise", "organiser", "ordonne",
            "planifie", "planifier", "inclus", "inclure", "incluez",
            "ajoute", "ajouter", "garde", "garder", "conserve",
            "conserver", "maintiens", "maintenir", "exclus", "exclure",
            "excluez", "retire", "retirer", "supprime", "supprimer",
            "omets", "omettre", "recommande", "recommander", "suggère",
            "suggérer", "propose", "proposer", "explique", "expliquer",
            "expliquez", "précise", "d'abord", "ensuite", "puis", "enfin",
            "sans", "ne pas", "n'ajoute pas", "ne supprime pas", "évite",
            "permets", "sans autorisation",
        }
    ),
    "pt": frozenset(
        {
            "resuma", "resumir", "resume", "compare", "comparar",
            "compara", "contraste", "agrupe", "agrupar", "agrupa",
            "classifique", "classificar", "categorize", "ordene",
            "ordenar", "organize", "organizar", "planeje", "planejar",
            "planeie", "inclua", "incluir", "inclui", "adicione",
            "adicionar", "acrescente", "mantenha", "manter", "conserve",
            "conservar", "guarde", "exclua", "excluir", "exclui",
            "remova", "remover", "retire", "apague", "elimine", "omita",
            "omitir", "recomende", "recomendar", "sugira", "sugerir",
            "proponha", "propor", "explique", "explicar", "esclareça",
            "primeiro", "depois", "em seguida", "por fim", "não", "sem",
            "evite", "permita", "sem permissão",
        }
    ),
    "de": frozenset(
        {
            "fasse zusammen", "zusammenfassen", "vergleiche",
            "vergleichen", "vergleicht", "gruppiere", "gruppieren",
            "klassifiziere", "klassifizieren", "sortiere", "sortieren",
            "ordne", "ordnen", "organisiere", "organisieren", "plane",
            "planen", "priorisiere", "berücksichtige", "berücksichtigen",
            "füge hinzu", "hinzufügen", "behalte", "behalten", "bewahre",
            "bewahren", "erhalte", "erhalten", "schließe aus",
            "ausschließen", "entferne", "entfernen", "lösche", "löschen",
            "lass weg", "weglassen", "empfiehl", "empfehlen",
            "schlage vor", "vorschlagen", "erkläre", "erklären",
            "beschreibe", "beschreiben", "prüfe", "wähle", "zuerst",
            "dann", "danach", "anschließend", "zuletzt", "nicht", "ohne",
            "vermeide", "erlaube", "ohne Erlaubnis", "nicht entfernen",
        }
    ),
    "id": frozenset(
        {
            "ringkas", "ringkaslah", "rangkum", "rangkumlah",
            "meringkas", "merangkum", "bandingkan", "membandingkan",
            "bedakan", "kelompokkan", "mengelompokkan", "golongkan",
            "klasifikasikan", "kategorikan", "urutkan", "mengurutkan",
            "susun", "susunlah", "atur", "aturlah", "rencanakan",
            "sertakan", "menyertakan", "masukkan", "tambahkan",
            "pertahankan", "simpan", "sisakan", "jaga", "kecualikan",
            "keluarkan", "hapus", "hapuslah", "menghapus", "buang",
            "hilangkan", "abaikan", "saring", "rekomendasikan",
            "sarankan", "usulkan", "jelaskan", "jelaskanlah",
            "terangkan", "uraikan", "perjelas", "pilih", "gabungkan",
            "pisahkan", "pertama", "lalu", "kemudian", "selanjutnya",
            "akhirnya", "jangan", "tanpa", "hindari", "izinkan",
            "tanpa izin",
        }
    ),
    "tr": frozenset(
        {
            "özetle", "özetleyin", "özetlemek", "karşılaştır",
            "karşılaştırın", "karşılaştırmak", "grupla", "gruplayın",
            "gruplandır", "gruplandırın", "sınıflandır", "sınıflandırın",
            "sırala", "sıralayın", "düzenle", "düzenleyin", "planla",
            "planlayın", "dahil et", "dahil edin", "ekle", "ekleyin",
            "tut", "tutun", "koru", "koruyun", "sakla", "saklayın",
            "hariç tut", "hariç tutun", "çıkar", "çıkarın", "kaldır",
            "kaldırın", "sil", "silin", "atla", "atlayın", "öner",
            "önerin", "tavsiye et", "teklif et", "açıkla", "açıklayın",
            "anlat", "anlatın", "seç", "birleştir", "ayır", "önce",
            "sonra", "ardından", "son olarak", "yapma", "yapmayın",
            "olmadan", "izin ver", "izinsiz", "silme",
        }
    ),
    "ru": frozenset(
        {
            "обобщи", "обобщите", "резюмируй", "резюмируйте",
            "сократи", "сократите", "сравни", "сравните", "сравнить",
            "сопоставь", "сопоставьте", "сгруппируй", "сгруппируйте",
            "классифицируй", "классифицируйте", "отсортируй",
            "отсортируйте", "упорядочь", "упорядочьте", "организуй",
            "организуйте", "спланируй", "спланируйте", "включи",
            "включите", "добавь", "добавьте", "оставь", "оставьте",
            "сохрани", "сохраните", "исключи", "исключите", "убери",
            "уберите", "удали", "удалите", "пропусти", "пропустите",
            "порекомендуй", "порекомендуйте", "предложи", "предложите",
            "объясни", "объясните", "поясни", "поясните", "выбери",
            "объедини", "раздели", "сначала", "затем", "потом",
            "наконец", "не", "без", "не удаляй", "разреши",
            "без разрешения",
        }
    ),
    "hi": frozenset(
        {
            "संक्षेप करो", "संक्षेप करें", "संक्षेप में बताओ",
            "संक्षेप में बताएं", "तुलना करो", "तुलना करें", "मिलान करो",
            "समूह बनाओ", "समूह बनाएं", "वर्गीकृत करो", "वर्गीकृत करें",
            "छाँटो", "छाँटें", "क्रम में रखो", "क्रम में रखें",
            "व्यवस्थित करो", "व्यवस्थित करें", "योजना बनाओ",
            "योजना बनाएं", "शामिल करो", "शामिल करें", "जोड़ो", "जोड़ें",
            "रखो", "रखें", "बनाए रखो", "बनाए रखें", "बचाओ", "बचाएं",
            "बाहर करो", "बाहर करें", "हटाओ", "हटाएं", "मिटाओ",
            "मिटाएं", "छोड़ो", "छोड़ें", "सुझाओ", "सुझाएं",
            "सिफारिश करो", "सिफारिश करें", "प्रस्ताव दो",
            "प्रस्ताव दें", "समझाओ", "समझाएं", "बताओ", "बताएं",
            "स्पष्ट करो", "चुनो", "अलग करो", "पहले", "फिर", "इसके बाद",
            "अंत में", "मत करो", "न करें", "बिना", "अनुमति के बिना",
            "अनुमति दो",
        }
    ),
    "mr": frozenset(
        {
            "संक्षेप कर", "संक्षेप करा", "थोडक्यात सांग",
            "थोडक्यात सांगा", "तुलना कर", "तुलना करा", "गट कर",
            "गट करा", "वर्गीकरण कर", "वर्गीकरण करा", "वर्गीकृत कर",
            "वर्गीकृत करा", "क्रम लाव", "क्रम लावा", "मांडणी कर",
            "मांडणी करा", "नियोजन कर", "नियोजन करा", "समाविष्ट कर",
            "समाविष्ट करा", "जोड", "जोडा", "ठेव", "ठेवा", "कायम ठेव",
            "कायम ठेवा", "जप", "जपा", "वगळ", "वगळा", "काढ",
            "काढा", "काढून टाक", "काढून टाका", "हटव", "हटवा",
            "सोड", "सोडा", "सुचव", "सुचवा", "शिफारस कर",
            "शिफारस करा", "प्रस्ताव मांड", "प्रस्ताव मांडा",
            "समजाव", "समजावून सांग", "समजावून सांगा", "स्पष्ट कर",
            "स्पष्ट करा", "निवड", "वेगळे कर", "आधी", "नंतर", "मग",
            "शेवटी", "करू नको", "करू नका", "शिवाय", "परवानगीशिवाय",
            "परवानगी द्या",
        }
    ),
    "bn": frozenset(
        {
            "সংক্ষেপ করো", "সংক্ষেপ করুন", "সংক্ষেপে বলো",
            "সংক্ষেপে বলুন", "সারসংক্ষেপ করো", "সারসংক্ষেপ করুন",
            "তুলনা করো", "তুলনা করুন", "মেলাও", "মেলান",
            "দলবদ্ধ করো", "দলবদ্ধ করুন", "শ্রেণিবদ্ধ করো",
            "শ্রেণিবদ্ধ করুন", "বাছাই করো", "বাছাই করুন", "সাজাও",
            "সাজান", "গুছিয়ে দাও", "গুছিয়ে দিন", "পরিকল্পনা করো",
            "পরিকল্পনা করুন", "অন্তর্ভুক্ত করো", "অন্তর্ভুক্ত করুন",
            "যোগ করো", "যোগ করুন", "রাখো", "রাখুন", "বজায় রাখো",
            "বজায় রাখুন", "সংরক্ষণ করো", "সংরক্ষণ করুন", "বাদ দাও",
            "বাদ দিন", "সরাও", "সরান", "মুছে দাও", "মুছে দিন",
            "এড়িয়ে যাও", "এড়িয়ে যান", "সুপারিশ করো",
            "সুপারিশ করুন", "প্রস্তাব দাও", "প্রস্তাব দিন", "বোঝাও",
            "বোঝান", "ব্যাখ্যা করো", "ব্যাখ্যা করুন", "বেছে নাও",
            "আলাদা করো", "আগে", "তারপর", "পরে", "সবশেষে", "করো না",
            "করবেন না", "ছাড়া", "অনুমতি ছাড়া", "অনুমতি দাও",
        }
    ),
    "ur": frozenset(
        {
            "مختصر کرو", "مختصر کریں", "خلاصہ کرو", "خلاصہ کریں",
            "موازنہ کرو", "موازنہ کریں", "مقابلہ کرو", "گروہ بناؤ",
            "گروہ بنائیں", "درجہ بندی کرو", "درجہ بندی کریں",
            "چھانٹو", "چھانٹیں", "ترتیب دو", "ترتیب دیں", "منظم کرو",
            "منظم کریں", "منصوبہ بناؤ", "منصوبہ بنائیں", "شامل کرو",
            "شامل کریں", "جوڑو", "جوڑیں", "رکھو", "رکھیں",
            "برقرار رکھو", "برقرار رکھیں", "محفوظ رکھو", "محفوظ رکھیں",
            "خارج کرو", "خارج کریں", "ہٹاؤ", "ہٹائیں", "مٹاؤ",
            "مٹائیں", "چھوڑو", "چھوڑیں", "تجویز کرو", "تجویز کریں",
            "سفارش کرو", "سفارش کریں", "سمجھاؤ", "سمجھائیں",
            "وضاحت کرو", "وضاحت کریں", "بتاؤ", "بتائیں", "منتخب کرو",
            "الگ کرو", "پہلے", "پھر", "اس کے بعد", "آخر میں", "مت کرو",
            "نہ کریں", "بغیر", "اجازت کے بغیر", "اجازت دو",
        }
    ),
    "te": frozenset(
        {
            "సంక్షిప్తం చేయి", "సంక్షిప్తం చేయండి", "క్లుప్తంగా చెప్పు",
            "క్లుప్తంగా చెప్పండి", "పోల్చు", "పోల్చండి", "పోల్చి చూడు",
            "పోల్చి చూడండి", "సమూహపరచు", "సమూహపరచండి", "వర్గీకరించు",
            "వర్గీకరించండి", "క్రమబద్ధీకరించు", "క్రమబద్ధీకరించండి",
            "అమర్చు", "అమర్చండి", "ప్రణాళిక వేయి", "ప్రణాళిక వేయండి",
            "చేర్చు", "చేర్చండి", "జోడించు", "జోడించండి", "ఉంచు",
            "ఉంచండి", "కొనసాగించు", "కొనసాగించండి", "భద్రపరచు",
            "భద్రపరచండి", "మినహాయించు", "మినహాయించండి", "తొలగించు",
            "తొలగించండి", "తీసివేయి", "తీసివేయండి", "వదిలేయి",
            "వదిలేయండి", "సిఫారసు చేయి", "సిఫారసు చేయండి", "సూచించు",
            "సూచించండి", "ప్రతిపాదించు", "ప్రతిపాదించండి", "వివరించు",
            "వివరించండి", "చెప్పు", "చెప్పండి", "స్పష్టం చేయి",
            "ఎంచుకో", "విడదీయి", "ముందు", "మొదట", "తర్వాత",
            "ఆ తరువాత", "చివరగా", "చేయవద్దు", "చేయకండి", "లేకుండా",
            "అనుమతి లేకుండా", "అనుమతించు",
        }
    ),
    "ar": frozenset(
        {
            "لخص", "لخّص", "لخصي", "لخصوا", "اختصر", "اختصري",
            "قارن", "قارني", "قارنوا", "قارن بين", "جمّع", "جمع",
            "صنف", "صنّف", "صنفي", "رتب", "رتّب", "رتبي", "نظم",
            "نظّم", "خطط", "خطّط", "أدرج", "أدرجي", "أضف", "أضيفي",
            "احتفظ", "احتفظي", "أبق", "أبقِ", "حافظ", "حافظ على",
            "استبعد", "استبعدي", "احذف", "احذفي", "أزل", "أزيلي",
            "تجاهل", "تخط", "تخطّ", "رشح", "رشّح", "اقترح", "اقترحي",
            "اشرح", "اشرحي", "وضح", "وضّح", "اختر", "ادمج", "افصل",
            "أولا", "أولاً", "ثم", "بعد ذلك", "أخيرا", "لا", "بدون",
            "دون إذن",
        }
    ),
    "zh": frozenset(
        {
            "总结", "總結", "概括", "归纳", "歸納", "比较", "比較",
            "对比", "對比", "分组", "分組", "分类", "分類", "归类",
            "歸類", "排序", "整理", "组织", "組織", "安排", "规划",
            "規劃", "计划", "計劃", "包含", "包括", "加入", "添加",
            "保留", "保持", "保存", "排除", "剔除", "去掉", "移除",
            "删除", "刪除", "省略", "忽略", "推荐", "推薦", "建议",
            "建議", "提议", "提議", "解释", "解釋", "说明", "說明",
            "阐明", "闡明", "首先", "然后", "然後", "接着", "最后",
            "最后再", "不要", "不许", "未经允许",
        }
    ),
    "ja": frozenset(
        {
            "要約して", "要約してください", "要約する", "まとめて",
            "まとめてください", "比較して", "比較してください",
            "比較する", "対比して", "グループ化して", "分類して",
            "分類してください", "分類する", "仕分けて", "並べて",
            "並べ替えて", "整理して", "整理してください", "整理する",
            "計画して", "計画してください", "含めて", "含めてください",
            "含める", "加えて", "追加して", "残して", "残してください",
            "保持して", "維持して", "保存して", "除いて", "除外して",
            "除外してください", "削除して", "削除してください",
            "取り除いて", "省いて", "省略して", "推薦して", "勧めて",
            "提案して", "提案してください", "説明して",
            "説明してください", "説明する", "明確にして", "選んで",
            "分けて", "まず", "最初に", "次に", "その後", "最後に",
            "しないで", "しないでください", "せずに", "なしで",
            "許可なく", "許可して",
        }
    ),
}
EXTRA_OPERATIONS = {
    "en": "infer guess assume invent send reserve book purchase buy execute change modify draft leave out",
    "ko": "추측해 가정해 예약해 구매해 변경해 보내 실행해 빼고 쓰지 쓰세요 마세요 그다음 제시해",
    "es": "supongas adivines inventes envíes reserves compres ejecutes cambies incluyas excluyas elimines omitas borres modifiques",
    "fr": "devine suppose invente envoie réserve achète exécute modifie",
    "pt": "suponha invente envie reserve compre execute altere separe separar",
    "de": "vermute erfinde sende reserviere kaufe führe ändere nenne erstelle erstellen löse lösen",
    "id": "asumsikan tebak kirim pesan beli jalankan ubah",
    "tr": "varsay tahmin gönder rezerve satın çalıştır değiştir listele listeleyin",
    "ru": "предполагай угадывай выдумывай отправляй отправляйте бронируй покупай покупайте выполняй изменяй изменяйте составь составьте описав описывай описывайте указывай указывайте меняй меняйте делай делайте",
    "hi": "अनुमान लगाओ मानो गढ़ो भेजो भेजें खरीदो खरीदें बदलो बदलें",
    "mr": "अंदाज धरा पाठवा आरक्षित खरेदी बदल बदला बदलू देऊ नावे तपशील वेगळा वेगळी वेगळे वेगळ्या त्यानंतर त्याआधी",
    "bn": "অনুমান পাঠাও কিনো বদলাও",
    "ur": "اندازہ فرض بھیجیں خریدیں بدلیں",
    "te": "ఊహించు ఊహించండి పంపు పంపండి కొనండి కొనుగోలు మార్చు మార్చండి చేర్చు చేర్చండి తొలగించు తొలగించండి",
    "ar": "تفترض تخمن تخترع ترسل تحجز تشتري تنفذ تنفّذ تغير تغيّر",
    "zh": "猜测 假设 编造 发送 预订 购买 执行 修改 擅自",
    "ja": "推測 仮定 捏造 送信 予約 購入 実行 変更",
}

# Task nouns are grammatical roles too: 'a summary of X' remains actionable
# even when X is private. These are reviewed operation/output words, not an
# inferred allowlist of arbitrary compounds or confidential domain terms.
TASK_NOUNS = {
    "en": "summary comparison classification recommendation explanation plan order condition permission assumption checklist steps result",
    "ko": "요약 비교 분류 추천 설명 계획 순서 조건 허가 가정 점검표 단계 결과",
    "es": "resumen comparación clasificación recomendación explicación plan orden condición permiso suposición lista pasos resultado",
    "fr": "résumé comparaison classification recommandation explication plan ordre condition permission hypothèse étapes résultat",
    "pt": "resumo comparação classificação recomendação explicação plano ordem condição permissão hipótese etapas resultado",
    "de": "Zusammenfassung Vergleich Klassifizierung Empfehlung Erklärung Plan Reihenfolge Bedingung Erlaubnis Annahme Schritte Ergebnis",
    "id": "ringkasan perbandingan klasifikasi rekomendasi penjelasan rencana urutan kondisi izin asumsi langkah hasil draf",
    "tr": "özet karşılaştırma sınıflandırma öneri açıklama plan sıra koşul izin varsayım adım sonuç",
    "ru": "резюме сравнение классификация рекомендация объяснение план порядок условие разрешение предположение шаги результат",
    "hi": "सारांश तुलना वर्गीकरण सिफारिश व्याख्या योजना क्रम शर्त अनुमति धारणा चरण परिणाम",
    "mr": "सारांश तुलना वर्गीकरण शिफारस स्पष्टीकरण योजना क्रम अट परवानगी गृहीतक पायऱ्या परिणाम",
    "bn": "সারাংশ তুলনা শ্রেণিবিন্যাস সুপারিশ ব্যাখ্যা পরিকল্পনা ক্রম শর্ত অনুমতি ধারণা ধাপ ফলাফল",
    "ur": "خلاصہ موازنہ درجہ بندی سفارش وضاحت منصوبہ ترتیب شرط اجازت مفروضہ مراحل نتیجہ",
    "te": "సారాంశం పోలిక వర్గీకరణ సిఫార్సు వివరణ ప్రణాళిక క్రమం షరతు అనుమతి ఊహ దశలు ఫలితం",
    "ar": "ملخص مقارنة تصنيف توصية شرح خطة ترتيب شرط إذن افتراض خطوات نتيجة",
    "zh": "摘要 总结 比较 分类 建议 说明 计划 顺序 条件 许可 假设 步骤 结果",
    "ja": "要約 比較 分類 推薦 説明 計画 順序 条件 許可 仮定 手順 結果",
}


@lru_cache(maxsize=17)
def operator_words(language: str) -> frozenset[str]:
    """Exact lexical components and reviewed inflections of task operators."""
    words = {unicodedata.normalize("NFC", chunk.text).casefold()
             for phrase in (*TASK_OPERATORS.get(language, ()), *WORKFLOW_OPERATIONS.get(language, ()), *WORKFLOW_RELATIONS.get(language, ()))
             for chunk in tokenize(phrase, language) if chunk.is_word}
    words.update(EXTRA_OPERATIONS.get(language, "").split())
    words.update(word.casefold() for word in TASK_NOUNS.get(language, "").split())
    if language == "ko":
        for word in tuple(words):
            if word.endswith("해"):
                root = word[:-1]
                words.update(root + ending for ending in ("하고", "하지", "하여", "해서", "하되", "할", "하기", "하는", "한", "하라"))
        # Reviewed predicate stems keep conditional, negative and relative
        # instructions readable; never strip arbitrary unknown/name stems.
        stems = "고르 추리 나열하 작성하 표시하 명시하 설명하 알리 알려 비교하 요약하 정리하 선택하 확인하 판단하 결정하 충족하 부족하 필요하 가능하 불가능하 분명하 불분명하 확실하 불확실하 적합하 맞 다르 일치하 비 비우 없 있 남기 유지하 보내 예약하 연락하 삭제하 변경하 제안하 권하 권장하 추천하 수정하 검토하 검증하 중단하 진행하 제출하".split()
        endings = "고 지 지는 지도 지만 면 다면 는지 도록 거나 면서 기 기에 기를 는 던 게 세요 십시오".split()
        words.update(stem + ending for stem in stems for ending in endings)
    elif language == "te":
        for word in tuple(words):
            if word.endswith("ు"):
                words.add(word[:-1] + "వద్దు")
    elif language == "mr":
        for word in tuple(words):
            if word.endswith("ा") and len(word) > 2:
                words.add(word[:-1] + "ू")
    elif language == "tr":
        # Only exact reviewed operator roots, never arbitrary stripped stems.
        for word in tuple(words):
            if word in TASK_OPERATORS[language] or word in EXTRA_OPERATIONS[language].split():
                words.update(word + suffix for suffix in ("ıp", "ip", "up", "üp", "arak", "erek", "ma", "me", "mayın", "meyin"))
    elif language == "ar":
        for word in tuple(words):
            words.update(prefix + word for prefix in ("و", "ف"))
    return frozenset(words)


@lru_cache(maxsize=17)
def _capital_operators(language: str) -> frozenset[str]:
    return frozenset(chunk.text.casefold()
                     for phrase in (*TASK_OPERATORS.get(language, ()), *WORKFLOW_OPERATIONS.get(language, ()), EXTRA_OPERATIONS.get(language, ""))
                     for chunk in tokenize(phrase, language) if chunk.is_word)


# Positive grammatical cues constrain a capitalization exception. In languages
# with articles, imperatives normally take a determiner; sequencing markers can
# precede another reviewed operator. This deliberately trades some coverage for
# keeping ambiguous capitalized subjects private.
_IMPERATIVE_CUE_TEXT = {
    "en": "the a an this that these those it them me us my our your both each all any no two three four five six first next then finally please not only for from with by into out missing blank empty unclear required optional",
    "es": "el la los las un una unos unas este esta estos estas esto eso ambos ambas cada todo toda todos todas dos tres cuatro primero después luego no para por con sin según",
    "fr": "le la les un une des ce cet cette ces ceci cela tout toute tous toutes deux trois quatre ensuite puis ne pour avec sans par selon d'abord",
    "pt": "o a os as um uma uns umas este esta estes estas isso isto ambos ambas cada todo toda todos todas dois duas três quatro primeiro depois não para com sem por conforme",
    "de": "den die das dem der des ein eine einen einem einer eines diese dieser dieses diesen diesem zuerst dann danach anschließend bitte nicht keine kein keinen zwei drei vier für aus mit nach ohne zusammen weg fehlende fehlenden leere unklare",
    "id": "ini itu saya kami kita kamu semua setiap dua tiga empat terlebih dahulu kemudian jangan untuk dengan dari menurut tanpa",
    "tr": "bu şu bunları şunları beni bize iki üç dört önce sonra lütfen için göre ile",
    "ru": "это эти этот эту все всё каждый каждую оба обе два две три четыре сначала затем пожалуйста не для по с без",
}
_IMPERATIVE_CUES = {language: frozenset(words.split()) for language, words in _IMPERATIVE_CUE_TEXT.items()}
_CLAUSE_MARKERS = frozenset("first next then finally no ne não zuerst dann danach anschließend nicht jangan önce sonra ardından сначала затем потом не".split())
_ENGLISH_FINITE = frozenset(word for word in WORKFLOW_OPERATIONS["en"] if word.endswith(("s", "ed"))) | frozenset(
    "is was were has had does did can could may might must should will would works offers announced acquired said bought wrote made kept sent".split()
)
_ENGLISH_PREDICATE = re.compile(
    r"\s+(?:(?:only|first|next|then|finally|already|also|usually|often|always)\s+)*(?P<verb>[A-Za-z]+)", re.IGNORECASE
)


def operator_capital_positions(text: str, language: str) -> frozenset[int]:
    """Scope sentence-initial instruction capitals to this occurrence only.

    A standalone 'Compare' is still a private name. An earlier private mapping
    or explicit rule overrides even a matching instruction position.
    """
    words = _capital_operators(language)
    positions = set()
    for match in re.finditer(
        r"(?:\A\s*|[.!?。！？]\s*|\n\s*)(?P<word>[^\W\d_]+)\s+(?P<next>[^\W_]+(?:['’][^\W_]+)?)", text
    ):
        if match.group("word").casefold() not in words:
            continue
        if language == "en":
            predicate = _ENGLISH_PREDICATE.match(text, match.end("word"))
            if predicate and predicate.group("verb").casefold() in _ENGLISH_FINITE:
                continue
        following = match.group("next").replace("’", "'")
        if following != following.casefold() or not (
            following.isdecimal() or following in _IMPERATIVE_CUES.get(language, frozenset())
            or following in TASK_NOUNS.get(language, "").casefold().split()
            or (match.group("word").casefold() in _CLAUSE_MARKERS and following in words)
        ):
            continue
        positions.add(match.start("word"))
    return frozenset(positions)
