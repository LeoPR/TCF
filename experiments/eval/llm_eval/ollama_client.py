"""Ollama HTTP client — generate + model management (pull / ensure)."""

from __future__ import annotations
import sys
import requests
from typing import Any, TypedDict


class GenerateResult(TypedDict):
    text: str            # model response text
    prompt_tokens: int   # tokens used by the prompt  (prompt_eval_count)
    response_tokens: int # tokens generated            (eval_count)
    total_duration_ns: int  # wall-clock in nanoseconds (total_duration)
    load_duration_ns: int   # model load time in ns (disk/cache -> GPU)
    prompt_eval_ns: int     # prompt processing time in ns (prefill)
    eval_ns: int            # response generation time in ns (decode)
    done_reason: str        # "stop", "length", etc.


class OllamaClient:
    def __init__(self, endpoint: str = "http://localhost:11434") -> None:
        self.endpoint = endpoint.rstrip("/")

    # ------------------------------------------------------------------
    # Core generation
    # ------------------------------------------------------------------

    # Keys that Ollama expects at top-level of /api/generate, not inside options.
    # See Ollama 0.21+ API: think/keep_alive/format are first-class request fields.
    _TOPLEVEL_KEYS = ("think", "keep_alive", "format", "raw", "system", "template")

    def generate(
        self,
        model: str,
        prompt: str,
        options: dict[str, Any] | None = None,
        auto_pull: bool = True,
        timeout: int = 7200,  # 2h — CPU thinking on 14-20B can exceed 1h
    ) -> GenerateResult:
        """Send a prompt to the model and return text + token metrics.

        Options dict may include top-level keys like `think`, `keep_alive`, `format`;
        these are auto-routed to the request body (not inside "options").
        Default timeout=3600s (1h) — CPU thinking on 14B can exceed 10min.
        """
        url = f"{self.endpoint}/api/generate"
        payload: dict[str, Any] = {"model": model, "prompt": prompt, "stream": False}
        if options:
            opts = dict(options)
            for k in self._TOPLEVEL_KEYS:
                if k in opts:
                    payload[k] = opts.pop(k)
            if opts:
                payload["options"] = opts
        r = requests.post(url, json=payload, timeout=timeout)
        # Auto-pull if model not found
        if r.status_code == 404 and auto_pull:
            self.pull(model)
            r = requests.post(url, json=payload, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        return GenerateResult(
            text=data.get("response", ""),
            prompt_tokens=data.get("prompt_eval_count", 0),
            response_tokens=data.get("eval_count", 0),
            total_duration_ns=data.get("total_duration", 0),
            load_duration_ns=data.get("load_duration", 0),
            prompt_eval_ns=data.get("prompt_eval_duration", 0),
            eval_ns=data.get("eval_duration", 0),
            done_reason=data.get("done_reason", ""),
        )

    # ------------------------------------------------------------------
    # Server / model checks
    # ------------------------------------------------------------------

    def is_available(self, timeout: int = 5) -> bool:
        """Return True if the Ollama server is reachable."""
        try:
            r = requests.get(f"{self.endpoint}/api/tags", timeout=timeout)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def installed_models(self) -> list[str]:
        """Return list of model names currently installed."""
        r = requests.get(f"{self.endpoint}/api/tags", timeout=15)
        r.raise_for_status()
        return [m["name"] for m in r.json().get("models", [])]

    def is_installed(self, model: str) -> bool:
        """Return True if *model* is already installed locally."""
        installed = self.installed_models()
        # Accept both "gemma3:12b" and "gemma3" (matches any tag)
        base = model.split(":")[0]
        for name in installed:
            if name == model or name.split(":")[0] == base:
                return True
        return False

    # ------------------------------------------------------------------
    # Model pull
    # ------------------------------------------------------------------

    def pull(self, model: str, verbose: bool = True) -> None:
        """Download *model* from the Ollama registry.

        Streams progress lines and prints them if verbose=True.
        Raises requests.HTTPError on failure.
        """
        url = f"{self.endpoint}/api/pull"
        if verbose:
            print(f"[ollama] Pulling {model!r} ...", flush=True)

        with requests.post(url, json={"name": model}, stream=True, timeout=3600) as r:
            r.raise_for_status()
            last_status = ""
            for raw in r.iter_lines():
                if not raw:
                    continue
                import json
                try:
                    data = json.loads(raw)
                except Exception:
                    continue
                status = data.get("status", "")
                if verbose and status != last_status:
                    total    = data.get("total", 0)
                    completed = data.get("completed", 0)
                    if total:
                        pct = 100 * completed // total
                        print(f"\r[ollama] {status} {pct}%   ", end="", flush=True)
                    else:
                        print(f"\r[ollama] {status}   ", end="", flush=True)
                    last_status = status
            if verbose:
                print(f"\r[ollama] {model!r} ready.        ", flush=True)

    def ensure(self, model: str, verbose: bool = True) -> None:
        """Pull *model* if it is not already installed."""
        if self.is_installed(model):
            if verbose:
                print(f"[ollama] {model!r} already installed.", flush=True)
            return
        self.pull(model, verbose=verbose)
