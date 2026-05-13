# Conclusões — flow semântico chegou perto do teto teórico

Ganhos honestos das Etapas 1 e 2:

| Técnica | Ganho |
|---|---|
| Etapa 1 — análise pura | mapeou espaço (80% A, 0% B, 20% C) |
| Etapa 2 — sumida | **-1 byte em emails-quote-id** |
| Etapa 2 — slice arbitrário (análise) | 2-5 bytes potenciais |

**Total possível com todas as técnicas implementadas**: ~5-10
bytes de ganho sobre v4-quote-fixed. Em 198 bytes, isso é
**2-5%**.

## A descoberta central — diminishing returns

O algoritmo do **exp 16 já fatora a maior parte do trabalho**.
As otimizações de sintaxe (escape, quote, sumida, slice) estão
raspando bytes em casos cada vez mais raros.

Trajetória das economias de sintaxe (sobre verbose, exp 16):

| Etapa | Sintaxe | Economia |
|---|---|---|
| 21 | v1 (`@N`, `<K`) | -45% |
| 22 | v2 (idx por frag) | varia |
| 23 | v3 (sem aspas) | -27% vs v1 em D2-mini |
| 25 | v4-quote-fixed | universalmente correto |
| 26 | v4-mixed | empate com v4-q-fix |
| 28 | v6-sumida | -0.5% |
| 28 | slice arbitrário (potencial) | -2% a -5% |

A curva mostra que a partir de v4-q-fix, **cada novo refinamento
captura menos**. O algoritmo já é robusto e a sintaxe está
próxima do ótimo.

## Por que sumida não ganhou mais

A análise refinada mostrou 3 razões estruturais:

### 1. Dígitos pequenos sempre colidem com idx

Em emails-quote-id, idx 1-N existem (~30 fragmentos). Dígitos
`1`, `2`, ..., `9` no literal sempre coincidem com algum idx
existente. Sumida só funciona para dígitos formando N > 30.

Em datasets reais, IDs costumam ser sequenciais (1, 2, 42, etc.),
**exatamente os números que colidem com idx**.

### 2. Vizinhança de refs neutraliza o ganho

Literal de dígitos entre 2 sequências de refs:
- Aspas: `'42'` = 4 bytes total
- Sumida + 2 separadores: `*42*` = 4 bytes total
- **Empate exato**.

Sumida só ganha em borda de linha ou entre literais (não entre refs).

### 3. Fragmentos misturados não podem sumir

Literais como `"o'connor103"` (letras+dígitos) precisariam ser
sub-divididos em fragmentos. Mudaria a estrutura de idx. Slice
arbitrário resolveria, mas não está implementado.

## Por que slice arbitrário também ganha pouco

O algoritmo do exp 16 captura padrões fortes via LCP/LCS. O que
sobra em fragmentos misturados é **estrutura residual** — IDs
únicos, terminações específicas, dados que não fatoram.

Slice arbitrário ganharia em datasets onde:
- O algoritmo não fatora (LCP=0 e LCS=0)
- Mas há substring forte no meio

Esses datasets são **raros** em produção. Quando a fatorização é
forte, slice não acrescenta. Quando é fraca, talvez seja porque
o dado é mesmo aleatório (UUIDs, hashes) e não há substring.

## Validação da intuição

> "ter um teste controlado pra ver onde cada técnica pode caber
> ou até substituir 100%"

Não chegamos a 100% de substituição. As 3 técnicas (escape,
quote, sumida) cobrem casos distintos mas com ganhos pequenos
incrementais.

> "se ele pode ser substituido totalmente pelas outras
> estratégias de marcaçao ou se ele pode ser usado como semantica
> extra para alguns casos"

Resposta empírica:
- **Sumida**: semântica EXTRA para casos onde dígitos formam N
  grande. Aplicável mas pequeno ganho.
- **Slice arbitrário**: semântica EXTRA para fragmentos
  misturados. Aplicável mas raro.
- **Nenhuma substitui** as outras 100%.

## A pergunta que sobra

**Vale a pena implementar slice arbitrário completo?**

| Lado | Análise |
|---|---|
| Pró | Ganho potencial 2-5 bytes em emails-quote-id; mais em datasets stress; semântica nova capturada |
| Contra | Implementação complexa (sub-fragmentar, novo tipo de token, decoder mais sofisticado); ganho marginal; manutenção |

**Minha leitura**: o ganho não justifica a complexidade. A não
ser que apareça um caso onde slice é a única forma de capturar
um padrão grande (LCP/LCS zero + substring central forte), o
custo de implementar não compensa.

## Pontos a registrar

1. **Sumida funciona conceitualmente** mas tem ganho mínimo em
   datasets fatorizados pelo exp 16
2. **Slice arbitrário tem potencial real mas pequeno** —
   próximo de 2-5 bytes mesmo em dataset stress
3. **O algoritmo do exp 16 é o trabalho pesado** — sintaxe está
   raspando os últimos bytes
4. **As Etapas 3-5 do plano original** (órfã, agrupamento,
   integração) provavelmente terão ganhos similarmente pequenos
5. **A direção honesta** após este exp: benchmark externo (gzip)
   ou abandonar refinamento de sintaxe textual

## Direções possíveis daqui

### A. Continuar Etapas 3-5 do flow semântico

- Etapa 3 — órfã: aspa sem fechamento se literal vai até fim de
  linha
- Etapa 4 — agrupamento: marcar segmento maior cobrindo grupo
- Etapa 5 — integração: tudo numa classe Syntax

**Custo**: alto. **Ganho esperado**: 5-10 bytes adicionais (curva
de retorno decrescente).

### B. Implementar slice arbitrário no algoritmo

Modificar o online.py para emitir TokRefSlice quando substring
no meio é maior que threshold.

**Custo**: alto (mexer no algoritmo, não só sintaxe). **Ganho**:
desconhecido em datasets reais.

### C. Pular para benchmark externo

Comparar v4-quote-fixed + gzip vs CSV + gzip e formatos como
HTFC/FSST. Saber se o TCF compete na prática.

**Custo**: médio. **Ganho**: informação sobre o panorama
externo — decide se vale continuar refinando.

### D. Parar e consolidar

Considerar o trabalho fechado em v4-quote-fixed. Documentar como
sintaxe vencedora. Voltar para o algoritmo (revisão retroativa,
delta encoding) ou para o **propósito original do TCF** (legibilidade
LLM, deferido).

## O que este experimento NÃO faz

- Não implementa slice arbitrário
- Não testa em datasets reais (somente sintéticos)
- Não compara com compressão estatística (gzip)
- Não explora Etapas 3-5 do flow semântico

## Recomendação pessoal

Após 6+ experimentos refinando sintaxe e Etapas 1-2 do flow
semântico, a curva de retorno está clara. **Sugiro Direção C
(benchmark externo)** antes de continuar refinando. Sem isso,
qualquer refinamento adicional é otimização sem norte.
