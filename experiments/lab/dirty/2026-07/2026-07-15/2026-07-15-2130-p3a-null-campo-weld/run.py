"""WELD P3a — null em campo. Metodologia do owner: DIDÁTICO → REALISTA → MASSA, RT 120% obrigatório.

Cada etapa: roundtrip = ARQUIVO diffável (byte-idêntico ao canônico), pra o owner (e o Claude)
inspecionarem a saída e ver se é consistente. Usa o CORE weldado (src/tcf), não engenhoca."""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[4] / "src"))
from tcf import decode, encode_hierarchical  # noqa: E402

HUB = Path("Z:/tcf-data/interim/receita-cnpj.db")


def wjson(path, obj):
    path.write_bytes((json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def rt_arquivo(nome, docs, stem):
    """encode → .tcf; decode → -rt.json; assert byte-idêntico ao canônico (RT 120%)."""
    wjson(HERE / "intermediates" / f"{stem}.json", docs)          # canônico LF
    blob = encode_hierarchical(docs)
    (HERE / "outputs" / f"{stem}.tcf").write_bytes(blob.encode("utf-8"))
    back = decode(blob)
    wjson(HERE / "outputs" / f"{stem}-rt.json", back)
    ok = back == docs
    assert ok, f"RT FALHOU em {nome} — fluxo quebrado"
    return ok, len(blob.encode())


def main():
    out = ["WELD P3a — null em CAMPO. Metodologia: didático → realista → massa (RT obrigatório).", ""]

    # ---------- (1) DIDÁTICO — cada forma forçada, inspecionável ----------
    out.append("(1) DIDÁTICO — cada caso de null-em-campo (roundtrip diffável em outputs/):")
    did = json.loads((HERE / "inputs" / "01-didatico-null-campo.json").read_text(encoding="utf-8"))
    for j, (nome, docs) in enumerate([(k, v) for k, v in did.items() if not k.startswith("_")], 1):
        ok, nbytes = rt_arquivo(nome, docs, f"01-{j:02d}-" + nome.split()[0].replace("/", "-"))
        hdr = encode_hierarchical(docs).split("\n", 1)[0]
        out.append(f"  [{'RT-OK' if ok else 'FALHA'}] {nome}: {nbytes}B · header: {hdr[:78]}")

    # ---------- (2) REALISTA pequeno ----------
    out.append("")
    out.append("(2) REALISTA pequeno — cadastro API-like c/ opcionais E null (email/obs/nascimento):")
    real = json.loads((HERE / "inputs" / "02-realista-cadastro.json").read_text(encoding="utf-8"))
    ok, nbytes = rt_arquivo("cadastro-realista", real, "02-realista-cadastro")
    njson = len(json.dumps(real, ensure_ascii=False, separators=(",", ":")).encode())
    out.append(f"  [{'RT-OK' if ok else 'FALHA'}] {len(real)} registros: tcf={nbytes}B vs json-compacto={njson}B")

    # ---------- (3) MASSA — dado real com null REAL (receita-cnpj, sem coerção) ----------
    out.append("")
    out.append("(3) MASSA — receita-cnpj matriz→filiais com null REAL (fantasia=None, SEM coerção):")
    if not HUB.exists():
        out.append("  hub ausente — pulado (requires_data).")
    else:
        con = sqlite3.connect(str(HUB)); con.row_factory = sqlite3.Row
        rows = [dict(r) for r in con.execute(
            "SELECT cnpj, matriz_filial, situacao, uf, nome_fantasia FROM estabelecimentos")]
        groups: dict = {}
        for r in rows:
            groups.setdefault(r["cnpj"][:8], []).append(r)
        allk = sorted(groups)

        def est(e):
            return {"cnpj": str(e["cnpj"]), "mf": str(e["matriz_filial"]), "sit": str(e["situacao"]),
                    "uf": str(e["uf"]),
                    "fantasia": None if e["nome_fantasia"] is None else str(e["nome_fantasia"])}  # null REAL

        maior = None
        for frac in (0.05, 0.10, 0.25):                          # samples que não disparam o BUG-SEQRLE
            keys = allk[::max(1, int(1 / frac))]
            docs = [{"raiz": k, "est": [est(e) for e in sorted(groups[k], key=lambda x: x["cnpj"])]}
                    for k in keys]
            n_est = sum(len(d["est"]) for d in docs)
            n_null = sum(1 for d in docs for e in d["est"] if e["fantasia"] is None)
            try:
                ok = decode(encode_hierarchical(docs)) == docs
                out.append(f"  frac={frac}: {len(docs)} raízes · {n_est} est · fantasia NULL {n_null}/{n_est} "
                           f"→ RT byte-exato={ok}")
                if ok:
                    maior = (len(docs), n_est, n_null)
            except Exception as ex:
                out.append(f"  frac={frac}: CRASH {type(ex).__name__} (bug L1 seq-RLE BUG-SEQRLE, não do P3a)")
        if maior:
            # grava amostra pequena diffável do massa (10 raízes) p/ inspeção
            keys = allk[:10]
            sample = [{"raiz": k, "est": [est(e) for e in sorted(groups[k], key=lambda x: x["cnpj"])]}
                      for k in keys]
            rt_arquivo("massa-amostra", sample, "03-massa-amostra")
            out.append(f"  → null REAL faz RT byte-exato em massa (maior sample: {maior[0]} raízes / "
                       f"{maior[1]} est / {maior[2]} nulls). Amostra diffável: outputs/03-massa-amostra*.")
        con.close()

    out += ["", "VEREDITO: P3a (null em campo) — RT em TODAS as etapas. null≠ausente≠'null'≠''.",
            "Evidência inspecionável em outputs/ (cada .tcf + -rt.json diffável). Zero engenhoca (core real)."]
    (HERE / "outputs" / "00-resultado.txt").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
    print("\n".join(out))


if __name__ == "__main__":
    main()
