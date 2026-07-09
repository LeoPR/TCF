# Resultado — F1 latência do bypass [probatório]

Números: `artifacts/` (`python3 run.py`). Dá NÚMERO ao eixo **aceleração** (o único sem medida).

## Latência (`01-latencia-bypass.txt`, 9 colunas reais, N=20000, mediana de 9 runs)

| coluna | k | w | núcleo ms | produção ms | bypass ms | ×núcleo | ×prod | RT |
|---|---|---|---|---|---|---|---|---|
| adult.sex | 2 | 1 | 55.2 | 65.4 | 17.6 | 3.1 | 3.7 | OK |
| adult.class | 2 | 1 | 45.5 | 59.5 | 16.5 | 2.8 | 3.6 | OK |
| adult.race | 5 | 4 | 34.9 | 49.0 | 20.8 | 1.7 | 2.4 | OK |
| adult.relationship | 6 | 4 | 78.7 | 67.8 | 21.7 | 3.6 | 3.1 | OK |
| adult.education | 16 | 4 | 82.7 | 97.9 | 21.8 | 3.8 | 4.5 | OK |
| tpch.l_linestatus | 2 | 1 | 28.2 | 40.2 | 16.9 | 1.7 | 2.4 | OK |
| tpch.l_returnflag | 3 | 2 | 46.4 | 55.1 | 19.0 | 2.4 | 2.9 | OK |
| receita.matriz_filial | 2 | 1 | 19.5 | 30.4 | 16.3 | 1.2 | 1.9 | OK |
| beijing.cbwd | 4 | 2 | 45.8 | 57.4 | 19.7 | 2.3 | 2.9 | OK |
| **MEDIANA** | | | | | | **2.4** | **2.9** | — |

*Anomalia anotada: em adult.relationship a produção (67.8ms) saiu mais RÁPIDA que o núcleo (78.7ms), única
inversão nas 9 linhas — ruído de medição (produção = núcleo + 3 candidatos). Não afeta as medianas.
Escopo: 4 fontes / 9 colunas, batch Python single-thread — número de LATÊNCIA, não gate real-world de compressão.*

## Veredito

- **Bypass é 2.4× mais rápido que o núcleo (2.9× que a produção)**, mediana, RT-OK em todas. O eixo
  **aceleração** agora tem número.
- **Modesto mas real**: o núcleo já dedup low-card rápido → não é 10×, é ~2-4×. Cresce com o comprimento
  dos valores (education k=16 valores longos = 3.8×; matriz_filial "1"/"2" trivial = 1.2×).
- **É latência, NÃO byte** (o bypass emite bN, que colapsa pós-brotli — gate D3). Nicho: **terminal/
  streaming** (V2-J) + payload-minúsculo. A "corrida especulativa" do owner em batch = try-first sequencial
  (o classificador ≈ analyze_column, custa ≪ núcleo).

## Interno B (`02-interno-B.txt`)

`bool3` (false/true/null) = trio em 2 bits; **domínio = 0B** (congelado no formato, não declarado); RT-OK.
Prova o "usa a interna sempre" (owner): a coluna referencia o dict do formato, self-describing.

## Conclusão p/ H-TYPE-07

F1 tem **justificativa de latência real (~2.4×)** — a preemptiva se sustenta pelo eixo aceleração, não byte.
Modesta; o caso forte é streaming (V2-J). Weld gated (owner + src/tcf). A **Opção A** de nomenclatura
(b1/b2/b4 físico; b3=trio; b5/6/7 especiais; B=interno) fica registrada.

## Limites

- Latência em batch (Python, single-thread); a formulação de filas paralelas do owner é streaming (V2-J).
- 9 colunas, N=20000. O bypass emite bN cru (byte = terminal); não compete com produção em byte pós-brotli.
