# Auditoria do `.8M` no corpus real — 23 tabelas, 186 colunas

> **Owner (2026-08-16)**: *"vamos focar ao máximo no 8M e ver se todas as otimizações e
> orientações de fluxo estão OK. Podemos fazer um teste de corpus se for o caso."*

## Por que corpus

Tudo que este ciclo mediu no `.8M` foi em **sintético**. O precedente do projeto é duro: o
`T-DATA-ALVO-MENSAL` deu 95% em sintético e **0,0% em real**. Esta auditoria repete as mesmas
perguntas contra `Z:/tcf-data/interim/` — 23 tabelas, 186 colunas.

## O veredito curto

**O `.8M` está saudável**, e a auditoria **corrigiu uma afirmação minha**.

- RT **23/23** · paridade `view`×`decode` **23/23** · as 6 invariantes **23/23 cada**,
  incluindo **decode paralelo == serial**.
- Os 3 guards recém-soldados: **zero disparo espúrio**, mesmo com **151 das 186 colunas** tendo
  nome com caractere não-alfanumérico.
- Os 4 candidatos do `min()` **têm todos domínio real** (dict 70 · tcf 59 · split 37 · raw 20).
  Nenhum é compute desperdiçado.

## A correção

Eu havia dito, do **adult-census**, que a soma de wires flat batia o `.8M` em **+27,2%**, e
usei isso para dimensionar o Grupo A. **No corpus inteiro o `.8M` VENCE por 5,1%** — e o
adult-census é justamente onde ele mais perde (62% de toda a perda do corpus). Generalizei do
pior caso.

Medido coluna a coluna, o **teto real da união** é **2,3%** do corpus (77 de 186 colunas teriam
candidato melhor no flat), não 27%.

**Consequência**: o Grupo A continua certo como unificação de *manutenção* (cada mecanismo
soldado uma vez, não duas), mas **o argumento de bytes ficou fraco** e não deve sustentar a
decisão de abrir a gramática do meta.

## Como rodar

```
python run.py    # sai 0 só se os RTs fecharem, as invariantes valerem em dado real,
                 # e nenhum guard disparar espúrio
```

**Precisa de `Z:/tcf-data/interim/`** (somente leitura; nada é baixado). `src/tcf` intocado.

## A régua de amostragem

Janela **contígua do meio**, alvo 2000 linhas — nunca passo espalhado. É a lição do lab
[`0530`](../../2026-08-15/2026-08-15-0530-date-real-e-cpu/): o passo espalhado destrói a
adjacência e mede uma distribuição que não existe na coluna.

## Onde olhar

| arquivo | o que é |
|---|---|
| [`result.md`](result.md) | os números, a correção e as ressalvas |
| `outputs/INDEX.md` | as 23 tabelas com bytes e RT |
| `outputs/*.tcf` + `.roundtrip.json` | as 4 maiores tabelas, com prova |
| `resultado.json` | tudo, incluindo o modo vencedor de cada uma das 186 colunas |

## Vínculo

`T-UM-CAMINHO-SO` (dimensionado aqui) · `T-8H-UM-CANDIDATO-SO` (não tocado — é outra rota) ·
welds `0dec1a06`/`ec08634c`/`2464f561` (verificados aqui em dado real) · labs
[`1530`](../2026-08-16-1530-piso-do-header-e-fronteira-paralela/) (as invariantes, em
sintético) e [`0530`](../../2026-08-15/2026-08-15-0530-date-real-e-cpu/) (a régua de amostragem)
