# SecureGateway — 한국어

[English](README.en.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Português](README.pt.md) · [Deutsch](README.de.md) · [Bahasa Indonesia](README.id.md) · [Türkçe](README.tr.md) · [Русский](README.ru.md) · [हिन्दी](README.hi.md) · [मराठी](README.mr.md) · [বাংলা](README.bn.md) · [اردو](README.ur.md) · [العربية](README.ar.md) · [తెలుగు](README.te.md) · [简体中文](README.zh.md) · [日本語](README.ja.md)

[README](../../README.md) · [Gateway](../GATEWAY.md) · [MCP / Hook](../LOCAL_INTEGRATION.md) · [Languages](../LANGUAGES.md)

SecureGateway는 지원하는 평문과 소스 코드를 AI 제공자에게 보내기 전에 로컬에서 마스킹합니다. 로컬 Gateway가 답변과 도구 인수를 복원합니다. 매핑 표는 로컬 메모리 또는 암호화된 로컬 스냅샷에 보관합니다.

## 설치

Python 3.10 이상, uv, Git을 준비하고 Claude Code 또는 Codex에 먼저 로그인하세요. 설치는 로그인 파일을 보존하면서 사용자 전체의 제공자 설정과 자동 시작을 구성합니다. 설치 후 AI 클라이언트를 다시 시작하세요. 첫 시험은 설치 전 대화를 이어가지 말고 새 대화로 시작하세요.

```sh
git clone https://github.com/mj10612/SecureGateway.git
cd SecureGateway
uv tool install .
```

명령을 찾지 못하면 `uv tool update-shell`을 실행하고 터미널을 다시 여세요.

```sh
secure-gateway gateway install --agent both
secure-gateway gateway status
```

## 사용

아래 예제는 한국어를 명시적으로 선택합니다. Gateway 평문 언어는 기존 설정 파일의 다른 항목을 유지한 채 natural_language 값을 ko로 지정하고 Gateway를 다시 시작하면 됩니다. 소스 코드의 숫자는 기본적으로 보존합니다. gateway diagnostics로 세션의 집계 한도를 확인할 수 있습니다.

```sh
secure-gateway mask "검토할 예제 문서" --language ko --json-output
secure-gateway gateway diagnostics
```

## 지원 범위와 제한

언어 지원은 어휘 처리 기반이며 마스킹은 휴리스틱입니다. 원문을 정확히 복원하더라도 마스킹된 코드의 모든 실행 의미를 보장하지는 않습니다. 이미지와 지원하지 않는 원격 첨부는 차단합니다. uncommon_words의 내장 일반 어휘는 영어·한국어에만 제공하며 다른 언어는 보수적으로 내용어를 마스킹합니다. MCP 서버만 추가해서는 프롬프트를 가로채지 않습니다. 복원은 모델 문맥 밖의 신뢰할 수 있는 로컬 앱에서 수행하세요.

## 중지와 제거

설정을 제거하기 전에 데몬을 중지하세요. 제거는 소유권을 확인한 설정을 복원하고 이후 사용자 편집은 덮어쓰지 않습니다. 호스트 설정은 직접 심볼릭 링크 대신 일반 파일을 사용하세요. 업그레이드·복구는 기본 안내를 참고하세요.

```sh
secure-gateway gateway stop
secure-gateway gateway uninstall
uv tool uninstall secure-gateway
```
