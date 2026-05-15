# EXP-008 — Compressao comparada (raw vs TCF) com compressores de fluxo geral

**Data**: 2026-05-15
**Tipo**: experimento clean
**Ciclo**: v0.6 (segundo experimento clean, apos EXP-007)
**Estado**: aberto

## Pergunta cientifica

Como o TCF se posiciona, em **bytes finais** e **latencia**, contra
e em conjunto com os compressores de fluxo geral disponiveis em
HTTP/3 (gzip, brotli, zstd) e em arquivos (lzma, bz2)?

Tres perguntas operacionais:

1. **Q1 (TCF stand-alone)**: para cada dataset `D` e compressor
   `C ∈ {gzip, brotli, zstd, lzma, bz2}`, como ficam `|tcf(D)|`,
   `|C(D)|` e a ordem entre eles?
2. **Q2 (TCF como pre-tx)**: `|C(tcf(D))| / |C(D)|` — TCF
   complementa o compressor (<1), e' ortogonal (≈1) ou interfere
   negativamente (>1)?
3. **Q3 (latencia)**: tempo de `encode/decode` do TCF + tempo de
   `compress/decompress` de cada `C`. Stack `tcf → C` vs `C` puro.

## Hipoteses

- **H1 (Q1)**: para datasets de **alta redundancia estrutural**
  (D1-D9: prefix/suffix/wrappers estaveis), TCF stand-alone deve
  ficar competitivo com gzip/brotli/zstd em bytes (na ordem de
  20-50% raw), e tipicamente abaixo de bz2/lzma em datasets onde
  o numero de linhas e' pequeno (overhead fixo dos compressores
  gerais e' significativo nessa escala).
- **H2 (Q2)**: tcf reduz redundancia explicita (afixos repetidos).
  Apos tcf, o resto e' "ja' meio comprimido": espera-se
  `|C(tcf)| < |C(raw)|` em datasets onde tcf ja' venceu por bytes
  (Q1), mas pode haver **diminishing returns** ou ate' inversao
  em datasets de baixa redundancia (D4 caos; D10-D15 variety).
- **H3 (Q3)**: tcf e' mais caro que gzip em encode/decode (algoritmo
  bidirecional + composicional vs LZ77 + Huffman tabulado), mas
  comparavel/menor que lzma/brotli max. Stack `tcf → gzip` deve
  ser mais lento que `gzip` puro mas pode entregar bytes melhores.

## Metodo

Para cada dataset `D ∈ {D1..D15}`:

1. Ler `D.csv` → `linhas` (lista de strings, sem header).
2. `raw_text = "\n".join(linhas) + "\n"` (payload do dataset, sem
   header — equivalente ao que TCF processa).
3. `tcf_text = encode(linhas)`; valida `decode(tcf_text) == linhas`.
4. Para cada compressor `C`:
   - `c_raw = C(raw_text.encode("utf-8"))`
   - `c_tcf = C(tcf_text.encode("utf-8"))`
   - valida: `C.decompress(c_raw) == raw_text.encode("utf-8")`
   - valida: `decode(C.decompress(c_tcf).decode("utf-8")) == linhas`
     (roundtrip completo: encode → compress → decompress → decode)
5. Mede tempo: mediana de N reps via `time.perf_counter_ns`.
   - encode/decode TCF: 20 reps (operacao mais cara)
   - compress/decompress compressor: 100 reps
6. Bytes registrados, ratios calculados, RT validado.

## Compressores e niveis

Niveis **maximos** (foco em compressao, latencia caracterizada como
custo associado):

| Compressor | Lib | Nivel | Padrao HTTP |
|---|---|---|---|
| gzip | `gzip` (stdlib) | level=9, mtime=0 | `Content-Encoding: gzip` |
| brotli | `brotli` 1.2.0 | quality=11 | `Content-Encoding: br` |
| zstd | `zstandard` 0.25.0 | level=22 | `Content-Encoding: zstd` (RFC 8478) |
| lzma | `lzma` (stdlib) | preset=9 | nao-HTTP padrao |
| bz2 | `bz2` (stdlib) | compresslevel=9 | obsoleto em HTTP |

Os 3 primeiros sao o conjunto canonico de HTTP/3 atual; lzma e bz2
entram como referencias de fluxo arquivo (mais agressivos em
bytes, mais lentos em CPU).

## Datasets

15 datasets sinteticos de controle (`datasets/synthetic/`):

| Grupo | IDs | Caracteristica |
|---|---|---|
| TCF-CORE classicos | D1-D9 | Padroes estruturais (afixos, wrappers, caos) |
| ERP/CRM tipos | D10-D15 | Variety datasets (datas, datetime, CPF, UUID, base64) |

D10-D15 nao foram projetados pra TCF-CORE atual (single-column, sem
type encoders); inclusao aqui e' pra **caracterizar limite atual**
do algoritmo em dados de tipos comuns.

## Como rodar

```bash
python experiments/lab/clean/EXP-008-compressao-comparada/run.py
```

Pre-requisitos:
- `src/tcf/` welded (EXP-007 valida);
- `pip install brotli zstandard` (gzip/lzma/bz2 sao stdlib).

## Resultado

Ver [`report.md`](report.md) (gerado por `run.py`).

## Significado

Diferente de EXP-007 (validacao byte-canonica), EXP-008 e'
**comparativo**: situa TCF dentro do espaco de compressores de
producao. Tres saidas esperadas:

1. **Mapa bytes** — onde TCF vence, onde perde, onde complementa.
2. **Mapa latencia** — custo CPU de cada pipeline.
3. **Limites identificados** — quais cenarios precisam de pre-tx
   (Estrategia 1.A type encoders, EXP-009) pra TCF ser competitivo.

## Conexoes

- [`../EXP-007-prototipo-tcf-core/`](../EXP-007-prototipo-tcf-core/) — validacao byte-canonica (precedente)
- [`../../../../datasets/synthetic/`](../../../../datasets/synthetic/) — D1-D15
- [`../../../../docs/theory/perspectiva-triplice-e-pre-tx.md`](../../../../docs/theory/perspectiva-triplice-e-pre-tx.md) — perspectiva triplice (compressao + memoria + latencia)
- [`../../../../docs/algorithms/`](../../../../docs/algorithms/) — especificacao TCF/OBAT/HCC
