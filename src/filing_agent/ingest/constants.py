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

TARGET_YEAR: int = 2025

# TARGET_COMPANIES 10개의 분야(업종) 분류 — 직접 라벨링.
# DART corpCode.xml·한투 API 모두 표준 업종 분류 필드를 제공하지 않아
# 관심 종목 소수(10개) 한정으로 직접 분류했다. 전체 시장 업종 분류가 아님.
SECTOR_MAP: dict[str, list[str]] = {
    "반도체·전자": ["삼성전자", "SK하이닉스", "LG전자"],
    "자동차": ["현대자동차", "기아", "현대모비스"],
    "화학·배터리·에너지": ["LG화학", "삼성SDI", "SK이노베이션"],
    "철강·소재": ["POSCO홀딩스"],
}
