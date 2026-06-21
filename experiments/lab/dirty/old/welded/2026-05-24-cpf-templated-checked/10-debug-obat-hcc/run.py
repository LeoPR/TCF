"""Sub-exp 10 — Debug OBAT + HCC nas cases mais reveladoras.

Owner pediu visibilidade dos algos internos. Sub-exp 10 dump:
- OBAT log (cobertura per string, LCP/LCS choices)
- HCC trace (detector iterations, candidatos considerados/rejeitados)
- HCC rede (atoms + composicoes + uso final)
- seq_rle_runs (cadence runs detectados)
- ColumnFeatures (pre-pass)

Cases (sample 50 valores cada pra trace ficar legivel):

| Case | Dataset | Variante | Ratio observado | Por que e' interessante |
|---|---|---|---|---|
| 1 | D-CPF-uniform | A (M10 puro) | 126% | OBAT/HCC ANTI-compressor; ver por que |
| 2 | D-CPF-clustered | B (base-94) | 47% | Caso medio, padroes mistos |
| 3 | D-IP-subnet | A (M10 puro) | 118% | M10 detecta cadence mas insuficiente |
| 4 | D-IP-subnet | C (padded 12) | 1.71% (!) | DRAMATIC — HCC seq-RLE explode |

Cada case gera pasta `<N>-<descr>/` com:
- input.txt: 50 valores de entrada
- pretx.txt: apos pre-tx (se houver)
- output.tcf: TCF final
- obat-log.txt: log OBAT por string
- hcc-trace.txt: trace HCC iteracoes
- hcc-rede.txt: rede atoms + composicoes
- seq_rle_runs.json: runs detectados
- column_features.json: features pre-pass
- analysis.md: interpretacao
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

THIS = Path(__file__).parent
LAB = THIS.parent
ROOT = LAB.parents[3]
sys.path.insert(0, str(ROOT / "src"))

from tcf import encode, decode, SideOutputs  # noqa: E402


_RESERVED = set('\n\r\t ,~*\\#=[]<>"\'`_')
BASE94 = ''.join(chr(c) for c in range(33, 127) if chr(c) not in _RESERVED)
MARKER_LITERAL = '_'

CPF_RE = re.compile(r'^(\d{3})\.(\d{3})\.(\d{3})-(\d{2})$')
IP_RE = re.compile(r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$')

SAMPLE_SIZE = 50


def load(name: str, n: int = SAMPLE_SIZE) -> list[str]:
    path = LAB / "data" / f"{name}.csv"
    with path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        rows = [row[0] if row else '' for row in r]
    return rows[:n]


def calc_check_cpf(body: list[int], weights: range) -> int:
    s = sum(d * w for d, w in zip(body, weights))
    rem = (s * 10) % 11
    return 0 if rem == 10 else rem


def encode_cpf_b(cpf: str) -> str:
    """CPF -> 5-char base94 (sub-exp 05 logic)."""
    m = CPF_RE.match(cpf)
    if not m:
        return MARKER_LITERAL + cpf
    digits = m.group(1) + m.group(2) + m.group(3) + m.group(4)
    body = [int(d) for d in digits[:9]]
    d1 = calc_check_cpf(body, range(10, 1, -1))
    d2 = calc_check_cpf(body + [d1], range(11, 1, -1))
    if [d1, d2] != [int(digits[9]), int(digits[10])]:
        return MARKER_LITERAL + cpf
    body_int = int(digits[:9])
    chars = []
    n = body_int
    for _ in range(5):
        chars.append(BASE94[n % len(BASE94)])
        n //= len(BASE94)
    return ''.join(reversed(chars))


def encode_ip_c(ip: str) -> str:
    """IP -> 12-char padded digits."""
    m = IP_RE.match(ip)
    if not m:
        return MARKER_LITERAL + ip
    octets = [int(g) for g in m.groups()]
    if any(o > 255 for o in octets):
        return MARKER_LITERAL + ip
    return ''.join(f"{o:03d}" for o in octets)


def dump_case(case_num: int, name_short: str, raw_values: list[str],
              pretx_values: list[str] | None, description: str):
    """Roda case + dump completo dos side outputs."""
    out_dir = THIS / f"case-{case_num}-{name_short}"
    out_dir.mkdir(exist_ok=True)

    actual_input = pretx_values if pretx_values is not None else raw_values

    side = SideOutputs()
    text = encode(actual_input, side_outputs=side)
    tcf_bytes = len(text.encode("utf-8"))
    raw_bytes_total = sum(len(v.encode("utf-8")) for v in raw_values) + len(raw_values)

    # Salvar tudo
    (out_dir / "input.txt").write_text(
        "# Raw values (input ao sub-exp):\n" + "\n".join(raw_values) + "\n",
        encoding="utf-8"
    )
    if pretx_values is not None:
        (out_dir / "pretx.txt").write_text(
            "# Apos pre-tx (input que vai pro encode TCF):\n" + "\n".join(pretx_values) + "\n",
            encoding="utf-8"
        )
    (out_dir / "output.tcf").write_text(text, encoding="utf-8")

    if side.column_features:
        cf = side.column_features
        cf_dict = {
            "n_rows": cf.n_rows,
            "n_unicas": cf.n_unicas,
            "avg_len": round(cf.avg_len, 3),
            "cardinality": round(cf.cardinality, 4),
            "is_numeric": cf.is_numeric,
            "sample": list(cf.sample),
        }
        (out_dir / "column_features.json").write_text(
            json.dumps(cf_dict, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8"
        )

    cadence_info = side.cadence_info or {}
    (out_dir / "cadence_info.json").write_text(
        json.dumps(cadence_info, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8"
    )

    if side.obat_log:
        (out_dir / "obat-log.txt").write_text(side.obat_log, encoding="utf-8")

    if side.hcc_trace:
        (out_dir / "hcc-trace.txt").write_text(side.hcc_trace, encoding="utf-8")

    if side.hcc_rede:
        (out_dir / "hcc-rede.txt").write_text(side.hcc_rede, encoding="utf-8")

    seq_rle = side.seq_rle_runs or []
    (out_dir / "seq_rle_runs.json").write_text(
        json.dumps(seq_rle, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8"
    )

    # RT check
    decoded = decode(text)
    rt_input_ok = (decoded == actual_input)

    summary = {
        "case": case_num,
        "name": name_short,
        "description": description,
        "n_values_sampled": len(raw_values),
        "raw_bytes_total": raw_bytes_total,
        "input_avg_len": round(sum(len(v) for v in actual_input) / len(actual_input), 2) if actual_input else 0,
        "tcf_bytes": tcf_bytes,
        "ratio_pct": round(tcf_bytes / raw_bytes_total * 100, 2) if raw_bytes_total > 0 else 0,
        "cadence_detected": side.cadence_detected,
        "cadence_rule": cadence_info.get("rule_hit"),
        "min_len": side.min_len,
        "obat_used_hint": side.obat_used_hint,
        "seq_rle_runs_count": len(seq_rle),
        "rt_input_ok": rt_input_ok,
        "n_unicas": side.column_features.n_unicas if side.column_features else 0,
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8"
    )
    return summary, out_dir


def write_case_analysis(out_dir: Path, case_num: int, name: str,
                         description: str, summary: dict, interpretation: str):
    """Escreve analysis.md interpretativo."""
    lines = [
        f"# Case {case_num} — {name}",
        "",
        f"**Descricao**: {description}",
        "",
        "## Resumo",
        "",
        f"- Valores: {summary['n_values_sampled']}",
        f"- Input avg length: {summary['input_avg_len']} chars",
        f"- Raw bytes (input ao sub-exp): {summary['raw_bytes_total']}",
        f"- TCF bytes: {summary['tcf_bytes']}",
        f"- Ratio: {summary['ratio_pct']}%",
        f"- cadence_detected: {summary['cadence_detected']} (rule={summary['cadence_rule']})",
        f"- min_len: {summary['min_len']}",
        f"- obat_used_hint: {summary['obat_used_hint']}",
        f"- seq_rle_runs: {summary['seq_rle_runs_count']}",
        f"- n_unicas: {summary['n_unicas']}",
        f"- RT input -> decoded: {summary['rt_input_ok']}",
        "",
        "## Arquivos neste case",
        "",
        "- `input.txt` — valores raw (input ao sub-exp)",
        "- `pretx.txt` — apos pre-tx (se aplicavel)",
        "- `output.tcf` — TCF final do encode",
        "- `column_features.json` — pre-pass features (analyze_column)",
        "- `cadence_info.json` — decisao detect_cadence",
        "- `obat-log.txt` — log per-string do OBAT (LCP/LCS, cobertura, tokens)",
        "- `hcc-trace.txt` — detector HCC iteracoes (candidatos / net / decisoes)",
        "- `hcc-rede.txt` — rede atoms + composicoes + uso por ref",
        "- `seq_rle_runs.json` — runs near-identical detectados",
        "- `summary.json` — metricas resumidas",
        "",
        "## Interpretacao",
        "",
        interpretation,
        "",
    ]
    (out_dir / "analysis.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    print("=== Sub-exp 10 — Debug OBAT/HCC nas 4 cases mais reveladoras ===\n")

    summaries = []

    # CASE 1: D-CPF-uniform variant A (M10 puro 126% — anti-compressor)
    raw = load("D-CPF-uniform")
    summ, out_dir = dump_case(
        1, "cpf-uniform-A-baseline-126pct",
        raw, None,
        "D-CPF-uniform (50 first) com M10 puro — sem pre-tx. Reproduz o 126% ratio."
    )
    summaries.append((1, "cpf-uniform-A", summ, out_dir))

    # CASE 2: D-CPF-clustered variant B (base-94 47%)
    raw = load("D-CPF-clustered")
    pretx = [encode_cpf_b(v) for v in raw]
    summ, out_dir = dump_case(
        2, "cpf-clustered-B-base94-46pct",
        raw, pretx,
        "D-CPF-clustered (50 first) com pre-tx B (strip+check+base94). "
        "5-char base-94 strings densas; OBAT/HCC com pouca redundancia visivel."
    )
    summaries.append((2, "cpf-clustered-B", summ, out_dir))

    # CASE 3: D-IP-subnet variant A (M10 puro 118%)
    raw = load("D-IP-subnet")
    summ, out_dir = dump_case(
        3, "ip-subnet-A-baseline-118pct",
        raw, None,
        "D-IP-subnet (50 first) com M10 puro. M10 detecta cadence mas variable-"
        "length octets quebram near-identical (so' 2 runs)."
    )
    summaries.append((3, "ip-subnet-A", summ, out_dir))

    # CASE 4: D-IP-subnet variant C (padded 1.71% — DRAMATIC)
    raw = load("D-IP-subnet")
    pretx = [encode_ip_c(v) for v in raw]
    summ, out_dir = dump_case(
        4, "ip-subnet-C-padded-1pct",
        raw, pretx,
        "D-IP-subnet (50 first) com pre-tx C (padded 12-digit). Strings fixas "
        "12-char com cadence visivel no ultimo octeto. HCC seq-RLE explode."
    )
    summaries.append((4, "ip-subnet-C", summ, out_dir))

    # CASE 5: D-IP-subnet 200 vals (cruzando 2 subnets) variant A
    # — investigar por que full 1000 da 118% mas sample 50 da 5.78%
    raw = load("D-IP-subnet", n=200)
    summ, out_dir = dump_case(
        5, "ip-subnet-A-200vals-cross-subnet",
        raw, None,
        "D-IP-subnet (200 first = 2 subnets completas) com M10 puro. "
        "Investiga discrepancia: 50 vals = 5.78%, mas full 1000 vals = 118%. "
        "Hipotese: transicao entre subnets quebra near-identical."
    )
    summaries.append((5, "ip-subnet-A-cross", summ, out_dir))

    # CASE 6: D-IP-subnet 200 vals variant C (padded)
    raw = load("D-IP-subnet", n=200)
    pretx = [encode_ip_c(v) for v in raw]
    summ, out_dir = dump_case(
        6, "ip-subnet-C-200vals-cross-subnet",
        raw, pretx,
        "D-IP-subnet (200 first = 2 subnets completas) com pre-tx C. "
        "Comparacao com case 5 mostra se padding ajuda no cruzamento de subnets."
    )
    summaries.append((6, "ip-subnet-C-cross", summ, out_dir))

    # Print summary table
    print(f"{'case':4s} {'name':30s} {'avg_len':>7} {'tcf':>8} {'ratio':>7} "
          f"{'cad':>4} {'rle':>4} {'min_len':>7}")
    print("-" * 90)
    for cnum, sname, s, _ in summaries:
        cad = 'Y' if s['cadence_detected'] else 'n'
        print(f"{cnum:>4} {sname:30s} {s['input_avg_len']:>7} "
              f"{s['tcf_bytes']:>8} {s['ratio_pct']:>6.2f}% "
              f"{cad:>4} {s['seq_rle_runs_count']:>4} {s['min_len']:>7}")

    # Interpretations
    interp_1 = """\
**OBAT/HCC com material aleatorio**. CPFs uniformes sao essencialmente
strings de alta entropia separadas por marcadores fixos `.` `.` `-`.

Observacoes esperadas no `obat-log.txt`:
- OBAT acha LCP=0/LCS=0 entre a maioria das strings (sem prefix/sufix
  significativo)
- min_len=3 padrao; raras coincidencias casam mas net negativo
- Cobertura per string: quase 100% TokLit (literais)

Observacoes esperadas no `hcc-trace.txt`:
- Detector itera procurando sub-tuplas com freq >=2
- Candidatos rejeitados (net <= 0) dominam
- Poucas composicoes welded; output dominado por literais + marcadores

**Conclusao**: M10 e' anti-compressor pra esta natureza. Pre-tx
explicito (variante B sub-exp 05) eh a saida.
"""

    interp_2 = """\
**OBAT/HCC com strings curtas densas (5-char base-94)**. Apos pre-tx
B, cada CPF vira 5 chars random em alfabeto BASE94.

Observacoes esperadas:
- OBAT raramente acha LCP/LCS >= 3 entre strings tao curtas
- HCC trabalha em pieces curtos; refs criados sao quase nulos
- Ganho da compressao vem do **encode mais denso** (5 vs 14 chars),
  nao do OBAT/HCC.

Cardinalidade altissima (1000 unique em 50 sample = 1.0). M10
cadence regra 2 (numeric+high-card) NAO dispara aqui porque o
output base-94 tem letras (`is_numeric=False`).

**Conclusao**: compressao real vem do pre-tx, nao do pipeline canonical.
TCF apenas serializa.
"""

    interp_3 = """\
**M10 puro em subnet IPs**. Strings variable-length (`57.12.140.0` =
11 chars vs `57.12.140.99` = 12 chars).

Observacoes esperadas:
- cadence_detected=True via regra 1 (LCP+LCS) PORQUE primeiras 5
  strings devem ter lengths uniformes (`57.12.140.0..4` todos 11 chars)
- HCC seq-RLE detecta ~2 runs entre IPs com mesmo length, depois
  para quando length muda (10..99 viram 12 chars)
- OBAT cria refs significativos pro prefix `57.12.140.`

**Conclusao**: HCC seq-RLE PARCIALMENTE funciona, mas variabilidade
de length impede captura total. Padding (case 4) resolve.
"""

    interp_4 = """\
**HCC seq-RLE EXPLODE com padding fixo**. Apos pre-tx C, cada IP vira
12-char com leading zeros (`057012140000`, `057012140001`, ...).

Observacoes esperadas:
- column_features: avg_len=12.0, cardinality=1.0, is_numeric=True
- cadence_detected=True (regra 2 ou 1)
- OBAT: usa `processar_with_hint` shape-preserve
- HCC: detector cria refs pro prefix `057012140`
- **seq_rle_runs ~11 runs** (1 por subrede de 100 IPs cada)
- Cada run: `*100+1|057012140000` (1 template + count + delta)

Cada subrede de 100 IPs vira 1 marker. 10 markers + headers = ~229B.

**Conclusao**: HCC seq-RLE eh perfeito pra este perfil. SlotBehavior
explicito desnecessario; padding visivel ja' aciona o mecanismo.
"""

    interp_5 = """\
**Cross-subnet behavior** — investigando a discrepancia 5.78% (50 vals)
vs 118% (1000 vals) reportada em sub-exp 08.

Hipotese: cada subnet tem prefix diferente (random 3 octetos). Quando
HCC seq-RLE detecta runs WITHIN um subnet, a transicao subnet1->subnet2
quebra near-identical (length pode mudar + prefix muda).

Observacoes esperadas:
- 200 IPs = 2 subnets × 100 IPs
- Esperado: runs dentro de cada subnet (similar a case 3) + literal na
  transicao
- Se M10 manage to capture 2 + 2 runs (4 total), ratio fica baixo
- Se M10 confunde por mudanca de prefix, ratio sobe

Comparar tcf_bytes com 2x bytes do case 3 (50 vals = 37B).
Esperado: ~150-300B se funciona; >500B se confunde.
"""

    interp_6 = """\
**Padded com cross-subnet**. Esperado bom comportamento mesmo no
cruzamento porque padding mantem length uniforme (sempre 12 chars).

Observacoes esperadas:
- 2 subnets, 100 IPs cada, padded
- HCC detecta runs em cada subnet (last octet 0-99)
- Transicao entre subnets: novo prefix mas mesma length
- Esperado: ratio similar ao case 4 (~7-10% em 200 vals)
- Se mantem proporcionalidade: confirma que C escala bem
"""

    interps = [interp_1, interp_2, interp_3, interp_4, interp_5, interp_6]
    for (cnum, sname, summ, out_dir), interp in zip(summaries, interps):
        write_case_analysis(out_dir, cnum, sname, summ['description'], summ, interp)

    # Consolidated report
    report_lines = [
        "# Sub-exp 10 — Debug OBAT/HCC (report consolidado)",
        "",
        "Owner pediu visibilidade dos algos internos pra entender por que",
        "M10 piora CPF (126%) e por que C subnet domina dramatically (1.71%).",
        "",
        "## Cases analisados",
        "",
        "| Case | Dataset | Variante | avg_len | TCF bytes | Ratio | cadence | seq_rle |",
        "|---|---|---|---:|---:|---:|:---:|---:|",
    ]
    for cnum, sname, s, _ in summaries:
        cad = '✓' if s['cadence_detected'] else '×'
        report_lines.append(
            f"| {cnum} | {sname.split('-')[0].upper()} | "
            f"{sname.split('-')[2] if '-' in sname else '?'} | "
            f"{s['input_avg_len']} | {s['tcf_bytes']} | {s['ratio_pct']}% | "
            f"{cad} | {s['seq_rle_runs_count']} |"
        )

    report_lines.extend([
        "",
        "## Arquivos por case",
        "",
        "Cada `case-N-*/` contem dump completo: input, pretx, output.tcf,",
        "column_features.json, cadence_info.json, obat-log.txt, hcc-trace.txt,",
        "hcc-rede.txt, seq_rle_runs.json, summary.json, analysis.md.",
        "",
        "## Cases listados",
        "",
    ])
    for cnum, sname, _, out_dir in summaries:
        rel = out_dir.relative_to(LAB.parents[3])
        report_lines.append(f"- `{rel}/analysis.md`")

    report_lines.extend([
        "",
        "## Achados consolidados",
        "",
        "### Cases 1-4 (sample 50)",
        "",
        "**Por que M10 piora CPF (case 1 126%)**: alta entropia + marcadores",
        "fixos. OBAT nao acha LCP/LCS significativos; HCC cria poucos refs;",
        "marcadores `.` `.` `-` viram overhead estatico.",
        "",
        "**Por que B funciona (case 2 46%)**: ganho vem do pre-tx (14->5 chars),",
        "NAO do pipeline canonical. TCF apenas serializa output base-94 denso.",
        "",
        "**Surpresa case 3 (M10 puro 5.78%!)**: com 50 IPs do mesmo subnet,",
        "M10 comprime BRILLIANTLY. seq-RLE pega 2 runs cobrindo todos. Body",
        "real eh 3 linhas: `\\57.\\12.\\140.*\\0`, `*9+1|1\\1`, `*40+1|1\\10`.",
        "Apenas 37 bytes pra 50 IPs!",
        "",
        "**Case 4 (padded 6.88%)** marginal pior que case 3 — padding adiciona",
        "leading zeros e marker overhead em sample pequeno.",
        "",
        "### Cases 5-6 (sample 200, cross-subnet)",
        "",
        "**Case 5 explica o 118% do sub-exp 08!** Com 200 IPs:",
        "- min_len pulou de 3 -> 6 (gating ADR-0010 ativa em n>=100)",
        "- M10 puro: 1827B = 68.17% (vs 5.78% em case 3!)",
        "- gating muda comportamento dramaticamente entre n<100 e n>=100",
        "",
        "**Case 6 imune ao gating**: padded C mantem 2.28% em 200 vals",
        "(similar 1.71% em 1000). Porque padding garante prefix >= 6 chars",
        "uniformes -> OBAT acha refs mesmo com min_len=6.",
        "",
        "### Lesson META — gating min_len escala mal em variable-length",
        "",
        "ADR-0010 gating (n>=100 ativa min_len heur v3) foi calibrado pra",
        "datasets reais Adult/TPC-H. Em IP subnet sem padding, min_len=6",
        "destroi a habilidade do OBAT de captar prefixos curtos (`140.0` =",
        "5 chars).",
        "",
        "Implicacao pra src/tcf canonical: gating ADR-0010 nao eh universal —",
        "tem cenarios onde min_len=3 (padrao) seria melhor. Hipotese pra",
        "investigar: detectar 'variable-length cadence' antes de aplicar",
        "gating, ou desativar gating quando cadence_detected=True.",
        "",
        "**Esta sub-experimento e' bom exemplo de como debug expoe bugs",
        "de calibracao do canonical pipeline.**",
        "",
        "### Lesson global",
        "",
        "HCC seq-RLE eh poderoso QUANDO:",
        "1. Input tem padroes near-identical de length uniforme",
        "2. min_len suficientemente baixo pra captar prefix comum",
        "",
        "Padding viabiliza ambos: length uniforme + prefix longo. Por isso",
        "C domina C subnet em 1.71% no full dataset 1000 vals.",
        "",
    ])
    (THIS / "report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(f"\nReport: {THIS / 'report.md'}")
    print(f"Cases: {THIS}/case-*/analysis.md")


if __name__ == "__main__":
    main()
