"""LiteLLM 게이트웨이 — LLM 완성·임베딩 공급자를 추상화한다.

이 모듈이 외부 LLM/임베딩 호출의 유일한 진입점이다.
공급자를 바꾸려면 .env 의 LLM_MODEL 만 수정하면 된다.
"""

from __future__ import annotations

from typing import Any

import litellm

from filing_agent.config import Settings

_SYSTEM_PROMPT = (
    "당신은 한국 기업 전자공시(DART) 자료를 기반으로 사실을 추출하는 어시스턴트입니다.\n"
    "규칙:\n"
    "1. 반드시 제공된 공시 자료 내에서만 답하시오.\n"
    "2. 답변에 출처(공시 자료 명칭·연도)를 항상 명시하시오.\n"
    "3. 자료에서 찾을 수 없으면 '공시 자료에서 확인할 수 없습니다'라고 답하시오.\n"
    "4. 투자 조언(매수·매도 추천)은 절대 하지 마시오."
)


def _build_context(chunks: list[dict[str, Any]]) -> str:
    parts = []
    for i, chunk in enumerate(chunks, 1):
        source = chunk.get("source", "")
        content = chunk.get("content", "")
        parts.append(f"[출처 {i}] {source}\n{content}")
    return "\n\n".join(parts)


def ask(
    question: str,
    context_chunks: list[dict[str, Any]],
    settings: Settings,
) -> str:
    """RAG 컨텍스트를 붙여 LLM 에 질의하고 답변 문자열을 반환한다."""
    context = _build_context(context_chunks)
    user_content = f"공시 자료:\n\n{context}\n\n질문: {question}"

    response = litellm.completion(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        api_key=settings.llm_api_key,
        max_tokens=1024,
    )
    return response.choices[0].message.content or ""


def embed(texts: list[str], settings: Settings) -> list[list[float]]:
    """텍스트 리스트를 임베딩 벡터 리스트로 변환한다."""
    response = litellm.embedding(
        model=settings.embedding_model,
        input=texts,
        api_key=settings.llm_api_key,
    )
    return [item["embedding"] for item in response.data]
