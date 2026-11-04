# SecureGateway — Deutsch

[English](README.en.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Português](README.pt.md) · [Deutsch](README.de.md) · [Bahasa Indonesia](README.id.md) · [Türkçe](README.tr.md) · [Русский](README.ru.md) · [हिन्दी](README.hi.md) · [मराठी](README.mr.md) · [বাংলা](README.bn.md) · [اردو](README.ur.md) · [العربية](README.ar.md) · [తెలుగు](README.te.md) · [简体中文](README.zh.md) · [日本語](README.ja.md)

[README](../../README.md) · [Gateway](../GATEWAY.md) · [MCP / Hook](../LOCAL_INTEGRATION.md) · [Languages](../LANGUAGES.md)

SecureGateway maskiert unterstützten Text und Quellcode lokal vor dem Versand an den KI-Anbieter. Das lokale Gateway stellt Antworten und Werkzeugargumente wieder her. Zuordnungen bleiben im lokalen Speicher oder in verschlüsselten lokalen Snapshots.

## Installation

Benötigt werden Python ab 3.10, uv und Git. Melden Sie sich zuerst bei Claude Code oder Codex an. Die Einrichtung ändert die Anbieter-Einstellungen des Benutzers und aktiviert den Autostart; Anmeldedateien bleiben erhalten. Starten Sie den KI-Client danach neu. Beginnen Sie den ersten Test mit einer neuen Unterhaltung statt einer vor der Einrichtung begonnenen Sitzung.

```sh
git clone https://github.com/mj10612/SecureGateway.git
cd SecureGateway
uv tool install .
```

Falls der Befehl nicht gefunden wird, führen Sie `uv tool update-shell` aus und öffnen Sie das Terminal erneut.

```sh
secure-gateway gateway install --agent both
secure-gateway gateway status
```

## Verwendung

Das Beispiel wählt Deutsch ausdrücklich aus. Setzen Sie für Gateway-Text natural_language in der vorhandenen Konfiguration auf de, behalten Sie alle anderen Felder bei und starten Sie das Gateway neu. Zahlen im Quellcode bleiben standardmäßig erhalten. gateway diagnostics zeigt zusammengefasste Sitzungslimits.

```sh
secure-gateway mask "Beispieldokument zur Prüfung" --language de --json-output
secure-gateway gateway diagnostics
```

## Umfang und Grenzen

Die Sprachunterstützung ist lexikalisch und die Maskierung heuristisch. Eine exakte Wiederherstellung garantiert nicht, dass maskierter Code jedes Verhalten beibehält. Bilder und nicht unterstützte entfernte Anhänge werden blockiert. uncommon_words enthält allgemeinen Wortschatz nur für Englisch und Koreanisch; andere Sprachen verwenden konservative Inhaltsmaskierung. Ein MCP-Server allein fängt keine Prompts ab. Wiederherstellung gehört in eine vertrauenswürdige lokale Anwendung außerhalb des Modellkontexts.

## Anhalten und entfernen

Halten Sie den Dienst vor dem Entfernen der Einstellungen an. Die Deinstallation stellt verwaltete Einstellungen wieder her und überschreibt keine späteren Benutzeränderungen. Verwenden Sie normale Einstellungsdateien statt direkter symbolischer Links. Hinweise zu Updates und Wiederherstellung stehen im Hauptleitfaden.

```sh
secure-gateway gateway stop
secure-gateway gateway uninstall
uv tool uninstall secure-gateway
```
