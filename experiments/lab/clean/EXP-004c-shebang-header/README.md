# EXP-004c — Header shebang `#TCF.5 SRDM`

## Hipotese

Sintaxe `# TCF v0.5` repete elementos posicionalmente fixos. Formato
shebang (`#TCF.5`, sem espaco, sem `v`) elimina **4 bytes por arquivo**
sem perda informacional. Para datasets pequenos, eh ganho substancial.

## Mudanca

| Variante | Header linha 1 | Bytes |
|----------|----------------|------:|
| **A** verbose | `# TCF v0.5 SRDM` | 15 |
| **B** mid (sort compact) | `# TCF v0.5 SRDM` | 15 |
| **C** shebang | `#TCF.5 SRDM` | **11** |

Diferenca C vs A: -4B no header (sempre); ganho relativo varia conforme
tamanho do payload.

## Regras de versionamento (consolidado)

| Semver | Header | Bytes | Comentario |
|--------|--------|------:|------------|
| 0.5 | `#TCF.5` | 6 | major 0 omitido |
| 0.8 | `#TCF.8` | 6 | idem |
| 1.0 | `#TCF1` | 5 | minor 0 omitido |
| 1.3 | `#TCF1.3` | 7 | major.minor explicito |
| 2.0 | `#TCF2` | 5 | minor 0 omitido |
| 2.10 | `#TCF2.10` | 8 | major.minor longos |

Ver [docs/workbench/research-notes/2026-05-09-formato-header-shebang.md](../../../../docs/workbench/research-notes/2026-05-09-formato-header-shebang.md).

## Resultados

### Tabela completa

| Cenario | rows | A | B | C | C vs A | C vs B | A+gz | C+gz | C+gz vs A+gz |
|---------|----:|--:|--:|--:|------:|------:|-----:|-----:|--------------:|
| S1 simple-strings | 6 | 112 | 93 | **89** | **-20.5%** | -4.3% | 116 | 105 | -9.5% |
| S2 with-int-col | 6 | 129 | 110 | **106** | **-17.8%** | -3.6% | 129 | 117 | -9.3% |
| S3 categorical-500 | 500 | 2452 | 2428 | **2424** | -1.1% | -0.2% | 1226 | 1207 | -1.5% |
| S4 tpch-supplier-100 | 100 | 2371 | 2357 | **2353** | -0.8% | -0.2% | 564 | 550 | -2.5% |
| **medias** | | | | | **-10.07%** | **-2.07%** | | | **-5.70%** |

### Headers reais

```
S1 — A:  '# TCF v0.5 SRDM\n# sort: comprador, produto\n'  → 41B
     B:  '# TCF v0.5 SRDM\n# s:1,2\n'                      → 22B (-46%)
     C:  '#TCF.5 SRDM\n# s:1,2\n'                          → 18B (-56% vs A)

S3 — A:  '# TCF v0.5 SRDM\n# sort: cidade, status, categoria\n'  → 48B
     B:  '# TCF v0.5 SRDM\n# s:4,2,3\n'                            → 24B (-50%)
     C:  '#TCF.5 SRDM\n# s:4,2,3\n'                                → 20B (-58% vs A)
```

Em headers isolados, ganho **-58%** consistente — vai escalar quando
chunks adicionarem mais metadata por bloco.

## Roundtrip

OK em todos os 4 cenarios. Decoder so aceita sintaxe shebang nesta
versao (sem retrocompat — encoder regera arquivos antigos se preciso).

## Achados

**1. C vence B em todos os cenarios** — sem custo computacional, so
mudanca de string. Variante C eh **estritamente melhor**.

**2. Ganho medio -10% no texto / -5.7% apos gzip** sobre verbose
original (A).

**3. Em micro datasets eh dominante** (-17 a -20% em S1/S2).

**4. Em datasets grandes eh marginal** (-0.8 a -1.1%) mas grátis.

**5. Apos gzip o ganho nao zera** — bytes que nao foram emitidos
nao podem ser comprimidos.

## Decisao consolidada

**C eh o default a partir desta data (2026-05-09).**

- Encoder so emite shebang
- Decoder so aceita shebang
- Sem retrocompat com v0.4 ou versoes intermediarias
- Documentado em research-notes para registro durable

## Arquivos produzidos

```
outputs/
  S1-simple-strings/
    source.csv
    tcf-A-verbose.tcf   (referencia historica)
    tcf-B-mid.tcf       (referencia historica)
    tcf-C-shebang.tcf   (formato atual)
  S2-with-int-col/
    ...
  S3-categorical-500/
    ...
  S4-tpch-supplier-100/
    ...
  results.json
```

## Codigo

`run.py` reusa encoder/decoder de `src/tcf/v05/`. Variantes A e B sao
**simuladas** (substituicao de header) apenas para fins comparativos.
Em producao, so existe C.

## Status

- [x] Formato shebang implementado em encoder.py + decoder.py
- [x] Testes 6/6 passando com nova sintaxe
- [x] Roundtrip OK em 4 cenarios
- [x] Comparativo A/B/C com estatisticas
- [x] Documentacao durable em research-notes/2026-05-09-formato-header-shebang.md
- [x] C como default permanente

## Reflexao para proximas iteracoes

Ainda em **lab experimental**. Cada bit que conseguimos espremer
agora reduz o trabalho quando virar prototipo formal — depois disso
vamos mexer cada vez menos nesses detalhes.

Documentar essas decisoes pequenas (como esta) garante que nao se
percam. Cada uma soma poucos bytes mas a soma de todas eh substancial
em datasets pequenos onde TCF tradicionalmente perdia para CSV.
