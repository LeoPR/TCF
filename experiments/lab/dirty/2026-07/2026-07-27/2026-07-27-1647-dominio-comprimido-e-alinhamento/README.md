# 2026-07-27-1647 — Domínio comprimido pelo core + alinhamento de bits

Refino da escada bN a partir de duas observações suas sobre `adult-sex-bn.tcfp`:

```
#TCF.8B164
Male                       ← você viu que isto podia ser  M*ale
Female                     ←                              Fem2
CIhmASAEyQvAQQZokA==
```

## 1. Sim, dá pra comprimir o domínio — e sem código novo

O domínio é uma **mini-coluna**. `_encode_column(dom)` já faz o que você descreveu como
*"aproveitando os índices inter tipos"* — é a tabela de fragmentos do próprio core:

| domínio | cru | pelo core | Δ |
|---|---:|---:|---:|
| `Private`, `Self-emp-not-inc`, … (6) | 69 | 58 | **−11** |
| `2020-01-01`, `-02`, `-03` | 32 | 23 | **−9** |
| `ativo`, `inativo`, `suspenso`, `cancelado` | 32 | 28 | **−4** |
| `Male`, `Female` | 11 | 10 | **−1** |
| `S`, `N` · `AC`,`AL`,…,`ES` | 3 · 23 | 3 · 23 | **0** |

Rende **pouco onde a escada já ganhava fácil** (k pequeno, valor curto) e **mais onde ela
perdia** (k grande com valor longo) — que é exatamente onde o domínio dominava o custo.

**Mas nem sempre ganha**: em domínio minúsculo o core cobra o próprio overhead
(`cnpj-situacao` 354 → **356**, `bool-null` 92 → **93**). Então cru × core é mais um `min()`,
não uma substituição.

## 2. O buraco que a sua pergunta destravou: onde o domínio termina?

Eu tinha assumido "leia k linhas". **Não funciona** — o seq-RLE colapsa o domínio:

| domínio | k | linhas emitidas |
|---|---:|---:|
| `['100','101','102','103']` | 4 | **1** — `*4+1\|\100` |
| `['A1','A2','A3','A4','A5']` | 5 | **1** — `*5+1\|A\1` |
| `['ativo','inativo','suspenso']` | 3 | 3 |

Duas saídas medidas:

| variante | como | custo |
|---|---|---|
| **V-len** | declara o tamanho do domínio no cabeçalho | 2–4 B |
| **V-b64** | põe o **b64 primeiro**; o que sobra é domínio | **0 B** |

O comprimento do b64 é `4·⌈⌈n·w/8⌉/3⌉` — **deduzível de `n` e `w`, que já estão no
cabeçalho**. `V-b64` ganha 2-3 B em todos os casos medidos, e é materialização mínima:
deduz em vez de declarar.

```
#TCF.8B164
CIhmASAEyQvAQQZokA==       ← comprimento DEDUZIDO de n=0x64 e w=1
M*ale
Fem2
```

## 3. O alinhamento — varredura exaustiva, não amostra

`n·w` quase nunca é múltiplo de 8, e o base64 ainda arredonda para múltiplos de 3 bytes. Os
bits do rabo são lixo.

**936 combinações** (`n` de 1 a 40 × `w` de 1 a 6 × 2 montagens × 2 grafias de domínio):
**936/936 reconstruíram os dados originais.**

O rabo não estraga porque `n` viaja no cabeçalho e o leitor para nele — **mas isso é
obrigação do leitor, não propriedade do formato**. Um leitor que desempacotasse até o fim do
buffer devolveria valores fantasma. Se isto for soldado, é teste, não comentário.

Desperdício em bits (≤ 40 bits = 5 B, sempre): ruído em `n` grande, e parte do porquê a
proposta não se paga abaixo de ~5 linhas.

## 4. O foco: bool + 3 a 7 tipos

Você perguntou se **7 seria o limite**. Com o `null` no slot 0: **7 de dado + null = 8 = 2³**.
A fronteira natural é o `w` fechar em 3 bits.

| k | w | usa o `w` inteiro? | slots desperdiçados |
|---:|---:|:-:|---:|
| 2 | 1 | **sim** | 0 |
| 3 | 2 | não | 1 |
| 4 | 2 | **sim** | 0 |
| 5 / 6 / 7 | 3 | não | 3 / 2 / 1 |
| 8 | 3 | **sim** | 0 |

Não é bug — é o preço de largura fixa. `k` potência de 2 é o caso justo; largura variável é
outra conversa.

Medição em n=200 (variante V-b64, melhor entre domínio cru e core):

| coluna | k | w | hoje | melhor bN | Δ |
|---|---:|---:|---:|---:|---:|
| `str-k2` | 2 | 1 | 611 | 57 | **−554** |
| `str-k3` | 3 | 2 | 617 | 98 | **−519** |
| `str-k4` | 4 | 2 | 624 | 108 | **−516** |
| `str-k5` | 5 | 3 | 629 | 148 | **−481** |
| `str-k6` | 6 | 3 | 635 | 157 | **−478** |
| `str-k7` | 7 | 3 | 641 | 166 | **−475** |
| `bool` | 2 | 1 | 612 | 58 | **−554** |
| `bool-null` | 3 | 2 | 589 | 92 | **−497** |

**Cada `+1` em `k` custa ~10 B** (o domínio cresce), enquanto o corpo fica quase igual. O
null nunca custa mais que um slot.

Reais: `cnpj-uf` (k=28) **−4614 B**, `adult-workclass` (k=6) **−116 B**, `adult-sex` **−163 B**.

## O que fica para quando formos soldar

1. **`V-b64`** — b64 primeiro, domínio depois. Custo zero de declaração.
2. **`min(domínio cru, domínio pelo core)`** — mais um candidato, não substituição.
3. **O leitor tem de parar em `n`** — vira teste obrigatório, não comentário.
4. **`k` potência de 2 é o caso justo**; 3, 5, 6, 7 desperdiçam slots por largura fixa.

## Limites

- **Nada soldado**; `src/tcf` intocado. Os `.tcfp` são proposta — o `decode` público não os lê.
- Alinhamento varrido até `n=40` e `w=6`; acima disso não foi varrido exaustivamente.
- **gzip e CPU não medidos.**
- Largura **variável** por valor (para não desperdiçar slots em k=3,5,6,7) não foi estudada.
- Escopo single-col. A decisão pendente de `bN-dense` no `STATUS.md` é multi-col `.8M`.

## Rodar

```
python run.py
```
`dominio.py` tem as duas montagens, as duas grafias de domínio e os **leitores independentes**.
