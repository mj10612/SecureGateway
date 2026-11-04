# SecureGateway — اردو

[English](README.en.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Português](README.pt.md) · [Deutsch](README.de.md) · [Bahasa Indonesia](README.id.md) · [Türkçe](README.tr.md) · [Русский](README.ru.md) · [हिन्दी](README.hi.md) · [मराठी](README.mr.md) · [বাংলা](README.bn.md) · [اردو](README.ur.md) · [العربية](README.ar.md) · [తెలుగు](README.te.md) · [简体中文](README.zh.md) · [日本語](README.ja.md)

[README](../../README.md) · [Gateway](../GATEWAY.md) · [MCP / Hook](../LOCAL_INTEGRATION.md) · [Languages](../LANGUAGES.md)

SecureGateway معاون متن اور سورس کوڈ کو AI فراہم کنندہ کو بھیجنے سے پہلے مقامی طور پر ماسک کرتا ہے۔ مقامی Gateway جوابات اور ٹول کے آرگومنٹس کو اصل صورت میں بحال کرتا ہے۔ میپنگ مقامی میموری یا خفیہ کردہ مقامی اسنیپ شاٹ میں رہتی ہے۔

## تنصیب

Python 3.10 یا نیا ورژن، uv اور Git تیار کریں اور پہلے Claude Code یا Codex میں لاگ ان کریں۔ تنصیب لاگ ان فائلوں کو محفوظ رکھتے ہوئے صارف کی فراہم کنندہ ترتیبات اور خودکار آغاز ترتیب دیتی ہے۔ اس کے بعد AI کلائنٹ دوبارہ شروع کریں۔ پہلے ٹیسٹ کے لیے تنصیب سے پہلے کی گفتگو جاری رکھنے کے بجائے نئی گفتگو شروع کریں۔

```sh
git clone https://github.com/mj10612/SecureGateway.git
cd SecureGateway
uv tool install .
```

کمانڈ نہ ملے تو `uv tool update-shell` چلائیں اور ٹرمینل دوبارہ کھولیں۔

```sh
secure-gateway gateway install --agent both
secure-gateway gateway status
```

## استعمال

یہ مثال واضح طور پر اردو منتخب کرتی ہے۔ Gateway کے متن کے لیے موجودہ کنفیگریشن میں natural_language کو ur کریں، باقی فیلڈ برقرار رکھیں اور Gateway دوبارہ شروع کریں۔ سورس کوڈ کے اعداد بطورِ طے شدہ برقرار رہتے ہیں۔ gateway diagnostics سیشن کی مجموعی حدود دکھاتا ہے۔

```sh
secure-gateway mask "جائزے کے لیے نمونہ دستاویز" --language ur --json-output
secure-gateway gateway diagnostics
```

## دائرہ اور حدود

زبان کی معاونت لغوی ہے اور ماسکنگ اندازوں پر مبنی ہے۔ درست بحالی اس بات کی ضمانت نہیں کہ ماسک شدہ کوڈ کا ہر رویہ برقرار ہے۔ تصاویر اور غیر معاون دور دراز منسلکات روکے جاتے ہیں۔ uncommon_words میں عام الفاظ کا اندرونی ذخیرہ صرف انگریزی اور کوریائی کے لیے ہے؛ دوسری زبانوں میں مواد کو احتیاط سے ماسک کیا جاتا ہے۔ صرف MCP سرور شامل کرنے سے پرامپٹ نہیں روکے جاتے۔ بحالی ماڈل کے سیاق سے باہر کسی قابلِ اعتماد مقامی ایپ میں کریں۔

## بند کرنا اور ہٹانا

ترتیبات ہٹانے سے پہلے سروس بند کریں۔ ان انسٹال اپنے زیرِ انتظام ترتیبات بحال کرتا ہے اور بعد کی صارف تبدیلیاں اوور رائٹ نہیں کرتا۔ میزبان ترتیبات کے لیے براہِ راست سِم لنک کے بجائے عام فائلیں استعمال کریں۔ اپ ڈیٹ اور بحالی کے لیے مرکزی رہنما دیکھیں۔

```sh
secure-gateway gateway stop
secure-gateway gateway uninstall
uv tool uninstall secure-gateway
```
