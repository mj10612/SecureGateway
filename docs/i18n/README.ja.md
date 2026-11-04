# SecureGateway — 日本語

[English](README.en.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Português](README.pt.md) · [Deutsch](README.de.md) · [Bahasa Indonesia](README.id.md) · [Türkçe](README.tr.md) · [Русский](README.ru.md) · [हिन्दी](README.hi.md) · [मराठी](README.mr.md) · [বাংলা](README.bn.md) · [اردو](README.ur.md) · [العربية](README.ar.md) · [తెలుగు](README.te.md) · [简体中文](README.zh.md) · [日本語](README.ja.md)

[README](../../README.md) · [Gateway](../GATEWAY.md) · [MCP / Hook](../LOCAL_INTEGRATION.md) · [Languages](../LANGUAGES.md)

SecureGateway は、対応する文章とソースコードを AI 提供元へ送る前にローカルでマスキングします。ローカル Gateway が応答とツール引数を復元します。対応表はローカルメモリまたは暗号化したローカルスナップショットに保存します。

## インストール

Python 3.10 以降、uv、Git を用意し、先に Claude Code または Codex にログインしてください。セットアップはログインファイルを保持したまま、ユーザー全体の提供元設定と自動起動を構成します。完了後は AI クライアントを再起動してください。 最初のテストは、設定前の会話を再開せず、新しい会話で始めてください。

```sh
git clone https://github.com/mj10612/SecureGateway.git
cd SecureGateway
uv tool install .
```

コマンドが見つからない場合は `uv tool update-shell` を実行し、ターミナルを開き直してください。

```sh
secure-gateway gateway install --agent both
secure-gateway gateway status
```

## 使い方

次の例では日本語を明示的に選択します。Gateway の文章には、既存設定の他の項目を保持して natural_language を ja に設定し、Gateway を再起動します。ソースコードの数値は標準で保持します。gateway diagnostics でセッションの集計上限を確認できます。

```sh
secure-gateway mask "確認するサンプル文書" --language ja --json-output
secure-gateway gateway diagnostics
```

## 対応範囲と制限

言語対応は字句処理に基づき、マスキングはヒューリスティックです。原文を正確に復元できても、マスキングしたコードの全動作が保持される保証はありません。画像と未対応のリモート添付は遮断します。uncommon_words の内蔵一般語彙は英語と韓国語のみで、他の言語では内容語を保守的にマスキングします。MCP サーバーの追加だけではプロンプトを仲介しません。復元はモデルの文脈外にある信頼できるローカルアプリで行ってください。共有文字を使う言語の自動判定には限界があるため、必要に応じて言語を明示してください。

## 停止と削除

設定を削除する前にサービスを停止してください。削除時は管理対象の設定を復元し、その後のユーザー編集は上書きしません。ホスト設定には直接のシンボリックリンクではなく通常のファイルを使用してください。更新と復旧はメインガイドを参照してください。

```sh
secure-gateway gateway stop
secure-gateway gateway uninstall
uv tool uninstall secure-gateway
```
