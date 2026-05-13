# TCF Formato Adaptativo — Plano de Pesquisa

**Data:** 2026-05-07
**Status:** teoria — nenhum código ainda

---

## Problema central

O TCF hoje descreve *o quê* os dados são (tipos, compressão, cardinalidade).
Ele não descreve *como* os dados devem ser entregues.

A hipótese de trabalho: se o formato incluir semântica de entrega, a camada de transporte
consegue começar a responder perguntas *antes* de ter recebido tudo — mesmo sob rede
variável, paralelismo ou latência alta.

---

## O conceito: "unidade macro de informação"

Exemplo concreto: cliente comprou itens em datas específicas. O sistema precisa
retornar o total por cliente o mais rápido possível, os detalhes depois.

Hoje: carrega tudo → processa → responde.
Com formato adaptativo: ao receber os primeiros chunks (tier-1), o receptor já sabe
responder "total do cliente X = R$Y" — sem esperar os detalhes de cada item.

A quebra do arquivo define isso. O arquivo *em si* diz:
- qual coluna é a chave de agrupamento
- quais colunas respondem a pergunta imediata (tier-1)
- quais são enriquecimento opcional (tier-2+)
- quais chunks são independentes (podem chegar em qualquer ordem)
- como montar a resposta parcial sem ter tudo

---

## Os 3 eixos ortogonais do TCF adaptativo

```
Eixo 1 — COMPRESSÃO      L0 → L3 (já existe)
Eixo 2 — TOPOLOGIA       monolítico | chunked | streaming
Eixo 3 — PRIORIDADE      flat | tiered | grouped
```

Esses eixos são independentes. Exemplos de combinações:
- L3 + monolítico + flat = TCF atual máximo (comprime, mas entrega tudo de uma vez)
- L2 + chunked + tiered = entrega rápida de totais, detalhes depois
- L1 + streaming + grouped = stream de eventos por grupo, sem buffering

---

## Primitivas de formato (o que o arquivo precisa expressar)

### MANIFEST (header do arquivo)
```
# MANIFEST chunks=N group_by=<col> delivery=<mode>
```

`delivery` modes:
- `bulk`       — monolítico, sem prioridade (default atual)
- `priority`   — chunks ordenados por tier, receptor pode responder cedo
- `parallel`   — chunks independentes, sem referência cruzada, qualquer ordem
- `stream`     — chunks gerados on-the-fly, n=? (tamanho desconhecido)

### PRIORITY tiers (opcional, só faz sentido com delivery=priority)
```
# TIER 1 cols=customer_id,total_amount  answer=true
# TIER 2 cols=item_name,date,quantity   answer=false
```

`answer=true` significa: ao receber esse tier completo para um grupo, o receptor
pode emitir uma resposta parcial imediata.

### Chunk com metadados de entrega
```
@chunk 2/5 tier=1 group=customer_id self_contained=true n=50
```

- `tier`           — prioridade de entrega (1 = primeiro)
- `group`          — coluna que define a unidade macro
- `self_contained` — true = sem dependência de outros chunks para decodificar
- `n`              — linhas nesse chunk (? se streaming)

### Completeness signal
```
@group_complete customer_id=C001
```
Sinal explícito: todos os dados do grupo C001 já foram enviados. Receptor pode
finalizar a resposta para C001 sem esperar mais chunks.

---

## Hipóteses formalizadas (extensão de H-transporte.md)

### H1.1 — Resposta antecipada por tier
> Com delivery=priority, o tempo entre "primeiro byte recebido" e "primeira resposta
> válida emitida" é menor do que com monolítico, mesmo sem compressão melhor.

Condição de falha: se o processamento de tier-1 for mais caro que a diferença de
latência de rede (improvável, mas possível em datasets muito pequenos).

### H1.2 — Grouping reduz buffering no receptor
> Com group_by explícito e @group_complete, o receptor pode liberar memória de grupos
> já respondidos enquanto ainda recebe dados de outros grupos.

Condição de falha: se todos os grupos forem igualmente pequenos, o ganho de memória
é irrelevante.

### H3.1 — Paralelismo de decode, não só de transferência
> Chunks com self_contained=true e tiers diferentes permitem pipeline de decode em
> paralelo (tier-1 decodificando enquanto tier-2 ainda transferindo).

Condição de falha: se o gargalo for I/O de rede, não CPU de decode.

### H6 — Custo de planejamento
> O ganho de latência percebida é anulado pelo custo de planejar a quebra dos dados
> (decidir tiers, grupos, ordem de chunks) quando o dataset é pequeno ou a query é
> simples.

Isso sugere um **threshold de complexidade mínima** abaixo do qual o TCF deve
permanecer monolítico/flat. O planner precisa detectar isso.

### H7 — Auto-explicabilidade suficiente para server burro
> Um server que apenas lê o arquivo TCF e transmite os chunks na ordem do arquivo
> (sem nenhum conhecimento da query original) já entrega os benefícios de prioridade,
> porque o planejamento foi feito no momento do encode.

Se verdadeira: o encode é o trabalho inteligente; o decode/transmit pode ser burro.
Isso é importante para adoção — servidores existentes não precisam entender TCF, só
transmitir.

---

## Motores necessários (o que precisará existir)

### Motor 1: Planner
Entrada: dados + query intent (o que precisa responder) + perfil de rede  
Saída: plano de quebra (tiers, grupos, tamanho de chunk, delivery mode)

Hoje: não existe. É o motor mais complexo.  
Futuro: pode ser um SQL engine (GROUP BY → group_by, SELECT cols → tier-1).

### Motor 2: Adaptive Encoder
Entrada: dados + plano do Planner  
Saída: TCF com MANIFEST + chunks ordenados + signals

Relação com encoder atual: extensão — o encoder atual produz L0-L3 monolítico;
o Adaptive Encoder adiciona topologia e prioridade em cima.

### Motor 3: Stream Decoder
Entrada: stream de chunks TCF (possivelmente fora de ordem)  
Saída: callbacks por evento:
- `on_tier_complete(tier, data)` — tier recebido, pode processar
- `on_group_complete(group_key, value)` — grupo completo, pode responder
- `on_file_complete()` — tudo recebido

Relação com decoder atual: extensão — decoder atual é batch (lê tudo, retorna tudo);
Stream Decoder é event-driven.

### Motor 4: Assembler (lado cliente)
Entrada: eventos do Stream Decoder + query original  
Saída: respostas parciais → resposta final  

É o que o cliente implementa. O TCF não dita a lógica de negócio, só fornece os
eventos e a semântica dos dados.

---

## Fases experimentais

### Fase 0 (atual): Teoria
- [x] Hipóteses H0-H5 (H-transporte.md)
- [x] Primitivas de formato (este documento)
- [ ] Validar primitivas com exemplo manual (cliente/compras)

### Fase 1: Formato no papel
- Pegar o dataset TPC-H (já usado no lab) — tabela `orders` + `lineitem`
- Desenhar à mão como ficaria o TCF com MANIFEST + tiers + group_complete
- Medir: quantos bytes a mais o MANIFEST/signals adicionam vs monolítico?
- Decidir: primitivas acima são suficientes, ou falta algo?

### Fase 2: Motores básicos
- Adaptive Encoder: só delivery=priority + tiers estáticos (planner manual)
- Stream Decoder: callbacks on_tier_complete + on_group_complete
- Sem Planner ainda — a quebra é especificada manualmente no experimento

### Fase 3: Experimentos de formato
Combinações a testar (matriz):

| ID | Compressão | Topologia  | Prioridade | Cenário de rede      |
|----|-----------|------------|------------|----------------------|
| F1 | L0        | monolítico | flat       | baseline (sem rede)  |
| F2 | L2        | monolítico | flat       | baseline comprimido  |
| F3 | L2        | chunked    | flat       | rede normal          |
| F4 | L2        | chunked    | tiered     | rede normal          |
| F5 | L2        | chunked    | tiered     | latência alta (300ms)|
| F6 | L2        | chunked    | tiered     | banda limitada (1Mbps)|
| F7 | L2        | parallel   | grouped    | múltiplas conexões   |

Métricas por combinação:
- `T_first`: tempo até primeira resposta parcial válida
- `T_total`: tempo até resposta completa
- `bytes`: tamanho total do payload
- `CPU_decode`: tempo de decodificação no receptor
- `memory_peak`: pico de memória no receptor

### Fase 4: Planner básico
- Planner recebe: SELECT + GROUP BY → detecta automaticamente tiers e group_by
- Integração com DuckDB (já está no pyproject.toml como dependência opcional)
- Hipótese H7 validada aqui: encode inteligente + decode/transmit burro = funciona?

### Fase 5: Suite científica
- Formalizar combinações da matriz como testes parametrizados
- Definir critério de aceitação: ganho >10% em T_first para rejeitar H0
- Rodar em datasets reais (TPC-H, UCI Adult — já referenciados no projeto)
- Documentar resultados para artigo (Cap. 5 ou 6 — performance e transport)

---

## Decisões pendentes (antes de implementar qualquer motor)

1. **@group_complete é explícito ou implícito?**  
   Explícito = server burro pode transmitir sem entender semântica.  
   Implícito (calculado pelo decoder) = formato mais limpo, mas decoder mais inteligente.  
   → Hipótese: explícito é melhor para H7.

2. **Tier é por coluna ou por chunk?**  
   Por coluna: mais flexível, mas chunk pode misturar tiers.  
   Por chunk: mais simples, chunk é a unidade de prioridade.  
   → Hipótese: por chunk, com `cols=` indicando quais colunas o chunk contém.

3. **self_contained proíbe dict global?**  
   Se sim: cada chunk carrega seu próprio dict (overhead).  
   Se não: chunks tier-2 podem referenciar dict do chunk tier-1 (dependência).  
   → Hipótese: self_contained=true proíbe referência cruzada; tier-2 pode referenciar tier-1 dict via `dict_ref=chunk_id`.

4. **Threshold de H6: quando não usar nada disso?**  
   Proposta: se `n_rows < 1000` e `n_groups < 10` e `delivery_latency_ms < 50`, usar monolítico.  
   Planner detecta isso automaticamente.

5. **Nomenclatura: "MANIFEST" ou continua no header TCF normal?**  
   Opção A: bloco separado `# BEGIN MANIFEST ... # END MANIFEST`  
   Opção B: linhas `# KEY=value` no header existente  
   → Hipótese: Opção B, consistente com o que já existe (menos tokens pra LLM).

---

## Próximo passo imediato

Fase 1: desenhar manualmente um TCF para `orders` + `lineitem` (TPC-H) com:
- `delivery=priority`
- `group_by=o_custkey`
- tier-1: `o_custkey, o_totalprice`
- tier-2: `l_partkey, l_quantity, l_extendedprice`
- `@group_complete` após cada cliente

Isso valida as primitivas antes de escrever uma linha de código.
