# SecureGateway — বাংলা

[English](README.en.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Português](README.pt.md) · [Deutsch](README.de.md) · [Bahasa Indonesia](README.id.md) · [Türkçe](README.tr.md) · [Русский](README.ru.md) · [हिन्दी](README.hi.md) · [मराठी](README.mr.md) · [বাংলা](README.bn.md) · [اردو](README.ur.md) · [العربية](README.ar.md) · [తెలుగు](README.te.md) · [简体中文](README.zh.md) · [日本語](README.ja.md)

[README](../../README.md) · [Gateway](../GATEWAY.md) · [MCP / Hook](../LOCAL_INTEGRATION.md) · [Languages](../LANGUAGES.md)

SecureGateway সমর্থিত লেখা ও সোর্স কোড AI প্রদানকারীর কাছে পাঠানোর আগে স্থানীয়ভাবে মাস্ক করে। স্থানীয় Gateway উত্তর ও টুলের আর্গুমেন্ট মূল অবস্থায় ফেরায়। ম্যাপিং স্থানীয় মেমরি বা এনক্রিপ্ট করা স্থানীয় স্ন্যাপশটে থাকে।

## ইনস্টলেশন

Python 3.10 বা নতুন সংস্করণ, uv ও Git প্রস্তুত রাখুন এবং আগে Claude Code বা Codex-এ লগইন করুন। ইনস্টলেশন লগইন ফাইল অক্ষত রেখে ব্যবহারকারীর প্রদানকারী সেটিং ও স্বয়ংক্রিয় চালু হওয়া কনফিগার করে। পরে AI ক্লায়েন্ট পুনরায় চালু করুন। প্রথম পরীক্ষায় ইনস্টলেশনের আগের কথোপকথন চালিয়ে না গিয়ে নতুন কথোপকথন শুরু করুন।

```sh
git clone https://github.com/mj10612/SecureGateway.git
cd SecureGateway
uv tool install .
```

কমান্ড না পাওয়া গেলে `uv tool update-shell` চালিয়ে টার্মিনাল আবার খুলুন।

```sh
secure-gateway gateway install --agent both
secure-gateway gateway status
```

## ব্যবহার

উদাহরণটি সরাসরি বাংলা নির্বাচন করে। Gateway-এর লেখার জন্য বিদ্যমান কনফিগারেশনে natural_language-এর মান bn দিন, অন্য ফিল্ড অক্ষত রাখুন এবং Gateway পুনরায় চালু করুন। সোর্স কোডের সংখ্যা ডিফল্টভাবে অপরিবর্তিত থাকে। gateway diagnostics সেশনের সামগ্রিক সীমা দেখায়।

```sh
secure-gateway mask "পর্যালোচনার জন্য নমুনা নথি" --language bn --json-output
secure-gateway gateway diagnostics
```

## পরিসর ও সীমাবদ্ধতা

ভাষা সমর্থন শব্দভিত্তিক এবং মাস্কিং হিউরিস্টিক পদ্ধতির। হুবহু মূল লেখা ফেরত পাওয়া মানেই মাস্ক করা কোডের সব আচরণ অক্ষত আছে এমন নয়। ছবি ও অসমর্থিত দূরবর্তী সংযুক্তি বন্ধ করা হয়। uncommon_words-এর অন্তর্নির্মিত সাধারণ শব্দভান্ডার কেবল ইংরেজি ও কোরীয় ভাষায় আছে; অন্য ভাষায় বিষয়বস্তু সতর্কভাবে মাস্ক করা হয়। শুধু MCP সার্ভার যোগ করলে প্রম্পট আটকানো হয় না। মডেলের প্রসঙ্গের বাইরে বিশ্বস্ত স্থানীয় অ্যাপে মূল তথ্য পুনরুদ্ধার করুন।

## বন্ধ করা ও সরানো

সেটিং সরানোর আগে পরিষেবা বন্ধ করুন। আনইনস্টল পরিচালিত সেটিং ফিরিয়ে আনে এবং পরে করা ব্যবহারকারীর পরিবর্তন ওভাররাইট করে না। হোস্ট সেটিংয়ে সরাসরি সিমলিংকের বদলে সাধারণ ফাইল ব্যবহার করুন। আপডেট ও পুনরুদ্ধারের জন্য মূল নির্দেশিকা দেখুন।

```sh
secure-gateway gateway stop
secure-gateway gateway uninstall
uv tool uninstall secure-gateway
```
