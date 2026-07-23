# 2026-07-23-1832 — Reality-check: o regime de seg-adapt existe em dados REAIS?

Micro-lab. Escolha do owner: provamos viabilidade sintética; falta saber se **vale a pena**. O achado
do [lab 1759](../2026-07-23-1759-bn-lowcard-generaliza-e-compoe/): seg-adapt (misto RLE+base64) só
vence em dados **genuinamente mistos** (run + ruído) com w≥2. Este lab testa se esse regime **acontece
em coluna real** — reusando o kit [`pecas.py`](../2026-07-23-1759-bn-lowcard-generaliza-e-compoe/pecas.py).

**Dados**: adult-census (`Z:/tcf-data/external`, REAL, 48k linhas — amostra 10k). 9 colunas categóricas
low-card (k=2..41). Cada uma em 2 ordens: `as-is` (natural) e `sorted`.

## Resultado decisivo (18/18 RT + passe único ✅)

**seg-adapt vence em 0/9 as-is (0/18 no total).** Os dados reais são BIMODAIS, sem o regime misto:

| ordem | regime real | vencedor | seg-adapt |
|---|---|---|---|
| **as-is** | ruído por-coluna (`mean_run` 1.1–5.4) | whole-dense (rle p/ native-country) | perde (+7 a +795) |
| **sorted** | runny puro (`mean_run` 625–5000) | whole-rle (esmaga: education 6668→**102**) | perde por pouco (+2 a +43) |

O "misto genuíno" onde seg-adapt ganhava é uma faixa ESTREITA entre ruído e ordenado que **não ocorre
naturalmente** em adult-census.

## Conclusão

- **Segmentação DEFLACIONADA**: 0/18 vitórias em dados reais. O regime que a favorecia é artefato
  sintético. **Não vale soldar a máquina de segmentos.**
- **A decisão real é BIMODAL e já é o FLOOR**: ruído→dense(bN), clusterizado→rle, escolhido por coluna
  pelo `min()` que o TCF já tem. Onde há valor de weld é o par **{modo denso bN, modo rle} competindo
  no FLOOR** — não a segmentação.
- **A alavanca grande é ordenar+RLE**: education 6668→102 (65×) quando ordenado. Mas é whole-rle + uma
  decisão de SORT, não segmentação.
- **RESSALVA (não medido)**: este lab compara os protótipos ENTRE SI, não contra o encoder ATUAL do
  TCF (dict/V2-B base-94). Se bN-dense bate o dict de hoje é medição SEPARADA. Este reality-check só
  derruba a segmentação; não estabelece bN-dense como ganho vs o TCF vigente.

## Valor do método

Foi o reality-check que evitou soldar algo inútil (segmentação parecia promissora no sintético). Confirma
[[metodo-lab-verificacao-adversarial]]: medir o caso real/adversarial, não só o favorável.

## Rodar / layout

```
python run.py     # 9 colunas × 2 ordens · 0 falhas · seg-adapt vence as-is em 0/9
```
`outputs/education.as-is.seg-adapt.tcfp` (1 wire de exemplo) · `result.md`. Lê `Z:/tcf-data` (real,
nunca baixa). Kit reusado do lab 1759. Não toca `src/tcf`.
