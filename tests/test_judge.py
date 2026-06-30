"""eval/judge.py 테스트 — 파싱은 순수 함수(키 없이), LLM 호출은 모킹."""

from unittest.mock import patch

from filing_agent.eval import judge


# ── _parse_verdict (순수 함수) ────────────────────────────────────────────────
class TestParseVerdict:
    def test_clean_json(self) -> None:
        v = judge._parse_verdict('{"faithfulness": 1, "relevance": 1, "reason": "근거 있음"}')
        assert v == {"faithfulness": 1, "relevance": 1, "reason": "근거 있음"}

    def test_json_in_code_fence(self) -> None:
        raw = '```json\n{"faithfulness": 0, "relevance": 1, "reason": "환각"}\n```'
        v = judge._parse_verdict(raw)
        assert v["faithfulness"] == 0
        assert v["relevance"] == 1

    def test_surrounding_text(self) -> None:
        raw = '판정: {"faithfulness": 1, "relevance": 0, "reason": "빗나감"} 입니다.'
        v = judge._parse_verdict(raw)
        assert v["faithfulness"] == 1
        assert v["relevance"] == 0

    def test_coerces_truthy_values(self) -> None:
        v = judge._parse_verdict('{"faithfulness": true, "relevance": "1"}')
        assert v["faithfulness"] == 1
        assert v["relevance"] == 1

    def test_garbage_falls_back(self) -> None:
        v = judge._parse_verdict("죄송합니다 점수를 못 매기겠어요")
        assert v["faithfulness"] == 0
        assert v["relevance"] == 0

    def test_empty_falls_back(self) -> None:
        assert judge._parse_verdict("") == judge._DEFAULT_VERDICT


# ── judge_answer (litellm 모킹) ──────────────────────────────────────────────
class _Msg:
    def __init__(self, content: str) -> None:
        self.message = type("M", (), {"content": content})()


class _Resp:
    def __init__(self, content: str) -> None:
        self.choices = [_Msg(content)]


class FakeSettings:
    llm_model = "gpt-4o-mini"
    llm_api_key = "dummy"


def test_judge_answer_parses_llm_response() -> None:
    fake = _Resp('{"faithfulness": 1, "relevance": 1, "reason": "ok"}')
    with (
        patch.object(judge, "get_settings", return_value=FakeSettings()),
        patch.object(judge.litellm, "completion", return_value=fake),
    ):
        v = judge.judge_answer("질문", "답변", context="컨텍스트")
    assert v["faithfulness"] == 1
    assert v["relevance"] == 1
