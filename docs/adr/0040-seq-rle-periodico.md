# ADR-0040 — seq-RLE periódico: o delta que CICLA entre linhas

- **Status**: proposto (2026-08-09) — **aguarda aprovação de weld do owner**
- **Escopo**: corpo de coluna (`compact_body` / `expand_seq_marker` em
  `src/tcf/composicional/hcc_seqrle.py`). Vale para **qualquer coluna numérica**, em
  todas as rotas que passam pelo corpo (flat, `.8M`, spec).
- **Interage com**: ADR-0011 (seq-RLE canônico), ADR-0016 (multi-delta per-run),
  ADR-0024 (baselines re-pináveis), ADR-0035 (polaridade), ADR-0036 (bN)
- **Origem**: ideia do owner, anterior à rodada de data (*"tinha pensado nisso antes mas
  não tive oportunidade de testar completamente"*), confirmada como candidata na triagem
  [`0024`](../../experiments/lab/dirty/2026-08/2026-08-09/2026-08-09-0024-data-hipoteses-restantes/result.md)
  e medida no lab [`0042`](../../experiments/lab/dirty/2026-08/2026-08-09/2026-08-09-0042-data-alvo-delta/result.md)

## Contexto

O seq-RLE de hoje come **delta uniforme entre linhas** (`*N+d|`). Duas cadências muito
comuns não são uniformes:

| regime | delta entre linhas | hoje |
|---|---|---|
| dias úteis | `1,3,1,1,1` repetindo | quebra a cada 5 linhas |
| ids por turno / lote | `10,10,10,50` | quebra a cada 4 |
| quinzenal, mensal | `14,17,14,16…` | quebra a cada 2 |

Não é caso de nicho: **dias úteis é o calendário de negócio**. Uma coluna de 600 dias
úteis custa **1590 B** com o spec de data; a mesma coluna diária custa 32 B.

O `*N+d1,d2,…|` do ADR-0016 **não** resolve isto — ele é per-**run** dentro da *mesma*
linha (prefixo invariante + sufixo cadenciado, tipo IP), não per-**linha**.

## Decisão

Marcador novo: **`*N~d1,…,dp|template`** — linha `k+1` = linha `k` deslocada por
`d[k mod p]`.

```
600 dias úteis, coluna inteira:     *600~1,3,1,1,1|\739617
```

**O ciclo paga UMA vez.** É a propriedade que separa este mecanismo de todos os outros
candidatos: com `n = 6000` o wire cresce **um byte** (o contador), enquanto qualquer
alternativa por-valor cresce com `n`.

### O caractere `~` é escolha reversível, não estrutura

Os marcadores do TCF são abstratos por dentro; o caractere é a *saída*. `~` já é operador
composicional em outro contexto, e a vírgula já é do ADR-0016 — não houve colisão em
teste (§Evidência), e **se colidir, troca-se antes do 1.0** (decisão do owner, 2026-08-09;
ADR-0024 já torna baselines re-pináveis).

### Escopo do primeiro weld: um run de escape-digit por linha

Pares com **mais de um** run (o território do ADR-0016) ficam de fora. Periódico ×
multi-run é produto cruzado das duas gramáticas e não tem caso medido que o justifique.
Registrado, não feito.

## As duas guardas — sem elas o mecanismo REGRIDE

Medidas no `design_probe.py`; sem cada uma, o placar piora:

1. **Padrão uniforme disfarçado.** `*600~1,1|` é `*600+1|` escrito com mais bytes. Sem
   rejeitar `len(set(pad)) == 1`, o diário piorava **32 → 34 B**.
2. **FLOOR contra o baseline que o encoder emitiria.** Comparar o candidato periódico com
   o corpo **cru** o fazia "vencer" e piorar **4 de 8** casos (ruído alta-cardinalidade
   203 → 253 B) — ele ganhava do cru e perdia do compactado. O FLOOR é
   `min(cru, compactado_de_hoje, periódico)`.

> A guarda 2 é a **terceira ocorrência** da mesma classe neste projeto — comparar com um
> baseline que o encoder não emitiria (antes: `T-BN-TIPADO`, e o FLOOR da nature em
> 2026-08-08). Vale como regra, não como caso.

**Desempate**: o critério de hoje prefere o **compactado** no empate
(`compactado if len(compactado) <= len(body_text)`). O `min()` do Python devolve o
*primeiro* mínimo, então a ordem dos candidatos é load-bearing para byte-canonicidade —
o weld deve preservar a preferência atual em empates.

## Onde o mecanismo mora — e por que o lugar importa

**Estender `expand_seq_marker`, deixando o laço de `decode` intocado.** Não é preferência
de estilo: é o que preserva o teto de memória.

O laço de `HCCSeqRLE.decode` pré-checa o contador **antes** de materializar
(`_contador_declarado`, que já lê `*2000000~1,2|` corretamente — verificado). Medido:

| colocação | bomba `*2000000~1,2\|` com `max_length=10` |
|---|---|
| expansão em passe separado (1º protótipo) | rejeita **em 2,473 s**, depois de materializar 2 M strings |
| dentro de `expand_seq_marker` (**decisão**) | rejeita **em 0,0000 s**, antes de materializar |

O marcador antigo rejeita em 0,0015 s. A colocação certa é **mais barata de escrever e
mais segura**; a errada passa nos testes funcionais e deixa a bomba de pé.

## Evidência

Lab [`0042`](../../experiments/lab/dirty/2026-08/2026-08-09/2026-08-09-0042-data-alvo-delta/),
sonda `design_probe.py` (subclasse + monkeypatch de `tcf.encoder/decoder.HCCSeqRLE` —
`src/tcf` intocado, `encode`/`decode` **reais**):

| caso | hoje | com periódico | |
|---|---:|---:|---|
| dias úteis n=600 | 1590 | **40** | 39,8× |
| dias úteis n=6000 | 15630 | **41** | 381× |
| ids de turno (não-data, sem nature) | 1959 | **32** | 61× |
| úteis + feriado mensal | 1889 | 677 | 2,8× |
| diário · semanal · texto · ruído alta-card | — | **byte-idêntico** | — |

**Gates byte-canonical, com a camada LIGADA:**

| | congelado | com periódico |
|---|---:|---:|
| D1-D9 sintéticos | 1545 | **1545** ✔ |
| real-world (retail ×2 + lineitem) | 89430 | **89430** ✔ |
| **suíte inteira** | 1199 passed | **1199 passed** ✔ |

**E3**: o decoder de hoje diante do wire novo **falha alto**
(`contador RLE invalido: '600~1,3,1,1,1'`) — nunca devolve dado errado calado.
**E1 adversarial**: valores que *imitam* o marcador (`"*600~1,3,1,1,1|739617"`,
`"*3~1,2|z"`, `"a|b"`) fazem round-trip — a heurística de separador do ADR-0007 protege.

## Consequências

**A favor**

- Ganho de ordem de grandeza num regime comum, e **`O(1)` em `n`** — nenhum outro
  candidato desta família tem isso.
- Vale para qualquer coluna numérica (ids, contadores, ordinais), não só data: o ganho de
  61× apareceu numa coluna que não passa por nature nenhuma.
- Um arquivo, encode e decode espelhados; `_contador_declarado` e o FLOOR por corpo já
  existem e não mudam.

**Contra / custos**

- É **format change** (`#TCF.8`): wire novo não é legível por decoder anterior — mas
  falha alto, não corrompe.
- O detector varre períodos `p ∈ [2, MAXP]` por cadeia; custo de encode a medir sob o
  `T-GATES-ANTES` (o FLOOR já é o gargalo conhecido, 58% do encode).
- `MAXP = 24` é limite arbitrário (cobre mensal=12 e quinzenal-ano=24). Sem caso medido
  acima disso.

**Não decidido aqui**

- Periódico × multi-run (ADR-0016) — registrado, fora do escopo.
- Trocar `~` se aparecer colisão — antes do 1.0.

## Alternativa considerada e rejeitada

**Forma-lista** (1 ciclo só: `*25~d1,…,d24|` = lista literal de deltas). É o transform de
coluna expresso em gramática, e **perde dele**: 1825 B contra 644 B do delta-coluna no
espalhado, porque o marcador paga ~3 chars por delta e o bN paga 2–5 bits. Pior, com a
forma-lista liberada o greedy prefere listas grandes que destroem runs periódicos
melhores (feriado-mensal: 904 B na forma livre contra 649 B na estrita). Daí a exigência
de **≥ 2 ciclos completos**.

O **transform de coluna** (delta-coluna) continua de pé como mecanismo *complementar* —
ganha onde o ciclo não é exato (mensal 349 B, espalhado-ordenado 644 B, robusto a ruído).
Mas é mudança de **protocolo** (contrato que as 4 specs implementam + decoder + registry)
e depende do `T-NATURE-CANDIDATO-BN`. Ordem: este ADR primeiro.
