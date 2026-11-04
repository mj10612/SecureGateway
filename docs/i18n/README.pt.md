# SecureGateway — Português

[English](README.en.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Português](README.pt.md) · [Deutsch](README.de.md) · [Bahasa Indonesia](README.id.md) · [Türkçe](README.tr.md) · [Русский](README.ru.md) · [हिन्दी](README.hi.md) · [मराठी](README.mr.md) · [বাংলা](README.bn.md) · [اردو](README.ur.md) · [العربية](README.ar.md) · [తెలుగు](README.te.md) · [简体中文](README.zh.md) · [日本語](README.ja.md)

[README](../../README.md) · [Gateway](../GATEWAY.md) · [MCP / Hook](../LOCAL_INTEGRATION.md) · [Languages](../LANGUAGES.md)

O SecureGateway mascara localmente texto e código compatíveis antes de enviá-los ao provedor de IA. O Gateway local restaura respostas e argumentos de ferramentas. As correspondências ficam na memória local ou em snapshots locais criptografados.

## Instalação

Prepare Python 3.10 ou mais recente, uv e Git e entre no Claude Code ou Codex primeiro. A instalação altera as configurações do provedor para o usuário e ativa a inicialização automática, preservando os arquivos de login. Reinicie o cliente de IA depois. No primeiro teste, inicie uma conversa nova em vez de retomar uma conversa anterior à instalação.

```sh
git clone https://github.com/mj10612/SecureGateway.git
cd SecureGateway
uv tool install .
```

Se o comando não for encontrado, execute `uv tool update-shell` e abra o terminal novamente.

```sh
secure-gateway gateway install --agent both
secure-gateway gateway status
```

## Uso

O exemplo seleciona português explicitamente. Para o texto do Gateway, defina natural_language como pt na configuração existente, mantenha os outros campos e reinicie o Gateway. Números no código-fonte são preservados por padrão. gateway diagnostics mostra os limites agregados das sessões.

```sh
secure-gateway mask "Documento de exemplo para revisão" --language pt --json-output
secure-gateway gateway diagnostics
```

## Escopo e limites

O suporte é lexical e o mascaramento é heurístico: restaurar o original com exatidão não garante todos os comportamentos do código mascarado. Imagens e anexos remotos não compatíveis são bloqueados. uncommon_words tem vocabulário comum integrado apenas para inglês e coreano; os demais idiomas usam mascaramento conservador de conteúdo. Adicionar um servidor MCP não intercepta prompts. A restauração deve ocorrer em um aplicativo local confiável, fora do contexto do modelo.

## Parar e remover

Pare o serviço antes de remover as configurações. A desinstalação restaura os ajustes gerenciados e se recusa a sobrescrever alterações posteriores. Use arquivos normais de configuração, não links simbólicos diretos. Veja o guia principal para atualização e recuperação.

```sh
secure-gateway gateway stop
secure-gateway gateway uninstall
uv tool uninstall secure-gateway
```
