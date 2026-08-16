# Resultado — o header tem um piso, e o piso É a garantia de paralelismo

7 colunas, 500 registros, **0 falhas**, as **6 invariantes passaram** (incluindo decode
paralelo real em 7 threads, idêntico byte a byte ao `decode()` público).

---

## 1. A tensão entre os dois pedidos, e como o projeto já a resolveu

*"Tirar o máximo de explicitudes do header"* e *"fechar os limites de coluna pra preparar
paralelismo"* **puxam para lados opostos** — e isso não é achado deste lab, está decidido:

- **O-FMT-19 tentou** trocar byte-size por row-count e foi **REFUTADO**: *"custa TUDO: o lazy
  perde acesso O(1) por coluna, perde **decode paralelo** (bytes deixam fatiar; linhas forçam
  scan sequencial) e group por slice"*.
- **O-FMT-11 fechou** o header como **near-optimal**: *"cada campo é load-bearing pro decode
  independente"*.

**Os byte-sizes SÃO o mecanismo de paralelismo.** Tirar explicitude tem um piso, e o piso é
exatamente a garantia que o owner quer preparar. Este lab não reabre — mede.

---

## 2. O piso, re-verificado pós-welds

O-FMT-11 mediu em 2026-07-05, antes do `:id` (ADR-0041), do split `%` e do FLOOR da nature.
Hoje a fórmula é a mesma:

```
header = 7 (magic `#TCF.8M`) + Σ|size_hex| + (ncols−1) vírgulas + marcadores + 1 LF
```

2 colunas anônimas hoje: **12 B** (`#TCF.8M!3,!`) — O-FMT-11 mediu 13 B com size de 2 hex.
**Mesmo piso.**

Break-even com dado realista (2 colunas do cadastro):

| N | wire | header | header % |
|---:|---:|---:|---:|
| 5 | 149 | 11 | 7,4% |
| 20 | 551 | 11 | 2,0% |
| 100 | 2.438 | 13 | 0,5% |
| 500 | 9.843 | 12 | 0,1% |

Mesma forma da curva de O-FMT-11 (39% → 1,3%). **O header só pesa em payload minúsculo.**

> ⚠️ Correção de método no próprio lab: a primeira versão da curva usava `v0..vN`, que é
> progressão — o seq-RLE esmaga o corpo, ele não cresce, e a curva mentia (N=20 e N=100 davam
> o mesmo wire). Refeita com dado real.

### O que os welds novos cobraram

| | header |
|---|---:|
| sem spec | 79 B |
| com spec (`:id`) | 82 B |
| com spec + `drop_names` | **39 B** |

**O `:id` custou +3 B de header e devolveu 4.450 B de corpo** — 1.483× de retorno. O header
cresceu, e cresceu bem.

---

## 3. As 6 invariantes de fronteira — todas testadas, todas passam

| # | invariante | resultado |
|---|---|---|
| **I1** | o plano de fatiamento sai **só da linha 1** (82 B), sem tocar em byte de corpo | 7 colunas, OK |
| **I2** | independência — decodar uma coluna não lê byte de outra | OK |
| **I3** | ordem livre — decodar embaralhado dá o mesmo resultado | OK |
| **I4** | **paralelismo real** — 7 threads, resultado idêntico ao `decode()` | **OK** |
| **I5** | a última é a única que depende de EOF; `min_header=False` zera isso | OK |
| **I6** | o plano é completo: Σ sizes (20.450) + última (514) = corpo (20.964) | OK |

O plano derivado só do header:

```
id          tcf              [0:15)
nome        tcf          [15:2661)
cpf         raw   :cpf  [2661:5660)
email       tcf         [5660:12845)
telefone    split      [12845:18407)
nascimento  split      [18407:20450)
ativo       dict         [20450:EOF)
```

**I4 é a prova que faltava**: o decode paralelo não precisa de nada novo no formato. Foi
orquestração externa sobre as funções que já existem (`_parse_meta` + `_decode_raw_body` /
`_decode_v2b` / `_decode_struct_split` / `_decode_column`), com `src/tcf` intocado.

---

## 4. O caminho barato — e ele custa 4 bytes

**`min_header=False` é a chave de perfil "pronto para paralelo/stream":**

| | colunas que dependem de EOF | custo |
|---|---:|---:|
| `min_header=True` (default) | 1 (a última) | — |
| `min_header=False` | **0** | **+4 B (+0,019%)** |

Quatro bytes compram *"toda coluna é fatiável sem conhecer o fim do blob"*. Para decode
paralelo isso é indiferente (o blob chegou inteiro); **para decode em STREAM é o que
destrava** — com a última sem size, ela só pode ser decodada no EOF.

O kwarg já existe e já é testado. Não é mudança de formato, é escolha de perfil.

---

## 5. A anatomia do que resta explícito — e o que é removível

Cadastro, 7 colunas, com spec. A soma bate exatamente com a linha 1 (82 B), nada sobra:

| campo | B | removível? |
|---|---:|---|
| magic `#TCF.8M` | 7 | não — roteamento; o `M` é deduzível (−1 B, O-FMT-11 chamou de marginal) |
| **sizes (hex)** | **18** | **NÃO** — é o plano de fatiamento (O-FMT-19 refutado por matar o paralelo) |
| **nomes** | **37** | **SIM** — `drop_names`; mas a ordem vira o contrato (lab `1450` P2) |
| modos `!@%` | 4 | não — o corpo não se auto-identifica |
| nature `:id` | 4 | opt-in — `T-SPEC-SEM-CARIMBO`, desenhado, falta weld |
| separadores `,` `=` | 12 | não — gramática |

**Os nomes são 45% do header** e são o único campo grande removível. `drop_names` leva 82 → 39
B. O preço está medido no lab `1450`: a ordem passa a ser o contrato, e reordenar troca os
donos dos valores calado.

---

## 6. View/lazy — olhada leve (por decisão do owner, fica pro fim)

Só o que toca a fronteira:

- o `view` usa **o mesmo `_parse_meta`** (`view.py:117`) — paridade por construção;
- os sizes que ele reporta **batem com o plano deste lab**;
- ele materializa **0 B ao abrir** (`touched=[]`) — **o header é o único coldstart,
  confirmado por medição**, exatamente como o owner formulou.

**Não investigado** (deliberadamente): as 8 formas de wire que ele recusa (lab `0800`), o
bypass aritmético (`T-LAZY-BYPASS-ARITMETICO`) e o `where` posicional
(`T-VIEW-PRED-POSICIONAL`).

---

## 7. O que isto fecha, e o que fica

**Fecha**: o header do `.8M` está no piso e o piso é justificado; o paralelismo de decode não
precisa de nada no formato (6 invariantes provam); o perfil stream-ready custa 4 B.

**Fica aberto, e nenhum é byte-tweak**:
1. **O-FMT-14 (header derivável)** — o único lever grande restante, e é feature de contrato.
2. **`T-SPEC-SEM-CARIMBO`** — tirar o `:id` do fio (−4 B aqui), desenhado, falta weld.
3. **`T-META-COLISAO-NOME-POSICIONAL`** — o guard de 1 linha (lab `1450` P4).
4. **A união dos candidatos** (`T-UM-CAMINHO-SO`) — que é de corpo, não de header.
