# Escala de verificação (E0–E5) e o fechamento do bN

**2026-08-07 · decisão de processo do owner**

> *"Prefiro fazer o código ingênuo, que é muito mais rápido, e fazer o fluxo encode↔decode,
> ou seja, ir fechando os bugs óbvios onde um faz e o outro não desfaz. (…) A última escala
> é o código ter sido mexido por um homem no meio. Nada é rígido, mas é bom separar as
> escalas no que é o foco do `.8` e do `.9`."*

O alerta que originou isto: eu vinha tratando "verificação" como uma coisa só, e defendendo
checagem cara com argumento de CPU (*"custa 0,17%"*) quando o critério certo era **se o modo
de falha está no modelo previsto**.

---

## A escala

| nível | o que é | custo no caminho feliz | onde mora |
|---|---|---|---|
| **E0** — ingênuo | nenhuma verificação; aposta no caminho feliz | zero | sempre o ponto de partida |
| **E1** — round-trip | `decode(encode(x)) == x`, com tipo, sinal e comprimento | zero (é teste) | **`.8` — o coração** |
| **E2** — assimetria | o decode desfaz **exatamente** o que o encode fez, nem mais nem menos | zero (é teste) | **`.8` — obrigatório** |
| **E3** — fail-loud barato | o ramo de falha já existe; trocar comportamento indefinido por `raise` claro | **zero** — só executa quando já deu errado | **`.8` — de graça, fazer** |
| **E4** — canonicidade | uma entrada → um wire; um wire → um significado | 1 comparação por unidade | `.8` quando barato; **`.9` sistemático** |
| **E5** — adulteração | assume adversário, corrupção de meio, wire escrito à mão | O(n) + superfície de código | **`.9` / opt-in** — é o "homem no meio" |

### Por que E1/E2 são o coração, e não retórica

Levantamento de **alcançabilidade** dos bugs reais do ciclo — todos catastróficos, todos
silenciosos:

| bug | nível | alcançável por `encode→decode`? |
|---|---|---|
| `_grafa` não-injetiva (`"0"` × `None`) | E2 | **sim** — corrompia pela API pública |
| `rstrip("\n")` comendo a linha vazia final | E2 | **sim** — `['a','b','']` perdia valor |
| `_opaca` cega à polaridade | E2 | **sim** — `"0"` voltava `None` |
| FLOOR ignorando o próprio prefixo | E1 | **sim** — o wire crescia |
| cabeçalho aceitando `0a`/`0x`/PEP-515/sinal | E4 | não |
| conteúdo depois do bloco de bits | E5 | não |

**Quatro de seis eram E1/E2, e são exatamente os que corrompiam dados de verdade.** Os dois
que só o unicórnio alcança não corrompiam nada em uso real.

Conclusão prática: **orçamento de auditoria vai pra round-trip e assimetria**, não pra wire
escrito à mão. A auditoria que rodou hoje tinha 1 lente de 5 dedicada a wire adulterado —
má alocação, e foi minha.

### A ressalva que o próprio `malloc` faz

O `malloc` não pré-verifica o heap — mas devolve `NULL`, não um ponteiro lixo. Ele não
*checa preventivamente*; ele *falha corretamente*. É por isso que **E3 fica no `.8`**: custa
zero no caminho feliz e é a diferença entre bug achado em 10 segundos e bug achado em 6
meses.

### Por que E4 não é a mesma coisa que E5

E5 defende contra alguém. **E4 define o formato.** Se cinco grafias decodificam pro mesmo
valor, isso não é vulnerabilidade — é ambiguidade de especificação, e ela cobra o preço no
dia em que houver uma segunda implementação. O `1.0` fecha em **Rust**: nesse dia o wire
deixa de ser canal interno e vira o contrato entre duas implementações.

Isso não torna E4 urgente no `.8`. Torna E4 **barato agora e caro depois** — o que é
argumento pra fazer o que é trivial e adiar o resto, não pra fazer tudo.

---

## As checagens do bN, classificadas

Todas as verificações existentes hoje na família, no nível a que pertencem:

| checagem | onde | nível |
|---|---|---|
| corpo ausente após o cabeçalho | `decode_bn` | E3 |
| largura fora de 1..8 | `decode_bn` | E3 |
| contagem não-hexadecimal | `decode_bn` | E3 |
| **contagem não-canônica** (`f"{n:x}" != nhex`) | `decode_bn` | **E4** |
| marcador `=` ausente | `decode_bn` | E3 (o parser precisa dele) |
| **conteúdo depois do bloco de bits** | `decode_bn` | **E5** |
| domínio vazio | `decode_bn` | E3 |
| domínio maior que `2^w` | `decode_bn` | E3 |
| índice fora do domínio | `decode_bn` | E3 |
| **todo slot referenciado** | `decode_bn` | **E5** |
| b64 `validate=True` | `valida_payload_b64` | E3 |
| **b64 re-codifica e compara** | `valida_payload_b64` | **E4** (grafia dupla dos mesmos bytes) |
| **b64 tamanho exato** | `valida_payload_b64` | **E5** (truncamento/extensão) |
| valor fora do domínio numérico | `_cast_tipo` | E3 |
| NaN/Inf recusado | `_cast_tipo` | E4 (simetria com o encode) |
| **grafia numérica não-canônica** (`str(v) != s`) | `_cast_tipo` | **E4** |
| `b4`/`b8` reservado | `_decode_denso` | E3 |
| símbolo 3 fora do ternário `b2` | `_decode_denso` | E3 |

**Placar: 10 em E3, 4 em E4, 3 em E5.**

As três de **E5** — conteúdo depois dos bits, todo-slot-referenciado, tamanho exato do
payload — são as únicas que assumem o homem no meio. Ficam **registradas como candidatas a
knob no `.9`**. Nenhuma sai agora: mexer nelas é churn, e churn no `.8` é o oposto do que
essa decisão quer.

---

## Fechamento do bN — a lista finita

O ponto do owner: *"concluir o máximo pra gente seguir, senão sempre vamos achar algo pra
fazer e nunca sairemos pro `.9`"*.

### Fechado (existe, funciona, tem teste)

| item | estado |
|---|---|
| bN modo `B` | emitido · rota flat e rota tipada |
| bN modo `C` | decodável, não emitido (decodável-não-emitido é precedente aceito) |
| denso `b1` / `b2` | emitidos · domínio implícito congelado |
| `b4`/`b8` | reservados, fail-loud |
| lazy `bB` | emitido |
| **tipado `nB`** | **soldado 2026-08-07** — era o último buraco |
| tag `s` | decodável; string já pega bN pela rota flat |
| slot nulo | em todas as facetas |
| polaridade × bN | compõem (camada de borda) |
| OBAT/RLE dentro do domínio | compõe sem código novo |
| larguras `w = ceil(log2(k))`, 1..8 | tabela gerada do código |

**Cobertura**: 1192 testes na suite · 252 na família · EXP-016 com 72 casos e 0 falhas.

### Fechado depois da nota (registro)

1. ~~**modo `B` × `C`**~~ — **não era pendência.** Correção do owner (2026-08-07): os dois
   modos existem, são duas trocas conhecidas, `B` é stream-friendly e é o default, `C` entra
   só quando declarado. Estava decidido há tempo; eu é que tratei escolha feita como item
   aberto. O que resta é o **opt-in de emissão** (`T-BN-LOTE`, `.9`) — esboço de flag em
   [`flags-modo-bn-e-perfis-macro`](2026-08-07-flags-modo-bn-e-perfis-macro.md).
2. ~~**Triagem da auditoria**~~ — **feita**: 9 achados → 6 distintos, **zero alcançável por
   `encode→decode`**. Os 2 do meu weld (comentário errado, rótulo de erro) foram aplicados;
   os 4 pré-existentes são E4/E5 e ficaram registrados.
   Ver [triagem](2026-08-07-triagem-auditoria-nB-pela-escala.md).

**Nada em aberto no bN.**

### Explicitamente `.9` (não abrir agora)

`T-BN-LARGURA-VARIAVEL` · `T-DENSO-PADDING` · `T-B64-BITS-MORTOS` · `T-FLOOR-MULTIVETOR` ·
`T-BN-LOTE` · `T-BN-GZIP` · `T-ONLINE-NESS-BENCH` · `T-ERRO-SET-ORDEM` · as 3 checagens E5.

### Fora do escopo "bN", mesmo parecendo perto

`T-BN-MULTICOL` — a rota multi-col já tem mecanismo pra baixa cardinalidade (V2-B, dicionário
por column-chunk, ADR-0025). Levar o bN pra lá é **otimização comparativa**, não buraco de
existência. Fica `.9`.

---

## O que vem depois do bN

O owner: *"a gente 'fingiu' mexer nos outros tipos, mas nosso foco foi na estrutura bN e só
enfiamos outros tipos pra ver o comportamento"*.

Procede, e o EXP-016 mostra isso: a família **F8 tipos** tem 8 casos e todos existem pra
exercer a *estrutura* (int, float, `-0.0`, misto, int grande) — nenhum explora o **tipo**
como assunto próprio (data, CPF, decimal, moeda, timestamp, duração). O
`dom-datas-incrementais` é a amostra do que aparece quando se olha de verdade: 3 datas em
~20 B de domínio, o OBAT comprimindo dentro do bloco do bN, sem uma linha nova.

Isso é o **próximo trabalho**, não uma pendência do bN.
