---
title: PERFIL JSON-LIKE — reavaliação medida + as CONDIÇÕES para um parâmetro existir
type: report
status: aberta
created: 2026-07-17
related:
  - experiments/lab/dirty/notas/json-chave-repetida-levantamento.md (o estudo que originou)
  - experiments/lab/dirty/2026-07-17-0050-json-chave-repetida-semantica/
  - tickets/T-API-BOUNDARY-CONTRACTS.md
  - tickets/T-CODE-TCF8H-JSON-PARITY.md
  - tickets/T-STUDY-DATASETH-COMPLETE-SEMANTICS.md (contrato S0)
  - experiments/lab/dirty/notas/roadmap-hipoteses.md (H-PROFILE-JSONLIKE-01 · H-HIER-SIDEOUTPUTS-01)
---

# Perfil json-like: reavaliação medida + as condições para ter parâmetro

**[probatório + recomendação]** Pedido do owner (2026-07-17): *"warning para comportamento similar
ao json para essas condições. Se o TCF puder superar em condições para hierarquias além do json,
mais complexas, tem que setar. Acho que um default com um conjunto de comportamentos 'json-like'
é útil. Reavalie e emita as condições para ter parâmetro disso."*

§1 é medido (lab `2026-07-17-0050` + medições desta sessão). §2-§6 é análise/recomendação —
**nada decidido**.

## 1. A matriz REAVALIADA — "json-like" não é um eixo, são 4 categorias

Medido (CPython 3.13 `json` × `.8H` de hoje). A coluna que decide tudo: *o que "fazer igual ao
json" significaria aqui*.

### ✅ Paridade já existente (nada a fazer)
`\t` em valor · `\x00` em valor · int gigante (`10**30`) · `-0.0` · `0.1+0.2` (precisão) —
**TCF já faz idêntico ao json**, RT-OK nos dois.

### A — CAPACIDADE: o json faz, o TCF não (4). Aqui warning é a resposta ERRADA
| borda | json | `.8H` hoje | o certo |
|---|---|---|---|
| chave vazia `{"": "x"}` | RT-OK | `HierarchicalError: nome de campo vazio` | **implementar** (é JSON válido e comum) |
| `\n` em valor | RT-OK | **`ValueError` CRU** (herdado do flat) | implementar (já é [T-API-BOUNDARY-CONTRACTS](../../../../tickets/T-API-BOUNDARY-CONTRACTS.md)) + re-tipar |
| chave contendo `\n` | RT-OK | `HierarchicalError` (tipado) | implementar ou declarar fronteira |
| ordem de chaves em ragged | preserva por-registro | ordem do schema | decidir contrato (S6/P4b) |

Warning aqui seria "avisei que não sei fazer" — não é política, é lacuna. **Nenhuma vira parâmetro.**

### B — POLÍTICA de adaptador: a informação só existe FORA do core (1). Aqui warning é CERTO
| borda | json | `.8H` | onde |
|---|---|---|---|
| chave duplicada em texto | last-wins **calado** | inexpressível na API (o dict colapsa antes) | **adaptador** texto→DatasetH |

### C — DEFEITO do json: ele aceita e corrompe (5). Aqui json-like IMPORTA o bug
| borda | json (medido) | `.8H` hoje | por que copiar é ruim |
|---|---|---|---|
| `NaN` | emite `NaN` — **inválido por RFC 8259** (`allow_nan=True` é o default!); RT **DIVERGE** (`nan != nan`) | fail-loud tipado | quebra a identidade do DatasetH — restrição que o owner já declarou inegociável ([[H-HIER-SCALAR-01]]) |
| `+Infinity` | emite `Infinity` — **inválido por RFC**; outros parsers rejeitam | fail-loud tipado | produz `.tcf` que só o Python lê |
| `tuple` | vira `list`; RT **DIVERGE** (tipo não volta) | fail-loud tipado | perda de tipo calada |
| chave não-str `{1:'x','1':'y'}` | **EMITE duplicata** `{"1":"x","1":"y"}`; RT perde calado | rejeita (`TypeError` cru) | é o único caminho que gera a duplicata do §B — copiar = fabricar o problema |
| lone surrogate `"\ud800"` | `dumps`/`loads` RT "OK"… mas a string **não é UTF-8 transmissível** | `UnicodeEncodeError` CRU | RT que não sobrevive à transmissão |

**Nas 5, o TCF ser mais estrito que o json é FEATURE, não lacuna** — e em 2 (chave não-str,
surrogate) o erro está cru: consertar = **tipar a mensagem**, não afrouxar.

### D — ALÉM do json: o TCF pode mais (o "tem que setar" do owner)
`NaN`/`±Infinity` **tipados** (representar em vez de tolerar) · chave não-str com tipo preservado ·
ordem por-registro · o DatasetH inteiro (grafo/N:N, v1.0/v2.0). Já registrado: [[H-HIER-SCALAR-01]].

## 2. As CONDIÇÕES para um parâmetro existir (o teste pedido)

Cinco condições **necessárias**. Se qualquer uma falha, não é parâmetro — é outra coisa.

- **C1 · A informação está viva no ponto de decisão.**
  *Falsificador*: escreva o teste que distingue os dois modos **no ponto exato do parâmetro**. Se
  não consegue (a informação morreu antes), o parâmetro é fictício ali — ele mora onde a
  informação ainda existe. → é por isso que "duplicata" não pode ser flag de `encode_hierarchical`:
  o dict já colapsou.
- **C2 · Os dois modos são lossless — ou a perda é declarada E observável.**
  Um modo que perde calado não é perfil, é defeito com interruptor. Se perde, tem de **reportar o
  que** perdeu, e o **default nunca é o lossy**.
- **C3 · A escolha não muda a semântica do wire — se muda, é FORMATO, não flag.**
  *Falsificador*: o **mesmo** `.tcf` decodifica diferente conforme o parâmetro? Então é
  discriminador/versão (ou contrato+assinatura — [[H-CONTRACT-EXTERN-01]]), senão o wire deixa de
  ser auto-contido. Parâmetro de API só pode mudar **o que é aceito**, nunca **o que o wire significa**.
- **C4 · O default é decidível** — por doutrina agora, ou por medição depois ([[H-PROFILE-01]]).
  Parâmetro não é lugar de adiar decisão indefinidamente.
- **C5 · O fail-loud continua alcançável.** Afrouxar, sim; remover a capacidade de detectar, não.

> **Regra-mestra**: **parâmetro é para POLÍTICA** (o que fazer com algo que sei detectar) —
> **nunca para CAPACIDADE** (o que sei representar → implementar) **nem para CORREÇÃO** (o que sei
> que quebra → o estrito é o certo; o caminho é representar, categoria D).

## 3. O teste aplicado (veredito por borda)

| borda | C1 | C2 | C3 | C4 | C5 | veredito |
|---|:--:|:--:|:--:|:--:|:--:|---|
| chave duplicada (adaptador) | ✅ | ✅¹ | ✅ | ✅ | ✅ | **PARÂMETRO** (no adaptador, opt-in) |
| chave duplicada (core) | ❌ | — | — | — | — | inexistente (info morreu) |
| chave `""` · `\n` em valor/chave | ✅ | ✅ | ❌² | ✅ | ✅ | **CAPACIDADE** → implementar |
| ordem de chaves ragged | ✅ | ✅ | ❌² | ✅ | ✅ | **CONTRATO** (S6/P4b) |
| NaN/Inf/tuple/surrogate | ✅ | ❌³ | — | ✅ | — | **CORREÇÃO** → estrito fica; evoluir por D |
| chave não-str | ✅ | ❌³ | — | ✅ | — | **CORREÇÃO** → tipar erro; evoluir por D |
| NaN/Inf **tipados** (D) | ✅ | ✅ | ❌² | ✅ | ✅ | **FORMATO** (tag nova → versão) |

¹ com o desvio reportado · ² muda o wire → é formato/capacidade, não flag · ³ o modo json-like
perde calado (medido) → reprova C2.

**Resultado: das 10 bordas, exatamente 1 vira parâmetro** — e ela vive no adaptador, fora do core.

## 4. Condição 0 (BLOQUEANTE): o canal antes da política

**Medido: o `.8H` não tem canal de efeito colateral.** `encode_hierarchical(records) -> str`;
`side_outputs`/`SideOutputs` **não aparecem** em `hierarchical.py` (o flat tem:
`encode(..., side_outputs=)`). Ou seja, **hoje um "warning" no `.8H` não tem onde morar**.

Precedentes que já existem no projeto:
- `warnings.warn(..., UserWarning)` em `multi/core.py:327` (nome vazio → anônima) — é exatamente
  a forma "aceita mas sinaliza" que o owner descreve. Limite: `warnings` é global e dedupado por
  local ("once"), ruim para stream/massa.
- **SideOutputs** é a "ponte oficial de efeito colateral" (CLAUDE.md), e `anomaly_flags` /
  `format_inconsistencies` **já estão previstos** lá como expansão opt-in (CLAUDE.md:240).

→ **Pré-requisito de qualquer política com warning**: ligar SideOutputs no `.8H`
([[H-HIER-SIDEOUTPUTS-01]]). Estruturado, por-encode, zero-custo — `warnings.warn` só para a
ergonomia de topo, como no precedente.

## 5. O perfil json-like: onde ele cabe (a proposta do owner, refinada)

**Útil — como perfil do ADAPTADOR, não como modo do core.** O caso real (ingerir payload sujo de
terceiro, migração) existe e merece ferramenta:

```
adaptador:  texto JSON estrangeiro  ──[perfil]──>  DatasetH  ──> TCF core (sempre estrito)
            perfil "strict" (default) = P0 fail-loud  (= contrato S0 de hoje)
            perfil "json_like" (opt-in, por nome)     = reproduz o CPython json:
                 last-wins  ·  str(key)  ·  NaN/Inf aceitos  ·  tuple→list
                 …com CADA desvio reportado (o que, onde, quantos) — nunca calado
```

Por que fora do core: C1 (a informação só existe no texto) e C2 (todo desvio é lossy → precisa
ser reportado, e o core não deve carregar política de terceiro). O core continua com **um**
comportamento — o que torna os pins/gates/byte-canonicidade possíveis.

**Sobre "default json-like é útil"**: útil como **default DO ADAPTADOR quando o usuário pede
ingestão tolerante**, jamais como default do core — um core que aceita NaN emite `.tcf` cujo RT
quebra a identidade (`nan != nan`, medido), e o owner já declarou isso inegociável.

## 6. "Além do json" (D): quando setar

Pelo C3: se a capacidade extra **muda o wire**, ela é **formato** — discriminador/versão
(pré-1.0: ADR-0024 permite re-pinar), não flag de API. NaN/Inf tipados = tag nova → decisão de
formato ([[H-HIER-SCALAR-01]], já aberta). Um "setar" de API só cabe quando o wire é o mesmo e a
escolha é de política/perfil ([[H-PROFILE-01]]).

## 7. Recomendações

1. **Não criar modo json-like no core.** Das 10 bordas, 9 reprovam o teste (4 são capacidade, 5
   são correção). O core segue com um comportamento.
2. **Ligar SideOutputs no `.8H`** ([[H-HIER-SIDEOUTPUTS-01]]) — pré-requisito de qualquer warning,
   e já previsto na filosofia (zero-custo, "só detecta, NUNCA arruma").
3. **Tipar os 2 erros crus** medidos (chave não-str → `TypeError` cru; `\n` em valor → `ValueError`
   cru; surrogate → `UnicodeEncodeError` cru) — mensagem que ensina, sem afrouxar (`src/tcf` =
   aprovação).
4. **Fechar as 4 lacunas de capacidade (A)** pela fila normal do `.8` — chave `""` é a mais barata
   e é JSON válido comum.
5. **Perfil json-like = ticket de ADAPTADOR/gadget** (`scripts/`), com desvios reportados. Não é `.8`.
