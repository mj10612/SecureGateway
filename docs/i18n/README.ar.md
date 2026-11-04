# SecureGateway — العربية

[English](README.en.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Português](README.pt.md) · [Deutsch](README.de.md) · [Bahasa Indonesia](README.id.md) · [Türkçe](README.tr.md) · [Русский](README.ru.md) · [हिन्दी](README.hi.md) · [मराठी](README.mr.md) · [বাংলা](README.bn.md) · [اردو](README.ur.md) · [العربية](README.ar.md) · [తెలుగు](README.te.md) · [简体中文](README.zh.md) · [日本語](README.ja.md)

[README](../../README.md) · [Gateway](../GATEWAY.md) · [MCP / Hook](../LOCAL_INTEGRATION.md) · [Languages](../LANGUAGES.md)

يخفي SecureGateway النصوص والشيفرات المدعومة محليًا قبل إرسالها إلى مزود الذكاء الاصطناعي. تستعيد البوابة المحلية الردود ووسائط الأدوات. تبقى جداول المطابقة في الذاكرة المحلية أو في لقطات محلية مشفرة.

## التثبيت

جهّز Python 3.10 أو أحدث وuv وGit، وسجّل الدخول إلى Claude Code أو Codex أولًا. يضبط التثبيت إعدادات المزود على مستوى المستخدم والتشغيل التلقائي مع الحفاظ على ملفات تسجيل الدخول. أعد تشغيل عميل الذكاء الاصطناعي بعد التثبيت. للاختبار الأول، ابدأ محادثة جديدة بدل متابعة محادثة أُنشئت قبل الإعداد.

```sh
git clone https://github.com/mj10612/SecureGateway.git
cd SecureGateway
uv tool install .
```

إذا لم يُعثر على الأمر، شغّل `uv tool update-shell` ثم أعد فتح الطرفية.

```sh
secure-gateway gateway install --agent both
secure-gateway gateway status
```

## الاستخدام

يحدد المثال اللغة العربية صراحة. لنصوص Gateway، اجعل قيمة natural_language هي ar في ملف الإعدادات الموجود مع الحفاظ على بقية الحقول، ثم أعد تشغيل البوابة. تبقى أرقام الشيفرة الأصلية كما هي افتراضيًا. يعرض gateway diagnostics الحدود الإجمالية للجلسات.

```sh
secure-gateway mask "مستند نموذجي للمراجعة" --language ar --json-output
secure-gateway gateway diagnostics
```

## النطاق والقيود

دعم اللغات معجمي والإخفاء يعتمد على قواعد تقريبية. الاستعادة الدقيقة لا تضمن الحفاظ على جميع سلوكيات الشيفرة المخفية. تُحظر الصور والمرفقات البعيدة غير المدعومة. تتوفر المفردات الشائعة المدمجة في uncommon_words للإنجليزية والكورية فقط؛ تستخدم اللغات الأخرى إخفاءً محافظًا للمحتوى. إضافة خادم MCP وحدها لا تعترض المطالبات. نفّذ الاستعادة في تطبيق محلي موثوق خارج سياق النموذج.

## الإيقاف والإزالة

أوقف الخدمة قبل إزالة الإعدادات. تعيد الإزالة الإعدادات التي تديرها وترفض الكتابة فوق تعديلات المستخدم اللاحقة. استخدم ملفات إعدادات عادية بدل الروابط الرمزية المباشرة. راجع الدليل الرئيسي للتحديث والاسترداد.

```sh
secure-gateway gateway stop
secure-gateway gateway uninstall
uv tool uninstall secure-gateway
```
