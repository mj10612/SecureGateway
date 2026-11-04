# SecureGateway — Türkçe

[English](README.en.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Português](README.pt.md) · [Deutsch](README.de.md) · [Bahasa Indonesia](README.id.md) · [Türkçe](README.tr.md) · [Русский](README.ru.md) · [हिन्दी](README.hi.md) · [मराठी](README.mr.md) · [বাংলা](README.bn.md) · [اردو](README.ur.md) · [العربية](README.ar.md) · [తెలుగు](README.te.md) · [简体中文](README.zh.md) · [日本語](README.ja.md)

[README](../../README.md) · [Gateway](../GATEWAY.md) · [MCP / Hook](../LOCAL_INTEGRATION.md) · [Languages](../LANGUAGES.md)

SecureGateway, desteklenen metin ve kaynak kodunu AI sağlayıcısına göndermeden önce yerel olarak maskeler. Yerel Gateway yanıtları ve araç bağımsız değişkenlerini geri yükler. Eşlemeler yerel bellekte veya şifreli yerel anlık görüntülerde tutulur.

## Kurulum

Python 3.10 veya üstünü, uv ve Git hazırlayın; önce Claude Code veya Codex hesabınıza giriş yapın. Kurulum, giriş dosyalarını koruyarak kullanıcı düzeyindeki sağlayıcı ayarlarını ve otomatik başlatmayı yapılandırır. Sonrasında AI istemcisini yeniden başlatın. İlk denemede kurulumdan önceki bir konuşmayı sürdürmek yerine yeni bir konuşma başlatın.

```sh
git clone https://github.com/mj10612/SecureGateway.git
cd SecureGateway
uv tool install .
```

Komut bulunamazsa `uv tool update-shell` çalıştırın ve terminali yeniden açın.

```sh
secure-gateway gateway install --agent both
secure-gateway gateway status
```

## Kullanım

Örnek, Türkçeyi açıkça seçer. Gateway metni için mevcut yapılandırmada natural_language değerini tr yapın, diğer alanları koruyun ve Gateway uygulamasını yeniden başlatın. Kaynak koddaki sayılar varsayılan olarak korunur. gateway diagnostics toplam oturum sınırlarını gösterir.

```sh
secure-gateway mask "İncelenecek örnek belge" --language tr --json-output
secure-gateway gateway diagnostics
```

## Kapsam ve sınırlar

Dil desteği sözcükseldir ve maskeleme sezgiseldir; tam geri yükleme, maskelenmiş kodun tüm davranışlarının korunduğunu kanıtlamaz. Görseller ve desteklenmeyen uzak ekler engellenir. uncommon_words yalnızca İngilizce ve Korece için yerleşik yaygın sözcük listesi sunar; diğer dillerde temkinli içerik maskelemesi kullanılır. Yalnızca MCP sunucusu eklemek istemleri yakalamaz. Geri yükleme, model bağlamının dışında güvenilir yerel uygulamada yapılmalıdır.

## Durdurma ve kaldırma

Ayarları kaldırmadan önce hizmeti durdurun. Kaldırma, yönetilen ayarları geri yükler ve sonraki kullanıcı değişikliklerinin üzerine yazmayı reddeder. Doğrudan sembolik bağlantılar yerine normal ayar dosyaları kullanın. Güncelleme ve kurtarma için ana kılavuza bakın.

```sh
secure-gateway gateway stop
secure-gateway gateway uninstall
uv tool uninstall secure-gateway
```
