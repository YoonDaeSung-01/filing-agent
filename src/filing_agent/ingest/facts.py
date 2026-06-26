"""DART 응답에서 재무 '사실'을 뽑는 순수 로직.

이 모듈은 네트워크/설정에 의존하지 않는다(표준 라이브러리 타입만 사용). 따라서 키 없이
픽스처만으로 테스트된다. 실제 HTTP 호출/캐싱은 ``dart_client`` 가 담당한다.

DART 규칙:
- DART 는 실패도 HTTP 200 + 본문 ``status`` 로 알린다("000" 정상, "013" 데이터 없음 등).
  → status != "000" 이면 :class:`DartApiError`.
- 금액은 콤마 포함 문자열("300,870,903")로 온다 → 콤마 제거 후 ``int``(원 단위 정수).
- ``fnlttSinglAcnt.json`` 응답은 한 호출에 CFS·OFS 행을 함께 주며 각 행이 ``fs_div`` 로
  태깅된다. 연결(CFS)에 계정이 없으면 별도(OFS)로 폴백한다.
"""

from collections.abc import Mapping, Sequence
from typing import Any, Literal, TypedDict

FsDiv = Literal["CFS", "OFS"]


class FinancialFact(TypedDict):
    """타입 있는 구조화 값 — 이후 단계에서도 이 구조를 그대로 사용한다."""

    company: str
    account: str
    year: int
    value: int  # 원 단위 정수
    fs_div: FsDiv
    source: str


class DartApiError(Exception):
    """DART 가 status != "000" 으로 응답했을 때 발생한다."""

    def __init__(self, status: str, message: str) -> None:
        self.status = status
        self.message = message
        super().__init__(f"DART status={status}: {message}")


def ensure_status_ok(payload: Mapping[str, Any]) -> None:
    """status 가 "000" 이 아니면 :class:`DartApiError` 를 던진다."""
    status = payload.get("status")
    if status != "000":
        message = str(payload.get("message", ""))
        raise DartApiError(status=str(status), message=message)


def _parse_amount(raw: Any) -> int | None:
    """'300,870,903' → 300870903. 빈 값/'-' 등 숫자가 아니면 None."""
    if not isinstance(raw, str):
        return None
    cleaned = raw.replace(",", "").strip()
    if cleaned in ("", "-"):
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None


def _build_source(row: Mapping[str, Any], fs_div: FsDiv) -> str:
    return (
        "OpenDART fnlttSinglAcnt.json "
        f"(corp_code={row.get('corp_code')}, bsns_year={row.get('bsns_year')}, "
        f"reprt_code={row.get('reprt_code')}, fs_div={fs_div})"
    )


def extract_account(
    payload: Mapping[str, Any],
    *,
    company: str,
    account_nm: str = "매출액",
    fs_div: FsDiv = "CFS",
    year: int | None = None,
) -> FinancialFact | None:
    """주어진 ``fs_div`` 에서 ``account_nm`` 계정 값을 구조화 값으로 반환한다.

    status 가 "000" 이 아니면 :class:`DartApiError`. 해당 계정 행이 없으면 None
    (호출부가 OFS 폴백 등을 결정할 수 있게).
    """
    ensure_status_ok(payload)
    rows: Sequence[Mapping[str, Any]] = payload.get("list", []) or []
    for row in rows:
        if row.get("account_nm") != account_nm or row.get("fs_div") != fs_div:
            continue
        value = _parse_amount(row.get("thstrm_amount"))
        if value is None:
            continue
        resolved_year = year if year is not None else int(row["bsns_year"])
        return FinancialFact(
            company=company,
            account=account_nm,
            year=resolved_year,
            value=value,
            fs_div=fs_div,
            source=_build_source(row, fs_div),
        )
    return None


def extract_change(
    payload: Mapping[str, Any],
    *,
    company: str,
    account_nm: str,
    year_to: int,
) -> tuple[FinancialFact, FinancialFact] | None:
    """단일 보고서 페이로드에서 당기(thstrm_amount)·전기(frmtrm_amount)를 꺼내 (from, to) 쌍 반환.

    연결(CFS) 우선, 없으면 별도(OFS). 어느 쪽도 없으면 None.
    """
    ensure_status_ok(payload)
    rows: Sequence[Mapping[str, Any]] = payload.get("list", []) or []

    def _try_fs(fs_div: FsDiv) -> tuple[FinancialFact, FinancialFact] | None:
        for row in rows:
            if row.get("account_nm") != account_nm or row.get("fs_div") != fs_div:
                continue
            v_to = _parse_amount(row.get("thstrm_amount"))
            v_from = _parse_amount(row.get("frmtrm_amount"))
            if v_to is None or v_from is None:
                return None
            src = _build_source(row, fs_div)
            fact_from = FinancialFact(
                company=company,
                account=account_nm,
                year=year_to - 1,
                value=v_from,
                fs_div=fs_div,
                source=src,
            )
            fact_to = FinancialFact(
                company=company,
                account=account_nm,
                year=year_to,
                value=v_to,
                fs_div=fs_div,
                source=src,
            )
            return fact_from, fact_to
        return None

    return _try_fs("CFS") or _try_fs("OFS")


def build_revenue_fact(
    payload: Mapping[str, Any],
    *,
    company: str,
    account_nm: str = "매출액",
    year: int | None = None,
    prefer: Sequence[FsDiv] = ("CFS", "OFS"),
) -> FinancialFact | None:
    """``prefer`` 순서대로 계정을 찾는다(기본: CFS → OFS 폴백).

    하나도 못 찾으면 None. status 가 "000" 이 아니면 :class:`DartApiError`.
    """
    ensure_status_ok(payload)
    for fs_div in prefer:
        fact = extract_account(
            payload, company=company, account_nm=account_nm, fs_div=fs_div, year=year
        )
        if fact is not None:
            return fact
    return None
