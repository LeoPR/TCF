"""Orquestrador 09 — auditoria self-containment D11a.

Demonstra que D11a.tcf (42 bytes) contem TUDO necessario pra
reconstruir D11a original, sem auxilio externo.

Procedimento:
1. Pega `input/D11a.tcf` (cópia byte-exata do tcf-C.tcf de sub-exp 08)
2. Roda `decode_standalone.decode_self_contained(D11a.tcf)`
   — passa APENAS o file path; nada mais
3. Compara saida com D11a-datas-dia.csv original
   (so' para VERIFICAR; o decoder nunca viu o csv)
4. Mostra audit trail das tecnicas aplicadas
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

THIS = Path(__file__).parent
ROOT = THIS.parents[6]
sys.path.insert(0, str(THIS))

from decode_standalone import decode_self_contained  # noqa: E402


def write_lf(path: Path, content: str) -> None:
    path.write_bytes(content.encode("utf-8"))


def main() -> None:
    print("=== 09-auditoria-self-contained-D11a ===\n")

    tcf_file = THIS / "input" / "D11a.tcf"
    csv_file = ROOT / "datasets" / "synthetic" / "D11a-datas-dia.csv"
    out_dir = THIS / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)

    # === 1) Mostrar conteudo do .tcf (e' so' isso que o decoder recebe)
    tcf_bytes = tcf_file.read_bytes()
    tcf_text = tcf_bytes.decode("utf-8")
    print(f"Arquivo input: {tcf_file}")
    print(f"Tamanho: {len(tcf_bytes)} bytes\n")
    print("Conteudo (bytes do .tcf — TUDO que o decoder recebe):")
    print("-" * 50)
    print(tcf_text)
    print("-" * 50)
    print()

    # === 2) Decodificar SEM passar mais nada
    decoded_lines, meta = decode_self_contained(tcf_file)
    print(f"Decoder auto-detectou: {meta}")
    print(f"Reconstruiu {len(decoded_lines)} linhas\n")

    # === 3) Carregar D11a.csv original (so' pra COMPARAR)
    with csv_file.open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)  # skip header
        original_lines = [row[0] for row in r if row]

    # === 4) Verificacao byte-canonical
    rt_ok = decoded_lines == original_lines
    write_lf(out_dir / "decoded.txt",
             "\n".join(decoded_lines) + "\n")
    write_lf(out_dir / "original.txt",
             "\n".join(original_lines) + "\n")

    diff_lines = []
    if rt_ok:
        diff_lines.append("RT byte-canonical: OK")
        diff_lines.append(f"Linhas: {len(decoded_lines)}/{len(original_lines)}")
    else:
        diff_lines.append("RT byte-canonical: FAIL")
        for i in range(max(len(decoded_lines), len(original_lines))):
            d = decoded_lines[i] if i < len(decoded_lines) else "<missing>"
            o = original_lines[i] if i < len(original_lines) else "<missing>"
            if d != o:
                diff_lines.append(f"  [{i}] decoded={d!r} != original={o!r}")
    write_lf(out_dir / "rt-result.txt", "\n".join(diff_lines) + "\n")

    print(f"RT vs D11a.csv original: {'OK' if rt_ok else 'FAIL'}")
    print(f"  decoded: {len(decoded_lines)} linhas")
    print(f"  original: {len(original_lines)} linhas")
    print()

    # === 5) Resultado consolidado
    result = [
        "# Resultado — 09-auditoria-self-contained-D11a",
        "",
        f"**Conclusao**: `D11a.tcf` ({len(tcf_bytes)} bytes) e' "
        f"**{'AUTO-CONTAINED' if rt_ok else 'NAO AUTO-CONTAINED'}**.",
        "",
        "## Procedimento",
        "",
        f"1. Decoder recebeu APENAS `input/D11a.tcf` ({len(tcf_bytes)} bytes)",
        f"2. Decoder usou algoritmo padrao (TCF.decode) + logica pre-tx",
        f"3. Auto-detectou natureza: {meta}",
        f"4. Reconstruiu {len(decoded_lines)} linhas",
        f"5. Comparou com D11a-datas-dia.csv original",
        f"   Resultado: **{'BYTE-CANONICAL OK' if rt_ok else 'FAIL'}**",
        "",
        "Decoder **NAO** recebeu:",
        "- D11a.csv original (nunca viu)",
        "- Metadata externo (JSON, sidecar, ...)",
        "- Hint sobre natureza ou granularidade",
        "- Count de linhas esperadas",
        "",
        "## Conteudo do .tcf (42 bytes — tudo que e' necessario)",
        "",
        "```",
        tcf_text.rstrip(),
        "```",
        "",
        "## Audit trail: tecnicas aplicadas a D11a (em ordem inversa do encode)",
        "",
        "### Camada 2 — TCF decode (OBAT + HCC, algoritmo compartilhado)",
        "",
        "TCF.decode aplica:",
        "- Parse linhas tipo `*N|<conteudo>` (RLE adjacente — N copias da linha)",
        "- Parse `^N` como referencia ao N-esimo node de declaracao anterior",
        "- Parse `\\<digits>` como literal escapado pra evitar conflito com IDs",
        "",
        "Resultado intermediario apos TCF.decode:",
        "",
        "```",
    ]
    from tcf import decode as tcf_decode
    pretx_out = tcf_decode(tcf_text)
    for i, l in enumerate(pretx_out):
        result.append(f"[{i}] {l!r}")
    result.append("```")
    result.append("")

    result.extend([
        "### Camada 1 — Pre-tx inverso (Stage A → C → B inversos)",
        "",
        "**Stage A (identify)** — Auto-deducao da primeira linha:",
        f"- Pattern: `YYYY-MM-DD` (regex match)",
        f"- Validacao: `date.fromisoformat('{pretx_out[0]}')` → OK",
        f"- Meta inferido: `{meta}`",
        "",
        "**Stage C inverso** — parse das escalas:",
        "- Para D11a, nenhuma escala (`Y`, `M`) presente",
        "- Todas as linhas (apos a primeira) sao integers em dias",
        "",
        "**Stage B inverso** — acumulacao dos deltas:",
        f"- `current = {decoded_lines[0]}`",
    ])
    if len(pretx_out) > 1:
        for i in range(1, min(5, len(pretx_out))):
            result.append(
                f"- `current += {pretx_out[i]} dia(s)` → "
                f"`{decoded_lines[i]}`")
        if len(pretx_out) > 5:
            result.append("- ... (segue ate' o fim)")
    result.append("")

    result.extend([
        "## Resultado final",
        "",
        f"- Bytes do .tcf: **{len(tcf_bytes)}**",
        f"- Linhas reconstruidas: **{len(decoded_lines)}**",
        f"- Linhas no original D11a.csv: **{len(original_lines)}**",
        f"- RT byte-canonical: **{'OK' if rt_ok else 'FAIL'}**",
        "",
        "## Implicacao",
        "",
        "O arquivo `.tcf` carrega **dados + estrutura de refs**. O resto",
        "(natureza, granularidade, semântica do delta) e' **auto-deduzido",
        "pela primeira linha**. Algoritmo de decoder e' conhecimento",
        "compartilhado (como `gunzip`).",
        "",
        "Se em iteracoes futuras for necessario um **cabecalho explicito**",
        "(ex: pra disambiguar quando first line nao da pra deduzir tudo),",
        "ele tera que estar **DENTRO do .tcf** — em principio numa linha",
        "de meta antes do base. Hoje nao precisa porque a inferencia",
        "automatica e' suficiente pra D11a-h.",
        "",
        "## Conexoes",
        "",
        "- [decode_standalone.py](decode_standalone.py) — decoder isolado",
        "- [`../08-granularidades-finas/`](../08-granularidades-finas/) — fonte do tcf-C.tcf",
        "- [TCF algoritmo](../../../../../../docs/algorithms/) — OBAT + HCC docs",
    ])

    write_lf(THIS / "result.md", "\n".join(result) + "\n")
    print(f"result.md: {THIS / 'result.md'}")


if __name__ == "__main__":
    main()
