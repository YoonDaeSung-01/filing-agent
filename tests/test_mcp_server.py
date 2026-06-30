"""mcp_server.py 테스트 — 키·네트워크·DB 불필요.

도구 등록과 위임만 검증한다(실제 도구 호출은 모킹). MCP 서버를 실제로 띄우지 않는다.
"""

import asyncio
from unittest.mock import MagicMock

from filing_agent import mcp_server as srv


def test_all_four_tools_registered() -> None:
    tools = asyncio.run(srv.mcp.list_tools())
    names = {tool.name for tool in tools}
    assert names == {"doc_search", "financial_lookup", "compute_change", "compute_sum"}


def test_financial_lookup_delegates_to_tool() -> None:
    fake = MagicMock()
    fake.invoke.return_value = {"value": 1, "found": True}
    # 래퍼는 호출 시점에 t.financial_lookup 을 참조 → 객체째 교체
    srv.t.financial_lookup, original = fake, srv.t.financial_lookup
    try:
        out = srv.financial_lookup("삼성전자", "매출액", 2024)
    finally:
        srv.t.financial_lookup = original
    assert out == {"value": 1, "found": True}
    fake.invoke.assert_called_once_with(
        {"company": "삼성전자", "account": "매출액", "year": 2024}
    )


def test_compute_sum_delegates_to_tool() -> None:
    fake = MagicMock()
    fake.invoke.return_value = {"total": 5}
    srv.t.compute_sum, original = fake, srv.t.compute_sum
    try:
        out = srv.compute_sum(["A사", "B사"], "매출액", 2024)
    finally:
        srv.t.compute_sum = original
    assert out == {"total": 5}
    fake.invoke.assert_called_once_with(
        {"companies": ["A사", "B사"], "account": "매출액", "year": 2024}
    )
