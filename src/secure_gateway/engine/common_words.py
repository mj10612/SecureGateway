"""Small offline starter vocabulary, authored for this Apache-2.0 project.

Vocabulary version 1. No third-party corpus, frequency ranking, or service is
used. These are illustrative general words, not a complete dictionary and not
evidence that a word is safe to disclose. Unknown words remain protected by the
uncommon_words policy; callers handle grammar, sensitive patterns and names.
Changes to this set change preservation decisions and require regression review.
"""

from __future__ import annotations

import unicodedata


COMMON_WORDS_VERSION = "1"


def vocabulary_key(word: str) -> str:
    """Normalize only the lookup key; never replace stored source spelling."""
    return unicodedata.normalize("NFC", word).casefold()


COMMON_WORDS: dict[str, frozenset[str]] = {
    "en": frozenset("""
        able about above across action add address after again age air allow
        answer appear area ask away back bad base basic become before begin
        best better big body book both bring build business call can care carry
        case change check child children city clear close cold come common
        company complete computer consider continue country create current day
        days decide different do document done door down draw during each early
        easy eat education end enough enter example explain eye face fact family
        far feel few field file find first follow food form found free friend
        full future game general get give go good great group grow half hand
        happen happy hard have head health hear help high history hold home hour
        house human idea important include information inside interest issue job
        keep kind know large last late later lead learn leave left less let
        letter life light like line list little live local long look low main
        make man many market matter may mean meeting member might minute miss
        money month more morning most move much must name near need new next
        night note number office often old once open order other outside own page
        paper parent part pass past pay people person place plan play point
        possible power present problem process program provide public put question
        quick read ready real reason receive record report request result return
        right room run same save say school second see seem send sentence service
        set several show side simple since small social some soon sound speak
        start state stay step still stop story student study such support system
        table take talk task teach team tell test text thing think three through
        time today together too top total town try turn two type understand use
        uses used user value view wait walk want warm water way week well went
        whole wide will woman word work world write year young
    """.split()),
    "ko": frozenset("""
        사람 시간 오늘 내일 어제 아침 점심 저녁 밤 낮 하루 일주일 주말
        봄 여름 가을 겨울 날씨 하늘 바다 산 강 땅 물 공기 빛 비 눈
        집 학교 교실 책상 의자 문 창문 방 길 거리 도시 나라 마을
        가족 부모 아이 친구 학생 선생님 생활 음식 밥 빵 과일 채소
        책 글 문장 단어 말 소리 이야기 질문 답변 생각 마음 기분
        일 업무 작업 회의 계획 일정 시작 끝 과정 방법 이유 목적
        문제 결과 내용 정보 자료 기록 문서 목록 항목 예시 설명 안내
        이름 주소 번호 날짜 위치 방향 앞 뒤 위 아래 안 밖 왼쪽 오른쪽
        크기 길이 높이 넓이 무게 색 모양 수량 금액 가격 돈 비용
        사용 확인 추가 변경 삭제 저장 조회 검색 입력 출력 선택 설정
        도움 요청 응답 전달 공유 연결 상태 화면 사진 그림 영상 음악
        컴퓨터 파일 폴더 프로그램 기능 서비스 시스템 사용자 계정 권한
        회사 사무실 조직 팀 고객 제품 사업 개발 시험 검토 개선 완료
        처음 다음 마지막 전체 일부 기본 일반 새 좋은 작은 큰 많은
    """.split()),
}


def is_common(word: str, language: str, extra: set[str] | None = None) -> bool:
    """Match a bundled or explicitly supplied common word, entirely locally.

    Unsupported languages have no bundled preservation vocabulary. A caller
    may still supply an explicit local vocabulary. ``extra`` must contain keys
    normalized with :func:`vocabulary_key` once at the request boundary, keeping
    per-token lookup constant-time. Input sets are not mutated.
    """
    key = vocabulary_key(word)
    return key in COMMON_WORDS.get(language, frozenset()) or (
        extra is not None and key in extra
    )
