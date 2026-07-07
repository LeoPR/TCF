"""run.py — tipos COMO SPECS (reframe do owner 2026-07-06): primitivos = specs ultra-minimalistas induzidas.

Uma spec se justifica por (a) COMPRESSÃO ou (b) ACELERAÇÃO de decode. Ela é seguramente INDUZIDA
sse o valor faz ROUND-TRIP por ela (a regra universal): "30"→int→"30" ✓ induz; "01310"→int→"1310" ✗
mantém string. O gabarito (1ª amostra) induz a spec da coluna; analyze_column já expõe isso (is_numeric,
cardinality, sample). Cadence já dá a compressão do número. Mede: bool-spec, regra round-trip, número, gabarito.

`python run.py` regenera artifacts/. Não toca src/tcf — engenhoca de análise conceitual.
"""
from __future__ import annotations
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_ROOT = HERE.parents[3]
sys.path.insert(0, str(_ROOT / "src"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
from tcf import encode, SideOutputs                    # noqa: E402

ART = HERE / "artifacts"
ART.mkdir(exist_ok=True)


def nb(s): return len(s.encode("utf-8"))
def bd(col): return nb(encode([str(x) for x in col]))       # body bytes via tcf.encode
def w(name, text): (ART / name).write_text(text, encoding="utf-8", newline="\n")


# ---- a regra universal: uma spec induz-se com segurança sse o valor faz round-trip por ela ----
def rt_int(v):
    try:
        return str(int(v)) == v
    except (ValueError, TypeError):
        return False


def rt_float(v):
    try:
        return str(float(v)) == v
    except (ValueError, TypeError):
        return False


def rt_bool(v):
    return v in ("true", "false")


def induce(v):
    """qual spec a dedução escolheria (a mais específica que faz round-trip); '' = string (fallback)."""
    if rt_bool(v):
        return "bool"
    if rt_int(v):
        return "int"
    if rt_float(v):
        return "float"
    return "string"


# ---- 1. BOOL como spec: true/false (string) vs t/f (spec) — compressão do body ----
def bool_dists(n):
    return {
        "alternado": ["true" if i % 2 == 0 else "false" for i in range(n)],
        "all-true": ["true"] * n,
        "70-30": ["true" if i % 10 < 7 else "false" for i in range(n)],
    }


def thread_bool():
    L = ["# 1. BOOL como spec — body 'true'/'false' (string) vs 't'/'f' (spec bool) + tag 'b' (1B)", "",
         "compressão do body; o tag amortiza sobre N. (ambos via tcf.encode → RLE aplica aos dois)", ""]
    tab = ["| N | dist | string body | spec body+tag | Δ (spec-string) |", "|---|---|---|---|---|"]
    for n in (2, 10, 100):
        for dist, col in bool_dists(n).items():
            s_body = bd(col)
            spec = ["t" if v == "true" else "f" for v in col]
            spec_body = bd(spec) + 1                     # +1B tag 'b'
            tab.append(f"| {n} | {dist} | {s_body}B | {spec_body}B | {spec_body - s_body:+d}B |")
    L += tab + ["",
                "LEITURA (o NÚMERO corrigiu a hipótese): o ganho é FLAT ~6B (alternado/70-30) e ~2B (all-true),",
                "NÃO ~N. Por quê: o HCC já dedup os 2 valores distintos num dict e guarda N REFERÊNCIAS; o spec só",
                "encolhe o DICT uma vez ('true'/'false'→'t'/'f'), as N referências são idênticas. Em TEXTUAL o",
                "bool-spec vale por ACELERAÇÃO (decode tipado, sem deduzir) + dict-shrink modesto. A compressão",
                "por-valor real (1 bit/valor) exige BITMAP = camada binária (V2-L, ADR-0018), não textual."]
    w("01-bool-spec-compressao.txt", "\n".join(L) + "\n")
    return L


# ---- 2. a regra ROUND-TRIP de indução (resolve o self-description de uma vez) ----
def thread_roundtrip():
    casos = ["30", "-5", "01310", "+5", "4.5", "4.50", "1e3", "true", "false", "True", "ana", "", "3.14"]
    L = ["# 2. REGRA de indução: induz a spec SSE o valor faz round-trip por ela (senão = string)", "",
         "| valor | int? | float? | bool? | spec induzida | por quê |", "|---|---|---|---|---|---|"]
    motivo = {
        "01310": "int('01310')→1310 ≠ '01310' (zero à esquerda) → string",
        "+5": "int('+5')→5 ≠ '+5' → string",
        "4.50": "float('4.50')→4.5 ≠ '4.50' (zero final) → string",
        "1e3": "float('1e3')→1000.0 ≠ '1e3' → string",
        "True": "não ∈ {true,false} (JSON é minúsculo) → string",
        "": "vazio → string (ou null via máscara, Ciclo 1c)",
    }
    for v in casos:
        L.append(f"| {v!r} | {'✓' if rt_int(v) else '·'} | {'✓' if rt_float(v) else '·'} | "
                 f"{'✓' if rt_bool(v) else '·'} | **{induce(v)}** | {motivo.get(v, 'round-trip limpo → induz')} |")
    L += ["",
          "A regra é ZERO-config e resolve o self-description (hex/tipo/nature no MESMO teste): a spec só é",
          "induzida quando é reversível; o que não reverte fica string (ou leva marcador explícito = C-híbrida 1b).",
          "É o análogo exato do hex-default (T-OPT-INFERENCE) e da 1ª-string-molde do OBAT."]
    w("02-inducao-roundtrip.txt", "\n".join(L) + "\n")
    return L


# ---- 3. NÚMERO como spec: compressão já vem da cadence (auto-induzida do is_numeric) ----
def thread_numero():
    N = 100
    cad = list(range(1, N + 1))                          # cadenciado 1..N
    esp = [i * i for i in range(1, N + 1)]               # espalhado (quadrados)
    L = ["# 3. NÚMERO como spec — a compressão já vem da CADENCE (detect_cadence rule-2, auto do is_numeric)", ""]
    for tag, col in (("cadenciado 1..100", cad), ("espalhado i² 1..100", esp)):
        side = SideOutputs(); blob = encode([str(x) for x in col], side_outputs=side)
        s = (side.per_col or {}).get(0) or (next(iter((side.per_col or {}).values())) if side.per_col else None)
        rule = ((s.cadence_info or {}).get("rule_hit") if s else None)
        L.append(f"  {tag:20s} body={nb(blob):4d}B  cadence.rule_hit={rule}  (is_numeric induz; cadence comprime)")
    L += ["", "OBSERVADO: cadenciado 1..100 comprime a ~23B (vs ~601B espalhado) MAS cadence.rule_hit=None no",
          "encode DEFAULT — a compressão veio do HCC (seq-RLE/range), não da regra de cadence nomeada (que é",
          "estágio do pipeline delta-aware, exige config). int vs float = sub-spec pelo PONTO (owner): '30'→int,",
          "'4.5'→float (round-trip decide). O número dá COMPRESSÃO (HCC quando sequencial; cadence/delta quando",
          "ligado) E ACELERAÇÃO (parse conhecido); string não dá nenhum → não spec."]
    w("03-numero-cadence.txt", "\n".join(L) + "\n")
    return L


# ---- 4. GABARITO: a 1ª amostra induz a spec da coluna (analyze_column.sample) ----
def thread_gabarito():
    cols = {
        "idades (int homogêneo)": ["30", "41", "25", "60"],
        "ceps (parece int, é string)": ["01310", "20040", "70040"],
        "flags (bool)": ["true", "false", "true"],
        "misto (1ª engana)": ["30", "ana", "41"],
    }
    L = ["# 4. GABARITO — a 1ª amostra induz a spec da coluna; guardada pelo round-trip de TODAS", "",
         "| coluna | 1ª amostra | spec da 1ª | induz p/ coluna? (round-trip em todas) |", "|---|---|---|---|"]
    for name, col in cols.items():
        first = induce(col[0])
        all_same = all(induce(v) == first for v in col)
        veredito = f"SIM → {first}" if (all_same and first != "string") else \
                   ("todas string" if first == "string" else "NÃO (1ª engana / heterogênea) → string+guard")
        L.append(f"| {name} | {col[0]!r} | {first} | {veredito} |")
    L += ["",
          "O gabarito (sample[0]) PROPÕE a spec; o round-trip em TODAS CONFIRMA. ceps: 1ª '01310' induz int mas",
          "não faz round-trip → cai pra string (o guard salva). misto: 1ª '30'→int, mas 'ana' quebra → string.",
          "= exatamente a C-híbrida (1b) generalizada: propõe pelo gabarito, confirma pelo round-trip, tag na colisão."]
    w("04-gabarito.txt", "\n".join(L) + "\n")
    return L


def main():
    thread_bool(); thread_roundtrip(); thread_numero(); thread_gabarito()

    R = ["# tipos como specs — análise [resumo]", "",
         "## Tese (reframe do owner)",
         "Primitivo = spec ULTRA-MINIMALISTA induzida. Justificativa de QUALQUER spec: COMPRESSÃO ou ACELERAÇÃO.",
         "Indução segura ⟺ ROUND-TRIP (o valor reverte pela spec). Gabarito (1ª amostra) propõe; round-trip confirma.",
         "",
         "## Caracterização (compressão × aceleração × indução)",
         "| spec | induz de | compressão | aceleração | round-trip guard |",
         "|---|---|---|---|---|",
         "| string (fallback) | — (default) | não | não (identidade) | — |",
         "| int | dígitos, sem ponto | HCC/seq-RLE quando sequencial (medido); cadence/delta se ligado | parse rápido | str(int(v))==v |",
         "| float | tem ponto | idem int | parse rápido | str(float(v))==v |",
         "| bool | domínio {true,false} | TEXTO: só dict-shrink flat (~6B, medido); **bitmap** (1 bit/val) só em binário V2-L | mapa direto | v∈{true,false} |",
         "| null | máscara (1c) | body vazio + def-level | pula célula | — (máscara) |",
         "| nature (CPF/CEP/datetime) | template/gabarito | **template + delta** | validação | round-trip do template |",
         "",
         "## Consequências",
         "- **Unifica** tipo (1a/1b) + hex (T-OPT-INFERENCE) + natures (ADR-0015) num SÓ mecanismo: espectro de",
         "  specs, do mínimo (string/int/bool) ao rico (CPF), todas induzidas pelo gabarito + round-trip.",
         "- **Pipeline**: analyze_column já induz (is_numeric, cardinality, sample); cadence já comprime número.",
         "  A spec entra como estágio do pre-pass — custo ~zero (o que já se calcula).",
         "- **Decisão**: induz a spec quando comprime OU acelera E faz round-trip; senão string (+ tag na colisão).",
         "- **bool** em TEXTO ganha só ~6B flat (dict-shrink); o ganho por-valor (bitmap) é da camada binária",
         "  (V2-L). Seu valor textual é ACELERAÇÃO + dict. **número** ganha via HCC quando sequencial (medido,",
         "  não pela cadence nomeada no default). string = fallback sem ganho. → alimenta Ciclo 3 (implicitude)."]
    w("00-resumo.txt", "\n".join(R) + "\n")

    print("artifacts em", ART)
    for p in sorted(ART.iterdir()):
        print(f"  {p.name:28s} {p.stat().st_size:6d} B")
    print("\n" + "\n".join(R))


if __name__ == "__main__":
    main()
