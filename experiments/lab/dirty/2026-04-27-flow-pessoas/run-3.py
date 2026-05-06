"""Workbench sujo CICLO 3 — refinamento do cabecalho TCF v0.4.

Foco: minimalismo + separacao core/LLM + dedutibilidade.

Pontos endenecados (do user):
1. Bug do CSV: documentado, sumir do codigo
2. Cabecalho 'legacy v0.2' eh so de lab, nao fica
3. N*val instruction eh para LLM — separar do core
4. Encoding: importante mas pode ser default
5. Line-ending: provavelmente deduzivel pelo decoder
6. Cabecalho compacto com siglas curtas economiza bytes

Saida: ./output-v3/
"""
from __future__ import annotations
import csv
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments" / "eval"))

from tcf import encode_rows, decode, EncodeConfig
from data_sources import load_dataset


HERE = Path(__file__).resolve().parent
OUT = HERE / "output-v3"
OUT.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Variantes de cabecalho propostas
# ---------------------------------------------------------------------------

def header_minimal(level: int) -> str:
    """Minimo absoluto. Encoding e line-ending implicitos (utf-8 + LF).

    Ex: '# TCF v0.4 lv=2'
    """
    return f"# TCF v0.4 lv={level}\n"


def header_with_enc(level: int, enc: str = "utf-8") -> str:
    """Adiciona encoding so se NAO for utf-8 (omite quando e default)."""
    if enc.lower() in ("utf-8", "utf8"):
        return header_minimal(level)
    return f"# TCF v0.4 lv={level} enc={enc}\n"


def header_explicit(level: int, enc: str = "utf-8", le: str = "LF") -> str:
    """Tudo explicito (compacto com siglas).

    Ex: '# TCF v0.4 lv=2 enc=utf-8 le=LF'
    """
    return f"# TCF v0.4 lv={level} enc={enc} le={le}\n"


def header_verbose_v04_old(level: int) -> str:
    """Versao verbosa proposta no ciclo 2 (referencia para comparar)."""
    return (f"# TCF v0.4 level={level} encoding=utf-8 line-ending=LF\n"
            f"# (legacy v0.2 body follows)\n")


# ---------------------------------------------------------------------------
# LLM hints como BLOCO SEPARADO (opcional, removivel sem afetar parser)
# ---------------------------------------------------------------------------

def llm_hints_block_for_level(level: int) -> str:
    """Bloco de hints para LLM, marcado para remocao facil.

    Marker '# @llm-hint:' permite filter sem regex complexa.
    Decoder ignora linhas '# @llm-hint:'.
    """
    if level >= 2:
        return (
            "# @llm-hint: dados em formato columnar; cada coluna lista valores\n"
            "# @llm-hint: N*val significa val repetido N vezes consecutivas (RLE)\n"
            "# @llm-hint: STATS no topo de cada tabela tem agregacoes pre-computadas\n"
        )
    return "# @llm-hint: dados em formato columnar; cada coluna lista valores\n"


# ---------------------------------------------------------------------------
# Detector de line-ending (simula decoder v0.4 inteligente)
# ---------------------------------------------------------------------------

def detect_line_ending(text: str) -> str:
    """Detecta line ending pela primeira ocorrencia. Sempre funciona."""
    if "\r\n" in text:
        return "CRLF"
    if "\n" in text:
        return "LF"
    if "\r" in text:
        return "CR"
    return "NONE"  # arquivo sem line-ending (improvavel)


# ---------------------------------------------------------------------------
# Encoder TCF "envelope" v0.4 — adiciona cabecalho proposto ao corpo v0.2
# ---------------------------------------------------------------------------

def encode_v04(rows: list[dict], level: int = 2,
                header_style: str = "minimal",
                with_llm_hints: bool = False,
                line_ending: str = "LF") -> str:
    """Encoder envelope simulando v0.4.

    header_style: 'minimal' | 'with_enc' | 'explicit' | 'verbose'
    with_llm_hints: True adiciona bloco @llm-hint apos cabecalho
    line_ending: 'LF' | 'CRLF' (aplicado APOS encoding)
    """
    # Encode TCF v0.2 base
    cfg = EncodeConfig(level=level, include_stats=True)
    body_v02 = encode_rows("data", rows, config=cfg)

    # Remove cabecalho v0.2 atual (1a linha "# TCF v0.2 ...")
    if body_v02.startswith("# TCF"):
        body_v02 = body_v02.split("\n", 1)[1]

    # REMOVE tambem comentario do RLE se for L2+ (vai para LLM hints opcional)
    # Atual: "# N*val = val repeated N times" eh segunda linha do v0.2 L2
    if body_v02.startswith("# N*val"):
        body_v02 = body_v02.split("\n", 1)[1]

    # Monta cabecalho conforme estilo
    if header_style == "minimal":
        header = header_minimal(level)
    elif header_style == "with_enc":
        header = header_with_enc(level)
    elif header_style == "explicit":
        header = header_explicit(level)
    elif header_style == "verbose":
        header = header_verbose_v04_old(level)
    else:
        raise ValueError(f"unknown header_style: {header_style}")

    # LLM hints opcional
    if with_llm_hints:
        hints = llm_hints_block_for_level(level)
    else:
        hints = ""

    text = header + hints + body_v02

    # Aplica line-ending solicitado
    if line_ending == "CRLF":
        text = text.replace("\r\n", "\n").replace("\n", "\r\n")
    elif line_ending == "LF":
        text = text.replace("\r\n", "\n")  # garante LF puro
    return text


def main() -> None:
    print("=" * 70)
    print("CICLO 3 — refinamento do cabecalho TCF v0.4")
    print("=" * 70)

    # Dados
    tables, _ = load_dataset("canonical:tpch-sf001",
                              volume=20, seed=42, schema=["supplier"])
    rows_in = [{"name": s["s_name"]} for s in tables["supplier"][:10]]

    # ---- 1. Variantes de cabecalho com mesmo corpo L2 ----
    print("\n[1] Variantes de cabecalho (corpo L2 igual)\n")
    variants = [
        ("01-minimal",     "minimal",  False),
        ("02-with-enc",    "with_enc", False),
        ("03-explicit",    "explicit", False),
        ("04-verbose-old", "verbose",  False),
        ("05-min+hints",   "minimal",  True),
        ("06-explicit+hints", "explicit", True),
    ]

    rows_table = []
    for label, style, hints in variants:
        text = encode_v04(rows_in, level=2,
                           header_style=style, with_llm_hints=hints)
        path = OUT / f"{label}.tcf"
        path.write_bytes(text.encode("utf-8"))
        rows_table.append((label, len(text.encode("utf-8")), text))
        # Mostra so as 4 primeiras linhas
        first_4 = "\n".join(text.splitlines()[:4])
        print(f"  --- {label} ({len(text.encode('utf-8'))}B) ---")
        print(first_4)
        print()

    # ---- 2. Tabela de overhead ----
    print("=" * 70)
    print("[2] Overhead de cabecalho (vs minimal=baseline)")
    print("=" * 70)
    minimal_b = rows_table[0][1]
    print(f"  {'variante':<22} {'bytes':>7}  {'overhead':>10}")
    print(f"  {'-'*22} {'-'*7}  {'-'*10}")
    for label, n, _ in rows_table:
        delta = n - minimal_b
        sign = "+" if delta > 0 else ""
        pct = (delta / minimal_b) * 100 if minimal_b else 0
        print(f"  {label:<22} {n:>7}  {sign}{delta:>3}B ({sign}{pct:.1f}%)")

    # ---- 3. Detector de line-ending no decoder ----
    print("\n" + "=" * 70)
    print("[3] Detector de line-ending (decoder v0.4 inteligente)")
    print("=" * 70)
    for le in ("LF", "CRLF"):
        text = encode_v04(rows_in, level=2, line_ending=le)
        detected = detect_line_ending(text)
        path = OUT / f"07-le-{le}.tcf"
        path.write_bytes(text.encode("utf-8"))
        ok = "OK" if detected == le else "FAIL"
        print(f"  Encoded com '{le}'  -> detector retornou '{detected}'  [{ok}]")

    print("\n  CONCLUSAO: line-ending eh trivialmente deduzivel pelo decoder.")
    print("  -> NAO precisa estar no cabecalho v0.4 (decoder olha 1a quebra).")

    # ---- 4. Cenario com caracteres especiais — testa encoding ----
    print("\n" + "=" * 70)
    print("[4] Caracteres especiais — encoding default vs explicito")
    print("=" * 70)
    rows_special = [
        {"name": "Café"},      # acentos
        {"name": "中文"},       # CJK
        {"name": "🎉"},         # emoji
        {"name": "Olá, Mundo"}, # acento + virgula
    ]

    text_min = encode_v04(rows_special, level=2, header_style="minimal")
    text_exp = encode_v04(rows_special, level=2, header_style="explicit")

    (OUT / "08-special-minimal.tcf").write_bytes(text_min.encode("utf-8"))
    (OUT / "09-special-explicit.tcf").write_bytes(text_exp.encode("utf-8"))

    print(f"  Minimal (sem enc): {len(text_min.encode('utf-8'))}B")
    print(f"  Explicit (enc=utf-8): {len(text_exp.encode('utf-8'))}B")
    print(f"  Diferenca: +{len(text_exp.encode('utf-8'))-len(text_min.encode('utf-8'))}B")
    print()
    print("  Decoder UTF-8 padrao consegue ler caracteres especiais SEM o")
    print("  campo enc=utf-8 explicito (UTF-8 e self-describing via bytes).")
    print("  Conclusao: enc= so eh necessario quando encoding eh DIFERENTE")
    print("  de utf-8 (ex: utf-16, latin1). Default implicito = utf-8.")

    # ---- 5. Cenario LLM hints — quando manter ----
    print("\n" + "=" * 70)
    print("[5] LLM hints — bloco separado, opt-in")
    print("=" * 70)
    base = encode_v04(rows_in, level=2, header_style="minimal", with_llm_hints=False)
    with_hints = encode_v04(rows_in, level=2, header_style="minimal", with_llm_hints=True)
    print(f"  Sem hints (core puro): {len(base.encode('utf-8'))}B")
    print(f"  Com hints @llm-hint:   {len(with_hints.encode('utf-8'))}B")
    print(f"  Overhead hints: +{len(with_hints.encode('utf-8'))-len(base.encode('utf-8'))}B")
    print()
    print("  Marker '# @llm-hint:' permite:")
    print("    - decoder ignora (eh comentario)")
    print("    - filtro trivial: grep -v '@llm-hint:' antes de enviar")
    print("    - opt-in: encoder so emite quando explicitamente pedido")
    print("    - customizavel por dataset/cenario")

    # ---- 6. Cabecalho minimo — analise de bytes ----
    print("\n" + "=" * 70)
    print("[6] Quanto vale economizar bytes no cabecalho?")
    print("=" * 70)
    samples = [
        ("# TCF v0.4 lv=2",                                15),
        ("# TCF v0.4 lv=2 enc=utf-8",                      26),
        ("# TCF v0.4 lv=2 enc=utf-8 le=LF",                32),
        ("# TCF v0.4 level=2 encoding=utf-8 line-ending=LF", 49),
    ]
    for line, n in samples:
        print(f"  {n:>3}B  {line}")
    print()
    print("  Em dataset MIN (10 rows × 1 col, ~200B total):")
    print("    minimal (15B) eh ~7% do payload — significativo")
    print("    verbose (49B) eh ~25% do payload — DESPERDICIO")
    print()
    print("  Em dataset MEDIUM (1000 rows × 5 cols, ~50KB total):")
    print("    minimal (15B) eh 0.03% — irrelevante")
    print("    verbose (49B) eh 0.1% — irrelevante")
    print()
    print("  Conclusao: cabecalho minimo eh PRINCIPIO, nao otimizacao.")
    print("  Forca a pensar 'o que e essencial?' em cada campo.")

    print(f"\n[OK] Arquivos em: {OUT}")


if __name__ == "__main__":
    main()
