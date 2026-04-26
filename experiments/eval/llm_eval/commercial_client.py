"""Commercial LLM clients — Anthropic + OpenAI (Google support TBD).

Mirrors interface of OllamaClient: client.generate(model, prompt, options=...)
returns dict with `text`, `total_duration_ns`, `prompt_tokens`, `response_tokens`,
`cost_usd`, `cumulative_cost_usd`, and (when caching is hit) `cached_tokens`.

API keys read from environment variables:
  ANTHROPIC_API_KEY  — for claude-* models
  OPENAI_API_KEY     — for gpt-*/o-* models

Or from config/api_keys.json (gitignored):
  {"anthropic": "sk-ant-...", "openai": "sk-..."}

Pricing in USD per 1M tokens — verified against official docs 2026-04-26.
Cached input is the price for cache READS (after a write happens). Anthropic
charges 1.25× input price for the WRITE; OpenAI caching is automatic on
prompts ≥1024 tokens with no extra write cost.

Use ``estimate_cost(model, in_tok, out_tok, cached_in_tok)`` to project costs
before the call. Use ``CommercialClient.count_tokens(model, prompt)`` for an
exact pre-flight token count (free on Anthropic; tiktoken locally on OpenAI).
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path


# Pricing in USD per million tokens.
# Tuple = (input, output, cached_input). cached_input=None means no caching tier.
# Sources verified 2026-04-26 (https://platform.claude.com/docs/en/about-claude/pricing,
# https://developers.openai.com/api/docs/pricing).
PRICING: dict[str, tuple[float, float, float | None]] = {
    # --- Anthropic Claude (active) ------------------------------------------
    "claude-haiku-4-5":   (1.00,  5.00,  0.10),
    "claude-sonnet-4-6":  (3.00, 15.00,  0.30),
    "claude-opus-4-7":    (5.00, 25.00,  0.50),
    # Legacy tags (some still in deprecation grace period)
    "claude-sonnet-4-7":  (3.00, 15.00,  0.30),
    "claude-haiku-3-5":   (0.80,  4.00,  None),  # deprecated
    # --- OpenAI ChatGPT-5 family (current) ---------------------------------
    "gpt-5.5":            (5.00, 30.00,  0.50),
    "gpt-5.4":            (2.50, 15.00,  0.25),
    "gpt-5.4-mini":       (0.75,  4.50,  0.075),
    "gpt-5.4-nano":       (0.20,  1.25,  0.02),
    "gpt-5.2":            (1.75, 14.00,  None),
    "gpt-5.1":            (1.25, 10.00,  None),
    # OpenAI o-series (reasoning)
    "o3":                 (2.00,  8.00,  None),
    # --- OpenAI 4o family (in deprecation path; gpt-4o sunsetting) ---------
    "gpt-4o-mini":        (0.15,  0.60,  0.075),
    "gpt-4o":             (2.50, 10.00,  1.25),
    "gpt-4o-2024-11-20":  (2.50, 10.00,  1.25),
}


def _provider_for(model: str) -> str:
    """Infer provider from model name."""
    m = model.lower()
    if m.startswith("claude") or m.startswith("anthropic"):
        return "anthropic"
    if m.startswith("gpt") or m.startswith("o1") or m.startswith("o3") or m.startswith("o4") or m.startswith("openai"):
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


def estimate_cost(
    model: str,
    prompt_tokens: int,
    response_tokens: int,
    cached_input_tokens: int = 0,
) -> float:
    """Compute USD cost for a single call.

    ``cached_input_tokens`` is the count of input tokens served from cache
    (subtracted from prompt_tokens before applying the cached_input rate).
    Anthropic adds a separate 1.25× multiplier on the WRITE (charged once
    per cache breakpoint creation) — that's not modelled here; pass write
    tokens as regular ``prompt_tokens`` to match how the API bills.
    """
    if model not in PRICING:
        return 0.0
    in_price, out_price, cached_price = PRICING[model]
    fresh_input = max(0, prompt_tokens - cached_input_tokens)
    cost = (fresh_input / 1_000_000) * in_price
    cost += (response_tokens / 1_000_000) * out_price
    if cached_input_tokens > 0 and cached_price is not None:
        cost += (cached_input_tokens / 1_000_000) * cached_price
    return cost


class CommercialClient:
    """Unified client for Anthropic + OpenAI models."""

    def __init__(self, max_cost_usd: float | None = None):
        self.keys = _load_keys()
        self.total_cost_usd = 0.0
        self.max_cost_usd = max_cost_usd  # None = no budget cap
        self._anthropic = None
        self._openai = None
        self._tiktoken_enc = None

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

    def _get_tiktoken(self):
        """Lazy load tiktoken encoder for OpenAI models (o200k_base for GPT-4o/5)."""
        if self._tiktoken_enc is None:
            try:
                import tiktoken
            except ImportError as e:
                raise ImportError(
                    "tiktoken not installed. Run: pip install tiktoken"
                ) from e
            self._tiktoken_enc = tiktoken.get_encoding("o200k_base")
        return self._tiktoken_enc

    def is_available(self, model: str) -> bool:
        """Check if model has API key configured (without making a call)."""
        try:
            provider = _provider_for(model)
        except ValueError:
            return False
        return bool(self.keys.get(provider))

    def count_tokens(self, model: str, prompt: str) -> int:
        """Pre-flight token count.

        For Anthropic: uses official ``messages.count_tokens`` endpoint (free).
        For OpenAI: uses local tiktoken with ``o200k_base`` encoding (matches
        GPT-4o and GPT-5 family).
        """
        provider = _provider_for(model)
        if provider == "anthropic":
            client = self._get_anthropic()
            try:
                resp = client.messages.count_tokens(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                )
                return int(resp.input_tokens)
            except Exception:
                # Fallback: rough heuristic ~4 chars/token
                return len(prompt) // 4
        elif provider == "openai":
            try:
                enc = self._get_tiktoken()
                return len(enc.encode(prompt))
            except Exception:
                return len(prompt) // 4
        return len(prompt) // 4

    def _is_openai_reasoning(self, model: str) -> bool:
        """OpenAI reasoning model family (gpt-5, o-series) require different params."""
        return (model.startswith("gpt-5") or model.startswith("o1")
                or model.startswith("o3") or model.startswith("o4"))

    def generate(
        self,
        model: str,
        prompt: str,
        *,
        options: dict | None = None,
        timeout: float = 120.0,
        cache_prefix: str | None = None,
        text_format: type | None = None,
        cache_key: str | None = None,
    ) -> dict:
        """Generate a model response. Provider-aware routing.

        Args
        ----
        model
            Provider-prefixed id (``claude-*``, ``gpt-*``, ``o3``, etc.).
        prompt
            User-side input (the variable part of the request).
        options
            ``num_predict`` (max output tokens) and ``temperature`` (only used
            for non-reasoning models).
        cache_prefix
            Static prefix that will be cached. Anthropic: passed as ``system``
            block with ``cache_control``. OpenAI: passed as ``instructions``
            in the Responses API (cached automatically; ``cache_key`` recommended).
        text_format
            Pydantic ``BaseModel`` subclass. When provided, OpenAI uses
            ``responses.parse`` and returns the parsed object in ``text_parsed``.
            Ignored for Anthropic (use tools/structured outputs there separately).
        cache_key
            OpenAI-only ``prompt_cache_key`` to keep cache reads attributed to
            this experiment. If None, defaults to model name.

        Returns
        -------
        dict with: ``text`` (raw), ``text_parsed`` (Pydantic instance or None),
        ``prompt_tokens``, ``response_tokens``, ``cached_tokens``, ``cost_usd``,
        ``cumulative_cost_usd``, ``total_duration_ns``.
        """
        options = options or {}
        max_tokens = options.get("num_predict", 2048)
        temperature = options.get("temperature", 0)

        if self.max_cost_usd is not None and self.total_cost_usd >= self.max_cost_usd:
            raise RuntimeError(
                f"Budget cap exceeded: ${self.total_cost_usd:.4f} >= ${self.max_cost_usd:.4f}"
            )

        provider = _provider_for(model)
        t_start = time.time()
        cached_tokens = 0
        text_parsed = None

        if provider == "anthropic":
            client = self._get_anthropic()
            kwargs = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            if cache_prefix is not None:
                kwargs["system"] = [{
                    "type": "text",
                    "text": cache_prefix,
                    "cache_control": {"type": "ephemeral"},
                }]
                kwargs["messages"] = [{"role": "user", "content": prompt}]
            else:
                kwargs["messages"] = [{"role": "user", "content": prompt}]
            resp = client.messages.create(**kwargs)
            text = "".join(b.text for b in resp.content if hasattr(b, "text"))
            usage = resp.usage
            prompt_tokens = usage.input_tokens
            response_tokens = usage.output_tokens
            cached_tokens = getattr(usage, "cache_read_input_tokens", 0) or 0
        elif provider == "openai":
            client = self._get_openai()
            is_reasoning = self._is_openai_reasoning(model)

            # Build Responses API kwargs.
            # cache_prefix → instructions (cached static prefix);
            # prompt → input (varies per call).
            kwargs = {
                "model": model,
                "input": prompt,
                "max_output_tokens": max_tokens,
            }
            if cache_prefix is not None:
                kwargs["instructions"] = cache_prefix
            kwargs["prompt_cache_key"] = cache_key or f"tcf_{model}"

            if is_reasoning:
                # GPT-5 / o-series: no temperature / top_p / seed accepted.
                # ``reasoning.effort='low'`` is the cheapest setting that still
                # allows real chain-of-thought (which is required for tasks
                # like distinct counts or filter+agg over RLE-encoded data).
                # ``effort='none'`` produces faster but worse answers (we
                # validated this empirically). Output budget bumped to fit
                # reasoning tokens + answer.
                kwargs["reasoning"] = {"effort": "low"}
                kwargs["text"] = {"verbosity": "low"}
                if max_tokens < 512:
                    kwargs["max_output_tokens"] = 512
            else:
                # gpt-4o family supports temperature/top_p.
                kwargs["temperature"] = temperature
                kwargs["top_p"] = 1

            if text_format is not None:
                resp = client.responses.parse(text_format=text_format, **kwargs)
                text_parsed = resp.output_parsed
                text = resp.output_text
            else:
                resp = client.responses.create(**kwargs)
                text = resp.output_text

            usage = resp.usage
            prompt_tokens = usage.input_tokens
            response_tokens = usage.output_tokens
            details = getattr(usage, "input_tokens_details", None)
            cached_tokens = getattr(details, "cached_tokens", 0) if details else 0
        else:
            raise ValueError(f"Provider {provider!r} not implemented")

        elapsed_ns = int((time.time() - t_start) * 1_000_000_000)
        cost = estimate_cost(model, prompt_tokens, response_tokens, cached_tokens)
        self.total_cost_usd += cost

        return {
            "text": text,
            "text_parsed": text_parsed,
            "total_duration_ns": elapsed_ns,
            "prompt_tokens": prompt_tokens,
            "response_tokens": response_tokens,
            "cached_tokens": cached_tokens,
            "cost_usd": cost,
            "cumulative_cost_usd": self.total_cost_usd,
        }


__all__ = ["CommercialClient", "PRICING", "estimate_cost"]
