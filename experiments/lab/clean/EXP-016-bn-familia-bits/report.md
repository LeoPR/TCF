# EXP-016 — família bN/bits: bateria sintética completa [probatório]

**72 casos** em 11 famílias. Cada um declara o que espera **antes** de rodar; o lab falha quando não acontece.

## As cinco provas, por caso

| prova | o que garante |
|---|---|
| **RT estrito** | valor + tipo + sinal + comprimento, contra os dados originais |
| **determinismo** | `encode` duas vezes → byte-idêntico |
| **nunca-pior** | o wire com bN nunca é maior que o wire sem bN |
| **correção ≠ bN** | o core sozinho também faz RT — o bN é opção de TAMANHO |
| **o artefato é o wire** | o `.tcf` em disco, em binário, == o wire medido |


## F1 bool/binário

| caso | rota | bytes | sem bN | espera | veredito | por que existe |
|---|---|---:|---:|:-:|:-:|---|
| `bool-nativo` | tipado-b | 47 | — | recusa | OK | bool Python puro: o modo denso `b1` tem domínio IMPLÍCITO e deve vencer o bN |
| `bool-nativo-null` | tipado-b | 79 | — | recusa | OK | com null o denso `b1` não se aplica; quem cobre é o `b2`/lazy |
| `bool-constante-true` | tipado-b | 16 | — | recusa | OK | k=1: o core resolve com RLE; o bN nem se qualifica |
| `str-01` | bN-B | 54 | 607 | ativa | OK | o caso que abriu a investigação: `"0"`/`"1"` como STRING |
| `str-01-null` | bN-B | 90 | 557 | ativa | OK | `"0"` como dado E o slot nulo na mesma coluna — a colisão que custou 4 bugs |
| `str-sn` | bN-B | 50 | 605 | ativa | OK | binário não-numérico: nenhum escape de dígito envolvido |
| `str-true-false` | bN-B | 57 | 612 | ativa | OK | as PALAVRAS que o denso usa implicitamente, mas como string de dado |
| `int-01` | bN-B-tipado-n | 55 | — | ativa | OK | `0`/`1` como int: rota tipada `n` COM bN (weld T-BN-TIPADO) — 608 B viraram 55 |

## F2 null

| caso | rota | bytes | sem bN | espera | veredito | por que existe |
|---|---|---:|---:|:-:|:-:|---|
| `null-so` | core | 14 | 14 | recusa | OK | coluna 100% null: k=1, o core resolve com RLE |
| `null-um-so` | core | 16 | 16 | recusa | OK | 1 null em N-1 iguais: k=2 mas RLE domina |
| `null-metade` | bN-B | 94 | 510 | ativa | OK | null alternado — exerce o slot 0 no meio do stream |
| `null-e-vazio` | bN-B | 85 | 537 | ativa | OK | null E string vazia na MESMA coluna: dois 'nadas' que não podem se fundir |
| `null-e-zero` | bN-B | 54 | 507 | ativa | OK | o par crítico mínimo: slot nulo (`0` cru) × literal `"0"` (`\0`) |
| `null-e-zero-e-escape` | bN-B | 94 | 542 | ativa | OK | os TRÊS: null, `"0"` e `"\0"` — a injetividade de `_grafa` no limite |

## F3 bordas

| caso | rota | bytes | sem bN | espera | veredito | por que existe |
|---|---|---:|---:|:-:|:-:|---|
| `n-zero` | core | 7 | — | recusa | OK | coluna vazia: `[]` tem grafia própria (`#TCF.8\n`) |
| `n-um` | core | 9 | 9 | recusa | OK | 1 valor: k=1 |
| `n-dois` | core | 11 | 11 | recusa | OK | k=2 com n=2: o cabeçalho+domínio não se pagam |
| `n-dez-k2` | bN-B | 18 | 35 | ativa | OK | n=10 é ~onde o bN passa a ganhar (medido no lab 1608) |
| `k-256` | bN-B | 730 | 1212 | ativa | OK | k=256 = 2^8: o TETO do namespace, w=8 |
| `k-257` | core+pol | 1217 | 1217 | recusa | OK | k=257: PASSA do teto — o bN deve recusar e o core assumir |
| `k-3-folga` | bN-B | 85 | 604 | ativa | OK | k=3 com w=2: sobra 1 slot — é onde o guard de largura NÃO pega slot extra |

## F4 espaços

| caso | rota | bytes | sem bN | espera | veredito | por que existe |
|---|---|---:|---:|:-:|:-:|---|
| `espaco-simples` | bN-B | 50 | 605 | ativa | OK | o valor É um espaço |
| `espaco-borda` | bN-B | 89 | 608 | ativa | OK | espaço no início/fim/ambos: o core NÃO faz strip (regressão conhecida) |
| `tab-e-espaco` | bN-B | 86 | 605 | ativa | OK | tab é whitespace mas não é o separador do formato |
| `so-vazio` | core | 13 | 13 | recusa | OK | todos vazios: k=1 |
| `vazio-no-fim-do-dominio` | bN-B | 84 | 603 | ativa | OK | string vazia como ÚLTIMO valor do domínio — o bug do `rstrip` (2026-07-28) |

## F5 número

| caso | rota | bytes | sem bN | espera | veredito | por que existe |
|---|---|---:|---:|:-:|:-:|---|
| `zeros-a-esquerda` | bN-B | 93 | 609 | ativa | OK | `0`, `00`, `000` são valores DISTINTOS — não podem colapsar |
| `numero-negativo` | bN-B | 92 | 608 | ativa | OK | `-0` × `0`: distintos como string |
| `notacao-cientifica` | bN-B | 99 | 615 | ativa | OK | três grafias do mesmo número — distintas como string |
| `hex-e-prefixo` | bN-B | 97 | 613 | ativa | OK | o que `int(x,16)` aceitaria no cabeçalho, mas aqui é DADO |
| `digito-nao-ascii` | bN-B | 90 | 608 | ativa | OK | dígito árabe-índico e sobrescrito: `str.isdigit()` aceita, o formato não deve confundir |
| `underscore-numerico` | bN-B | 60 | 615 | ativa | OK | PEP 515: `int('1_000')` funciona — como dado são distintos |

## F6 cabeçalho

| caso | rota | bytes | sem bN | espera | veredito | por que existe |
|---|---|---:|---:|:-:|:-:|---|
| `imita-magic` | bN-B | 56 | 611 | ativa | OK | o valor É o magic do formato |
| `imita-wire-bn` | bN-B | 62 | 616 | ativa | OK | o valor é um CABEÇALHO bN completo |
| `imita-marcador` | bN-B | 55 | 609 | ativa | OK | o valor começa com o marcador `=` que abre o bloco de bits |
| `imita-marcador-escapado` | bN-B | 92 | 608 | ativa | OK | o valor É a forma ESCAPADA do marcador — a inversa não pode desfazer demais |
| `imita-referencia` | bN-B | 91 | 610 | ativa | OK | o valor parece referência de linha do core |
| `imita-rle` | bN-B | 98 | 616 | ativa | OK | o valor parece marcador RLE / seq-RLE |
| `imita-b64` | bN-B | 95 | 614 | ativa | OK | o valor É base64 válido — não pode ser confundido com payload |

## F7 escape

| caso | rota | bytes | sem bN | espera | veredito | por que existe |
|---|---|---:|---:|:-:|:-:|---|
| `todos-os-especiais` | bN-B | 130 | 605 | ativa | OK | os 6 chars da gramática do corpo, um por valor |
| `escape-duplo` | bN-B | 95 | 613 | ativa | OK | 1, 2 e 3 barras: a injetividade sob repetição |
| `escape-mais-digito` | bN-B | 93 | 611 | ativa | OK | `\1` (literal) × `1` (que o core escaparia) — a colisão de grafia |
| `circunflexo-lider` | bN-B | 95 | 614 | ativa | OK | `^` líder é escapado à parte pelo core |
| `til-e-asterisco` | bN-B | 93 | 612 | ativa | OK | os separadores dentro do valor |

## F8 tipos

| caso | rota | bytes | sem bN | espera | veredito | por que existe |
|---|---|---:|---:|:-:|:-:|---|
| `float-simples` | bN-B-tipado-n | 93 | — | ativa | OK | float k=3 na rota tipada `n` com bN: a grafia canônica vira domínio |
| `float-integral` | bN-B-tipado-n | 59 | — | ativa | OK | float que parece int no `repr` |
| `float-neg-zero` | bN-B-tipado-n | 96 | — | ativa | OK | `-0.0 == 0.0` em Python: só o `copysign` distingue |
| `misto-int-float` | bN-B-tipado-n | 98 | — | ativa | OK | int e float na MESMA coluna |
| `bool-vs-int` | — | — | — | qualquer | fail-loud | `True == 1` em Python. FRONTEIRA DECLARADA: união bool+int no mesmo slot está fora do `.8H` (ratificada 2026-07-17) — tem de falhar alto, não deduplicar em silêncio |
| `int-grande` | bN-B-tipado-n | 74 | — | ativa | OK | int além de 64 bits |
| `nan` | — | — | — | qualquer | fail-loud | NaN: fora do JSON (RFC 8259) — deve FALHAR ALTO |
| `inf` | — | — | — | qualquer | fail-loud | ±Inf: idem |

## F9 unicode

| caso | rota | bytes | sem bN | espera | veredito | por que existe |
|---|---|---:|---:|:-:|:-:|---|
| `acentuado` | bN-B | 98 | 617 | ativa | OK | acentos: 2 bytes por char em UTF-8 |
| `emoji` | bN-B | 90 | 609 | ativa | OK | 4 bytes por char — o domínio paga, o corpo não |
| `cjk` | bN-B | 100 | 619 | ativa | OK | 3 bytes por char |
| `zero-width` | bN-B | 90 | 609 | ativa | OK | zero-width space: invisível mas distinto |

## F10 bN×RLE

| caso | rota | bytes | sem bN | espera | veredito | por que existe |
|---|---|---:|---:|:-:|:-:|---|
| `dom-seqrle-colapsa` | bN-B | 89 | 605 | ativa | OK | o seq-RLE colapsa o domínio inteiro em `*4+1\|@` — 4 valores, 1 linha |
| `dom-seqrle-alfanum` | bN-B | 121 | 601 | ativa | OK | idem com prefixo: `*5+1\|A` |
| `dom-datas-incrementais` | bN-B | 103 | 620 | ativa | OK | domínio que o seq-RLE encadeia — o caso mais realista do colapso |
| `dom-prefixo-comum` | bN-B | 110 | 629 | ativa | OK | domínio que o OBAT/HCC fatora por afixo, sem seq-RLE |
| `dom-sem-estrutura` | bN-B | 95 | 611 | ativa | OK | domínio que NÃO comprime — o custo dele é o cru |
| `corpo-rle-vs-bn` | core | 21 | 21 | recusa | OK | corpo perfeitamente RLE-ável (2 blocos): o core faz `*100\|a`+`*100\|b` e VENCE o bN |
| `corpo-rle-parcial` | bN-B | 50 | 455 | ativa | OK | blocos de 3 iguais: RLE parcial contra bits fixos |

## F11 fronteira

| caso | rota | bytes | sem bN | espera | veredito | por que existe |
|---|---|---:|---:|:-:|:-:|---|
| `fronteira-n08` | bN-B | 17 | 29 | ativa | OK | n=8: a vizinhança da virada em k=2 (medida em ~10 no lab 1608) |
| `fronteira-n09` | bN-B | 18 | 32 | ativa | OK | n=9: a vizinhança da virada em k=2 (medida em ~10 no lab 1608) |
| `fronteira-n10` | bN-B | 18 | 35 | ativa | OK | n=10: a vizinhança da virada em k=2 (medida em ~10 no lab 1608) |
| `fronteira-n11` | bN-B | 18 | 38 | ativa | OK | n=11: a vizinhança da virada em k=2 (medida em ~10 no lab 1608) |
| `fronteira-n12` | bN-B | 18 | 41 | ativa | OK | n=12: a vizinhança da virada em k=2 (medida em ~10 no lab 1608) |
| `fronteira-len01` | bN-B | 87 | 603 | ativa | OK | len(valor)=1 com k=4: o teto real é `k x len(valor)`, não `k` |
| `fronteira-len08` | bN-B | 98 | 614 | ativa | OK | len(valor)=8 com k=4: o teto real é `k x len(valor)`, não `k` |
| `fronteira-len16` | bN-B | 106 | 622 | ativa | OK | len(valor)=16 com k=4: o teto real é `k x len(valor)`, não `k` |
| `fronteira-len32` | bN-B | 122 | 638 | ativa | OK | len(valor)=32 com k=4: o teto real é `k x len(valor)`, não `k` |

## Resultado

- casos: **72**
- falhas: **0**

## Contraprova agregada

- o bN **ativou** em 58 dos 72 casos; nos demais o FLOOR escolheu o core, o denso ou o tipado — e **em nenhum** o wire ficou maior;
- **em todos** os casos de rota flat, o core sozinho também faz RT: o bN nunca é necessário para correção, só para tamanho;
- `encode` é determinístico em 100% dos casos.

