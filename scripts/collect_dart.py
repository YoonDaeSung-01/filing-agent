"""DART 데이터만 수집한다 (LLM 키 불필요).

- 재무 수치: data/raw/facts/ 에 JSON 캐싱
- 서술 텍스트: data/raw/filings/ 에 TXT 캐싱

임베딩·pgvector 저장은 LLM 키 준비 후 ingest_all.py 로 한다.

실행: uv run python scripts/collect_dart.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from filing_agent.config import get_settings
from filing_agent.ingest import dart_client
from filing_agent.ingest.constants import TARGET_ACCOUNTS, TARGET_COMPANIES, TARGET_YEAR
from filing_agent.ingest.facts import DartApiError, build_revenue_fact
from filing_agent.ingest.filings import fetch_filing_text


def main() -> None:
    settings = get_settings()
    api_key = settings.dart_api_key
    year = TARGET_YEAR

    print(f"[1/3] corp_code 매핑 로드 중 (대상 {len(TARGET_COMPANIES)}개 기업)...")
    corp_code_map: dict[str, str] = {}
    for company in TARGET_COMPANIES:
        code = dart_client.resolve_corp_code(api_key, company)
        if code:
            corp_code_map[company] = code
            print(f"  {company}: {code}")
        else:
            print(f"  {company}: FAIL corp_code 없음 — 건너뜀")

    print(f"\n[2/3] 재무 수치 수집 ({year}년, 계정 {len(TARGET_ACCOUNTS)}개)...")
    for company, corp_code in corp_code_map.items():
        try:
            payload = dart_client.fetch_single_account(
                api_key,
                corp_code=corp_code,
                bsns_year=year,
                reprt_code=settings.dart_report_code,
            )
            for account in TARGET_ACCOUNTS:
                prefer = (
                    settings.dart_fs_div,
                    "OFS" if settings.dart_fs_div == "CFS" else "CFS",
                )
                fact = build_revenue_fact(
                    payload,
                    company=company,
                    account_nm=account,
                    year=year,
                    prefer=prefer,
                )
                status = f"{fact['value']:,}원 ({fact['fs_div']})" if fact else "없음"
                print(f"  {company} / {account}: {status}")
        except DartApiError as e:
            print(f"  {company}: DART 오류 — {e}")

    print(f"\n[3/3] 사업보고서 서술 텍스트 수집 ({year}년)...")
    success = 0
    for company, corp_code in corp_code_map.items():
        text = fetch_filing_text(api_key, corp_code, company, year)
        if text:
            print(f"  {company}: {len(text):,}자 수집 → data/raw/filings/{corp_code}_{year}.txt")
            success += 1
        else:
            print(f"  {company}: FAIL 수집 실패")

    total = len(corp_code_map)
    print(f"\n완료! 재무 수치: {total}개 기업, 서술 텍스트: {success}/{total}개")
    print("LLM_API_KEY 설정 후 ingest_all.py 로 임베딩·저장을 이어서 진행하세요.")


if __name__ == "__main__":
    main()
