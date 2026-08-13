# Resposta aos poréns — o que se sustenta, o que já caiu, e o que ele não viu

**Data**: 2026-08-13
**Tipo**: registro de sessão única (crítica da avaliação
[`2026-08-13-0148-parens-avaliacao-semana`](2026-08-13-0148-parens-avaliacao-semana.md))
**Método**: cada porém testado com `encode`/`decode` reais antes de opinar. Nada aceito
por plausibilidade.

---

## Veredito por item

| # | porém | veredito |
|---|---|---|
| 1a | o compartilhamento do array de deltas entrou no weld? | **já resolvido** — entrou |
| 1b | os +35% são custo fixo do default? | **válido, e corrige o MEU ADR**: no corpus real é **1,37%** |
| 2 | desempate por ordem de argumento é frágil | **válido — e é o MESMO item que o #6** |
| 3 | a classe do bug do view não está fechada | **premissa errada, ação certa** |
| 4 | ADR-0041 tem prazo | válido, e ele **subdimensiona** o ADR |
| 5 | "guard vira amplificador" sem casa fixa | **válido, sem ressalva** |
| 6 | `T-FLOOR-POS-POLARIDADE` é prioridade escondida | **válido, e MAIS forte do que ele argumentou** |

---

## 1. CPU do periódico — ele fez a pergunta certa, e a resposta corrige o ADR-0040

**1a está resolvido**: o compartilhamento entrou. `encode` computa `pares = deltas_pares(body_lines)`
uma vez e passa para `compact_body`, `detect_periodic_runs` e `compact_body_periodico`.
A afirmação do ADR ("é parte do weld") é verdadeira.

**1b é o achado, e ele é contra mim.** A pergunta *"os +35% são custo fixo do default ou
do perfil latência?"* tem resposta medida — e mostra que **o número que publiquei no
ADR-0040 é o pior caso apresentado como se fosse o custo**:

| medição | contexto | custo |
|---|---|---|
| ADR-0040 (publicado) | série uniforme longa, n=2400 — o caso **adversarial**: o detector varre tudo e nunca acha | **+35%** |
| corpus real (agora) | **138 colunas** (samples + synthetic + hub), 266 chamadas | **1,37%** |

O periódico ativou em **4 de 138** colunas. O "+35%" é o custo de um formato de dado
construído para maltratar o detector, não o custo de rodar o detector.

**Correção aplicada ao ADR-0040** — não porque o +35% era falso (era medido e é real no
seu regime), mas porque publicado sozinho ele **descreve o mecanismo errado**.

Isso também dissolve a pergunta "fixo ou de perfil?": a 1,37% não há o que gatear. Se um
dia houver perfil, o eixo dele é outro (o forfeit de bN medido em `2026-08-12`, +4,73%),
não o detector.

## 2 + 6 — **o reviewer separou em dois o que é um só**

Ele tratou o desempate (#2) como fragilidade de estilo e o FLOOR-pós-polaridade (#6) como
dívida do core. Medindo, **são o mesmo fenômeno**: o `min()` decide no corpo canônico, e
o empate é exatamente onde a grandeza final (pós-polaridade) pode divergir.

**E o #6 é mais forte do que ele argumentou.** Ele escreveu "as rotas existentes *podem*
estar escolhendo com régua errada". Não é "podem" — **estão**:

| corpus | inversões | no empate | fora do empate |
|---|---:|---:|---:|
| 300 sintéticas | 2 | 2 | 0 |
| **77 colunas reais** | **6 (7,8%)** | 2 | **4** |

Piores casos reais: `online-retail/UnitPrice` **349 → 356 B (perde 7 B, 2,0%)`;
`tpch/l_quantity` 2 B; `wine-quality/chlorides` 2 B (empate).

O item que ele pôs em **3º** é o único que descreve dinheiro perdido **no wire que sai
hoje**, sem depender de nenhum weld pendente. A medição sustenta subir.

**Consequência de desenho**: pinar o desempate na suíte (a ação do #2) trata o sintoma;
a cura é o `min()` medir a grandeza que embarca. Fazer os dois na mesma mexida.

## 3 — a suspeita não se confirma, mas a ação continua boa (por outro motivo)

Ele suspeitou que a matriz de testes não cobre `nature × modo` e que **haveria mais
bugs**. Varri o produto cruzado:

| modo do corpo | header | where | group_count | select |
|---|---|---|---|---|
| dict (k moderado) | `#TCF.8M@1c7=dt:data-iso,@v` | ok | ok | ok |
| run sequencial | `#TCF.8Mf=dt:data-iso,@v` | ok | ok | ok |
| run **periódico** | `#TCF.8M17=dt:data-iso,@v` | ok | ok | ok |
| raw (alta card) | `#TCF.8Mf=dt:data-iso,@v` | ok | ok | ok |

Mais CPF em dict (200/200) e `group_ranges`/`agg_by` (chaves revertidas). **Zero bugs
novos** — porque o fix não remendou o segundo caminho, criou **fonte única**: só existem
dois leitores (`_col`, que cobre os 4 modos, e `_dict_parts`), e ambos passam por
`_reverte_nature`.

Ou seja: **a classe está fechada por construção**, não por sorte. Mas a ação dele
continua valendo por um motivo diferente do que ele deu: pinar o sweep protege contra um
**terceiro leitor futuro** — não contra bug existente.

## 4 — ele subdimensiona o ADR-0041

Ele o reduz a *"decisão `dt` vs `dtiso` está medida"*. O ADR tem **quatro** decisões, e a
terceira é **obrigatória**: a resolução passa a comparar `wire_id` em vez de `name` —
sem ela, o rename **quebra** a declaração out-of-band (medido: `decode(wire ':dt',
nature=SPEC_DATA_ISO)` → erro de divergência). Não é ADR de nomenclatura; é ADR de
separação de planos, e o nome é a consequência visível.

Ele também não menciona a decisão 4 (modo sem-carimbo, **32 → 15 B**), que é o maior
ganho unitário da rodada e está quebrado nas duas pontas.

## 5 — válido, sem ressalva

Duas ocorrências na semana, mesma forma. A lição está em prosa no ADR-0040 e deveria ser
checklist. Acrescento a régua concreta que a segunda ocorrência produziu: **nenhuma
validação wire-facing pode alocar ou iterar proporcional ao que o wire DECLARA antes de
validar o declarado** — e a ordem das condições (O(1) barato primeiro) é parte da defesa.

## O que ele não viu

**`T-UM-CAMINHO-SO`** — registrado às 00:21, a nota é de 01:48, e há **zero menções**.
Não é detalhe: essa direção diz que o **#2 da ordem dele** (`T-NATURE-CANDIDATO-BN`) e o
`T-BN-MULTICOL` são instâncias do mesmo problema — capacidade que existe num caminho e
não no outro, porque um e muitos são caminhos separados. Antes de soldar qualquer um
deles, a pergunta de triagem é *"isso é mais uma solda dupla?"*.

Também ficou de fora a **leniência `\<pontuação>` não-contratada**, que tem prazo como o
ADR-0041 (decide se a via "sufixo precoce" existe ou morre).

---

## Ordem revisada

| | item | por quê mudou |
|---|---|---|
| 1 | **ADR-0041** (4 decisões, não só o nome) | mantido — prazo real, e é a mesa do owner |
| 2 | **`T-FLOOR-POS-POLARIDADE` + pin do desempate** | **subiu de 3º** — é o único com perda medida no wire de HOJE (7 B/2% em coluna real), e absorve o #2 dele |
| 3 | **`T-NATURE-CANDIDATO-BN`** | **desceu de 2º** — não por mérito, mas porque a triagem do `T-UM-CAMINHO-SO` deve passar antes (solda dupla?) |
| 4 | checklist do amplificador (AGENTS.md) + pin do sweep `nature × modo` | higiene, custo baixo, previne reincidência |
| 5 | leniência `\<pontuação>`: fechar ou contratar | tem prazo, e ele não listou |

**Fora da fila**: o item 1 dele (CPU do periódico) — respondido e corrigido; não há ação.
