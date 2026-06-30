"""인제스트 기본값 — ingest_all.py --companies / --year 로 재정의 가능.

financial_lookup 은 DART corp_code 조회로 모든 상장사를 지원하므로 기업 제한 없음.
doc_search 는 pgvector 인제스트된 기업만 검색 가능(인제스트 후 지원).
"""

TARGET_COMPANIES: list[str] = [
    "삼성전자",
    "SK하이닉스",
    "LG전자",
    "현대자동차",
    "기아",
    "POSCO홀딩스",
    "LG화학",
    "삼성SDI",
    "현대모비스",
    "SK이노베이션",
]

TARGET_ACCOUNTS: list[str] = [
    "매출액",
    "영업이익",
    "당기순이익",
    "자산총계",
    "부채총계",
]

TARGET_YEAR: int = 2024
