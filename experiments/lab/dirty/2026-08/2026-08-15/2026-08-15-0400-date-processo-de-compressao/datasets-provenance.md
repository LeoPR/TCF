# Procedência dos dados — e o viés declarado

## Inteiramente sintético, e os regimes não são invenção

Os 14 regimes são **os que o projeto já catalogou** em labs anteriores (`2311`, `0235`, `0042`,
`1853`, `1650`, EXP-017): diária, semanal, quinzenal, mensal dia-1, mensal com faltas, dias
úteis, úteis+feriado, trimestral, descendente, agrupada, cíclica, esparsa ordenada, esparsa
desordenada, suja.

Gerados em `run.py`, **sem `random`** (LCG determinístico), n=600, base `2024-01-01`.

## O viés, declarado — e o precedente que o torna sério

**Quatro regimes são progressões exatas** (diária, semanal, quinzenal, trimestral) e
**dois são ciclos limpos** (úteis, mensal-dia1). São o melhor caso dos mecanismos aritméticos,
e existem para exibir o comportamento — **não estimam frequência no mundo**.

**O precedente é duro e está registrado**: o `T-DATA-ALVO-MENSAL` mediu **95% em sintético e
0,0% em dado real**, porque nenhuma coluna do corpus tem cadência mensal. Os **80% do
`mensal-faltas`** deste lab estão sob exatamente o mesmo risco, e o `T-CORPUS-DATA-MENSAL`
continua bloqueado.

**Os que têm mais chance de sobreviver ao real**: `cíclica` (o `T-CANDIDATO-SEM-DEDUP` já a
mediu em coluna real) e `esparsa` (aparece nas colunas de data do TPC-H e do `br-identidades`).
São justamente onde `delta` e `delta2` ganham.

## Os pares de contra-prova

| par | o que isola |
|---|---|
| `esparsa-ordenada` × `esparsa-desordenada` | os mesmos saltos, só a **ordem** muda — isola quanto cada mecanismo depende de vizinhança |
| `uteis` × `uteis-feriado` | o mesmo ciclo, com ~2% de quebra — isola a robustez ao ruído |
| `mensal-dia1` × `mensal-faltas` | a mesma cadência, com 10% de ausências |
| `diaria` × `suja` | a mesma progressão, com 10% de grafias não-canônicas |

## O que NÃO foi medido aqui (e deveria entrar antes de qualquer weld)

- **CPU.** Transformação de coluna é passe extra; o `T-CANDIDATO-SEM-DEDUP` mediu **+84–93%**
  de encode para um candidato análogo. Um `min()` com seis candidatos custa tempo.
- **Dado real.** Nenhum regime aqui vem do corpus — só a *forma* deles vem.
- **A interação com o multi-col**, o `.8H` e o split real (que é multi-col embutido).
