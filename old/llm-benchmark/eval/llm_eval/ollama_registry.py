"""Ollama registry scraper — discover models, tags, sizes from ollama.com.

No public API exists for listing remote models/tags. This module scrapes
the HTML pages to extract structured data.

Endpoints used:
    https://ollama.com/library                       → list all model names
    https://ollama.com/library/{model}               → model description + size badges
    https://ollama.com/library/{model}/tags           → all tags with disk sizes
    https://ollama.com/search?q={query}              → search models by name
    https://registry.ollama.com/v2/library/{model}/manifests/{tag}  → OCI manifest (exact size)
    http://localhost:11434/api/tags                   → locally installed models

Usage:
    from llm_eval.ollama_registry import OllamaRegistry

    reg = OllamaRegistry()
    models = reg.list_models()                 # all 219+ model names
    tags = reg.list_tags("qwen3")              # all tags with sizes
    installed = reg.list_installed()            # local models with details
    plan = reg.recommend_for_benchmark(gpu_gb=12)  # smart selection
"""

from __future__ import annotations
import re
import json
import requests
from dataclasses import dataclass, field
from typing import Any


OLLAMA_COM = "https://ollama.com"
REGISTRY = "https://registry.ollama.com"
LOCAL = "http://localhost:11434"


@dataclass
class ModelTag:
    model: str
    tag: str
    size_gb: float
    quantization: str = ""  # q4_K_M, q8_0, fp16, etc.
    variant: str = ""       # instruct, base, thinking, etc.

    @property
    def full_name(self) -> str:
        return f"{self.model}:{self.tag}"

    @property
    def param_size(self) -> str:
        """Extract parameter size like '8b', '14b' from tag."""
        m = re.match(r"(\d+(?:\.\d+)?[bm])", self.tag, re.I)
        return m.group(1).lower() if m else ""


class OllamaRegistry:
    """Discover and analyze Ollama models from ollama.com and local server."""

    def __init__(self, local_endpoint: str = LOCAL, timeout: int = 15):
        self.local = local_endpoint
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Remote: ollama.com scraping
    # ------------------------------------------------------------------

    def list_models(self) -> list[str]:
        """List all model names from ollama.com/library."""
        r = requests.get(f"{OLLAMA_COM}/library", timeout=self.timeout)
        r.raise_for_status()
        names = re.findall(r'href="/library/([^/"]+)"', r.text)
        return sorted(set(names))

    def search_models(self, query: str) -> list[str]:
        """Search models by name on ollama.com."""
        r = requests.get(f"{OLLAMA_COM}/search", params={"q": query}, timeout=self.timeout)
        r.raise_for_status()
        names = re.findall(r'href="/library/([^/"]+)"', r.text)
        return sorted(set(names))

    def get_size_badges(self, model: str) -> list[str]:
        """Get the size badges (1b, 4b, 12b...) from model's main page."""
        r = requests.get(f"{OLLAMA_COM}/library/{model}", timeout=self.timeout)
        r.raise_for_status()
        badges = re.findall(r">([\d.]+[bBmM])<", r.text)
        return sorted(set(b.lower() for b in badges))

    def list_tags(self, model: str) -> list[ModelTag]:
        """List all tags with disk sizes from model's tags page."""
        r = requests.get(f"{OLLAMA_COM}/library/{model}/tags", timeout=self.timeout)
        r.raise_for_status()
        html = r.text

        results = []
        lines = html.split("\n")
        current_tag = None

        for line in lines:
            tag_match = re.search(rf'/library/{re.escape(model)}[:/]([^"]+)', line)
            if tag_match:
                current_tag = tag_match.group(1)
            size_match = re.search(r"(\d+(?:\.\d+)?)\s*(GB|MB|KB)", line)
            if size_match and current_tag:
                size_val = float(size_match.group(1))
                unit = size_match.group(2)
                if unit == "MB":
                    size_val /= 1000
                elif unit == "KB":
                    size_val /= 1_000_000

                # Parse tag components
                quant = ""
                variant = ""
                qm = re.search(r"(q\d+_\w+|fp16|fp32)", current_tag, re.I)
                if qm:
                    quant = qm.group(1).lower()
                for v in ("instruct", "base", "thinking", "chat", "code", "coder"):
                    if v in current_tag.lower():
                        variant = v
                        break

                results.append(ModelTag(
                    model=model, tag=current_tag,
                    size_gb=round(size_val, 1),
                    quantization=quant, variant=variant,
                ))
                current_tag = None

        # Deduplicate by tag name
        seen = set()
        unique = []
        for mt in results:
            if mt.tag not in seen:
                seen.add(mt.tag)
                unique.append(mt)
        return unique

    def list_default_tags(self, model: str) -> list[ModelTag]:
        """List only the default (non-quantized) tags — the main size variants."""
        all_tags = self.list_tags(model)
        return [t for t in all_tags if not t.quantization
                and "cloud" not in t.tag
                and t.tag != "latest"]

    # ------------------------------------------------------------------
    # Local: installed models
    # ------------------------------------------------------------------

    def list_installed(self) -> list[dict]:
        """List locally installed models with full details."""
        r = requests.get(f"{self.local}/api/tags", timeout=self.timeout)
        r.raise_for_status()
        return r.json().get("models", [])

    def list_installed_names(self) -> list[str]:
        """Just the names of installed models."""
        return [m["name"] for m in self.list_installed()]

    def get_installed_details(self) -> list[dict[str, Any]]:
        """Installed models with parsed details."""
        results = []
        for m in self.list_installed():
            d = m.get("details", {})
            results.append({
                "name": m["name"],
                "size_gb": round(m["size"] / 1e9, 1),
                "params": d.get("parameter_size", "?"),
                "quant": d.get("quantization_level", "?"),
                "family": d.get("family", "?"),
            })
        return sorted(results, key=lambda x: x["size_gb"])

    # ------------------------------------------------------------------
    # Analysis: smart model selection
    # ------------------------------------------------------------------

    def recommend_for_benchmark(
        self,
        gpu_gb: float = 12.0,
        families: list[str] | None = None,
    ) -> dict[str, list[ModelTag]]:
        """Recommend models to install for comprehensive benchmark.

        Strategy:
        - One model per parameter-size bucket (1B, 3B, 4B, 7B, 9B, 12B, 14B, 20B)
        - Prefer latest version of each family
        - Skip models that don't fit in GPU
        - Return grouped by: 'installed', 'to_install', 'too_large'
        """
        if families is None:
            families = [
                "qwen3", "gemma3", "llama3.2", "llama3.1",
                "deepseek-r1", "phi4", "mistral", "gpt-oss",
            ]

        installed = {m["name"] for m in self.list_installed()}
        max_disk = gpu_gb * 1.2  # rough: Q4 model disk ≈ GPU memory needed

        to_install = []
        too_large = []
        already = []

        for fam in families:
            try:
                defaults = self.list_default_tags(fam)
            except Exception:
                continue
            for tag in defaults:
                if tag.full_name in installed or f"{tag.model}:latest" in installed:
                    already.append(tag)
                elif tag.size_gb <= max_disk:
                    to_install.append(tag)
                else:
                    too_large.append(tag)

        return {
            "installed": already,
            "to_install": sorted(to_install, key=lambda t: t.size_gb),
            "too_large": sorted(too_large, key=lambda t: t.size_gb),
        }


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Ollama model registry explorer")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("models", help="List all models on ollama.com")
    p_tags = sub.add_parser("tags", help="List tags for a model")
    p_tags.add_argument("model")
    p_tags.add_argument("--all", action="store_true", help="Include quantized variants")
    p_search = sub.add_parser("search", help="Search models")
    p_search.add_argument("query")
    sub.add_parser("installed", help="List locally installed models")
    sub.add_parser("recommend", help="Recommend models for benchmark")
    p_family = sub.add_parser("family", help="Show latest version of a model family")
    p_family.add_argument("prefix", help="e.g. 'deepseek' or 'llama'")

    args = parser.parse_args()
    reg = OllamaRegistry()

    if args.cmd == "models":
        for m in reg.list_models():
            print(m)

    elif args.cmd == "tags":
        tags = reg.list_tags(args.model) if args.all else reg.list_default_tags(args.model)
        print(f"\n{args.model} — {len(tags)} tags:")
        for t in tags:
            print(f"  {t.full_name:40s} {t.size_gb:>7.1f}GB  {t.quantization or 'default':>8s}  {t.variant}")

    elif args.cmd == "search":
        for m in reg.search_models(args.query):
            print(m)

    elif args.cmd == "installed":
        for m in reg.get_installed_details():
            print(f"  {m['name']:30s} {m['size_gb']:>6.1f}GB  params={m['params']:>6s}  quant={m['quant']:>6s}  family={m['family']}")

    elif args.cmd == "recommend":
        plan = reg.recommend_for_benchmark(gpu_gb=12)
        print("\n=== INSTALLED ===")
        for t in plan["installed"]:
            print(f"  {t.full_name:40s} {t.size_gb:>6.1f}GB")
        print(f"\n=== TO INSTALL ({len(plan['to_install'])}) ===")
        for t in plan["to_install"]:
            print(f"  ollama pull {t.full_name:35s} # {t.size_gb:.1f}GB")
        print(f"\n=== TOO LARGE ({len(plan['too_large'])}) ===")
        for t in plan["too_large"]:
            print(f"  {t.full_name:40s} {t.size_gb:>6.1f}GB")

    elif args.cmd == "family":
        all_models = reg.list_models()
        matches = [m for m in all_models if args.prefix.lower() in m.lower()]
        print(f"Models matching '{args.prefix}': {matches}")
        for m in matches:
            badges = reg.get_size_badges(m)
            print(f"  {m}: sizes = {badges}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
