"""Phase 1 전체 인제스트 파이프라인.

실행: uv run python scripts/ingest_all.py

흐름:
1. corpCode.xml 로 10개 기업 corp_code 확보
2. fnlttSinglAcnt.json 으로 재무 수치 수집 → data/raw/facts/
3. document.xml 로 사업보고서 서술 텍스트 수집 → data/raw/filings/
4. 서술 텍스트 청킹 → OpenAI 임베딩 → pgvector 저장
"""

from __future__ import annotations

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
    settings = get_settings()
    api_key = settings.dart_api_key
    year = TARGET_YEAR

    print("[1/4] corp_code 매핑 로드 중...")
    corp_code_map: dict[str, str] = {}
    for company in TARGET_COMPANIES:
        code = dart_client.resolve_corp_code(api_key, company)
        if code:
            corp_code_map[company] = code
            print(f"  {company}: {code}")
        else:
            print(f"  {company}: corp_code 없음 -건너뜀")

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
            print(f"  {company}: DART 오류 -{e}")

    print("\n[3/4] 사업보고서 서술 텍스트 수집...")
    filing_texts: dict[str, str] = {}
    for company, corp_code in corp_code_map.items():
        text = fetch_filing_text(api_key, corp_code, company, year)
        if text:
            filing_texts[company] = text
            print(f"  {company}: {len(text):,}자 수집")
        else:
            print(f"  {company}: 수집 실패 -건너뜀")

    if not filing_texts:
        print("수집된 서술 텍스트가 없습니다. 종료.")
        return

    print("\n[4/4] 임베딩 + pgvector 저장...")
    print("  pgvector 테이블 초기화...")
    setup_table(settings)

    total = 0
    for company, text in filing_texts.items():
        source = f"{company} 사업보고서 {year}"
        chunks = chunk_text(text, corp_name=company, year=year, source=source)
        print(f"  {company}: {len(chunks)}개 청크 → 임베딩 중...")
        clear_corp_year(company, year, settings)
        stored = index_chunks(chunks, settings)
        total += stored
        print(f"    {stored}개 저장 완료")

    print(f"\n완료! 총 {total}개 청크 저장됨.")
    print("이제 POST /ask 로 질의할 수 있습니다.")


if __name__ == "__main__":
    main()
