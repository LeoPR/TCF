# 2026-08-17-1800 — o que de fato falta pro grupo

## A tese

> *"o desafio é meramente juntar as colunas. temos vários mecanismos prontos que bastam
> complementar. tratar como colunas independentes já é feito… no final, quem paga de verdade
> é tanto a técnica pra fazer o split como alguma coisa no cabeçalho que lembre que são duas
> (ou mais) colunas que são uma só na verdade na hora de decode."* — owner, 2026-08-17

Isso é **falsificável**, e este lab tentou derrubar.

## As três hipóteses e o veredito

| | hipótese | resultado |
|---|---|---|
| **H1** | o **corpo** do grupo é byte-idêntico ao de N colunas independentes num `.8M` comum | **CONFIRMADA 4/4** |
| **H2** | a única diferença no wire está no **cabeçalho** | **CONFIRMADA** (corolário de H1) |
| **H3** | as duas perspectivas do owner — multi-col+indicador **e** hierarquia-de-uma-coluna-com-duas-dentro — dão o **mesmo corpo** | **CONFIRMADA 4/4** |

**H1 é o achado.** O corpo do grupo não é *parecido* com N colunas independentes — é
**byte-idêntico**, comparado contra o `encode` público. Não há pipeline novo, não há
transformação de corpo: são as mesmas colunas, pelos mesmos candidatos, concatenadas na
mesma ordem. *"Tratar como colunas independentes já é feito"* — literalmente.

## O custo isolado: só o marcador

| caso | n | corpo | **marcador** | split atual | grupo | delta |
|---|--:|--:|--:|--:|--:|--:|
| decimal | 24 | 91 | **+9 B** | 134 | 118 | −16 |
| data-iso | 24 | 75 | **+9 B** | 127 | 106 | −21 |
| telefone | 24 | 276 | **+11 B** | 331 | 310 | −21 |
| cep-real | 19 988 | 164 463 | **+10 B** | 164 510 | 164 494 | −16 |

O marcador (o template + a marca de junção no meta) custa **9 a 11 bytes**, e é **constante
em n** — o mesmo +10 B numa coluna de 24 valores e numa de 19 988. E mesmo pagando isso, o
grupo fica **menor que o split atual** em 4/4, porque devolve mais do que cobra: some a
recursão (`#TCF.8M` aninhado + sub-header + moldura `<ntmpl>` + nomes `c0..cN`).

## As duas perspectivas são a mesma coisa

```
col. independentes : #TCF.8M!1d477=z0,@z1                ← já funciona hoje
grupo (multi-col)  : #TCF.8M&2|-|=cep-real,!1d477,@      ← perspectiva (a)
grupo (hierarquia) : #TCF.8Hcep-real||-||:!1d477,@       ← perspectiva (b)
                                          └──────┴─ MESMAS entradas de coluna
```

**Corpo idêntico nas três.** A escolha entre (a) e (b) é de **gramática do meta**, não de
mecanismo — e portanto é decisão de onde a marca mora, não de como o dado é escrito. Isso
significa que a escolha pode ser adiada sem custo de arquitetura.

RT validado nas duas perspectivas, com o mesmo decoder genérico (fatia pelo meta, junta pelo
template).

## O que isso deixa como trabalho real

Confirmada a tese, a lista do que falta é curta:

1. **A técnica do split** — detectar o template uniforme. **Já existe** (`split.py`), só
   deixaria de emitir o sub-wire.
2. **O marcador no cabeçalho** — 9–11 B, gramática a definir. É o **único item novo**.
3. **A junção no decode** — uma linha:
   `"".join(partes[k] + cols[k][r] …) + partes[-1]`.

Tudo o mais — shredding, plano de fatias, `min()` por coluna, os três decoders — **já está
pronto e é reusado sem alteração**.

## O que este lab NÃO prova

- **Não testa a composição** com máscara (`?:`), contagem (`#:[`) ou array-em-array. A
  H-13-06 segue aberta, e é onde eu esperaria a primeira dificuldade real (um grupo dentro
  de array precisa que os N campos compartilhem a contagem).
- **Não decide a gramática.** Os metas aqui são ilustrativos; a escolha de char é reversível
  por decisão de projeto.
- **Não mede o encode streaming.** H-13-03/04 seguem abertas — a técnica do split ainda é
  batch por natureza (precisa ver todos os valores para afirmar template uniforme).
- **Não mede CPU.** Só bytes e estrutura.
- **4 casos, uma seed.** O CEP real usa `stratify_by="uf"`, seed 42, n≈20k.

## Evidência

16 wires (por caso: `atual-split`, `colunas-independentes`, `grupo-multicol`,
`grupo-hierarquia`) + 4 roundtrips. RT validado nas duas perspectivas de grupo e nas formas
de referência.

## Conexões

- [`1500`](../2026-08-17-1500-split-didatico/) (o didático) ·
  [`1600`](../2026-08-17-1600-split-como-grupo-no-meta/) (grupo no `.8M`) ·
  [`1700`](../2026-08-17-1700-grupo-como-combinador-do-H/) (grupo como combinador do `.8H`)
- [`0400`](../2026-08-17-0400-o-candidato-unico-do-H/) (o gap de +23% que isto amarra)
- [roadmap-hipoteses Pacote 13](../../../notas/2026-05/roadmap-hipoteses.md)
