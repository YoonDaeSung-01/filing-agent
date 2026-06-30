"""전체 인제스트 파이프라인 — 기업·연도를 CLI 인자로 지정 가능.

기본 실행 (constants.py 기본 기업 목록):
    uv run python scripts/ingest_all.py

특정 기업 추가 인제스트:
    uv run python scripts/ingest_all.py --companies 카카오 네이버 --year 2024

기업 목록 전체 교체 + 연도 변경:
    uv run python scripts/ingest_all.py --companies 삼성전자 SK하이닉스 --year 2023

흐름:
1. corpCode.xml 로 기업 corp_code 확보
2. fnlttSinglAcnt.json 으로 재무 수치 수집 → data/raw/facts/
3. document.xml 로 사업보고서 서술 텍스트 수집 → data/raw/filings/
4. 서술 텍스트 청킹 → 임베딩 → pgvector 저장
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path 에 추가 (uv run 환경에선 불필요하지만 안전하게)
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from filing_agent.config import get_settings
from filing_agent.ingest import dart_client
from filing_agent.ingest.chunker import chunk_text
from filing_agent.ingest.constants import TARGET_ACCOUNTS, TARGET_COMPANIES, TARGET_YEAR
from filing_agent.ingest.facts import DartApiError, build_revenue_fact
from filing_agent.ingest.filings import fetch_filing_text
from filing_agent.ingest.indexer import clear_corp_year, index_chunks, setup_table


def main() -> None:
    parser = argparse.ArgumentParser(description="DART 사업보고서 인제스트 파이프라인")
    parser.add_argument(
        "--companies", nargs="+", default=None,
        metavar="COMPANY",
        help=(
            "인제스트할 기업 이름 목록 (DART corpCode.xml 등록명과 정확히 일치). "
            "생략 시 constants.TARGET_COMPANIES(기본 10개) 사용."
        ),
    )
    parser.add_argument(
        "--year", type=int, default=TARGET_YEAR,
        help=f"수집 연도 (기본: {TARGET_YEAR})",
    )
    parser.add_argument(
        "--no-clear", action="store_true",
        help="pgvector의 기존 데이터를 지우지 않고 추가(기본: 해당 기업·연도 덮어쓰기)",
    )
    args = parser.parse_args()

    companies: list[str] = args.companies if args.companies else TARGET_COMPANIES
    year: int = args.year
    skip_clear: bool = args.no_clear

    settings = get_settings()
    api_key = settings.dart_api_key

    print(f"[1/4] corp_code 매핑 로드 중 ({len(companies)}개 기업)...")
    corp_code_map: dict[str, str] = {}
    for company in companies:
        code = dart_client.resolve_corp_code(api_key, company)
        if code:
            corp_code_map[company] = code
            print(f"  {company}: {code}")
        else:
            print(f"  {company}: corp_code 없음 — 건너뜀 (DART 등록명 확인 필요)")

    if not corp_code_map:
        print("유효한 기업이 없습니다. 종료.")
        return

    print(f"\n[2/4] 재무 수치 수집 ({year}년, 계정 {len(TARGET_ACCOUNTS)}개)...")
    for company, corp_code in corp_code_map.items():
        try:
            payload = dart_client.fetch_single_account(
                api_key,
                corp_code=corp_code,
                bsns_year=year,
                reprt_code=settings.dart_report_code,
            )
            for account in TARGET_ACCOUNTS:
                fact = build_revenue_fact(
                    payload,
                    company=company,
                    account_nm=account,
                    year=year,
                    prefer=(
                        settings.dart_fs_div,
                        "OFS" if settings.dart_fs_div == "CFS" else "CFS",
                    ),
                )
                status = f"{fact['value']:,}원 ({fact['fs_div']})" if fact else "없음"
                print(f"  {company} {account}: {status}")
        except DartApiError as e:
            print(f"  {company}: DART 오류 — {e}")

    print("\n[3/4] 사업보고서 서술 텍스트 수집...")
    filing_texts: dict[str, str] = {}
    for company, corp_code in corp_code_map.items():
        text = fetch_filing_text(api_key, corp_code, company, year)
        if text:
            filing_texts[company] = text
            print(f"  {company}: {len(text):,}자 수집")
        else:
            print(f"  {company}: 수집 실패 — 건너뜀")

    if not filing_texts:
        print("수집된 서술 텍스트가 없습니다. 종료.")
        return

    print("\n[4/4] 임베딩 + pgvector 저장...")
    setup_table(settings)

    total = 0
    for company, text in filing_texts.items():
        source = f"{company} 사업보고서 {year}"
        chunks = chunk_text(text, corp_name=company, year=year, source=source)
        print(f"  {company}: {len(chunks)}개 청크 → 임베딩 중...")
        if not skip_clear:
            clear_corp_year(company, year, settings)
        stored = index_chunks(chunks, settings)
        total += stored
        print(f"    {stored}개 저장 완료")

    # 재인덱싱 후 메모리 BM25 인덱스 무효화(같은 프로세스에서 검색 시 반영).
    from filing_agent.retrieval.retriever import reset_bm25_cache

    reset_bm25_cache()

    ingested = list(filing_texts.keys())
    summary = ", ".join(ingested)
    print(f"\n완료! 총 {total}개 청크 저장됨 ({year}년 · {len(ingested)}개 기업: {summary})")
    print("이제 POST /ask 로 질의할 수 있습니다.")


if __name__ == "__main__":
    main()
