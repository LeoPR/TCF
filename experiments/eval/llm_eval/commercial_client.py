"""Commercial LLM clients — Anthropic + OpenAI (Google support TBD).

Mirrors interface of OllamaClient: client.generate(model, prompt, options=...)
returns dict with `text`, `total_duration_ns`, `prompt_tokens`, `response_tokens`.

API keys read from environment variables:
  ANTHROPIC_API_KEY  — for claude-* models
  OPENAI_API_KEY     — for gpt-* models

Or from config/api_keys.json (gitignored):
  {"anthropic": "sk-ant-...", "openai": "sk-..."}

Cost tracking: each call returns `cost_usd` in result for budget control.

Pricing (USD per 1M tokens, as of 2026-04):
  claude-haiku-4-5:  $0.80 input / $4.00 output
  claude-sonnet-4-6: $3.00 input / $15.00 output
  gpt-4o-mini:       $0.15 input / $0.60 output
  gpt-4o:            $2.50 input / $10.00 output

Usage:
    client = CommercialClient()
    result = client.generate("claude-sonnet-4-6", "What is 2+2?")
    print(result["text"], result["cost_usd"])
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path


# Pricing in USD per million tokens (input, output)
PRICING = {
    "claude-haiku-4-5":   (0.80, 4.00),
    "claude-sonnet-4-6":  (3.00, 15.00),
    "claude-sonnet-4-7":  (3.00, 15.00),
    "claude-opus-4-7":    (15.00, 75.00),
    "gpt-4o-mini":        (0.15, 0.60),
    "gpt-4o":             (2.50, 10.00),
    "gpt-4o-2024-11-20":  (2.50, 10.00),
    "gpt-5-mini":         (0.25, 2.00),
    "gpt-5":              (1.25, 10.00),
}


def _provider_for(model: str) -> str:
    """Infer provider from model name."""
    m = model.lower()
    if m.startswith("claude") or m.startswith("anthropic"):
        return "anthropic"
    if m.startswith("gpt") or m.startswith("o1") or m.startswith("openai"):
        return "openai"
    raise ValueError(f"Unknown provider for model: {model!r}")


def _load_keys() -> dict[str, str]:
    """Load API keys from env vars or config/api_keys.json."""
    keys = {
        "anthropic": os.environ.get("ANTHROPIC_API_KEY", ""),
        "openai": os.environ.get("OPENAI_API_KEY", ""),
    }
    cfg_path = Path(__file__).resolve().parents[3] / "config" / "api_keys.json"
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            for k, v in cfg.items():
                if not keys.get(k):
                    keys[k] = v
        except Exception as e:
            print(f"[CommercialClient] WARN: failed to read {cfg_path}: {e}")
    return keys


def estimate_cost(model: str, prompt_tokens: int, response_tokens: int) -> float:
    """Compute USD cost for a single call."""
    if model not in PRICING:
        return 0.0
    in_price, out_price = PRICING[model]
    return (prompt_tokens / 1_000_000) * in_price + (response_tokens / 1_000_000) * out_price


class CommercialClient:
    """Unified client for Anthropic + OpenAI models."""

    def __init__(self, max_cost_usd: float | None = None):
        self.keys = _load_keys()
        self.total_cost_usd = 0.0
        self.max_cost_usd = max_cost_usd  # None = no budget cap
        self._anthropic = None
        self._openai = None

    def _get_anthropic(self):
        if self._anthropic is None:
            try:
                import anthropic
            except ImportError as e:
                raise ImportError(
                    "anthropic package not installed. Run: pip install anthropic"
                ) from e
            if not self.keys["anthropic"]:
                raise RuntimeError(
                    "ANTHROPIC_API_KEY not set (env var or config/api_keys.json)"
                )
            self._anthropic = anthropic.Anthropic(api_key=self.keys["anthropic"])
        return self._anthropic

    def _get_openai(self):
        if self._openai is None:
            try:
                import openai
            except ImportError as e:
                raise ImportError(
                    "openai package not installed. Run: pip install openai"
                ) from e
            if not self.keys["openai"]:
                raise RuntimeError(
                    "OPENAI_API_KEY not set (env var or config/api_keys.json)"
                )
            self._openai = openai.OpenAI(api_key=self.keys["openai"])
        return self._openai

    def is_available(self, model: str) -> bool:
        """Check if model has API key configured (without making a call)."""
        try:
            provider = _provider_for(model)
        except ValueError:
            return False
        return bool(self.keys.get(provider))

    def generate(
        self,
        model: str,
        prompt: str,
        *,
        options: dict | None = None,
        timeout: float = 120.0,
    ) -> dict:
        """Generate completion. Returns dict with text, tokens, cost, latency_ns."""
        options = options or {}
        max_tokens = options.get("num_predict", 2048)
        temperature = options.get("temperature", 0)

        # Budget check before call
        if self.max_cost_usd is not None and self.total_cost_usd >= self.max_cost_usd:
            raise RuntimeError(
                f"Budget cap exceeded: ${self.total_cost_usd:.4f} >= ${self.max_cost_usd:.4f}"
            )

        provider = _provider_for(model)
        t_start = time.time()

        if provider == "anthropic":
            client = self._get_anthropic()
            resp = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            text = "".join(b.text for b in resp.content if hasattr(b, "text"))
            prompt_tokens = resp.usage.input_tokens
            response_tokens = resp.usage.output_tokens
        elif provider == "openai":
            client = self._get_openai()
            resp = client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            text = resp.choices[0].message.content or ""
            prompt_tokens = resp.usage.prompt_tokens
            response_tokens = resp.usage.completion_tokens
        else:
            raise ValueError(f"Provider {provider!r} not implemented")

        elapsed_ns = int((time.time() - t_start) * 1_000_000_000)
        cost = estimate_cost(model, prompt_tokens, response_tokens)
        self.total_cost_usd += cost

        return {
            "text": text,
            "total_duration_ns": elapsed_ns,
            "prompt_tokens": prompt_tokens,
            "response_tokens": response_tokens,
            "cost_usd": cost,
            "cumulative_cost_usd": self.total_cost_usd,
        }


__all__ = ["CommercialClient", "PRICING", "estimate_cost"]
