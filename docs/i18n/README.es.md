# SecureGateway — Español

[English](README.en.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Português](README.pt.md) · [Deutsch](README.de.md) · [Bahasa Indonesia](README.id.md) · [Türkçe](README.tr.md) · [Русский](README.ru.md) · [हिन्दी](README.hi.md) · [मराठी](README.mr.md) · [বাংলা](README.bn.md) · [اردو](README.ur.md) · [العربية](README.ar.md) · [తెలుగు](README.te.md) · [简体中文](README.zh.md) · [日本語](README.ja.md)

[README](../../README.md) · [Gateway](../GATEWAY.md) · [MCP / Hook](../LOCAL_INTEGRATION.md) · [Languages](../LANGUAGES.md)

SecureGateway enmascara localmente el texto y el código compatibles antes de enviarlos al proveedor de IA. El Gateway local restaura las respuestas y los argumentos de las herramientas. Las correspondencias se guardan en memoria local o en instantáneas locales cifradas.

## Instalación

Necesitas Python 3.10 o posterior, uv y Git. Inicia sesión en Claude Code o Codex antes de instalar. La instalación modifica la configuración de proveedor del usuario y activa el inicio automático, conservando los archivos de inicio de sesión. Reinicia el cliente de IA después. Para la primera prueba, inicia una conversación nueva en lugar de continuar una anterior a la instalación.

```sh
git clone https://github.com/mj10612/SecureGateway.git
cd SecureGateway
uv tool install .
```

Si no se encuentra el comando, ejecuta `uv tool update-shell` y vuelve a abrir la terminal.

```sh
secure-gateway gateway install --agent both
secure-gateway gateway status
```

## Uso

El ejemplo selecciona español explícitamente. Para el texto del Gateway, establece natural_language en es dentro de la configuración existente, conserva los demás campos y reinicia el Gateway. Los números del código fuente se conservan por defecto. gateway diagnostics muestra límites agregados de las sesiones.

```sh
secure-gateway mask "Documento de ejemplo para revisar" --language es --json-output
secure-gateway gateway diagnostics
```

## Alcance y límites

El soporte es léxico y el enmascaramiento es heurístico: una restauración exacta no garantiza que el código anonimizado conserve todo su comportamiento. Se bloquean las imágenes y los adjuntos remotos no compatibles. uncommon_words solo incluye vocabulario común para inglés y coreano; los demás idiomas usan enmascaramiento conservador del contenido. Añadir un servidor MCP no intercepta los mensajes. Restaura el contenido en una aplicación local de confianza, fuera del contexto del modelo.

## Detener y desinstalar

Detén el proceso antes de eliminar su configuración. La desinstalación restaura los ajustes propios y rechaza sobrescribir cambios posteriores del usuario. Usa archivos normales para los ajustes del cliente, no enlaces simbólicos directos. Consulta la guía principal para actualizar o recuperar la instalación.

```sh
secure-gateway gateway stop
secure-gateway gateway uninstall
uv tool uninstall secure-gateway
```
