# SecureGateway — 简体中文

[English](README.en.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Português](README.pt.md) · [Deutsch](README.de.md) · [Bahasa Indonesia](README.id.md) · [Türkçe](README.tr.md) · [Русский](README.ru.md) · [हिन्दी](README.hi.md) · [मराठी](README.mr.md) · [বাংলা](README.bn.md) · [اردو](README.ur.md) · [العربية](README.ar.md) · [తెలుగు](README.te.md) · [简体中文](README.zh.md) · [日本語](README.ja.md)

[README](../../README.md) · [Gateway](../GATEWAY.md) · [MCP / Hook](../LOCAL_INTEGRATION.md) · [Languages](../LANGUAGES.md)

SecureGateway 在向 AI 服务商发送内容前，在本地对支持的文本和源代码进行掩码处理。本地 Gateway 会还原回复和工具参数。映射表保存在本地内存或加密的本地快照中。

## 安装

请准备 Python 3.10 或更高版本、uv 和 Git，并先登录 Claude Code 或 Codex。安装会配置用户级服务商设置和自动启动，同时保留登录文件。安装后请重新启动 AI 客户端。 首次测试请新建对话，不要继续安装前已有的对话。

```sh
git clone https://github.com/mj10612/SecureGateway.git
cd SecureGateway
uv tool install .
```

如果找不到命令，请运行 `uv tool update-shell`，然后重新打开终端。

```sh
secure-gateway gateway install --agent both
secure-gateway gateway status
```

## 使用

下例明确选择中文。对于 Gateway 中的普通文本，请在现有配置中将 natural_language 设置为 zh，保留其他字段后重启 Gateway。源代码中的数字默认保留。gateway diagnostics 可查看会话的汇总限制。

```sh
secure-gateway mask "待审阅的示例文档" --language zh --json-output
secure-gateway gateway diagnostics
```

## 支持范围与限制

语言支持基于词法处理，掩码采用启发式规则。精确还原不代表掩码代码的所有行为都保持不变。图片和不支持的远程附件会被阻止。uncommon_words 仅内置英语和韩语常用词表；其他语言采用保守的内容词掩码。仅添加 MCP 服务器不会拦截提示词。还原应在模型上下文之外的可信本地应用中进行。自动语言检测无法区分所有共享文字系统的语言，必要时请明确指定语言。

## 停止与卸载

移除设置前请先停止服务。卸载会还原其管理的设置，并拒绝覆盖用户后续的修改。主机设置请使用普通文件，而非直接的符号链接。升级和恢复步骤请参考主指南。

```sh
secure-gateway gateway stop
secure-gateway gateway uninstall
uv tool uninstall secure-gateway
```
