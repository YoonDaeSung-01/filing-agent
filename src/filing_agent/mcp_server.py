"""MCP 서버 — filing-agent 도구를 Model Context Protocol 로 노출한다.

Claude Desktop 등 MCP 클라이언트가 DART 재무 도구를 직접 호출할 수 있게 한다.
도구 본체는 agent/tools.py 를 재사용(LangChain 도구에 위임)하므로 로직이 한 곳에 있다.

실행(stdio 트랜스포트):
    uv run python -m filing_agent.mcp_server

키·DB 는 도구를 실제 호출할 때만 필요하다. 모듈 임포트·도구 등록 자체는 키 없이 된다.

Claude Desktop 설정 예(claude_desktop_config.json):
    {
      "mcpServers": {
        "filing-agent": {
          "command": "uv",
          "args": ["run", "python", "-m", "filing_agent.mcp_server"],
          "cwd": "<프로젝트 절대경로>"
        }
      }
    }
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from filing_agent.agent import tools as t

mcp = FastMCP("filing-agent")


@mcp.tool()
def doc_search(query: str, company: str | None = None, year: int | None = None) -> list[dict]:
    """공시 '서술'(사업 위험·전략·경영진단 등)을 의미 검색한다.

    수치(매출/이익 등)는 financial_lookup 을 쓸 것.
    """
    return t.doc_search.invoke({"query": query, "company": company, "year": year})


@mcp.tool()
def financial_lookup(company: str, account: str, year: int) -> dict:
    """공시 재무 '수치'를 구조화 값으로 반환한다.

    account 는 {매출액, 영업이익, 당기순이익, 자산총계, 부채총계} 중 하나.
    """
    return t.financial_lookup.invoke({"company": company, "account": account, "year": year})


@mcp.tool()
def compute_change(company: str, account: str, year_from: int, year_to: int) -> dict:
    """두 연도 사이 증감액·증감률을 도구 내부에서 계산해 반환한다."""
    return t.compute_change.invoke({
        "company": company,
        "account": account,
        "year_from": year_from,
        "year_to": year_to,
    })


@mcp.tool()
def compute_sum(companies: list[str], account: str, year: int) -> dict:
    """여러 회사의 같은 계정·같은 연도 수치를 도구 내부에서 결정론 합산한다."""
    return t.compute_sum.invoke({"companies": companies, "account": account, "year": year})


def main() -> None:
    """stdio 트랜스포트로 MCP 서버를 띄운다."""
    mcp.run()


if __name__ == "__main__":
    main()
