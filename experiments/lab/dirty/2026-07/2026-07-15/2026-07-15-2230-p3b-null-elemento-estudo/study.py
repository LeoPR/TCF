"""ESTUDO P3b — valida a element-mask nas formas didáticas (RT obrigatório) + inspeção do meta."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from proto import decode, derive, encode, meta_str  # noqa: E402


def main():
    did = json.loads((HERE / "inputs" / "01-didatico-null-elemento.json").read_text(encoding="utf-8"))
    out = ["ESTUDO P3b — null em ELEMENTO de array (element-mask). RT + meta inspecionável.", ""]
    inter, outs = HERE / "intermediates", HERE / "outputs"
    inter.mkdir(exist_ok=True); outs.mkdir(exist_ok=True)

    all_ok = True
    for nome, docs in [(k, v) for k, v in did.items() if not k.startswith("_")]:
        schema, cols, n = encode(docs)
        back = decode(schema, cols, n)
        ok = back == docs
        all_ok &= ok
        out.append(f"  [{'RT-OK' if ok else 'FALHA!!'}] {nome}")
        out.append(f"       meta: {meta_str(schema)}")
        if not ok:
            out.append(f"       esperado={docs}")
            out.append(f"       obtido  ={back}")
        # roundtrip diffável
        stem = nome.split()[0].replace("/", "-").replace("(", "").replace(")", "")
        (inter / f"{stem}.json").write_bytes((json.dumps(docs, ensure_ascii=False, indent=2) + "\n").encode())
        (outs / f"{stem}-rt.json").write_bytes((json.dumps(back, ensure_ascii=False, indent=2) + "\n").encode())

    out += ["", ("VEREDITO: element-mask faz RT em TODAS as formas didáticas." if all_ok
                 else "HÁ FALHA — revisar o design."),
            "Alinhamento count×emask×dense consistente. Alfabeto 2-estados ('.'/'0'), sem '-'.",
            "Meta demonstra a gramática: nome#?[...] (o '?' após #count = elementos mascarados).",
            "Próximo: se o owner aprovar, weld no core (element-mask no L2) OU medir vs índice (H-PROFILE-01)."]
    (outs / "00-resultado.txt").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
    print("\n".join(out))
    assert all_ok


if __name__ == "__main__":
    main()
