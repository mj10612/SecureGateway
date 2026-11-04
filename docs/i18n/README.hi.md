# SecureGateway — हिन्दी

[English](README.en.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Português](README.pt.md) · [Deutsch](README.de.md) · [Bahasa Indonesia](README.id.md) · [Türkçe](README.tr.md) · [Русский](README.ru.md) · [हिन्दी](README.hi.md) · [मराठी](README.mr.md) · [বাংলা](README.bn.md) · [اردو](README.ur.md) · [العربية](README.ar.md) · [తెలుగు](README.te.md) · [简体中文](README.zh.md) · [日本語](README.ja.md)

[README](../../README.md) · [Gateway](../GATEWAY.md) · [MCP / Hook](../LOCAL_INTEGRATION.md) · [Languages](../LANGUAGES.md)

SecureGateway समर्थित पाठ और स्रोत कोड को AI प्रदाता के पास भेजने से पहले स्थानीय रूप से मास्क करता है। स्थानीय Gateway उत्तरों और टूल के आर्ग्युमेंट को मूल रूप में लौटाता है। मैपिंग स्थानीय मेमोरी या एन्क्रिप्ट किए गए स्थानीय स्नैपशॉट में रहती है।

## स्थापना

Python 3.10 या नया संस्करण, uv और Git तैयार रखें तथा पहले Claude Code या Codex में लॉग इन करें। स्थापना लॉगिन फ़ाइलों को सुरक्षित रखते हुए उपयोगकर्ता के प्रदाता सेटिंग और अपने आप शुरू होने की व्यवस्था बदलती है। स्थापना के बाद AI क्लाइंट फिर शुरू करें। पहले परीक्षण के लिए स्थापना से पहले की बातचीत जारी रखने के बजाय नई बातचीत शुरू करें।

```sh
git clone https://github.com/mj10612/SecureGateway.git
cd SecureGateway
uv tool install .
```

कमांड न मिले तो `uv tool update-shell` चलाएँ और टर्मिनल दोबारा खोलें।

```sh
secure-gateway gateway install --agent both
secure-gateway gateway status
```

## उपयोग

यह उदाहरण हिन्दी को स्पष्ट रूप से चुनता है। Gateway के पाठ के लिए मौजूदा कॉन्फ़िगरेशन में natural_language को hi करें, बाकी फ़ील्ड बनाए रखें और Gateway फिर शुरू करें। स्रोत कोड की संख्याएँ डिफ़ॉल्ट रूप से सुरक्षित रहती हैं। gateway diagnostics से सत्र की कुल सीमाएँ देखें।

```sh
secure-gateway mask "समीक्षा के लिए उदाहरण दस्तावेज़" --language hi --json-output
secure-gateway gateway diagnostics
```

## दायरा और सीमाएँ

भाषा समर्थन शब्द-आधारित है और मास्किंग अनुमान-आधारित है। बिल्कुल सही बहाली से यह साबित नहीं होता कि मास्क किया गया कोड हर तरह से वही व्यवहार करेगा। चित्र और असमर्थित दूरस्थ अटैचमेंट रोके जाते हैं। uncommon_words में सामान्य शब्दों का अंतर्निहित संग्रह केवल अंग्रेज़ी और कोरियाई के लिए है; दूसरी भाषाओं में सामग्री को सावधानी से मास्क किया जाता है। केवल MCP सर्वर जोड़ने से प्रॉम्प्ट बीच में नहीं रोके जाते। बहाली मॉडल के संदर्भ से बाहर किसी भरोसेमंद स्थानीय ऐप में करें।

## रोकना और हटाना

सेटिंग हटाने से पहले सेवा रोकें। हटाने की प्रक्रिया अपने प्रबंधित सेटिंग वापस लाती है और बाद के उपयोगकर्ता बदलावों को नहीं लिखती। होस्ट सेटिंग के लिए सीधे प्रतीकात्मक लिंक के बजाय सामान्य फ़ाइलें इस्तेमाल करें। अपडेट और पुनर्प्राप्ति के लिए मुख्य गाइड देखें।

```sh
secure-gateway gateway stop
secure-gateway gateway uninstall
uv tool uninstall secure-gateway
```
