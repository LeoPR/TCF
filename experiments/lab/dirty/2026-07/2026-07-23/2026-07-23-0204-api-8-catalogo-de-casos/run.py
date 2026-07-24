#!/usr/bin/env python3
"""Catálogo de casos da API .8 (pós-Passo 2) — um exemplo de CADA situação de dispatch,
com input · wire .tcf · roundtrip · debug (SideOutputs + header), pra inspeção.

`python run.py` regenera TUDO: inputs/, outputs/ (.tcf + .roundtrip.json), intermediates/
(.debug.txt) e result.md. Synthetic pequeno e determinístico — é pra ver COMPORTAMENTO de
saída (header, marcadores, tipos, telemetria), não volume. Zero toque em src/tcf.

Coberto: single-col · multi-col (! @ % / hex / min_header / knobs) · hierárquico .8H
(dataset/objeto/escalar/vazios/tipado/aninhado) · naturezas (CPF/CNPJ/IP) · contratos
type-coherent do Passo 2 (tipado/None/ragged/union/tuple/kwarg — inclui os fail-loud) ·
fontes JSON/CSV/dataset lado a lado · comparação com gzip/brotli/zstd (sinal, não-TCF).
"""
from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
# repo root = experiments/lab/dirty/2026-07/2026-07-23/<lab>/ -> sobe 6
ROOT = AQUI.parents[5]
sys.path.insert(0, str(ROOT / "src"))

from tcf import (encode, decode, SideOutputs, PipelineConfig,  # noqa: E402
                 SPEC_CPF, SPEC_CNPJ, SPEC_IP)

INP, OUT, INT = AQUI / "inputs", AQUI / "outputs", AQUI / "intermediates"
for d in (INP, OUT, INT):
    d.mkdir(exist_ok=True)

# ---- placeholders SEGUROS (nunca dados reais): CPF repetido mod-11-válido; CNPJ/IP synthetic ----
CPFS = ["111.111.111-11", "222.222.222-22", "333.333.333-33"]
CNPJS = ["11.222.333/0001-81", "11.444.777/0001-61"]      # DV-válidos synthetic (não-reais)
IPS = ["10.0.0.1", "10.0.0.2", "10.0.1.5"]


# ============================================================ os CASOS ============
def casos():
    """Cada caso: (id, grupo, desc, kind, input, kwargs, fonte). kind: 'ok' | 'fail'."""
    C = []
    add = lambda *a: C.append(a)

    # -------- SINGLE-COLUMN (list[str]) --------
    add("S1", "single", "emails c/ prefixo/sufixo compartilhado — órfão (0 B header), OBAT+HCC",
        "ok", ["ana@site.com", "ana.b@site.com", "carlos@site.com", "carla@site.com"], {}, "list")
    add("S2", "single", "linhas idênticas adjacentes — RLE de linha (*N|linha)",
        "ok", ["ok", "ok", "ok", "erro", "ok", "ok"], {}, "list")
    add("S3", "single", "version-stamp opt-in (#TCF.8\\n) — magic p/ file/libmagic",
        "ok", ["a", "ab", "abc"], {"stamp": True}, "list")
    add("S4", "single", "nature CPF single-col — FLOOR compete (órfão vs #TCF.8 :cpf, fica a menor)",
        "ok", CPFS * 2, {"nature": SPEC_CPF}, "list")

    # -------- MULTI-COLUMN (dict[str, list[str]]) --------
    tab = {
        "hora": [str(i % 3) for i in range(6)],                       # baixa-card -> dict @
        "codigo": [f"{(i * 2654435761) & 0xFFFF:04x}" for i in range(6)],  # incompr. -> raw !
        "nome": [f"pedido_{i:03d}_descricao_unica" for i in range(6)],     # prefixo -> tcf
    }
    add("M1", "multi", "tabela mista — #TCF.8M, marcadores por-coluna (! raw · @ dict · % split), hex",
        "ok", tab, {}, "dict")
    add("M2", "multi", "MESMA tabela, min_header=False + fallback=False — header explícito p/ inspeção",
        "ok", tab, {"min_header": False, "fallback": False}, "dict")
    add("M3", "multi", "sort_by='hora' + drop_names=True — linhas reordenadas + colunas anônimas",
        "ok", tab, {"sort_by": "hora", "drop_names": True}, "dict")
    add("M4", "multi", "nature CNPJ por-coluna (nature_per_col) — o FLOOR escolhe por coluna",
        "ok", {"cnpj": CNPJS * 3, "valor": [f"{i*10}" for i in range(6)]},
        {"nature_per_col": {"cnpj": SPEC_CNPJ}}, "dict")

    # -------- HIERÁRQUICO (.8H) --------
    pessoas = [
        {"nome": "Ana", "idade": 30, "ativo": True, "fones": ["11 9999-0001", "11 3000-0002"]},
        {"nome": "Bruno", "idade": 25, "ativo": False, "fones": ["21 9888-7766"]},
    ]
    add("H1", "hier", "dataset (list[dict]) c/ escalares tipados + array — #TCF.8H dataset",
        "ok", pessoas, {}, "dataset")
    add("H2", "hier", "objeto único (dict com valores escalar/nested) — #TCF.8H #O",
        "ok", {"cidade": "SP", "populacao": 12300000, "capital": True,
               "prefeito": {"nome": "X", "partido": "Y"}}, {}, "json")
    add("H3", "hier", "escalar solto — #TCF.8H #V (envelope; decode desembrulha)",
        "ok", 42, {}, "scalar")
    add("H4a", "hier", "lista vazia [] — FLAT #TCF.8\\n (weld #2 2026-07-24: canonicidade do vazio; era .8H #D0)",
        "ok", [], {}, "list")
    add("H4b", "hier", "dict vazio {} — #TCF.8H #E (definição)", "ok", {}, {}, "dict")
    add("H4c", "hier", "[{}, {}] — #TCF.8H #D2 (N registros, zero colunas)", "ok", [{}, {}], {}, "dataset")
    add("H5", "hier", "tipos PRESERVADOS (int/float/bool/null) num objeto — decode devolve o tipo exato",
        "ok", {"i": 7, "f": 3.5, "b": False, "n": None, "s": "txt"}, {}, "json")
    add("H6", "hier", "aninhado profundo (objeto dentro de objeto, array de arrays)",
        "ok", [{"id": "1", "geo": {"lat": "1.0", "lng": "2.0"}, "matriz": [["a", "b"], ["c"]]}], {}, "dataset")
    add("H7", "hier", "nature CPF em FOLHA aninhada (nature_per_col path) no dataset .8H",
        "ok", [{"nome": "Ana", "doc": {"cpf": CPFS[0]}}, {"nome": "Bru", "doc": {"cpf": CPFS[1]}}],
        {"nature_per_col": {"doc/cpf": SPEC_CPF}}, "dataset")

    # -------- CONTRATOS type-coherent do PASSO 2 (inclui fail-loud) --------
    add("C1", "contrato", "encode([1,2,3]) — array .8H TIPADO (int preservado; era single 1,2,3)",
        "ok", [1, 2, 3], {}, "list")
    add("C2", "contrato", "coluna com None — vira .8H, None PRESERVADO (não vira '')",
        "ok", {"a": ["x", None, "y"]}, {}, "dict")
    add("C3", "contrato", "dict ragged (colunas de tamanhos != ) — .8H OBJETO (cada campo = array)",
        "ok", {"a": ["1", "2"], "b": ["x"]}, {}, "dict")
    add("C4", "contrato", "array de tipos MISTOS (int+null+str) — FAIL-LOUD (union fora do .8H)",
        "fail", [1, None, "x"], {}, "list")
    add("C5", "contrato", "tuple no lugar de lista — FAIL-LOUD (tipo não-JSON, não converte calado)",
        "fail", {"a": ("x", "y")}, {}, "dict")
    add("C6", "contrato", "kwarg SÓ-flat (parallel) com entrada .8H — FAIL-LOUD (nunca ignora calado)",
        "fail", [{"a": "1"}], {"parallel": 4}, "dataset")

    return C


# ---- fontes: mesmo dado lógico via CSV (flat) vs JSON (aninhado) lado a lado ----
def caso_fontes():
    # CSV = tabela plana (multi-col #TCF.8M); JSON aninhado = dataset (#TCF.8H). Mesma info, wires diferentes.
    linhas = [{"id": "1", "nome": "Ana", "cidade": "SP"}, {"id": "2", "nome": "Bruno", "cidade": "RJ"}]
    # via CSV -> dict de colunas
    buf = io.StringIO(); w = csv.DictWriter(buf, fieldnames=["id", "nome", "cidade"]); w.writeheader()
    for r in linhas:
        w.writerow(r)
    csv_txt = buf.getvalue()
    (INP / "F1.csv").write_text(csv_txt, encoding="utf-8")
    rd = csv.DictReader(io.StringIO(csv_txt))
    cols = {c: [] for c in ["id", "nome", "cidade"]}
    for r in rd:
        for c in cols:
            cols[c].append(r[c])
    return linhas, cols


# ============================================================ execução ============
def _mag(w):  # discriminador legível
    l0 = w.split("\n", 1)[0]
    if not w.startswith("#TCF."):
        return "(sem header — single-col órfão)"
    if l0.startswith("#TCF.8M"):
        return f"multi-col #TCF.8M · meta inline: {l0[7:]!r}"
    if l0.startswith("#TCF.8H"):
        resto = l0[7:]
        if resto[:1] == "#":                       # #D<N> / #E / #O<meta> / #V<meta>
            nomes = {"D": "dataset sem-colunas (#D<N>)", "E": "objeto-vazio {} (#E)",
                     "O": "objeto único (#O)", "V": "valor escalar (#V, envelope)"}
            return f"hierárquico #TCF.8H · {nomes.get(resto[1:2], '#'+resto[1:2])} · meta {resto[:14]!r}"
        return f"hierárquico #TCF.8H · DATASET (list[dict]) · meta {resto[:26]!r}"
    if l0 == "#TCF.8":
        return "single-col version-stamp (#TCF.8\\n)"
    if l0.startswith("#TCF.8 "):
        return f"single-col + spec/nature · meta: {l0[6:]!r}"
    return l0[:20]


def _debug_so(so, kind_grp):
    """Campos relevantes do SideOutputs por grupo, robusto (None onde não aplica)."""
    L = []
    hi = getattr(so, "hier_info", None)
    if hi:
        L.append(f"  hier_info: root_kind={hi.get('root_kind')} n_records={hi.get('n_records')} "
                 f"cols={hi.get('cols')} fields={hi.get('fields')}")
    mi = getattr(so, "multi_info", None)
    if mi:
        L.append(f"  multi_info: {mi}")
    na = getattr(so, "nature_apply", None)
    if na:
        L.append(f"  nature_apply: {na}")
    per = getattr(so, "per_col", None)
    if per:
        for col, sub in list(per.items())[:8]:
            bb = getattr(sub, "body_bytes", None)
            cf = getattr(sub, "column_features", None)
            L.append(f"  per_col[{col}]: body_bytes={bb}" + (f" features={cf}" if cf else ""))
    cf = getattr(so, "column_features", None)
    if cf and not per:
        L.append(f"  column_features: {cf}")
    hcc = getattr(so, "hcc_trace", None)
    if hcc:
        L.append(f"  hcc_trace: {str(hcc)[:120]}")
    return L or ["  (sem telemetria relevante p/ este caso)"]


def _ext(fonte):
    return {"json": "json", "dataset": "json", "dict": "json", "list": "json",
            "scalar": "json", "csv": "csv"}.get(fonte, "txt")


def rodar():
    linhas_ct = ["# Catálogo de casos da API .8 — resultado (gerado por run.py)\n",
                 "Um exemplo de cada situação de dispatch. Artefatos por caso em "
                 "`inputs/` · `outputs/*.tcf` · `outputs/*.roundtrip.json` · `intermediates/*.debug.txt`.\n"]
    rt_ok = rt_fail = 0
    grupo_atual = None
    for (cid, grupo, desc, kind, dado, kw, fonte) in casos():
        if grupo != grupo_atual:
            linhas_ct.append(f"\n## {grupo.upper()}\n")
            grupo_atual = grupo
        # input
        ext = _ext(fonte)
        try:
            (INP / f"{cid}.{ext}").write_text(
                json.dumps(dado, ensure_ascii=False, indent=1) if ext == "json" else str(dado),
                encoding="utf-8")
        except TypeError:
            (INP / f"{cid}.txt").write_text(repr(dado), encoding="utf-8")

        dbg = [f"CASE {cid} — {desc}", f"FONTE: {fonte} · kwargs: {kw or '{}'}",
               f"INPUT: {repr(dado)[:160]}"]
        if kind == "fail":
            try:
                encode(dado, **kw)
                status = "ERRO: deveria ter FALHADO mas não falhou!"
            except Exception as e:
                status = f"FAIL-LOUD (esperado): {type(e).__name__}: {str(e)[:90]}"
            dbg += [f"RESULTADO: {status}"]
            linhas_ct.append(f"- **{cid}** — {desc}\n  → `{status}`")
        else:
            so = SideOutputs()
            wire = encode(dado, side_outputs=so, **kw)
            (OUT / f"{cid}.tcf").write_text(wire, encoding="utf-8", newline="")
            back = decode(wire)
            # RT: transformação declarada (sort_by/drop_names) NÃO é identidade — ordem/nomes
            # mudam de propósito; prova por IDEMPOTÊNCIA 2ª geração (re-encoda a saída, RT estável).
            transform = ("sort_by" in kw) or ("drop_names" in kw)
            rt_mode = "idempotencia-2a-geracao" if transform else "identidade"
            ok = (decode(encode(back)) == back) if transform else (back == dado)
            (OUT / f"{cid}.roundtrip.json").write_text(
                json.dumps(back, ensure_ascii=False, indent=1), encoding="utf-8")
            rt_ok += ok
            rt_fail += (not ok)
            nb = len(wire.encode("utf-8"))
            dbg += [f"WIRE ({nb} B): {wire!r}", f"HEADER: {_mag(wire)}",
                    f"ROUNDTRIP ({rt_mode}): {'OK' if ok else 'FALHOU! back=' + repr(back)[:120]}",
                    "DEBUG (SideOutputs):"] + _debug_so(so, grupo)
            nota_rt = "✅ OK" + (f" ({rt_mode})" if transform else "")
            linhas_ct.append(
                f"- **{cid}** — {desc}\n"
                f"    - input `{repr(dado)[:90]}`\n"
                f"    - wire ({nb} B): `{wire!r}`\n"
                f"    - header: {_mag(wire)}\n"
                f"    - roundtrip: {nota_rt if ok else '❌ FALHOU'}")
        (INT / f"{cid}.debug.txt").write_text("\n".join(dbg) + "\n", encoding="utf-8")

    # -------- FONTES: CSV vs JSON lado a lado --------
    linhas_ct.append("\n## FONTES (mesmo dado: CSV plano vs JSON aninhado)\n")
    linhas, cols = caso_fontes()
    w_csv = encode(cols)                                   # CSV -> tabela -> #TCF.8M
    w_json = encode(linhas)                                # JSON aninhado -> dataset -> #TCF.8H
    (OUT / "F1-csv.tcf").write_text(w_csv, encoding="utf-8", newline="")
    (OUT / "F1-json.tcf").write_text(w_json, encoding="utf-8", newline="")
    (INP / "F1.json").write_text(json.dumps(linhas, ensure_ascii=False, indent=1), encoding="utf-8")
    ok_csv = decode(w_csv) == cols
    ok_json = decode(w_json) == linhas
    rt_ok += ok_csv + ok_json
    linhas_ct += [
        f"- **F1-csv** (colunas planas): `{w_csv!r}` → {_mag(w_csv)} · RT {'✅' if ok_csv else '❌'}",
        f"- **F1-json** (mesmos dados aninhados): `{w_json!r}` → {_mag(w_json)} · RT {'✅' if ok_json else '❌'}",
        "  > mesma informação, WIRES diferentes: CSV plano vira multi-col `#TCF.8M`; "
        "JSON aninhado vira `#TCF.8H` (o TCF entende DATASET, o JSON/CSV é a materialização).",
    ]

    # -------- COMPRESSÃO EXTERNA (sinal qualitativo, NÃO é TCF) --------
    linhas_ct.append("\n## COMPRESSÃO EXTERNA (comparação — gzip/brotli/zstd NÃO fazem parte do TCF)\n")
    import gzip
    amostra = {"nome": [f"cliente_{i:04d}_nome_completo" for i in range(50)],
               "uf": [["SP", "RJ", "MG"][i % 3] for i in range(50)]}
    tcf_b = encode(amostra).encode("utf-8")
    raw_b = json.dumps(amostra, ensure_ascii=False).encode("utf-8")
    linhas_ct.append(f"- amostra 50 linhas · JSON raw={len(raw_b)} B · **TCF={len(tcf_b)} B** · "
                     f"gzip(json)={len(gzip.compress(raw_b, 6))} B · gzip(tcf)={len(gzip.compress(tcf_b, 6))} B")
    linhas_ct.append("  > o TCF é TEXTO inspecionável; gzip é sinal de redundância oculta, não critério.")

    linhas_ct.append(f"\n---\n**Roundtrip: {rt_ok} OK, {rt_fail} falhas** · fail-loud (contratos): "
                     f"C4/C5/C6 esperados. Regenera: `python run.py`.\n")
    (AQUI / "result.md").write_text("\n".join(linhas_ct), encoding="utf-8", newline="\n")
    print(f"OK · roundtrip {rt_ok} ok / {rt_fail} falhas · artefatos em inputs/ outputs/ intermediates/ + result.md")
    return rt_fail


if __name__ == "__main__":
    raise SystemExit(1 if rodar() else 0)
