---
title: "BUG-SEQRLE-DIGITO-UNICODE: dígito decimal não-ASCII volta como ASCII, em silêncio, quando o seq-RLE desloca a corrida"
status: closed-fixed
priority: P1
severity: R0 (round-trip lossy e silencioso na API pública)
created: 2026-11-06
updated: 2026-11-07
gate: "solda autorizada pelo owner em 2026-11-07 (o bug passa na frente da fila do .9); gates byte-canônicos verdes sem re-pin"
blocked-by: []
related: [
      src/tcf/composicional/hcc_seqrle.py,
      src/tcf/natures/int_pad.py,
      tests/test_core_rt.py,
      docs/adr/0036-bn-de-dominio-cardinalidade-baixa.md,
      docs/adr/0042-cnpj-alfanumerico-dois-specs.md,
      tickets/BUG-SEQRLE-RANGE-EMPTY-B.md,
      experiments/lab/dirty/2026-11/2026-11-07/2026-11-07-0100-digito-unicode/,
]
---

> **CLOSED 2026-11-07 (vermelho → verde).** O detector de corridas do seq-RLE passou a aceitar
> só dígito ASCII, e a nature `int-pad` ganhou o mesmo guard. Neutro em bytes para todo dado
> que já fazia round-trip, medido: gates byte-canônicos (D1-D9/D17a, real-world, equivalência
> do `.pyx`) verdes **sem re-pin**, suíte 1997 em 3.13.13 com acelerador e 1948 em 3.14.4 sem
> ele. Pinos em `tests/test_core_rt.py::TestSeqRleDigitoUnicodeBug`, incluindo a propriedade
> sobre todo conjunto `Nd` do interpretador.

# BUG-SEQRLE-DIGITO-UNICODE

**[probatório → execução]** Uma coluna cujos valores formam sequência com dígitos decimais
**não-ASCII** (arábico-índicos, devanágari, fullwidth) passava pelo `encode` sem reclamar e
voltava do `decode` com parte dos dígitos trocados pelos ASCII de mesmo valor. A `0.8.4`
publicada é afetada, em todas as versões de Python, com o acelerador ligado ou desligado.
Violava o invariante mais duro do projeto: ou o round-trip devolve o mesmo dado, ou falha alto.

Achado lateral da análise da política de versão de Python (2026-11-06, [ADR-0051](../docs/adr/0051-politica-de-versao-de-python.md)).

## Repro mínimo (três valores)

```python
from tcf import decode, encode
x = ["١٠٠٠", "١٠٠١", "١٠٠٢"]          # 1000, 1001, 1002 em arábico-índico
decode(encode(x))
# na 0.8.4: ['١٠٠٠', '١٠٠١', '١٠٠2']  (o último dígito saía ASCII)
```

## Causa

O detector de corridas `find_escape_digit_runs`, em `src/tcf/composicional/hcc_seqrle.py`,
usava `str.isdigit()`, que aceita qualquer dígito Unicode. O delta saía de `int()` sobre a
corrida, e `int()` também aceita dígito Unicode (`int('١٠٠٢') == 1002`). Na expansão, o valor
deslocado era reescrito por `str(new_val)`, que é sempre ASCII. Encoder e decoder chamam a
mesma função, então a correção vale igual dos dois lados.

É a família de assimetria que a ADR-0036 §2 contou na quinta aparição (o cabeçalho bN aceitava
`#TCF.8B٢c8`) e que a ADR-0042 corrigiu na telemetria do CNPJ. Esta foi a primeira no caminho do
dado do usuário, e a primeira silenciosa.

## O que o lab mediu

[Lab `2026-11-07-0100-digito-unicode`](../experiments/lab/dirty/2026-11/2026-11-07/2026-11-07-0100-digito-unicode/result.md),
Python 3.13.13 (Unicode 15.1):

| | sonda por forma (154 casos) | fuzz (3000 colunas) |
|---|---|---|
| antes | 88 corrompem · 2 recusam com exceção crua · 64 ok | 803 corrompem |
| depois | 154 ok | 3000 ok |

- **Uma causa, quatro rotas.** `.8`, `.8M`, `.8R` e `.8H` quebravam, e as natures `int-pad`,
  `ip` e `data-iso` também, porque a saída delas passa pelo HCC. A correção no detector fechou
  todos os casos de uma vez.
- **A versão de Python mudava o alcance.** Tangsa (Unicode 14) e Kawi (Unicode 15) corrompiam em
  3.13 e passavam em 3.10, onde `isdigit()` os recusa. Só o guard ASCII contém isso.
- **Neutro onde já funcionava.** Os 64 casos que faziam round-trip saem com wire idêntico. Os
  corrigidos gastam mais bytes, porque deixam de ser comprimidos à custa do dado.

## Varredura da família em `src/tcf`

Todo `isdigit()`, `int()` e `\d` que toca dado ou wire, com veredito. "Wire" quer dizer que o
ponto só lê o que o encoder escreveu; aceitar grafia não canônica ali é E4 (canonicidade), não
round-trip.

| ponto | o que lê | veredito |
|---|---|---|
| `composicional/hcc_seqrle.py`, `find_escape_digit_runs` | dado (corrida escapada) | **corrigido**: só ASCII |
| `natures/int_pad.py`, `classify_value` | dado | **corrigido**: `²`/`①` davam `ValueError` cru; Unicode `Nd` já ia para literal pelo guard de reemissão |
| `natures/int_pad.py`, `decode_value` e `int_pad_para` | wire / detector | **corrigido** junto, mesmo guard |
| `composicional/syntax.py`, `_escape_lit` e scanner de refs | dado e wire | consistente: os dois lados usam `isdigit()`; round-trip exato na sonda e no fuzz. Escapar dígito não-ASCII custa um byte por corrida, sem defeito |
| `composicional/syntax.py`, detecção de wire concatenado | corpo | consistente com `_escape_lit`: valor com dígito Unicode sai escapado, nunca bare |
| `composicional/polaridade.py` | dado e wire | consistente; o fuzz não acha falha |
| `multi/split.py`, `(\d+)` | dado | os campos viajam como texto; round-trip exato nas formas de data e decimal |
| `natures/templated_checked.py` (CPF, CNPJ), `templated_padded.py` (IPv4) | dado | round-trip exato na sonda; a corrupção de `ip` vinha do seq-RLE |
| `composicional/hcc_seqrle.py`, `_contador_declarado` e contador do periódico | wire | **E4 aberto**: aceita `*٢|` num wire forjado; o encoder nunca emite. O contador uniforme já tem o guard |
| `hierarchical.py`, `syntax.py` (contador RLE), `view.py`, `natures/__init__.py` | wire | já guardados por `isascii()`, regex de bytes ou classe explícita |

## Critério de aceite

- [x] Teste vermelho com o repro mínimo e a matriz, nas quatro rotas (4 de 5 falham no código
      antigo; o quinto confere que o seq-RLE ASCII continua comprimindo)
- [x] Varredura da família, com veredito por ponto (tabela acima)
- [x] Correção aprovada pelo owner (I5), gates byte-canônicos verdes sem re-pin, neutralidade
      medida no lab
- [x] Propriedade: todo conjunto `Nd` do interpretador, em sequência de 3 e de 60, round-trip
      exato (`test_todos_os_conjuntos_nd`, roda em toda versão da matriz do CI)

## O que fica fora

- **E4 nos contadores de marcador** do seq-RLE (tabela acima): canonicidade de wire forjado,
  sistemática no `.9` pela escala de verificação. Não perde dado do usuário.
- **Quem usa a `0.8.4`** segue afetado até um release. Patch `0.8.5` não está decidido.
