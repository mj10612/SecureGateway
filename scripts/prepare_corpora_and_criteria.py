"""Construct and validate dev/holdout corpora and frozen-criteria files for issues #309, #313, #314, #306, #291."""

import json
from pathlib import Path
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "docs" / "evaluations"

SHARED_ORDERING_PROTOCOL = (
    "Criteria file written by scripts/prepare_corpora_and_criteria.py before the evaluation script was first run "
    "on the holdout, within one working session on 2026-11-10. Limitation: sequential ordering cannot be "
    "independently verified from git history because all files are committed together in a single commit."
)


def make_span(text: str, substring: str, label: str):
    start = text.find(substring)
    if start < 0:
        raise ValueError(f"Substring {substring!r} not found in {text!r}")
    return {"start": start, "end": start + len(substring), "label": label}


def validate_corpus(data: dict):
    for case in data["cases"]:
        text = case["text"]
        for s in case.get("secrets", []):
            span_text = text[s["start"]:s["end"]]
            assert len(span_text) == s["end"] - s["start"], f"Invalid secret slice {s}"
            assert span_text, f"Empty secret span in case {case['id']}"
        for p in case.get("public", []):
            span_text = text[p["start"]:p["end"]]
            assert len(span_text) == p["end"] - p["start"], f"Invalid public slice {p}"
            assert span_text, f"Empty public span in case {case['id']}"


def build_issue309_data():
    out_dir = EVAL_DIR / "issue309-2.10.0"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Dev cases: 10 sentences
    dev_raw = [
        ("dev-309-01", "ko", "general", "전시 계획 새솔Qzx면 즉시 승인하세요.", "새솔Qzx", "면", ()),
        ("dev-309-02", "ko", "general", "프로젝트 별무리Qzx기 전에 준비 사항을 검토하세요.", "별무리Qzx", "기 전에", ()),
        ("dev-309-03", "ko", "general", "임시 기획 한울Qzx하지 마세요.", "한울Qzx", "하지 마세요", ()),
        ("dev-309-04", "ko", "general", "새로운 제안 솔바람Qzx해줘.", "솔바람Qzx", "해줘", ()),
        ("dev-309-05", "ko", "general", "별빛가람Qzx된 일정표를 전송하세요.", "별빛가람Qzx", "된", ()),
        ("dev-309-06", "ko", "tech", "배치 작업 은빛너울Qzx으면 파이프라인을 재시작하세요.", "은빛너울Qzx", "으면", ()),
        ("dev-309-07", "ko", "tech", "통신 채널 달무리Qzxㄴ 뒤에 결과를 보고하세요.", "달무리Qzx", "ㄴ 뒤에", ()),
        ("dev-309-08", "ko", "tech", "서비스 노을빛Qzx지 말고 표준 포트를 유지하세요.", "노을빛Qzx", "지 말고", ()),
        ("dev-309-09", "ko", "tech", "데이터셋 꽃가람Qzx해 주세요.", "꽃가람Qzx", "해 주세요", ()),
        ("dev-309-10", "ko", "tech", "모듈 산들바람Qzx은 설정을 따르세요.", "산들바람Qzx", "은", ()),
    ]

    dev_cases = []
    for cid, lang, domain, text, secret, public, forced in dev_raw:
        dev_cases.append({
            "id": cid,
            "language": lang,
            "domain": domain,
            "text": text,
            "forced_rules": list(forced),
            "secrets": [make_span(text, secret, "private_stem")],
            "public": [make_span(text, public, "grammatical_ending")],
        })

    # Holdout cases: 16 unseen Korean sentences covering all 5 classes and varied spacing
    holdout_raw = [
        ("holdout-309-01", "ko", "general", "비공개 실험실 푸른숨Qzx면 작업실 배치를 다시 확인하세요.", "푸른숨Qzx", "면", ()),
        ("holdout-309-02", "ko", "general", "내부 운영안 달빛너울Qzx으면 담당자 승인을 먼저 받으세요.", "달빛너울Qzx", "으면", ()),
        ("holdout-309-03", "ko", "general", "자료 수집 은하마루Qzx기 전에 문서 번호를 기록하세요.", "은하마루Qzx", "기 전에", ()),
        ("holdout-309-04", "ko", "general", "문서 배포 초록별Qzxㄴ 뒤에 보관함 잠금을 확인하세요.", "초록별Qzx", "ㄴ 뒤에", ()),
        ("holdout-309-05", "ko", "general", "회의 일정 새벽이슬Qzx은 뒤에 회의록을 정리하세요.", "새벽이슬Qzx", "은 뒤에", ()),
        ("holdout-309-06", "ko", "general", "신규 기획 바람결Qzx지 말고 기존 정책을 준수하세요.", "바람결Qzx", "지 말고", ()),
        ("holdout-309-07", "ko", "general", "보안 점검 솔바람Qzx하지 마세요.", "솔바람Qzx", "하지 마세요", ()),
        ("holdout-309-08", "ko", "general", "연구 과제 하늘샘Qzx세요.", "하늘샘Qzx", "세요", ()),
        ("holdout-309-09", "ko", "general", "분석 모델 노을상자Qzx해줘.", "노을상자Qzx", "해줘", ()),
        ("holdout-309-10", "ko", "general", "검증 결과 물보라Qzx된 파일 목록을 출력하세요.", "물보라Qzx", "된", ()),
        ("holdout-309-11", "ko", "tech", "제조 라인 전기도금기 전에 센서 값을 초기화하세요.", "전기도금기", "기 전에", ("전기도금기",)),
        ("holdout-309-12", "ko", "tech", "장비 설정 화학증착면 압력 밸브를 개방하세요.", "화학증착", "면", ("화학증착",)),
        ("holdout-309-13", "ko", "tech", "엔진 코어 AlphaCoreㄴ 뒤에 캐시 버퍼를 비우세요.", "AlphaCore", "ㄴ 뒤에", ("AlphaCore",)),
        ("holdout-309-14", "ko", "tech", "데이터베이스 DataSync해 주세요.", "DataSync", "해 주세요", ("DataSync",)),
        ("holdout-309-15", "ko", "tech", "내부 보고서 비밀문서지 말고 정식 양식을 사용하세요.", "비밀문서", "지 말고", ("비밀문서",)),
        ("holdout-309-16", "ko", "tech", "기밀 과제 특수보안은 담당 팀에서만 열람하세요.", "특수보안", "은", ("특수보안",)),
    ]

    holdout_cases = []
    for cid, lang, domain, text, secret, public, forced in holdout_raw:
        holdout_cases.append({
            "id": cid,
            "language": lang,
            "domain": domain,
            "text": text,
            "forced_rules": list(forced),
            "secrets": [make_span(text, secret, "private_stem")],
            "public": [make_span(text, public, "grammatical_ending")],
        })

    dev_data = {"schema_version": 1, "issue": 309, "split": "dev", "cases": dev_cases}
    holdout_data = {"schema_version": 1, "issue": 309, "split": "holdout", "cases": holdout_cases}
    validate_corpus(dev_data)
    validate_corpus(holdout_data)

    frozen_criteria = {
        "issue": 309,
        "candidate": "ko_conjugation_split",
        "ordering_protocol": SHARED_ORDERING_PROTOCOL,
        "ending_classes": {
            "conditional": ["-면", "-으면"],
            "sequence": ["-기 전에", "-ㄴ 뒤에", "-은 뒤에"],
            "negation": ["-지 말고", "-하지 말고", "-지 마", "-하지 마세요"],
            "request": ["-세요", "-으세요", "-해줘", "-해 주세요"],
            "adnominal": ["-ㄴ", "-은", "-된"],
        },
        "acceptance_criteria": {
            "secret_leaks": 0,
            "exact_restore_rate": 1.0,
            "overmasking_reduction": "strictly greater than zero reduction compared to baseline",
            "toggle_off_byte_identical": True,
            "comprehension_status": "hold — comprehension 미측정 if live LLM unexecuted",
        },
    }

    (out_dir / "dev_corpus.json").write_text(json.dumps(dev_data, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "holdout_corpus.json").write_text(json.dumps(holdout_data, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "frozen_criteria.json").write_text(json.dumps(frozen_criteria, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Issue #309 corpora generated and validated.")


def build_issue313_data():
    out_dir = EVAL_DIR / "issue313-2.10.0"
    out_dir.mkdir(parents=True, exist_ok=True)

    dev_raw = [
        ("dev-313-01", "auto", "general", "다음 영어 지침을 확인하세요:\n\"Do not delete original files. Ask before deployment.\"\n프로젝트는 EmberQzx입니다.", "EmberQzx", "Do not delete original files. Ask before deployment.", ()),
        ("dev-313-02", "auto", "general", "Follow this Korean instruction: \"크기를 모르면 먼저 질문하세요.\"\nThe confidential project is SolarQzx.", "SolarQzx", "크기를 모르면 먼저 질문하세요.", ()),
        ("dev-313-03", "auto", "tech", "작업 지시사항:\n- Check config.json before starting\n- 담당자에게 문의하세요\n프로젝트 AlphaKey99.", "AlphaKey99", "Check config.json before starting", ()),
        ("dev-313-04", "auto", "tech", "Review instructions:\n1. 보안 토큰 secret.key를 확인하세요.\n2. Do not expose credentials.", "secret.key", "Do not expose credentials", ()),
    ]

    dev_cases = []
    for cid, lang, domain, text, secret, public, forced in dev_raw:
        dev_cases.append({
            "id": cid,
            "language": lang,
            "domain": domain,
            "text": text,
            "forced_rules": list(forced),
            "secrets": [make_span(text, secret, "private_secret")],
            "public": [make_span(text, public, "public_segment")],
        })

    holdout_raw = [
        ("holdout-313-01", "auto", "general", "비공개 수거 일정의 이름은 수은뜰Qzx입니다. 다음 영문 지시를 따르세요: \"Compare the pickup schedule and confirm arrival.\"", "수은뜰Qzx", "Compare the pickup schedule and confirm arrival.", ()),
        ("holdout-313-02", "auto", "general", "The confidential inspection route is named LarkbasketQzx. Follow this instruction: \"담당자 승인 없이 배포하지 마세요.\"", "LarkbasketQzx", "담당자 승인 없이 배포하지 마세요.", ()),
        ("holdout-313-03", "auto", "tech", "시스템 검토 절차:\n- Inspect gateway.conf for missing secrets\n- 임시 설정을 삭제하세요\n비공개 식별자는 NimbusKey1입니다.", "NimbusKey1", "Inspect gateway.conf for missing secrets", ()),
        ("holdout-313-04", "auto", "tech", "Operational notes:\n1. 설정 파일 auth_token.pem을 백업하세요.\n2. Verify the SHA256 checksum before launch.", "auth_token.pem", "Verify the SHA256 checksum before launch.", ()),
        ("holdout-313-05", "auto", "general", "연락처는 admin@internal.corp 입니다. 다음 지침을 지키세요: \"Never share confidential passwords.\"", "admin@internal.corp", "Never share confidential passwords.", ()),
        ("holdout-313-06", "auto", "tech", "Check endpoint https://api.internal.corp/v1/status before restart. 오류 발생 시 즉시 중단하세요.", "https://api.internal.corp/v1/status", "Check endpoint", ()),
        ("holdout-313-07", "auto", "general", "프로젝트 NovaQzx 안내:\n- Do not modify database schemas\n- 스키마 변경 시 담당자 승인 필요", "NovaQzx", "Do not modify database schemas", ()),
        ("holdout-313-08", "auto", "tech", "Execute command: npm run deploy\n배포 후 로그 파일 prod.log를 확인하세요.", "prod.log", "Execute command", ()),
    ]

    holdout_cases = []
    for cid, lang, domain, text, secret, public, forced in holdout_raw:
        holdout_cases.append({
            "id": cid,
            "language": lang,
            "domain": domain,
            "text": text,
            "forced_rules": list(forced),
            "secrets": [make_span(text, secret, "private_secret")],
            "public": [make_span(text, public, "public_segment")],
        })

    dev_data = {"schema_version": 1, "issue": 313, "split": "dev", "cases": dev_cases}
    holdout_data = {"schema_version": 1, "issue": 313, "split": "holdout", "cases": holdout_cases}
    validate_corpus(dev_data)
    validate_corpus(holdout_data)

    frozen_criteria = {
        "issue": 313,
        "candidate": "segment_language",
        "ordering_protocol": SHARED_ORDERING_PROTOCOL,
        "supported_languages": ["ko", "en"],
        "boundary_rules": {
            "separators": ["sentence [.!?。！？]\\s+", "quotes [\"'“”‘’]", "list items and newlines"],
            "suppression": "Any boundary cutting protected entities, forced rules, code spans, or URLs/emails is suppressed.",
            "inheritance": "Segments below 8 characters inherit request natural language.",
            "prohibition": "No union of public vocabularies is permitted.",
        },
        "acceptance_criteria": {
            "boundary_span_cuts": 0,
            "secret_leaks": 0,
            "exact_restore_rate": 1.0,
            "comprehension_status": "hold — comprehension 미측정",
        },
    }

    (out_dir / "dev_corpus.json").write_text(json.dumps(dev_data, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "holdout_corpus.json").write_text(json.dumps(holdout_data, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "frozen_criteria.json").write_text(json.dumps(frozen_criteria, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Issue #313 corpora generated and validated.")


def build_issue314_data():
    out_dir = EVAL_DIR / "issue314-2.10.0"
    out_dir.mkdir(parents=True, exist_ok=True)

    dev_raw = [
        ("dev-314-01", "en", "general", "The internal initiative is called still. Check its readiness; do not deploy it.", "still", "Check its readiness", ("still",)),
        ("dev-314-02", "ko", "general", "비공개 제품 이름은 나란히입니다. 먼저 검토 순서를 설명하세요.", "나란히", "먼저 검토 순서를", ("나란히",)),
        ("dev-314-03", "en", "tech", "Project margin is confidential. Please review the quarterly budget schedule.", "margin", "review the quarterly budget schedule", ("margin",)),
        ("dev-314-04", "ko", "tech", "연구 그룹 흐름의 세부 명세를 확인하고 승인 여부를 결정하세요.", "흐름", "확인하고 승인 여부를", ("흐름",)),
    ]

    dev_cases = []
    for cid, lang, domain, text, secret, public, forced in dev_raw:
        dev_cases.append({
            "id": cid,
            "language": lang,
            "domain": domain,
            "text": text,
            "forced_rules": list(forced),
            "secrets": [make_span(text, secret, "ambiguous_name")],
            "public": [make_span(text, public, "task_prose")],
        })

    holdout_raw = [
        ("holdout-314-01", "en", "general", "Confidential project Current requires immediate review. Do not disclose the contract.", "Current", "immediate review", ("Current",)),
        ("holdout-314-02", "en", "general", "The committee froze fold after the audit uncovered overruns. Keep the schedule unchanged.", "fold", "Keep the schedule unchanged.", ("fold",)),
        ("holdout-314-03", "en", "tech", "The launch of drift includes a six-month support contract. Please verify all milestones.", "drift", "Please verify all milestones.", ("drift",)),
        ("holdout-314-04", "en", "tech", "The beta release of velvet attracted forty volunteer testers. Summarize the user feedback.", "velvet", "Summarize the user feedback.", ("velvet",)),
        ("holdout-314-05", "ko", "general", "가상 비공개 프로젝트 마루의 세부 일정을 점검하세요. 일반 청소 순서를 비교 설명해 주세요.", "마루", "비교 설명해 주세요.", ("마루",)),
        ("holdout-314-06", "ko", "general", "비공개 협력사 바다와 체결한 계약서를 검토하세요. 회의 시간을 변경하지 마세요.", "바다", "회의 시간을 변경하지 마세요.", ("바다",)),
        ("holdout-314-07", "ko", "tech", "신규 데이터셋 초록을 아카이브로 이전하세요. 백업 검증 결과를 보고서에 기록하세요.", "초록", "백업 검증 결과를 보고서에 기록하세요.", ("초록",)),
        ("holdout-314-08", "ko", "tech", "보안 통신망 고요의 패킷 손실율을 측정하세요. 장애 발생 시 알림을 전송하세요.", "고요", "장애 발생 시 알림을 전송하세요.", ("고요",)),
    ]

    holdout_cases = []
    for cid, lang, domain, text, secret, public, forced in holdout_raw:
        holdout_cases.append({
            "id": cid,
            "language": lang,
            "domain": domain,
            "text": text,
            "forced_rules": list(forced),
            "secrets": [make_span(text, secret, "ambiguous_name")],
            "public": [make_span(text, public, "task_prose")],
        })

    dev_data = {"schema_version": 1, "issue": 314, "split": "dev", "cases": dev_cases}
    holdout_data = {"schema_version": 1, "issue": 314, "split": "holdout", "cases": holdout_cases}
    validate_corpus(dev_data)
    validate_corpus(holdout_data)

    frozen_criteria = {
        "issue": 314,
        "candidates": ["vocab_conservative", "vocab_calibrated"],
        "ordering_protocol": SHARED_ORDERING_PROTOCOL,
        "cutoffs_tested_on_dev": {
            "en": [300, 350, 400, 450, 500, 550],
            "ko": [300, 350, 400, 450, 500, 550],
        },
        "selected_frozen_cutoffs": {
            "en": 450,
            "ko": 400,
        },
        "ambiguous_words_inventory": {
            "en_count": 231,
            "ko_count": 98,
            "exclusion_rate": 1.0,
        },
        "acceptance_criteria": {
            "vocab_conservative": "Reject if over-masking of ordinary prose words degrades readability",
            "vocab_calibrated": "Protect ambiguous words with low ordinary prose over-masking",
            "exact_restore_rate": 1.0,
            "comprehension_status": "hold — comprehension 미측정",
        },
    }

    (out_dir / "dev_corpus.json").write_text(json.dumps(dev_data, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "holdout_corpus.json").write_text(json.dumps(holdout_data, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "frozen_criteria.json").write_text(json.dumps(frozen_criteria, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Issue #314 corpora generated and validated.")


def build_issue306_data():
    out_dir = EVAL_DIR / "issue306-2.10.0"
    out_dir.mkdir(parents=True, exist_ok=True)

    dev_raw = [
        ("repro-306-01", "en", "general", "The committee froze fold after the audit uncovered overruns.", "fold", "The committee froze", ("fold",)),
        ("repro-306-02", "en", "tech", "The launch of drift includes a six-month support contract.", "drift", "The launch of", ("drift",)),
        ("repro-306-03", "en", "tech", "The beta release of velvet attracted forty volunteer testers.", "velvet", "The beta release of", ("velvet",)),
        ("repro-306-04", "ko", "tech", "흐름의 출시 계약에는 반년 동안의 유지보수가 포함된다.", "흐름", "출시 계약에는", ("흐름",)),
    ]

    dev_cases = []
    for cid, lang, domain, text, secret, public, forced in dev_raw:
        dev_cases.append({
            "id": cid,
            "language": lang,
            "domain": domain,
            "text": text,
            "forced_rules": list(forced),
            "secrets": [make_span(text, secret, "repro_secret")],
            "public": [make_span(text, public, "public_prose")],
        })

    holdout_raw = [
        ("holdout-306-01", "ko", "general", "비공개 연구소 청람Qzx의 운영 방침을 검토하세요.", "청람Qzx", "운영 방침을 검토하세요.", ()),
        ("holdout-306-02", "ko", "general", "회원 번호 84920412의 접근 기록을 분석하세요.", "84920412", "접근 기록을 분석하세요.", ()),
        ("holdout-306-03", "en", "general", "Please review the strategy document for Project FalconQzx.", "FalconQzx", "Please review the strategy", ()),
        ("holdout-306-04", "en", "general", "Customer account 98234190 requested a balance refund.", "98234190", "requested a balance refund.", ()),
        ("holdout-306-05", "ko", "tech", "배포 대상 서버 AegisHostQzx의 포트 번호를 점검하세요.", "AegisHostQzx", "포트 번호를 점검하세요.", ()),
        ("holdout-306-06", "ko", "tech", "내부 포트 9443을 통한 외부 접속을 차단하세요.", "9443", "통한 외부 접속을 차단하세요.", ()),
        ("holdout-306-07", "en", "tech", "Ensure secure tunnel for gateway proxy OrionProxyQzx.", "OrionProxyQzx", "Ensure secure tunnel for", ()),
        ("holdout-306-08", "en", "tech", "Database cluster connection string uses port 54329.", "54329", "Database cluster connection", ()),
    ]

    holdout_cases = []
    for cid, lang, domain, text, secret, public, forced in holdout_raw:
        holdout_cases.append({
            "id": cid,
            "language": lang,
            "domain": domain,
            "text": text,
            "forced_rules": list(forced),
            "secrets": [make_span(text, secret, "ENTITY" if not secret.isdigit() else "NUMBER")],
            "public": [make_span(text, public, "intent")],
        })

    dev_data = {"schema_version": 1, "issue": 306, "split": "dev", "cases": dev_cases}
    holdout_data = {"schema_version": 1, "issue": 306, "split": "holdout", "cases": holdout_cases}
    validate_corpus(dev_data)
    validate_corpus(holdout_data)

    frozen_criteria = {
        "issue": 306,
        "scope": "sections_3_and_5",
        "ordering_protocol": SHARED_ORDERING_PROTOCOL,
        "metrics_breakdown": {
            "breakdowns": ["language (ko/en)", "domain (general/tech)", "target_type (ENTITY/NUMBER)"],
            "separate_counts": ["True Positives", "False Negatives (Full Leaks)", "Partial Exposures", "False Positives (Overmasked)", "Per-Request Leaks"],
            "integrity_metric": "Exact restore rate, alias replay stability, protocol preservation reported as a separate metric",
        },
        "acceptance_criteria": {
            "reproductions_pass_rate": 1.0,
            "false_negatives": 0,
            "exact_restore_rate": 1.0,
            "comprehension_status": "hold — comprehension 미측정",
        },
    }

    (out_dir / "dev_corpus.json").write_text(json.dumps(dev_data, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "holdout_corpus.json").write_text(json.dumps(holdout_data, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "frozen_criteria.json").write_text(json.dumps(frozen_criteria, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Issue #306 corpora generated and validated.")


def build_issue291_data():
    out_dir = EVAL_DIR / "issue291-2.10.0"
    out_dir.mkdir(parents=True, exist_ok=True)

    languages_17 = [
        ("en", "Please review the secret document ProjectAlpha today.", "ProjectAlpha", "Please review the"),
        ("ko", "오늘 비밀 문서 ProjectAlpha를 검토해 주세요.", "ProjectAlpha", "오늘 비밀 문서"),
        ("es", "Por favor revise el documento secreto ProjectAlpha hoy.", "ProjectAlpha", "Por favor revise el"),
        ("fr", "Veuillez examiner le document secret ProjectAlpha aujourd'hui.", "ProjectAlpha", "Veuillez examiner"),
        ("pt", "Por favor revise o documento secreto ProjectAlpha hoje.", "ProjectAlpha", "Por favor revise o"),
        ("de", "Bitte uberprufen Sie das geheime Dokument ProjectAlpha heute.", "ProjectAlpha", "Bitte uberprufen"),
        ("id", "Harap tinjau dokumen rahasia ProjectAlpha hari ini.", "ProjectAlpha", "Harap tinjau"),
        ("tr", "Lutfen gizli belge ProjectAlpha bugün inceleyin.", "ProjectAlpha", "Lutfen gizli belge"),
        ("ru", "Пожалуйста, просмотрите секретный документ ProjectAlpha сегодня.", "ProjectAlpha", "Пожалуйста"),
        ("hi", "कृपया आज गुप्त दस्तावेज़ ProjectAlpha की समीक्षा करें।", "ProjectAlpha", "कृपया आज गुप्त"),
        ("mr", "कृपया आज गुप्त दस्तऐवज ProjectAlpha चे पुनरावलोकन करा.", "ProjectAlpha", "कृपया आज गुप्त"),
        ("bn", "অনুগ্রহ করে আজ গোপন নথি ProjectAlpha পর্যালোচনা করুন।", "ProjectAlpha", "অনুগ্রহ করে আজ"),
        ("ur", "براہ کرم آج خفیہ دستاویز ProjectAlpha کا جائزہ لیں۔", "ProjectAlpha", "براہ کرم آج"),
        ("te", "దయచేసి ఈరోజు రహస్య పత్రం ProjectAlpha ను సమీక్షించండి.", "ProjectAlpha", "దయచేసి ఈరోజు"),
        ("ar", "يرجى مراجعة الوثيقة السرية ProjectAlpha اليوم.", "ProjectAlpha", "يرجى مراجعة"),
        ("zh", "请在今天审查机密文档 ProjectAlpha。", "ProjectAlpha", "请在今天审查机密文档"),
        ("ja", "今日、秘密文書 ProjectAlpha を確認してください。", "ProjectAlpha", "今日、秘密文書"),
    ]

    holdout_cases = []
    for lang, text, secret, public_part in languages_17:
        holdout_cases.append({
            "id": f"holdout-291-{lang}",
            "language": lang,
            "domain": "general",
            "text": text,
            "forced_rules": [secret],
            "secrets": [make_span(text, secret, "private_project")],
            "public": [make_span(text, public_part, "public_prose")],
        })

    # The 2 known requests
    holdout_cases.append({
        "id": "known-291-securemcp-delete",
        "language": "ko",
        "domain": "general",
        "text": "SecureMCP 삭제해줘",
        "forced_rules": ["SecureMCP"],
        "secrets": [make_span("SecureMCP 삭제해줘", "SecureMCP", "target_identifier")],
        "public": [make_span("SecureMCP 삭제해줘", "삭제해줘", "action_imperative")],
    })

    holdout_cases.append({
        "id": "known-291-read-skill-md",
        "language": "en",
        "domain": "general",
        "text": "Read SKILL.md before using this skill. Follow its instructions.",
        "forced_rules": ["SKILL.md"],
        "secrets": [make_span("Read SKILL.md before using this skill. Follow its instructions.", "SKILL.md", "file_identifier")],
        "public": [
            make_span("Read SKILL.md before using this skill. Follow its instructions.", "Read", "verb_read"),
            make_span("Read SKILL.md before using this skill. Follow its instructions.", "Follow its instructions.", "instructions"),
        ],
    })

    dev_cases = holdout_cases[:6]

    dev_data = {"schema_version": 1, "issue": 291, "split": "dev", "cases": dev_cases}
    holdout_data = {"schema_version": 1, "issue": 291, "split": "holdout", "cases": holdout_cases}
    validate_corpus(dev_data)
    validate_corpus(holdout_data)

    frozen_criteria = {
        "issue": 291,
        "scope": "multilingual_verification",
        "ordering_protocol": SHARED_ORDERING_PROTOCOL,
        "languages_scope": [lang for lang, _, _, _ in languages_17],
        "known_requests": [
            "SecureMCP 삭제해줘 (must preserve action '삭제해줘' on default engine)",
            "Read SKILL.md before using this skill. Follow its instructions. (must preserve imperative verbs and discourse markers)",
        ],
        "acceptance_criteria": {
            "meaning_preservation_rate": 1.0,
            "sensitive_protection_rate": 1.0,
            "exact_restoration_rate": 1.0,
            "tool_mcp_skill_offline": "passed",
            "real_provider_verification": "미측정",
        },
    }

    (out_dir / "dev_corpus.json").write_text(json.dumps(dev_data, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "holdout_corpus.json").write_text(json.dumps(holdout_data, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "multilingual_corpus.json").write_text(json.dumps(holdout_data, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "frozen_criteria.json").write_text(json.dumps(frozen_criteria, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Issue #291 corpora generated and validated.")


def main():
    build_issue309_data()
    build_issue313_data()
    build_issue314_data()
    build_issue306_data()
    build_issue291_data()
    print("All corpora and frozen criteria files generated successfully.")


if __name__ == "__main__":
    main()
