"""OpenDART 호출 클라이언트 — 네트워크 + 캐싱 + corp_code 매핑.

규칙:
- 인증키(``api_key``)는 항상 인자로 주입받는다. 전역/하드코딩/로깅 금지.
- 일일 호출 한도 보호를 위해 응답을 디스크에 캐싱하고, 캐시가 있으면 네트워크를 건너뛴다.
- 실제 네트워크 요청 직전에만 ~100ms 지연을 둔다.
- ``corpCode.xml`` 은 zip(binary)로 오므로 다운로드 → 압축 해제 → XML 파싱 →
  ``{회사명: corp_code}`` 매핑을 로컬 JSON 캐시에 저장한다.
- status 검사/예외는 facts 모듈(:func:`ensure_status_ok`, :class:`DartApiError`)을 재사용한다.
"""

from __future__ import annotations

import io
import json
import time
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import httpx

from filing_agent.ingest.facts import DartApiError, ensure_status_ok

_BASE_URL = "https://opendart.fss.or.kr/api"
_REQUEST_DELAY_SEC = 0.1
_TIMEOUT_SEC = 30.0

# 캐시 경로(프로젝트 루트 기준 상대). 런타임에 생성되며 git 에는 포함되지 않는다.
_DATA_ROOT = Path("data/raw")
_FACTS_DIR = _DATA_ROOT / "facts"
_CORP_CODE_CACHE = _DATA_ROOT / "corp_code_map.json"
_STOCK_CODE_CACHE = _DATA_ROOT / "stock_code_map.json"


# ---------------------------------------------------------------------------
# 캐시 헬퍼
# ---------------------------------------------------------------------------
def _read_json_cache(path: Path) -> Any | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json_cache(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# 재무 주요계정 (fnlttSinglAcnt.json)
# ---------------------------------------------------------------------------
def fetch_single_account(
    api_key: str,
    *,
    corp_code: str,
    bsns_year: int | str,
    reprt_code: str,
) -> dict[str, Any]:
    """단일회사 주요계정 응답(JSON)을 반환한다. 캐시 우선, status != "000" 이면 DartApiError.

    이 엔드포인트는 한 응답에 CFS·OFS 행을 함께 주므로 fs_div 별 선택은 호출부(facts)에서 한다.
    """
    cache_path = _FACTS_DIR / f"{corp_code}_{bsns_year}_{reprt_code}.json"
    cached = _read_json_cache(cache_path)
    if cached is not None:
        ensure_status_ok(cached)
        return cached

    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code,
        "bsns_year": str(bsns_year),
        "reprt_code": reprt_code,
    }
    time.sleep(_REQUEST_DELAY_SEC)
    resp = httpx.get(f"{_BASE_URL}/fnlttSinglAcnt.json", params=params, timeout=_TIMEOUT_SEC)
    resp.raise_for_status()
    payload: dict[str, Any] = resp.json()

    # status != "000" 은 캐시하지 않는다(데이터 없음/오류를 영구 저장하지 않기 위함).
    ensure_status_ok(payload)
    _write_json_cache(cache_path, payload)
    return payload


# ---------------------------------------------------------------------------
# 회사 고유번호 매핑 (corpCode.xml, zip)
# ---------------------------------------------------------------------------
def resolve_corp_code(api_key: str, name: str) -> str | None:
    """회사명을 corp_code(8자리 고유번호)로 정확히 매칭한다. 없으면 None."""
    return _load_corp_code_map(api_key).get(name)


def resolve_stock_code(api_key: str, name: str) -> str | None:
    """회사명을 6자리 종목코드(ticker)로 반환한다. 비상장이면 None."""
    return _load_stock_code_map(api_key).get(name)


# 일상 표현 → DART 공식 상장사명. 부분일치로는 안 잡히는 흔한 별칭만 최소로 유지.
_SEARCH_ALIASES: dict[str, str] = {
    "네이버": "NAVER",
    "카카오톡": "카카오",
    "기아차": "기아",
    "현대차": "현대자동차",
    "kt": "케이티",
}


def search_listed_companies(api_key: str, query: str, limit: int = 10) -> list[dict[str, str]]:
    """상장사 이름 부분검색. 별칭 우선 → startswith → 부분일치. → [{name, ticker}]."""
    q = query.strip()
    if not q:
        return []
    mapping = _load_stock_code_map(api_key)  # {회사명: stock_code}

    aliased: list[dict[str, str]] = []
    alias_target = _SEARCH_ALIASES.get(q.lower())
    if alias_target and alias_target in mapping:
        aliased.append({"name": alias_target, "ticker": mapping[alias_target]})

    starts: list[dict[str, str]] = []
    contains: list[dict[str, str]] = []
    seen_tickers = {a["ticker"] for a in aliased}
    for name, code in mapping.items():
        if code in seen_tickers:
            continue
        if name.startswith(q):
            starts.append({"name": name, "ticker": code})
        elif q in name:
            contains.append({"name": name, "ticker": code})
    starts.sort(key=lambda m: len(m["name"]))
    return (aliased + starts + contains)[:limit]


def _load_corp_code_map(api_key: str) -> dict[str, str]:
    cached = _read_json_cache(_CORP_CODE_CACHE)
    if cached is not None:
        return cached
    corp_map, stock_map = _download_both_maps(api_key)
    _write_json_cache(_CORP_CODE_CACHE, corp_map)
    _write_json_cache(_STOCK_CODE_CACHE, stock_map)
    return corp_map


def _load_stock_code_map(api_key: str) -> dict[str, str]:
    cached = _read_json_cache(_STOCK_CODE_CACHE)
    if cached is not None:
        return cached
    corp_map, stock_map = _download_both_maps(api_key)
    _write_json_cache(_CORP_CODE_CACHE, corp_map)
    _write_json_cache(_STOCK_CODE_CACHE, stock_map)
    return stock_map


def _download_both_maps(api_key: str) -> tuple[dict[str, str], dict[str, str]]:
    time.sleep(_REQUEST_DELAY_SEC)
    resp = httpx.get(
        f"{_BASE_URL}/corpCode.xml", params={"crtfc_key": api_key}, timeout=_TIMEOUT_SEC
    )
    resp.raise_for_status()
    content = resp.content

    # 정상 응답은 zip(매직바이트 'PK'). 키 오류 등은 XML status 본문이 온다.
    if content[:2] != b"PK":
        _raise_from_error_body(content)
    xml_bytes = _unzip_single(content)
    return _parse_corp_code_xml(xml_bytes), _parse_stock_code_xml(xml_bytes)


def _unzip_single(content: bytes) -> bytes:
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        return zf.read(zf.namelist()[0])  # CORPCODE.xml


def _parse_corp_code_xml(xml_bytes: bytes) -> dict[str, str]:
    """corpCode.xml → {회사명: corp_code}. 동명일 경우 상장사(stock_code 있음)를 우선한다."""
    root = ElementTree.fromstring(xml_bytes)
    mapping: dict[str, str] = {}
    listed_names: set[str] = set()
    for item in root.iter("list"):
        corp_code = (item.findtext("corp_code") or "").strip()
        corp_name = (item.findtext("corp_name") or "").strip()
        stock_code = (item.findtext("stock_code") or "").strip()
        if not corp_code or not corp_name:
            continue
        is_listed = bool(stock_code)
        if corp_name not in mapping:
            mapping[corp_name] = corp_code
            if is_listed:
                listed_names.add(corp_name)
        elif is_listed and corp_name not in listed_names:
            # 기존이 비상장이고 새 항목이 상장사면 교체
            mapping[corp_name] = corp_code
            listed_names.add(corp_name)
    return mapping


def _parse_stock_code_xml(xml_bytes: bytes) -> dict[str, str]:
    """corpCode.xml → {회사명: stock_code}. 비상장(stock_code 공백)은 제외."""
    root = ElementTree.fromstring(xml_bytes)
    mapping: dict[str, str] = {}
    for item in root.iter("list"):
        corp_name = (item.findtext("corp_name") or "").strip()
        stock_code = (item.findtext("stock_code") or "").strip()
        if corp_name and stock_code:
            mapping[corp_name] = stock_code
    return mapping


def _raise_from_error_body(content: bytes) -> None:
    status = "unknown"
    message = "corpCode.xml 응답이 zip 이 아닙니다."
    try:
        root = ElementTree.fromstring(content)
        status = root.findtext("status") or status
        message = root.findtext("message") or message
    except ElementTree.ParseError:
        pass
    raise DartApiError(status=str(status), message=str(message))
