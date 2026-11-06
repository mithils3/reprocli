"""muse-wonder-1.0 for the mini-SWE-agent arm: litellm against Meta's OpenAI-compatible endpoint.

Every call keeps its token counts and its cost, so usage.json has one row per call. The key is read from
META_MODEL_KEY into OPENAI_API_KEY in this process only; it never goes into model_kwargs, so serialize() cannot
write it to a trajectory.
"""
import litellm
from minisweagent.models.litellm_model import LitellmModel

MODEL_NAME = "openai/muse-wonder-1.0"
API_BASE = "https://api.meta.ai/v1"
# xhigh, as the thin harness's Muse Wonder arm sets it, so the two arms differ only in harness.
# drop_params lets litellm omit any field the provider does not take; Meta rejects unknown body fields with a 400.
MODEL_KWARGS = {"api_base": API_BASE, "reasoning_effort": "xhigh", "drop_params": True}
# USD per million tokens: input, cached input, output (rebuttal/ops/COMMON.md).
PRICE = {"in": 4.00, "cached": 0.20, "out": 20.00}


def usage_of(response) -> dict:
    """Token counts of one response: prompt, cached prompt, completion, reasoning, and the cost in USD."""
    raw = getattr(response, "usage", None)
    u = raw.model_dump() if hasattr(raw, "model_dump") else (raw or {})
    prompt = int(u.get("prompt_tokens") or 0)
    cached = int((u.get("prompt_tokens_details") or {}).get("cached_tokens") or 0)
    out = int(u.get("completion_tokens") or 0)
    reasoning = (u.get("completion_tokens_details") or {}).get("reasoning_tokens")
    usd = ((prompt - cached) * PRICE["in"] + cached * PRICE["cached"] + out * PRICE["out"]) / 1e6
    return {"prompt_tokens": prompt, "cached_tokens": cached, "completion_tokens": out,
            "reasoning_tokens": reasoning, "usd": round(usd, 6)}


class MuseWonderModel(LitellmModel):
    def __init__(self, **kwargs):
        super().__init__(model_name=MODEL_NAME, model_kwargs=dict(MODEL_KWARGS), cost_tracking="ignore_errors",
                         **kwargs)
        self.calls: list[dict] = []

    def _record(self, response, call: str) -> dict:
        row = {"call": len(self.calls), "kind": call, "id": getattr(response, "id", None),
               "finish_reason": getattr(response.choices[0], "finish_reason", None) if response.choices else None,
               **usage_of(response)}
        self.calls.append(row)
        return row

    def _query(self, messages, **kwargs):
        response = super()._query(messages, **kwargs)
        self._record(response, "step")
        return response

    def _calculate_cost(self, response) -> dict[str, float]:
        return {"cost": usage_of(response)["usd"]}

    def final_report(self, messages: list[dict], response_format: dict) -> str:
        """One call with no tools and the report schema as response_format. Returns the message content."""
        response = litellm.completion(model=self.config.model_name, messages=self._prepare_messages_for_api(messages),
                                      response_format=response_format, **self.config.model_kwargs)
        self._record(response, "final")
        return response.choices[0].message.content or ""

    def totals(self) -> dict:
        keys = ("prompt_tokens", "cached_tokens", "completion_tokens", "usd")
        return {k: round(sum(c[k] for c in self.calls), 6) for k in keys} | {"calls": len(self.calls)}
