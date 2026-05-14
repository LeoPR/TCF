# Vetores de comparacao alem de bytes

**Data**: 2026-05-14
**Tipo**: nota transversal
**Origem**: revisao critica pos-M5; user perguntou "vantagens algebricas
de outras naturezas — velocidade, memoria, busca/latencia"

## Vetores nao-byte para comparar sintaxes

Bytes e' a metrica primaria mas nao a unica. Para empates ou
dominacoes pequenas em bytes, esses vetores podem inverter ou
matizar a conclusao:

| Vetor | Como medir | Quando medir |
|---|---|---|
| Velocidade encode (CPU) | wallclock detector + serializador | curto prazo, D1-D4 |
| Velocidade decode (CPU) | wallclock decoder | curto prazo, D1-D4 |
| Memoria pico encode | `tracemalloc` Counter + estruturas | curto prazo |
| Memoria pico decode | `tracemalloc` aliases dict + frags | curto prazo |
| Streaming-encode compat | analise estrutural (preambulo bloqueia) | algebrico, ja' avaliado |
| Streaming-decode compat | analise estrutural (single-pass possivel?) | algebrico, ja' avaliado |
| Latencia first-byte encode | tempo ate emitir 1a linha | empirico, requer instrumentacao |
| Random access decode | possivel pular linha N sem reprocessar? | algebrico, todos atuais sao sequenciais |
| Complexidade Big-O detector | analise algebrica | algebrico |
| Complexidade Big-O decoder | analise algebrica | algebrico |

## Diferencas algebricas conhecidas (M2.A vs M4.C1' vs M4.C1 v1)

| Vetor | M2.A | M4.C1' | M4.C1 v1 |
|---|---|---|---|
| Espaco busca detector | O(N·L) sufixos K>=3 | O(N·L²) subseqs K>=2 | O(N) runs inteiras |
| Memoria encode peak | Counter de sufixos | Counter de subseqs (maior) | Counter de runs (menor) |
| Decoder single-pass | semanticamente 2-pass (preambulo) | nativo | nativo |
| Streaming encode | incompativel | compativel em principio | compativel em principio |

## Cronograma de avaliacao

### Algebrico (agora, sem rodar)
- Complexidade encode/decode Big-O
- Streaming compatibility
- Memoria estrutural pico

### Curto prazo (1 sessao, dados atuais)
- Wallclock encode/decode com `timeit` em D1-D4
- Peak memory com `tracemalloc`

### Medio prazo (datasets extra ja' existentes)
- M2.A, M4.C1', M5.A em DE5/DE6 (`data_extra/` do M1)
- Ver forma de degradacao em datasets adversariais

### Longo prazo (novos datasets)
- Escala N (mais linhas)
- Escala L (runs mais longas — estressa O(L²))
- Escala K (mais aliases candidatos)
- Dados complexos (CPF + email + UUID em mistura)

### Limites do dirty
- Dirty cumpriu papel de descoberta. Escalas amplas (N, L, K grandes)
  cabem melhor no protótipo, com infraestrutura de benchmark.

## Critica das proprias conclusoes (registradas em sessao M5)

1. **"Dominacao algebrica de M4.C1' sobre M2.A"** — vale so' para
   mesmo padrao e mesma sintaxe de def. Se M2.A migrar para inline
   (sem preambulo), a diff cai de `2+2*len(N)` para `len(N)` por
   alias. **Conclusao M5 enviesada.** Ver
   [[../../2026-05-14-M5-pilha-M2A-M4C1p/]] e
   [`marcadores-multiplo-proposito.md`](marcadores-multiplo-proposito.md).

2. **"M2.A fora do prototipo"** — vale em bytes (ate' agora). Em
   vetores nao-byte, M2.A pode ainda ter nicho (batch decode com
   tabela de aliases acessivel, separacao limpa). Nao avaliado.

3. **"Streaming-encode" empate atual** — todos batch hoje. Vetor
   estrutural a favor de inline (M4.C1*) sobre preambulo (M2.A) se
   detector for online (futuro M4.C2).

## Conexoes

- [[marcadores-multiplo-proposito.md]] — analise da redundancia de
  markers em M4.C1' e proposta hierarquica
- [[../../2026-05-14-M5-pilha-M2A-M4C1p/notas/conclusoes_M5.md]] —
  conclusao M5 sob revisao
- [[comparacao-modular-camadas.md]] — modos de comparacao no
  prototipo
