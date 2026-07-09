# 2026-07-08-2302 — F1: latência do bypass (dá número ao eixo aceleração)

**Hipótese**: [H-TYPE-07](../notas/roadmap-hipoteses.md) (fluxo F1) · nota
[bn-dict-perspectivas](../notas/bn-dict-perspectivas-e-dict-interno.md). O F1 (bypass) era a motivação real
da preemptiva, mas o **eixo aceleração** estava **sem número** em todos os labs (só medimos compressão).
Este lab mede. NÃO toca `src/tcf`.

## Estado

- **era**: F1 = pular OBAT+HCC pra colunas trivialmente tipadas — um play de latência não medido.
- **é**: medido bypass (classify+map+pack, 1-2 passadas) vs núcleo (`encode` single-col) e produção
  (`encode(dict, fallback=True)`, min de 4 candidatos), em **9 colunas low-card reais** (k≤16), mediana de
  9 runs. **Speedup mediano: 2.4× vs núcleo · 2.9× vs produção. RT-OK em todas.** Interno `B` (dict
  congelado) demonstrado (bool3 trio, domínio 0B).
- **será**: se valer, o nicho é **streaming (V2-J)** + payload-minúsculo; weld gated (owner + src/tcf).

## Resultado (`01-latencia-bypass.txt`)

Speedup vs núcleo por coluna: 1.2× (matriz_filial, k=2 trivial) a 3.8× (education, k=16, valores longos).
Mediana **2.4× (núcleo) / 2.9× (produção)**. Modesto mas real — o núcleo já é rápido em low-card (HCC
dedup), então o bypass não é 10×; é ~2-4×.

## Enquadramento honesto

- É **latência**, NÃO byte. O bypass emite bN (bit-packed) → o byte colapsa pós-brotli (gate D3); o valor
  é throughput/latência no nicho **terminal/streaming**.
- Modesto: 2.4× porque o núcleo já dedup low-card rápido. O ganho cresce com o comprimento dos valores
  (education 3.8× vs matriz_filial 1.2×).
- **A corrida especulativa** (owner) em batch = este *try-classifier-first*: o classificador (≈`analyze_column`)
  custa ≪ núcleo, então tentar-primeiro sequencial já colhe o ganho; as filas paralelas só importam em
  streaming.

## Nomenclatura (owner 2026-07-08) — não confundir largura física com código semântico

- **b1/b2/b4** (minúsculo) = LARGURA FÍSICA (1/2/4 bits, tile-de-byte). Reativo (domínio na coluna).
- **b3** = código reusado p/ "b2 + null" (trio, 2 bits). **b5/b6/b7** = tipos especiais (reservados).
- **B** (MAIÚSCULO) = bool com dict INTERNO congelado — não declara referência, usa a interna sempre.

## Arquivos

- `bypass_codec.py` — bypass reativo (b1/b2/b4) + interno (B) + INTERNAL registry.
- `run.py` — latência (mediana) + RT. **`python3 run.py`**.
- `artifacts/` — `00-resumo` · `01-latencia-bypass` · `02-interno-B`.

## Escopo

Dirty. NÃO toca `src/tcf`. Latência medida em batch; a formulação de filas do owner é o desenho streaming.
