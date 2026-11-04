# SecureGateway — Bahasa Indonesia

[English](README.en.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Português](README.pt.md) · [Deutsch](README.de.md) · [Bahasa Indonesia](README.id.md) · [Türkçe](README.tr.md) · [Русский](README.ru.md) · [हिन्दी](README.hi.md) · [मराठी](README.mr.md) · [বাংলা](README.bn.md) · [اردو](README.ur.md) · [العربية](README.ar.md) · [తెలుగు](README.te.md) · [简体中文](README.zh.md) · [日本語](README.ja.md)

[README](../../README.md) · [Gateway](../GATEWAY.md) · [MCP / Hook](../LOCAL_INTEGRATION.md) · [Languages](../LANGUAGES.md)

SecureGateway menyamarkan teks dan kode yang didukung secara lokal sebelum mengirimkannya ke penyedia AI. Gateway lokal memulihkan jawaban dan argumen alat. Pemetaan disimpan di memori lokal atau snapshot lokal terenkripsi.

## Pemasangan

Siapkan Python 3.10 atau lebih baru, uv, dan Git, lalu masuk ke Claude Code atau Codex terlebih dahulu. Pemasangan mengubah pengaturan penyedia pada tingkat pengguna dan mengaktifkan mulai otomatis tanpa menghapus berkas login. Mulai ulang klien AI setelahnya. Untuk pengujian pertama, mulai percakapan baru, bukan melanjutkan percakapan sebelum pemasangan.

```sh
git clone https://github.com/mj10612/SecureGateway.git
cd SecureGateway
uv tool install .
```

Jika perintah tidak ditemukan, jalankan `uv tool update-shell` lalu buka ulang terminal.

```sh
secure-gateway gateway install --agent both
secure-gateway gateway status
```

## Penggunaan

Contoh memilih bahasa Indonesia secara eksplisit. Untuk teks Gateway, atur natural_language menjadi id pada konfigurasi yang sudah ada, pertahankan kolom lainnya, lalu mulai ulang Gateway. Angka dalam kode sumber dipertahankan secara bawaan. gateway diagnostics menampilkan batas sesi secara agregat.

```sh
secure-gateway mask "Dokumen contoh untuk ditinjau" --language id --json-output
secure-gateway gateway diagnostics
```

## Cakupan dan batasan

Dukungan bahasa bersifat leksikal dan penyamaran menggunakan heuristik. Pemulihan yang tepat tidak menjamin seluruh perilaku kode yang disamarkan tetap sama. Gambar dan lampiran jarak jauh yang tidak didukung akan diblokir. uncommon_words hanya menyertakan kosakata umum untuk bahasa Inggris dan Korea; bahasa lain memakai penyamaran konten yang konservatif. Menambahkan server MCP saja tidak mencegat prompt. Pemulihan dilakukan dalam aplikasi lokal tepercaya, di luar konteks model.

## Menghentikan dan menghapus

Hentikan layanan sebelum menghapus pengaturannya. Penghapusan memulihkan pengaturan yang dikelola dan menolak menimpa perubahan pengguna berikutnya. Gunakan berkas pengaturan biasa, bukan tautan simbolis langsung. Lihat panduan utama untuk pembaruan dan pemulihan.

```sh
secure-gateway gateway stop
secure-gateway gateway uninstall
uv tool uninstall secure-gateway
```
