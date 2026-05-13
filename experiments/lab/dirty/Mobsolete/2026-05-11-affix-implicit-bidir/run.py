"""Lab dirty: affix implicito bidirecional.

Implementacao ad-hoc (NAO toca core) de:
  - Encoder com flag P-bidir (affix declarado inline + multi)
  - Decoder paralelo
  - 6 cenarios comparativos

Compara com:
  - CSV puro
  - TCF v0.5 SRDMP atual (etapa 1)
  - TCF v0.5 affix-bidir (etapa 2 proposta)

Saida: ./output/
"""
from __future__ import annotations
import csv
import gzip
import io
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))

from tcf.v05 import encode as tcf_encode, Flags

HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
OUT.mkdir(exist_ok=True)
random.seed(42)


# ---------------------------------------------------------------------------
# Encoder/decoder ad-hoc para affix bidirecional implicito
# ---------------------------------------------------------------------------

def _split_prefix(values: list[str]) -> list[tuple[str, str]]:
    """Para cada valor, separa em (prefix, var) usando heuristica.

    Heuristica: encontra o LCP em janela deslizante. Para simplicidade
    aqui: tenta detectar separadores comuns (`-`, `_`, `/`, `:`) e
    usa o ultimo separador antes do qual ha texto comum.

    Implementacao naive: extrai LCP completo entre cada string e a
    proxima; se LCP > 4 chars, divide ali.
    """
    out = []
    if not values:
        return out
    # Pega o LCP global como prefix candidato
    lcp = values[0]
    for v in values[1:]:
        i = 0
        while i < min(len(lcp), len(v)) and lcp[i] == v[i]:
            i += 1
        lcp = lcp[:i]
        if not lcp:
            break
    # Se LCP forte (>=4 chars), usa
    if len(lcp) >= 4:
        return [(lcp, v[len(lcp):]) for v in values]
    # Fallback: sem split confiavel — retorna ("", v)
    return [("", v) for v in values]


def _split_suffix(values: list[str], separators: tuple = ("@", ".", "/")) -> list[tuple[str, str]]:
    """Para cada valor, separa em (var, suffix) baseado em separadores comuns.

    Heuristica: encontra o ultimo separador (`@` para emails, `.` para
    extensoes, etc.) que cria um suffix repetido em pelo menos 2 valores.
    """
    if not values:
        return []
    # Tenta cada separador
    best_split = None
    best_score = 0
    for sep in separators:
        # Para cada valor, pega tudo apos o ultimo `sep`
        suffixes = []
        for v in values:
            idx = v.rfind(sep)
            if idx >= 0:
                suffixes.append((v[:idx], v[idx:]))
            else:
                suffixes.append((v, ""))
        # Conta frequencia dos suffixes
        from collections import Counter
        suffix_counts = Counter(s for _, s in suffixes if s)
        if not suffix_counts:
            continue
        most_common_count = suffix_counts.most_common(1)[0][1]
        if most_common_count > best_score:
            best_score = most_common_count
            best_split = suffixes

    if best_split is None or best_score < 2:
        return [(v, "") for v in values]
    return best_split


def encode_affix_bidir(values: list[str], direction: str = ">",
                        col_name: str = "col") -> str:
    """Encoda lista de strings em formato affix-bidir.

    direction: ">" (prefix) ou "<" (suffix)
    """
    if not values:
        return f"{col_name},{direction}:\n"

    if direction == ">":
        splits = _split_prefix(values)
        # splits = [(prefix, var)]
    else:
        splits = _split_suffix(values)
        # splits = [(var, suffix)]

    # Emite linhas
    out = [f"{col_name},{direction}:"]
    affix_dict: list[str] = []  # affixes declarados, 1-based externamente
    affix_dict_idx: dict[str, int] = {}  # affix -> idx

    last_affix: str | None = None

    for split in splits:
        if direction == ">":
            affix, var = split
        else:
            var, affix = split

        if not affix:
            # excecao — sem affix (raro)
            out.append(f"\\!{var}")
            continue

        if affix not in affix_dict_idx:
            # declara novo
            affix_dict.append(affix)
            affix_dict_idx[affix] = len(affix_dict)
            last_affix = affix
            # Linha com declaracao explicita
            if direction == ">":
                out.append(f"{affix} {var}")
            else:
                out.append(f"{var} {affix}")
        else:
            # reusa
            idx = affix_dict_idx[affix]
            if affix == last_affix:
                # so var, sem ref
                out.append(var)
            else:
                # var + idx
                if direction == ">":
                    out.append(f"{idx} {var}")
                else:
                    out.append(f"{var} {idx}")
                last_affix = affix

    return "\n".join(out) + "\n"


def decode_affix_bidir(text: str) -> list[str]:
    """Decoda formato affix-bidir."""
    lines = text.splitlines()
    if not lines:
        return []

    header_match = re.match(r"^([^,:]+),([><]):\s*$", lines[0])
    if not header_match:
        raise ValueError(f"Bad header: {lines[0]!r}")
    direction = header_match.group(2)

    affix_dict: list[str] = []  # 1-based externamente
    last_affix: str | None = None
    out: list[str] = []

    for line in lines[1:]:
        if not line:
            continue

        # Excecao (\!)
        if line.startswith("\\!"):
            out.append(line[2:])
            continue

        # Tem espaco interno?
        if " " in line:
            part1, part2 = line.split(" ", 1)
            if direction == ">":
                # part1 = affix-or-ref, part2 = var
                if part1.isdigit():
                    idx = int(part1)
                    if 1 <= idx <= len(affix_dict):
                        affix = affix_dict[idx - 1]
                        last_affix = affix
                        out.append(affix + part2)
                    else:
                        raise ValueError(f"affix idx out of range: {part1}")
                else:
                    affix_dict.append(part1)
                    last_affix = part1
                    out.append(part1 + part2)
            else:  # "<"
                # part1 = var, part2 = suffix-or-ref
                if part2.isdigit():
                    idx = int(part2)
                    if 1 <= idx <= len(affix_dict):
                        affix = affix_dict[idx - 1]
                        last_affix = affix
                        out.append(part1 + affix)
                    else:
                        raise ValueError(f"affix idx out of range: {part2}")
                else:
                    affix_dict.append(part2)
                    last_affix = part2
                    out.append(part1 + part2)
        else:
            # so var; usa ultimo affix declarado
            if last_affix is None:
                raise ValueError("var sem affix declarado")
            if direction == ">":
                out.append(last_affix + line)
            else:
                out.append(line + last_affix)

    return out


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def csv_encode(rows):
    if not rows:
        return ""
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()),
                        lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def gz(text: str) -> bytes:
    return gzip.compress(text.encode("utf-8"), compresslevel=9)


# ---------------------------------------------------------------------------
# Cenarios
# ---------------------------------------------------------------------------

def S1_codigos_uniforme():
    """100 codigos com 1 prefix."""
    return [f"INV-2026-{i:04d}" for i in range(1, 101)]


def S2_emails_1dominio():
    """100 emails com 1 suffix."""
    return [f"user{i:03d}@gmail.com" for i in range(100)]


def S3_emails_2dominios_5050():
    """100 emails 50/50 em 2 dominios misturados."""
    out = []
    for i in range(50):
        out.append(f"user{i:03d}@gmail.com")
    for i in range(50):
        out.append(f"user{i+50:03d}@yahoo.com")
    random.shuffle(out)
    return out


def S4_emails_3dominios():
    """100 emails 33/33/34 em 3 dominios misturados."""
    domains = ["@gmail.com", "@yahoo.com", "@outlook.com"]
    out = []
    for i in range(100):
        out.append(f"user{i:03d}{domains[i % 3]}")
    random.shuffle(out)
    return out


def S5_codigos_misturados():
    """100 codigos misturados em 3 prefixes."""
    prefixes = ["INV-2026-", "PED-2026-", "REQ-2026-"]
    out = []
    for i in range(100):
        out.append(f"{prefixes[i % 3]}{i:04d}")
    random.shuffle(out)
    return out


def S6_nomes_sem_padrao():
    """100 nomes pessoais (deve detectar nada)."""
    nomes = ["Ana", "Bruno", "Carlos", "Diana", "Eduardo",
             "Fernanda", "Gabriel", "Helena", "Igor", "Juliana"]
    return [random.choice(nomes) + f"_{i:03d}" for i in range(100)]


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run_scenario(name: str, values: list[str], col_name: str = "col",
                  direction: str = ">"):
    print("=" * 90)
    print(f"[{name}] {len(values)} valores, direcao={direction}")
    print("=" * 90)

    # CSV (1 coluna)
    rows = [{col_name: v} for v in values]
    csv_text = csv_encode(rows)
    b_csv = len(csv_text.encode("utf-8"))
    b_csv_gz = len(gz(csv_text))

    # TCF v0.5 SRDM (sem affix)
    text_srdm = tcf_encode(rows, flags=Flags(S=True, R=True, D=True, M=True))
    b_srdm = len(text_srdm.encode("utf-8"))
    b_srdm_gz = len(gz(text_srdm))

    # TCF v0.5 SRDMP (affix simples atual)
    text_srdmp = tcf_encode(rows, flags=Flags(S=True, R=True, D=True, M=True, P=True))
    b_srdmp = len(text_srdmp.encode("utf-8"))
    b_srdmp_gz = len(gz(text_srdmp))

    # Affix-bidir (proposto)
    bidir_text = encode_affix_bidir(values, direction=direction, col_name=col_name)
    b_bidir = len(bidir_text.encode("utf-8"))
    b_bidir_gz = len(gz(bidir_text))

    # Roundtrip bidir
    try:
        decoded = decode_affix_bidir(bidir_text)
        rt_bidir = decoded == values
        rt_msg = "OK" if rt_bidir else f"FAIL (decoded {len(decoded)} != {len(values)})"
    except Exception as e:
        rt_bidir = False
        rt_msg = f"FAIL — {type(e).__name__}: {e}"

    print(f"\n  bytes:")
    print(f"    csv           {b_csv:>5}  csv+gz   {b_csv_gz:>5}")
    print(f"    tcf-SRDM      {b_srdm:>5}  +gz      {b_srdm_gz:>5}")
    print(f"    tcf-SRDMP     {b_srdmp:>5}  +gz      {b_srdmp_gz:>5}  ({(b_srdmp/b_srdm-1)*100:+.1f}% vs SRDM)")
    print(f"    affix-bidir   {b_bidir:>5}  +gz      {b_bidir_gz:>5}  ({(b_bidir/b_srdmp-1)*100:+.1f}% vs SRDMP)")
    print(f"\n  roundtrip bidir: {rt_msg}")

    # Mostra primeiras 10 linhas do bidir
    print(f"\n  --- affix-bidir output (primeiras 10 linhas) ---")
    for line in bidir_text.splitlines()[:10]:
        print(f"    {line}")
    if len(bidir_text.splitlines()) > 10:
        print(f"    ... ({len(bidir_text.splitlines())-10} linhas a mais)")

    # Salva
    scen_dir = OUT / name
    scen_dir.mkdir(exist_ok=True)
    (scen_dir / "source.csv").write_text(csv_text, encoding="utf-8")
    (scen_dir / "tcf-SRDM.tcf").write_text(text_srdm, encoding="utf-8")
    (scen_dir / "tcf-SRDMP.tcf").write_text(text_srdmp, encoding="utf-8")
    (scen_dir / "tcf-bidir.txt").write_text(bidir_text, encoding="utf-8")

    return {
        "name": name,
        "n": len(values),
        "direction": direction,
        "csv": b_csv, "csv_gz": b_csv_gz,
        "srdm": b_srdm, "srdm_gz": b_srdm_gz,
        "srdmp": b_srdmp, "srdmp_gz": b_srdmp_gz,
        "bidir": b_bidir, "bidir_gz": b_bidir_gz,
        "bidir_vs_srdmp_pct": (b_bidir/b_srdmp - 1)*100 if b_srdmp else 0,
        "bidir_vs_srdm_pct": (b_bidir/b_srdm - 1)*100 if b_srdm else 0,
        "bidir_vs_csv_pct": (b_bidir/b_csv - 1)*100 if b_csv else 0,
        "roundtrip_bidir": rt_bidir,
    }


def main():
    print("\n" + "=" * 90)
    print("Lab dirty: affix-bidir implicito (proposta etapa 2)")
    print("=" * 90)

    results = []
    results.append(run_scenario("S1-codigos-uniforme", S1_codigos_uniforme(),
                                  col_name="codigo", direction=">"))
    results.append(run_scenario("S2-emails-1dominio", S2_emails_1dominio(),
                                  col_name="email", direction="<"))
    results.append(run_scenario("S3-emails-2dominios", S3_emails_2dominios_5050(),
                                  col_name="email", direction="<"))
    results.append(run_scenario("S4-emails-3dominios", S4_emails_3dominios(),
                                  col_name="email", direction="<"))
    results.append(run_scenario("S5-codigos-misturados", S5_codigos_misturados(),
                                  col_name="codigo", direction=">"))
    results.append(run_scenario("S6-nomes-sem-padrao", S6_nomes_sem_padrao(),
                                  col_name="nome", direction="<"))

    # Sintese
    print("\n" + "=" * 90)
    print("Sintese")
    print("=" * 90)
    print(f"\n  {'cenario':<24} {'csv':>6} {'SRDM':>6} {'SRDMP':>6} {'bidir':>6} "
          f"{'bidir vs SRDMP':>15} {'rt':>4}")
    print(f"  {'-'*24} {'-'*6} {'-'*6} {'-'*6} {'-'*6} {'-'*15} {'-'*4}")
    for r in results:
        rt = "OK" if r["roundtrip_bidir"] else "FAIL"
        print(f"  {r['name']:<24} {r['csv']:>6} {r['srdm']:>6} {r['srdmp']:>6} "
              f"{r['bidir']:>6} {r['bidir_vs_srdmp_pct']:>+13.1f}%  {rt:>4}")

    avg_vs_srdmp = sum(r["bidir_vs_srdmp_pct"] for r in results) / len(results)
    avg_vs_srdm = sum(r["bidir_vs_srdm_pct"] for r in results) / len(results)
    avg_vs_csv = sum(r["bidir_vs_csv_pct"] for r in results) / len(results)
    print(f"\n  Avg bidir vs SRDMP: {avg_vs_srdmp:+.2f}%")
    print(f"  Avg bidir vs SRDM:  {avg_vs_srdm:+.2f}%")
    print(f"  Avg bidir vs CSV:   {avg_vs_csv:+.2f}%")

    summary = {"experiment": "affix-bidir-implicit",
                "scenarios": results,
                "averages": {"vs_SRDMP": avg_vs_srdmp,
                              "vs_SRDM": avg_vs_srdm,
                              "vs_CSV": avg_vs_csv}}
    (OUT / "results.json").write_text(json.dumps(summary, indent=2),
                                        encoding="utf-8")
    print(f"\n  Outputs: {OUT}")


if __name__ == "__main__":
    main()
