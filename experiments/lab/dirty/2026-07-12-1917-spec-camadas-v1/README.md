# 2026-07-12-1917-spec-camadas-v1

**data/hora**: 2026-07-12 19:17 · **versão**: v1 · **nome**: spec-camadas
**ticket**: T-SPEC-DEEPDIVE-08 §4-ter · **status**: probatório (dirty)

## Pergunta
O owner (2026-07-12) articulou o spec em **3 formas** (A entrada-total = nature hoje; B paralela
= núcleo trabalha e troca base-94 nas REFERÊNCIAS; C misto = limpa na entrada + troca na saída),
~6 camadas (limpeza·derivação·pré-forma·núcleo·troca-refs·saída). Em que grau cada camada dá
vantagem em CPF/CNPJ?

## Método
5 degraus (S1 masked → S2 clean → S3 clean+delta → S4 base94 absoluto=hoje → S5 delta→base94=misto),
medidos pelo pipeline REAL. **Cada degrau com RT end-to-end PROVADO**: original→transform→encode→
decode→untransform→reconstruído `==` original (assert). NENHUM byte sem RT verde (§RT).
4 regimes: CNPJ real ord/embaralhado (receita, não-PII), CPF sintético random/clustered (efêmero §2.3).

## Artefatos (a contra-prova de experimentação)
- `01-input-samples.txt` — o dado que entrou (CPF mascarado §2.3)
- `02-flow-debug.txt` — o NÚCLEO trabalhando (SideOutputs: modo, cadência, seq-RLE, OBAT, HCC)
- `03-output-blobs.txt` — input → blob (.tcf) → decode → reconstrução, por degrau
- `04-rt-counterproof.txt` — **RT 20/20 verde** (5 degraus × 4 regimes), o retorno ao dado original
- `05-ladder-bytes.txt` — a tabela de bytes (todos RT-válidos)

## Achados (ver result.md)
S5 (misto) é a única sempre-boa; CPF clustered→14B (delta vira RLE); máscara tem valor estrutural
(camadas não-monotônicas → escolha por-coluna). **Achado colateral: BUG-15** (literal `^`-líder
quebra RT em tcf/dict) — descoberto SÓ porque o lab exigiu RT end-to-end; usei alfabeto base-62
marker-safe pra medir o conceito sem o bug. O CEILING de produção depende do fix do BUG-15.
