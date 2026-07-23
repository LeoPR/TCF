# 2026-07-23-1548 — Telemetria decide modo por lote: FIXO-S (frágil) vs ADAPTATIVO (robusto)

Micro-lab EXPERIMENTAL (viabilidade). **Corrigido pós-verificação adversarial** (`wf_876541f7`): a
primeira versão reportou ganho −23%/−25% do batch de tamanho FIXO, mas era **artefato de alinhamento**
(os blocos dos dados tinham tamanho == S vencedor). Esta versão mede o caso desalinhado e acrescenta a
**segmentação adaptativa**. Continua [decisão passe-único `1533`](../2026-07-23-1533-decisao-rle-vs-denso-passe-unico/)
· [modo denso `0345`](../../../notas/2026-07/2026-07-23-0345-modo-denso-marcador-binarizacao.md).

## Contexto

O pipeline HOJE já escolhe o modo vencedor **por coluna** a partir de bytes "contados no processo,
não no fim" ([side_outputs.py:61-67](../../../../../src/tcf/side_outputs.py#L61-L67)). A pergunta era
se a mesma ideia decide **por lote** (RLE vs base64), e se lotes independentes abrem streaming/paralelismo.

## Evidência (corpo-vs-corpo; 6/6 RT + passe único ✅)

| caso | whole-best | batch-fix(melhor S) | Δfix | seg-adapt | Δadapt |
|---|---:|---:|---:|---:|---:|
| `het-align128` (bloco=128=S) | 344 | 264 | **−80** | 295 | −49 |
| `het-mis100` (bloco=100, desalinhado) | 336 | 384 | **+48** | 314 | **−22** |
| `het-mis77` | 320 | 300 | −20 | 320 | +0 |
| `half-100-156` | 44 | 48 | +4 | 40 | −4 |
| `noisy` (homogêneo) | 344 | 416 | **+72** | 350 | +6 |
| `alt` (homogêneo) | 344 | 416 | **+72** | 350 | +6 |

## Conclusão honesta

- **Batch de S FIXO é frágil/imprevisível**: ganha só quando a fronteira de regime cai em múltiplo de
  S (`het-align128`); no desalinhado (`het-mis100`, `half-100-156`) e no homogêneo PERDE — até **+72**.
  O −23% da v1 era artefato de bloco==S. **Fixo não é composição confiável.**
- **Segmentação ADAPTATIVA é robusta**: fronteira ONDE o regime vira (do run-list) → ganha em
  heterogêneo **independente de alinhamento** (−22 a −49), degenera pra ~neutro no homogêneo (+6, que
  é só o header `D<n>:` do único segmento). Sob o **FLOOR** que o TCF já usa (competir com `min(whole-
  dense, whole-rle)`, como a nature) vira **estritamente nunca-pior**.
- **Mecanismo válido pras duas**: decisão sai da telemetria, materializa só o vencedor, `reads/n==1.0`
  (passe único), RT self-contained no corpo do adaptativo (cada segmento declara seu count).

## Custo — enquadramento corrigido (grounding `wf_876541f7`)

"Custo de qualquer forma" cobre **só o run-list** da coluna (o `_rle_adjacente` já roda sobre o bool e
emite `*N|`). **NÃO é reuso puro**: (a) o **tamanho base64** é computação nova (o pipeline nunca calcula
bitmap denso), (b) a **segmentação** é passo novo (barato, O(runs), 1 acumulador), (c) o ponto de
seleção estilo `emitted_mode` é do **`.8M` multi-col** — o caminho **`.8H` single-col do bool não tem
um hoje**. Então: "adiciona um passo barato num ponto que ainda não existe", não "reusa número pronto".

## O que NÃO está provado

Bool `w=1`, sintético pequeno. Generalização bN/`w>1` e dados reais = hipótese seguinte. Nada é gate
pra soldar — é sinal de VIABILIDADE (o adaptativo, não o fixo) e de ONDE.

## Rodar / layout

```
python run.py     # 6 casos × 3 S · 0 falhas (RT + passe único)
```
`inputs/<caso>.json` · `outputs/<caso>.seg-adapt.tcfp` · `result.md`. Protótipos lab-local — não tocam `src/tcf`.
