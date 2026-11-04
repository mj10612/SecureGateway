# SecureGateway — Français

[English](README.en.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Português](README.pt.md) · [Deutsch](README.de.md) · [Bahasa Indonesia](README.id.md) · [Türkçe](README.tr.md) · [Русский](README.ru.md) · [हिन्दी](README.hi.md) · [मराठी](README.mr.md) · [বাংলা](README.bn.md) · [اردو](README.ur.md) · [العربية](README.ar.md) · [తెలుగు](README.te.md) · [简体中文](README.zh.md) · [日本語](README.ja.md)

[README](../../README.md) · [Gateway](../GATEWAY.md) · [MCP / Hook](../LOCAL_INTEGRATION.md) · [Languages](../LANGUAGES.md)

SecureGateway masque localement le texte et le code pris en charge avant leur envoi au fournisseur IA. Le Gateway local restaure les réponses et les arguments des outils. Les correspondances restent en mémoire locale ou dans des instantanés locaux chiffrés.

## Installation

Préparez Python 3.10 ou ultérieur, uv et Git, puis connectez-vous à Claude Code ou Codex. La configuration modifie les paramètres du fournisseur au niveau utilisateur et active le démarrage automatique tout en conservant les fichiers de connexion. Redémarrez ensuite le client IA. Pour le premier essai, démarrez une nouvelle conversation au lieu de reprendre une conversation antérieure à la configuration.

```sh
git clone https://github.com/mj10612/SecureGateway.git
cd SecureGateway
uv tool install .
```

Si la commande est introuvable, exécutez `uv tool update-shell`, puis rouvrez le terminal.

```sh
secure-gateway gateway install --agent both
secure-gateway gateway status
```

## Utilisation

Cet exemple sélectionne explicitement le français. Pour le texte du Gateway, définissez natural_language sur fr dans la configuration existante, conservez les autres champs et redémarrez le Gateway. Les nombres du code source sont conservés par défaut. gateway diagnostics affiche les limites agrégées des sessions.

```sh
secure-gateway mask "Document exemple à examiner" --language fr --json-output
secure-gateway gateway diagnostics
```

## Portée et limites

La prise en charge est lexicale et le masquage heuristique : une restauration exacte ne garantit pas que le code masqué conserve tous ses comportements. Les images et pièces jointes distantes non prises en charge sont bloquées. Le vocabulaire courant intégré de uncommon_words est limité à anglais et coréen ; les autres langues utilisent un masquage conservateur du contenu. Ajouter un serveur MCP ne suffit pas à intercepter les messages. La restauration doit rester dans une application locale de confiance, hors du contexte du modèle.

## Arrêt et désinstallation

Arrêtez le service avant de supprimer sa configuration. La désinstallation restaure les paramètres gérés et refuse de remplacer les modifications ultérieures. Utilisez des fichiers de configuration ordinaires plutôt que des liens symboliques directs. Consultez le guide principal pour les mises à jour et la récupération.

```sh
secure-gateway gateway stop
secure-gateway gateway uninstall
uv tool uninstall secure-gateway
```
