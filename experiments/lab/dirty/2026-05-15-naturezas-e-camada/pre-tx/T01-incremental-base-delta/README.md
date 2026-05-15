# T01 — Incremental (base + delta) — dirty

**Estado**: aberto (primeira natureza, foco unico — 2026-05-15)
**Plano-mestre**: [`../../../../../tickets/META-TYPE-ENCODERS.md`](../../../../../tickets/META-TYPE-ENCODERS.md)
**Natureza**: incremental (cf. [`docs/theory/data-natures-taxonomy.md` §1](../../../../../docs/theory/data-natures-taxonomy.md))

## Pergunta cientifica

Para datasets onde linhas formam **serie numerica/temporal** (datas,
timestamps, IDs sequenciais), conseguimos reduzir bytes substituindo
cada valor por `(base, delta)` — onde `base` e' valor de referencia
e `delta` e' pequena diferenca codificada compactamente?

## Hipotese (a refinar conforme experimentos)

D11 (datetime-precisao) atualmente **70% vs csv** com TCF puro.
Hipotese inicial: com `base + delta` cai pra **<30%** (deltas
sao numeros pequenos codificaveis em poucos bytes; base e' constante).

## Principio metodologico

- Sub-experimentos **pequenos, descartaveis, refazaveis**. Nada aqui
  e' canonico; quebrar e reconstruir e' esperado.
- **RT byte-canonical obrigatorio**: encoder + decoder reproduzem
  input bit-a-bit. Sem RT, sub-experimento nao fecha.
- **Stress test** antes de fechar sub-experimento: dataset
  adversarial + favoravel.
- **Comparacao**: bytes vs TCF puro, vs csv + brotli (campeao do
  EXP-008), vs raw csv.
- **Nao tocar `src/tcf/`** ate' encoder estar solido. Trabalho
  fica aqui no dirty.

## Sub-perguntas a explorar (ordem de prioridade)

1. **Representacao do delta**: decimais? bytes raw? codigo Elias
   gamma? varint? — qual representa numeros pequenos mais compactamente?
2. **Granularidade**: deltas em segundos vs dias vs nanossegundos —
   depende do dataset.
3. **Base unica global vs reset periodico** (chunks)?
4. **Sinal de delta**: negativos permitidos? como representar?
5. **Detecao automatica vs manual**: encoder recebe "isto e'
   incremental" do usuario, ou deduz da serie?
6. **Composicao com templated**: encoder templated (futuro) extrai
   estrutura do formato data; encoder incremental opera nos slots
   numericos depois. Hoje so' explorar incremental isolado.
7. **Cabecalho/metadata**: como representar `(base, ...)` no output?
   Quanto custa em bytes?

## Datasets alvo

| Dataset | Foco em T01 | Razao |
|---|---|---|
| D11 datetime-precisao | **primario** | 13 linhas, todas mesma estrutura data, precisao crescente |
| D12 datetime-timezone | secundario | mais complexo, mas tem incremental forte |
| D6 poucos-em-ruido | secundario | timestamps em log lines |
| D10 datas-mundiais | **deixar pra depois** | 15 layouts diferentes — exige templated primeiro |

## Estrutura prevista de sub-experimentos

Cada sub-experimento e' um diretorio descartavel dentro deste T01.
Numeracao `NN-nome-curto/`. Espera-se **varias iteracoes**.

```
T01-incremental-base-delta/
├── README.md                          # este arquivo
├── 01-prova-conceito-D11/             # encoder simples, base+delta em segundos, so D11
├── 02-formato-delta/                  # comparar representacoes de delta
├── 03-stress-D12-tz/                  # adicionar timezone
├── 04-composicao-templated/           # combinar com templated (se necessario)
└── conclusoes_T01.md                  # registrado quando T01 fechar (vai pra ../../notas/ no final)
```

Ordem e numeros podem mudar conforme aprendizado. Sub-experimentos
podem ser **deletados** se virarem becos sem saida — historia
preservada em commits.

## Saidas esperadas ao fechar T01

1. **Encoder + decoder** funcional pra ao menos D11 com RT
   byte-canonical.
2. **Hipotese byte-reducao** confirmada ou explicitamente refutada
   (com dados).
3. **Lecoes pra metodologia** das proximas naturezas — o processo
   refinado aqui sera padronizado pras outras.
4. **Decisao registrada** sobre incremental:
   - Pre-tx separado (vira `src/tcf/pretx/incremental.py` ao weldar)
   - Ou candidato a embutir no OBAT (input pra Track 2 futuro)
   - Ou ambos (pre-tx + tambem detectavel pelo OBAT)
5. **Pista pra proxima natureza** — qual abrir depois? Como T01
   compoe (ou nao) com ela?

## Criterio de fechamento

- [ ] Pelo menos 1 sub-experimento com encoder/decoder funcional
- [ ] RT byte-canonical validado pra dataset primario (D11)
- [ ] Comparacao de bytes vs baseline (TCF puro, csv+brotli) registrada
- [ ] `conclusoes_T01.md` escrito em `../../notas/` (move-se quando fechar)
- [ ] Decisao sobre proxima natureza registrada no plano-mestre

## Conexoes

- [`../../README.md`](../../README.md) — entrada do dirty lab
- [`../../../../../tickets/META-TYPE-ENCODERS.md`](../../../../../tickets/META-TYPE-ENCODERS.md) — plano-mestre
- [`../../../../../docs/theory/data-natures-taxonomy.md`](../../../../../docs/theory/data-natures-taxonomy.md) — taxonomia das naturezas
- [`../../../../clean/EXP-008-compressao-comparada/`](../../../../clean/EXP-008-compressao-comparada/) — baseline atual de bytes
