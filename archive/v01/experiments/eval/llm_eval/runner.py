import json
import time
from pathlib import Path
from typing import Iterable, Dict, Any, List, Tuple, Callable

from .ollama_client import OllamaClient
from .formats import render_format
from .prompts import build_prompt


def run_questions_over_chunks(
    model: str,
    chunks: Iterable[Tuple[str, List[Dict[str, Any]]]],
    sum_field: str | None = None,
    endpoint: str = "http://localhost:11434",
    options: Dict[str, Any] | None = None,
    format_name: str = "jsonl",
    preview_callback: Callable[[Dict[str, Any]], None] | None = None,
) -> List[Dict[str, Any]]:
    """Executa perguntas padrão sobre cada chunk usando o formato solicitado.

    Perguntas atuais: count_rows, (opcional) sum_field.
    """
    client = OllamaClient(endpoint)
    results: List[Dict[str, Any]] = []

    for chunk_id, rows in chunks:
        data_block = render_format(rows, format_name)
        # Perguntas padronizadas
        questions: List[Tuple[str, str, Dict[str, Any]]] = [("count_rows", "count_rows", {})]
        if sum_field:
            questions.append(("sum_field", "sum_field", {"field": sum_field}))

        for qname, qtemplate, params in questions:
            prompt = build_prompt(format_name, data_block, qtemplate, **params)
            if preview_callback:
                preview_callback(
                    {
                        "model": model,
                        "chunk_id": chunk_id,
                        "format": format_name,
                        "question": qname,
                        "prompt": prompt,
                        "rows": len(rows),
                    }
                )
            t0 = time.perf_counter()
            result = client.generate(model=model, prompt=prompt, options=options)
            latency = time.perf_counter() - t0
            results.append(
                {
                    "chunk_id": chunk_id,
                    "question": qname,
                    "format": format_name,
                    "prompt_chars": len(prompt),
                    "prompt_tokens": result["prompt_tokens"],
                    "response_tokens": result["response_tokens"],
                    "response": result["text"].strip(),
                    "latency_s": round(latency, 4),
                    "rows": len(rows),
                }
            )
    return results


def save_results(results: List[Dict[str, Any]], out_path: str | Path) -> None:
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for row in results:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
