---
title: LEVANTAMENTO — P4b (raiz generalizada) — PARA INSPEÇÃO E DECISÃO DO OWNER
type: report
status: aberta
created: 2026-07-16
related:
  - tickets/T-CODE-TCF8H-JSON-PARITY.md
  - experiments/lab/dirty/notas/p4-replevel-nroots-levantamento.md (revisão crítica: recomendação, não decisão)
  - experiments/lab/dirty/notas/p4a-atividade-levantamento.md (o incremento anterior)
  - tickets/T-API-BOUNDARY-CONTRACTS.md (contrato público)
  - tickets/T-FMT-OMIT-OR-DECLARE.md (vazios / registro-'0')
  - docs/adr/0033-hierarchical-codec-weld.md
---

# Levantamento — P4b (raiz generalizada). Para inspeção e DECISÃO do owner.

**[probatório + recomendação]** Levantamento, não plano de execução. Os fatos de §1–§2 são **medidos**
(executados contra o core em `2e0b222`); §3–§4 são **minha análise/recomendação**; §5 lista o que é
**decisão sua** — e hoje **nada disso está decidido**.

> **Proveniência, para não repetir o erro do P4a**: as restrições que circulam sobre P4b (envelope
> transparente, `root_kind` inequívoco, "a ordem de arrays é semântica e não é livre", a lista de 8
> formas) estão na seção *Revisão crítica independente* de `p4-replevel-nroots-levantamento.md`, que
> **você marcou** `[probatório→opinião; não é decisão do owner]`. No P4a elas viraram operativas
> porque **você adotou** o plano explicitamente. Para P4b **não houve adoção**: são recomendação em
> aberto. Este documento as trata assim.

## O que é P4b (e por que é ato separado)

P4a acrescentou um kind **interno** (`arr_arrays`) — invisível na fronteira. P4b muda a **entrada e a
saída públicas**: hoje `encode_hierarchical(records: list[dict]) -> str` e
`decode_hierarchical(tcf_text) -> list`. Raiz generalizada = a raiz pode ser qualquer valor JSON
(objeto único, array, escalar, `null`), não só uma lista de registros. É mudança de **contrato**, não
de estrutura interna — por isso gate e decisões distintos.

## 1. Estado MEDIDO hoje — a superfície de raiz é fail-loud completa

14 formas de raiz testadas contra o core. **Nenhuma é aceita: as 14 levantam `HierarchicalError`.**
Logo: **zero wire emitido, zero decode, zero corrupção silenciosa**. Não há dívida escondida aqui —
há uma funcionalidade ausente, declarada.

| forma de raiz | resultado | onde |
|---|---|---|
| `[]` · `{}` · `{"a":1}` · `42` · `"texto"` · `""` · `None` | `hierárquico espera uma lista NÃO-VAZIA de objetos (registros)` | `hierarchical.py:191-192` |
| `[1,2,3]` · `["a","b"]` · `[[1,2],[3]]` · `[None]` · `[1,{"a":2}]` | `hierárquico espera objetos (dict) em cada registro` | `hierarchical.py:193-194` |
| `[{}]` · `[{},{}]` | `nenhuma coluna derivável (registros sem campos) — nº de registros irrepresentável` | `hierarchical.py:304-307` |

Nota factual: `[1,{"a":2}]` (misto, que seria P5) **não** é rejeitado por P5 — morre antes, na guarda
genérica `:194`. A mensagem não distingue "misto" de "array de escalares".

## 2. A ambiguidade — byte-confirmada, não inferida

A rota óbvia ("embrulha a raiz numa lista sintética") é **provadamente lossy**. Medido:

| documento | rota | wire |
|---|---|---|
| raiz-objeto `{"a":"1"}` | embrulhar → `[{"a":"1"}]` | `#TCF.8Ha\n\\1\n` |
| dataset de 1 registro `[{"a":"1"}]` | direto | `#TCF.8Ha\n\\1\n` |

`w1 == w2` → **`True`**. Byte-idênticos. O decoder não tem como saber se desembrulha: **a informação
não existe no wire**. Qualquer raiz sintética sem discriminador perde o tipo da raiz — isto é fato
medido, não opinião.

**Não há discriminador de raiz hoje** (`hierarchical.py:58,313`): `MAGIC = "#TCF.8H"` e o meta vem
**direto** depois. Pela convenção do CLAUDE.md o `H` já é o discriminador — mas ele discrimina
**codec** (hierárquico), **não tipo de raiz**.

## 3. Minha análise: o gate de 8 formas decompõe em 3 problemas DISTINTOS

Este é o principal achado do levantamento. A lista `[]`/`[{}]`/`{}`/objeto único/array de
escalares/escalar/string vazia/`null` parece uma coisa só e **não é** — são três mecanismos, com
custos e riscos diferentes:

| # | problema | formas | o que exige | independente? |
|---|---|---|---|---|
| **A** | **Discriminação da raiz** | `{}`-único vs `[{…}]`-dataset; array na raiz | 1 bit/char de `root_kind` no wire | sim — resolve com §4 |
| **B** | **Contagem irrepresentável** | `[]`, `[{}]`, `[{},{}]` | o count vem de `len(1ª coluna)` (`:638-640`); **sem colunas não há onde contar** | **não** — é o `T-FMT-OMIT-OR-DECLARE` / registro-'0' (O-FMT-20), já registrado |
| **C** | **Raiz não-objeto** | `42`, `"x"`, `""`, `null`, `[1,2,3]` | a raiz carregar um VALOR que não é registro | parcialmente — precisa de A |

**Consequência prática**: **B não se resolve com `root_kind`.** `[{},{}]` = "dois registros sem
campos" precisa de um portador de contagem explícito — exatamente o mecanismo de vazios que já está
ticketado em outro lugar. Se P4b for tratado como um bloco único, ele **arrasta** uma decisão de
formato (vazios/schema-declare) que tem escopo próprio. Recomendo separar: **P4b = A + C**; B vai
para o ticket de vazios e os dois se encontram no gate.

Cruzamento com P5: `[1,2,3]` (homogêneo) é P4b puro; `[1,"a"]` é P4b **+** P5. A fronteira P5
continua valendo dentro da raiz.

## 4. Opções de discriminador (recomendação; a escolha é sua)

O princípio decisor do Ciclo 4 (O(1)/stream/partes separáveis) favorece ler o tipo de raiz **num
offset fixo, sem parsear o meta**. As três formas viáveis:

| opção | forma | custo | byte-compat `.8H` atual | leitura |
|---|---|---|---|---|
| **(1) char sempre presente** | `#TCF.8H<k><meta>` — `D`=dataset, `O`=objeto, `A`=array, `S`=escalar, `N`=null | +1 B **sempre** | **quebra** (re-pinar baselines) | O(1), offset fixo |
| **(2) char só quando ≠ dataset** | `#TCF.8H<meta>` = dataset (hoje); `#TCF.8H<sentinela><k><meta>` p/ o resto | 0 B no caso comum; +2 B no resto | **preserva** | O(1), 1 lookahead |
| **(3) campo no meta** | pseudo-campo de raiz dentro do meta | ~vários B | preserva | exige parsear meta — **conflita com O(1)** |

Descarto (3) pelo princípio do Ciclo 4. Entre (1) e (2):

- **(1)** é mais limpo e uniforme; custa 1 B em todo wire `.8H` e **re-pina** baselines — o que a
  política pré-1.0 (ADR-0024, git-as-compat) **permite explicitamente**.
- **(2)** custa 0 B no caso dominante (dataset) e preserva os wires atuais, mas cria dois caminhos —
  exatamente o tipo de "solda demais" que você pediu para evitar; e a sentinela precisa ser um char
  que **não pode iniciar um meta** (nome de campo vazio já é erro, e `,[]{}:#?\` são escapados em
  nomes — então há candidatos seguros, mas é regra sutil a documentar).

**Minha recomendação: (1)**, pela uniformidade e porque o custo (1 B) é ínfimo perto de ter dois
caminhos de parsing para sempre — e a política pré-1.0 cobre a re-pinagem. Mas o eixo "cada byte
conta em payload minúsculo" ([[project_byte_level_compression_focus]], O-FMT-15/16) é seu, e ele
empurra para (2). **Por isso a decisão é sua, não minha.**

O `root_kind` também compõe com `H-DISC-ACCEL-01` (discriminador como dica p/ blocos acelerados e
mimemagic): um char de raiz adjacente ao `H` é legível por fora sem parsear nada.

## 5. O que é DECISÃO SUA (nada disso está decidido)

1. **P4b entra no `.8`?** Pelo seu critério ("basear na capacidade de json que as pessoas já usam"),
   objeto-único e array-na-raiz são comuns; escalar/`null` na raiz são legais mas raros. Entra
   inteiro, ou só {objeto único, array na raiz, `[]`}?
2. **Escopo**: aceita separar **B** (contagem/vazios) para o ticket de vazios, como recomendo em §3?
3. **Discriminador**: opção (1), (2) ou outra? (Isto decide se re-pinamos baselines.)
4. **Contrato de API**: `decode` volta a devolver o tipo original da raiz — o que muda para quem hoje
   assume `list`? Uma API só (`encode_hierarchical`) ou porta separada para documento vs dataset?
5. **Terminologia**: adoto "raiz generalizada"/"array na raiz" e mantenho "N-raízes" só como nome
   histórico? (Recomendado na revisão crítica; não adotado por você ainda.)

## 6. Cobertura de teste hoje — 4 das 8 formas do gate

`tests/test_hierarchical_rt.py` tem **3 testes de raiz, todos negativos** (fail-loud), nenhum RT:
`test_p1_registros_sem_campos_fail_loud` (`[{}]`, `[]`), `test_p1_raiz_nao_lista_fail_loud` (`{"a":"1"}`),
`test_nao_dict_fail_loud` (`["nao","e","objeto"]`).

**Sem teste hoje**: `[{},{}]`, `{}` vazio, `42`, `""`, `None`, `[[1,2],[3]]`, `[None]`, `[1,{"a":2}]`,
`[1,2,3]`. Ou seja: mesmo mantendo P4b fora do `.8`, há **lacuna de fail-loud declarado** — barata de
fechar e independente da decisão de escopo.

## 7. Fronteira e o que NÃO foi medido

- **Custo em bytes de qualquer envelope/`root_kind`: NÃO MEDIDO** — não existe implementação a
  instrumentar. Os "+1 B"/"+2 B" de §4 são aritmética do formato proposto, **não medição**.
- **P5 union** segue fora (não usar "qualquer JSON" antes dele).
- **N:N / grafo** segue fora (`project_json_alvo_pratico_objetivo_amplo`: JSON é o alvo prático; a
  estrutura ampla é v1.0/v2.0).
- Nenhum dataset real-world aninhado no hub para medir raiz em massa (`T-SHAPER-NESTED-OUTPUT`).

`confianca: Alta` p/ §1–§2 (medido, reprodutível). `confianca: Média` p/ §3–§4 (análise minha; a
decomposição A/B/C é sólida, a escolha de discriminador depende de eixo que é seu).
