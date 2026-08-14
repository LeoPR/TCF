# Resultado — os gatilhos do int em 39 colunas numéricas reais

39 colunas descobertas automaticamente nos hubs de `Z:/tcf-data`, medidas nas duas ordens
(78 medições), **0 falhas de round-trip**. Este lab fecha a lacuna que os três labs
sintéticos declararam.

## O agregado

**245.094 B → 217.670 B = 11,2% menor** (ordem natural, somando as 39 colunas com o melhor
mecanismo de cada). Em **18 das 39**, ninguém bate o núcleo.

## Quem ganha, e quanto

| mecanismo | vence com ganho real | mediana | máx | empates (≤1 B) |
|---|---:|---:|---:|---:|
| **PAD** | 21 | **1,72×** | **2,73×** | **0** |
| **B94** | 22 | 1,14× | 1,39× | **33** |
| `min_len` | **0** | — | — | 2 |

A contagem bruta de vitórias enganava: o B94 "vencia" 72% das colunas, mas **33 dessas
vitórias são de um byte ou menos** — o `min()` o escolhendo por desempate. Com ganho real,
ele fica em 1,14× de mediana. O **PAD é o mecanismo que vale**: mediana 1,72×, máximo 2,73×,
e **nenhum empate** — quando ganha, ganha de verdade.

Os maiores ganhos são em chaves: `o_orderkey` (123 → 45 B, 2,73×), `p_partkey` e `c_custkey`
(1,72×). São colunas de progressão com largura variável — exatamente o gatilho do PAD.

## Segunda reversão minha: o `min_len` não se confirma

Ontem eu inverti minha própria recomendação e disse que o `min_len` *"resolve 3 dos 5 casos e
resolve melhor"*. **Neste corpus ele não ganha em nenhuma coluna** — zero ganho real, dois
empates.

A explicação, e ela importa: os três casos em que ele brilhava (epoch, base alta `1e9+i`,
`2⁶³+i`) são **regimes que este corpus não tem**. As 39 colunas são chaves, quantidades,
tamanhos e IDs — nenhuma é timestamp Unix nem número de base alta. Timestamps são comuns em
dados reais; só não estão *aqui*.

Então o enunciado honesto não é "o `min_len` não serve", é: **neste corpus ele não aparece**,
e o corpus tem viés declarado (ver `datasets-provenance.md` — 25 das 39 colunas são TPC-H).
O que fica medido é que ele **não é prioridade para este perfil de dado**.

## Meus gatilhos estão mal calibrados — e isso é achado sobre o desenho

| gatilho | disparou | acertou | mas o mecanismo venceu |
|---|---:|---:|---:|
| `gat_PAD` | 11 | 9 | 10 vezes |
| `gat_B94` | **2** | 2 | **28 vezes** |
| `gat_min_len` | 1 | **0** | 1 vez |

O do PAD está bom. O do **B94 subestima grosseiramente** — eu o defini como "sem progressão +
largura fixa + cardinalidade > 0,5", e ele venceu 28 vezes porque comprime qualquer coluna de
largura fixa, com ou sem progressão. O do `min_len` não previu nada.

Isso é informação de projeto: **a auto-detecção que eu propus para o `.9` não funcionaria
como está**. Se o spec for auto-detectado, os gatilhos precisam ser recalibrados contra este
corpus — ou o FLOOR decide sozinho, sem gatilho nenhum, que é o que ele já faz bem.

## Achado de carona: `min_len` também é recusado na rota tipada

O lab produziu isto antes de rodar:

```
encode([1,2,3], min_len=12)
→ ValueError: kwargs ['min_len'] só valem no flat de STRING
```

Mesma classe do `nature=`. **A rota tipada é fechada para os dois mecanismos que o int
precisa** — o spec e o tuning do núcleo. Some-se isso ao `T-NATURE-IGNORADA-CALADA` e ao item
1 da lista de conformidade: não é só o spec que falta na porta tipada.

## O que isso recomenda

1. **O PAD é o alvo que vale** — 1,72× de mediana em dado real, gatilho bem calibrado, e é
   auto-contido. Se for soldar um spec de int, é esse.
2. **O B94 é marginal neste perfil** — 1,14× de mediana e 33 empates. Não descartar (ele
   brilha em ids de largura fixa de 11 dígitos, medido 1,52× no lab sintético), mas não é o
   caso de abrir por ele.
3. **O `min_len` fica para quando houver corpus com timestamps** — o regime existe, este
   corpus não o tem.
4. **Abrir a rota tipada** para `nature=` e `min_len=` é pré-requisito de qualquer um dos
   três: hoje o caminho natural do inteiro não aceita nenhum deles.

## Ressalvas

- **Viés do corpus**: 25 das 39 colunas vêm de TPC-H (sf001 e sf01), que é um gerador
  sintético de benchmark com muitas chaves sequenciais. Isso **favorece o PAD**. As colunas
  independentes (IBGE, retail, wine, br-identidades, receita) são 14.
- Os números de PAD/B94/`min_len` incluem **+1 byte** do discriminador `n`, que é o que um
  mecanismo na rota tipada pagaria. Medi-los na rota string e não somar seria comparar
  wires que não se emitem.
- Dirty: conclusão **orientativa**.
