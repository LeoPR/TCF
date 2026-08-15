# Date — o processo de compressão, com o formato fixo

> **Owner (2026-08-15)**: *"a gente pode fazer o **mínimo** pra sustentar o ponto de vista de
> **compressão**: a gente vê o formato mais comum e se sustenta nele pra ver o processo de
> compressão primeiro. Se tudo isso funcionar, aí depois a gente ajusta entradas e saídas."*
>
> *"o core do tcf vai tratar a data de outra forma, **com permissão de transformação** se isso
> significa obter compressões melhores, e isso **não se mistura com a entrada e saída**."*

**Formato de entrada FIXO** (`YYYY-MM-DD`, já decidido e welded). **Nada de entrada/saída
aqui** — nem grafia, nem decode tipado, nem spec novo.

## O gap que este lab fecha

O date é o tipo mais medido do projeto — ordinal, delta de coluna, periódico, alvos mensais,
split, bN, epoch, base-80, sniff. O levantamento mostrou dois buracos:

1. **cada transformação foi medida contra o ordinal, nunca todas no mesmo `min()`**;
2. **delta-of-delta nunca foi medido** — o único candidato clássico de série temporal que o
   projeto não tinha tocado.

Este lab põe 6 candidatos para competirem sobre 14 regimes.

## Estado — era / foi / é / será

- **Era**: 10+ transformações medidas isoladamente, cada uma contra o ordinal.
- **Foi**: a reordenação do owner — compressão primeiro, I/O depois.
- **É**: 6 × 14, 0 falhas (cada transformação validada pela **própria inversa**). **Delta² tem
  nicho próprio** (esparsa-ordenada: 3854 → **605 B**), e a partição por regime é limpa.
  Resultado em [`result.md`](result.md).
- **Será**: a decisão de design que destrava — **protocolo de transformação de COLUNA** (hoje
  a nature é per-valor, e por isso só o ordinal cabe).

> **FECHADO** por [`…-0530-date-real-e-cpu`](../2026-08-15-0530-date-real-e-cpu/), que mediu as
> duas ressalvas em 8 colunas do corpus. Em dado real quem vence é `componentes` (7 de 8,
> 51,9–55,1%) e `delta` (a única coluna ordenada, 71,0%); **o `delta2` deste lab não venceu
> nenhuma vez**. Ver [`result.md` §7](result.md).

## A correção que o `result.md` faz

A tabela do `run.py` diz "14 de 14 regimes ganham". **Está inflado** — em 7 deles o vencedor é
o próprio `ordinal` contra o `spec`, e a diferença de 4 B é **o carimbo `:dt`**, não
transformação. A régua honesta (transformação × transformação) é **6 de 14**.

## Como rodar

```
python run.py     # sai 0 só se toda transformação fechar o RT pela sua inversa
```

**Sem `Z:`** — inteiramente sintético, sobre os regimes que o projeto já catalogou.
`src/tcf` intocado: as transformações são funções de coluna do lab.

## Onde olhar

| arquivo | o que é |
|---|---|
| `transformacoes.py` | as 6 leituras da coluna, cada uma com a inversa |
| `inputs/<regime>.entrada.json` · `.fonte.json` | a coluna e a procedência |
| `outputs/<regime>.<transf>.tcf` | **o wire de cada candidato**, isolado |
| `outputs/<regime>.spec-welded.tcf` · `.roundtrip.json` | o que o TCF emite hoje |
| `intermediates/candidatos.json` | as medições com `CONSTANTE_na_comparacao` |

## Vínculo

`T-DATA-ALVO-DELTA` (pedia exatamente o protocolo de coluna) · `T-SEQRLE-PERIODICO` (ADR-0040,
welded) · `T-DATA-LAZY-ISO` (o ordinal welded) · `T-CANDIDATO-SEM-DEDUP` · `T-SPEC-SEM-CARIMBO`
(os 4 B do `:dt`) · `T-DATA-ALVO-MENSAL` / `T-CORPUS-DATA-MENSAL` (o precedente de 95%
sintético → 0,0% real) · `T-SPLIT-SINGLE-COL`
