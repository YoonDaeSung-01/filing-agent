"""DART 사업보고서 서술 섹션 수집.

흐름:
1. list.json → 해당 연도 사업보고서의 rcept_no 확보
2. document.xml → ZIP 다운로드
3. ZIP 에서 가장 큰 HTML 파일 추출
4. BeautifulSoup 으로 텍스트 파싱
5. data/raw/filings/{corp_code}_{year}.txt 에 캐싱

사업보고서는 보통 다음 해 1~4월에 제출되므로 검색 범위를 (year+1)의 상반기로 잡는다.
"""

from __future__ import annotations

import io
import time
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import httpx
from bs4 import BeautifulSoup

from filing_agent.ingest.facts import DartApiError

_BASE_URL = "https://opendart.fss.or.kr/api"
_REQUEST_DELAY_SEC = 0.15
_TIMEOUT_SEC = 60.0

_FILINGS_DIR = Path("data/raw/filings")


def _cache_path(corp_code: str, year: int) -> Path:
    return _FILINGS_DIR / f"{corp_code}_{year}.txt"


# ---------------------------------------------------------------------------
# 접수번호 조회
# ---------------------------------------------------------------------------

def _get_rcept_no(api_key: str, corp_code: str, year: int) -> str | None:
    """해당 연도 사업보고서의 접수번호(rcept_no)를 반환한다. 없으면 None."""
    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code,
        "bgn_de": f"{year + 1}0101",
        "end_de": f"{year + 1}0630",
        "pblntf_ty": "A",
        "last_reprt_at": "Y",
        "page_count": 10,
    }
    time.sleep(_REQUEST_DELAY_SEC)
    resp = httpx.get(f"{_BASE_URL}/list.json", params=params, timeout=_TIMEOUT_SEC)
    resp.raise_for_status()
    payload: dict[str, Any] = resp.json()

    if payload.get("status") != "000":
        return None
    for item in payload.get("list", []):
        if "사업보고서" in (item.get("report_nm") or ""):
            return item["rcept_no"]
    return None


# ---------------------------------------------------------------------------
# 원문 다운로드 + 텍스트 추출
# ---------------------------------------------------------------------------

def _download_zip(api_key: str, rcept_no: str) -> bytes:
    time.sleep(_REQUEST_DELAY_SEC)
    resp = httpx.get(
        f"{_BASE_URL}/document.xml",
        params={"crtfc_key": api_key, "rcept_no": rcept_no},
        timeout=_TIMEOUT_SEC,
    )
    resp.raise_for_status()
    content = resp.content
    if content[:2] != b"PK":
        try:
            root = ElementTree.fromstring(content)
            status = root.findtext("status") or "unknown"
            message = root.findtext("message") or "document.xml 응답이 ZIP 이 아닙니다."
        except ElementTree.ParseError:
            status, message = "unknown", "document.xml 응답이 ZIP 이 아닙니다."
        raise DartApiError(status=status, message=message)
    return content


def _extract_text(zip_bytes: bytes) -> str:
    """ZIP 에서 가장 큰 HTML 파일을 찾아 순수 텍스트로 추출한다."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        html_files = [n for n in zf.namelist() if n.lower().endswith((".html", ".htm"))]
        if not html_files:
            html_files = [
                n for n in zf.namelist()
                if n.lower().endswith(".xml") and "meta" not in n.lower()
            ]
        if not html_files:
            return ""
        largest = max(html_files, key=lambda n: zf.getinfo(n).file_size)
        raw = zf.read(largest)

    for enc in ("utf-8", "euc-kr", "cp949"):
        try:
            html_text = raw.decode(enc)
            break
        except (UnicodeDecodeError, LookupError):
            continue
    else:
        html_text = raw.decode("utf-8", errors="replace")

    soup = BeautifulSoup(html_text, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    lines = [line.strip() for line in soup.get_text(separator="\n").splitlines()]
    return "\n".join(line for line in lines if line)


# ---------------------------------------------------------------------------
# 공개 API
# ---------------------------------------------------------------------------

def fetch_filing_text(
    api_key: str,
    corp_code: str,
    corp_name: str,
    year: int,
    reprt_code: str = "11011",
) -> str | None:
    """서술 섹션 텍스트를 반환한다. 캐시 우선. 실패하면 None."""
    cache = _cache_path(corp_code, year)
    if cache.exists():
        return cache.read_text(encoding="utf-8")

    rcept_no = _get_rcept_no(api_key, corp_code, year)
    if rcept_no is None:
        return None

    try:
        zip_bytes = _download_zip(api_key, rcept_no)
    except (DartApiError, httpx.HTTPError):
        return None

    text = _extract_text(zip_bytes)
    if not text:
        return None

    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(text, encoding="utf-8")
    return text


def collect_all_filings(
    api_key: str,
    corp_code_map: dict[str, str],
    companies: list[str],
    year: int,
) -> dict[str, str]:
    """{corp_name: text} 를 반환한다. corp_code 를 찾을 수 없거나 수집 실패 시 해당 기업은 제외."""
    results: dict[str, str] = {}
    for company in companies:
        corp_code = corp_code_map.get(company)
        if corp_code is None:
            continue
        text = fetch_filing_text(api_key, corp_code, company, year)
        if text:
            results[company] = text
    return results
