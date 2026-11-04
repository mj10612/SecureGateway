# SecureGateway — मराठी

[English](README.en.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Português](README.pt.md) · [Deutsch](README.de.md) · [Bahasa Indonesia](README.id.md) · [Türkçe](README.tr.md) · [Русский](README.ru.md) · [हिन्दी](README.hi.md) · [मराठी](README.mr.md) · [বাংলা](README.bn.md) · [اردو](README.ur.md) · [العربية](README.ar.md) · [తెలుగు](README.te.md) · [简体中文](README.zh.md) · [日本語](README.ja.md)

[README](../../README.md) · [Gateway](../GATEWAY.md) · [MCP / Hook](../LOCAL_INTEGRATION.md) · [Languages](../LANGUAGES.md)

SecureGateway समर्थित मजकूर आणि स्रोत कोड AI प्रदात्याकडे पाठवण्यापूर्वी स्थानिक पातळीवर मास्क करते. स्थानिक Gateway उत्तरे आणि टूलचे आर्ग्युमेंट मूळ स्वरूपात आणते. मॅपिंग स्थानिक मेमरीत किंवा कूटबद्ध स्थानिक स्नॅपशॉटमध्ये राहते.

## स्थापना

Python 3.10 किंवा नवीन आवृत्ती, uv आणि Git तयार ठेवा आणि आधी Claude Code किंवा Codex मध्ये लॉग इन करा. स्थापना लॉगिन फाइल जपून वापरकर्त्याच्या प्रदाता सेटिंग आणि स्वयंचलित प्रारंभाची व्यवस्था बदलते. त्यानंतर AI क्लायंट पुन्हा सुरू करा. पहिल्या चाचणीसाठी स्थापनेपूर्वीचे संभाषण पुढे नेण्याऐवजी नवीन संभाषण सुरू करा.

```sh
git clone https://github.com/mj10612/SecureGateway.git
cd SecureGateway
uv tool install .
```

आज्ञा सापडत नसल्यास `uv tool update-shell` चालवा आणि टर्मिनल पुन्हा उघडा.

```sh
secure-gateway gateway install --agent both
secure-gateway gateway status
```

## वापर

या उदाहरणात मराठी स्पष्टपणे निवडली आहे. Gateway मजकुरासाठी सध्याच्या कॉन्फिगरेशनमध्ये natural_language चे मूल्य mr करा, इतर फील्ड जपून Gateway पुन्हा सुरू करा. स्रोत कोडमधील संख्या मूळतः जशाच्या तशा ठेवल्या जातात. gateway diagnostics सत्रांच्या एकत्रित मर्यादा दाखवते.

```sh
secure-gateway mask "पुनरावलोकनासाठी उदाहरण दस्तऐवज" --language mr --json-output
secure-gateway gateway diagnostics
```

## व्याप्ती आणि मर्यादा

भाषा समर्थन शब्दविश्लेषणावर आणि मास्किंग अनुमानांवर आधारित आहे. अचूक पुनर्स्थापना झाली तरी मास्क केलेल्या कोडचे सर्व वर्तन जतन झाले असे सिद्ध होत नाही. प्रतिमा आणि असमर्थित दूरस्थ जोडण्या रोखल्या जातात. uncommon_words मध्ये सामान्य शब्दांचा अंगभूत संच फक्त इंग्रजी आणि कोरियनसाठी आहे; इतर भाषांमध्ये मजकूर सावधपणे मास्क होतो. केवळ MCP सर्व्हर जोडल्याने प्रॉम्प्ट अडवले जात नाहीत. पुनर्स्थापना मॉडेलच्या संदर्भाबाहेर विश्वसनीय स्थानिक अॅपमध्ये करा.

## थांबवणे आणि काढून टाकणे

सेटिंग काढण्यापूर्वी सेवा थांबवा. काढण्याची प्रक्रिया व्यवस्थापित सेटिंग पूर्ववत करते आणि नंतरचे वापरकर्ता बदल अधिलिखित करत नाही. होस्ट सेटिंगसाठी थेट प्रतीकात्मक दुव्यांऐवजी नियमित फाइल वापरा. अद्यतन आणि पुनर्प्राप्तीसाठी मुख्य मार्गदर्शक पाहा.

```sh
secure-gateway gateway stop
secure-gateway gateway uninstall
uv tool uninstall secure-gateway
```
