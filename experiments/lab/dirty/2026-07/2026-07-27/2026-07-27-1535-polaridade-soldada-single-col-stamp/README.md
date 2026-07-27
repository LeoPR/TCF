# 2026-07-27-1535 — A polaridade SOLDADA (single-col stamp)

Os quatro labs que precederam este (`1853`/`1913`/`1954`/`2126`) **propunham**: o mecanismo
vivia no lab e os artefatos eram `.tcfp`, que o núcleo não lia. Aqui ele está em `src/tcf`
(ADR-0035), e **os `.tcf` em `outputs/` são wires de verdade** — o `decode` público os lê.

```
outputs/cpf-mascara-antes.tcf      outputs/cpf-mascara-depois.tcf
#TCF.8                             #TCF.8!!
\000.\000.\000-\00                 000.000.000-00
\001.\007.\013-\01                 001.007.013-01
```

O *antes* é reconstruível **byte a byte** sem checkout: a grafia anterior era exatamente
`'#TCF.8\n' + _encode_column(dados)`, porque o corpo canônico não mudou — só ganhou uma
camada de borda. A comparação é exata, não estimada.

## A — antes × depois, 33 colunas

**Ativa em 21, recusa em 12. Ganho somado −6663 B. Pior caso +0 B. RT 33/33.**

| coluna | n | antes | depois | Δ |
|---|---:|---:|---:|---:|
| `cpf-mascara` | 200 | 3807 | 3009 | **−798** |
| `cartao` | 200 | 4805 | 4008 | **−797** |
| `timestamp` | 200 | 4539 | 3899 | **−640** |
| `cnpj-mascara` | 200 | 3947 | 3411 | **−536** |
| `isbn` | 200 | 3688 | 3203 | **−485** |
| **`pessoas-cpf`** (real) | 100 | 1907 | 1509 | **−398** |
| `cep` | 200 | 2404 | 2010 | **−394** |
| **`cnpj-doc`** (real) | 200 | 3000 | 2849 | **−151** |
| **`retail-stockcode`** (real) | 200 | 1240 | 1164 | **−76** |
| **`tpch-phone`** (real) | 20 | 400 | 335 | **−65** |
| `texto`, `frase`, `nomes`, `email`, `sem-digito` | 200 | — | — | **0** |
| **`lineitem-comment`**, **`retail-description`** (real) | 200 | — | — | **0** |
| `vazia`, `uma-linha`, `so-vazio` | 0-1 | — | — | **0** |

## B — o FLOOR, contado

Nenhuma coluna sai maior: o FLOOR inclui o custo do próprio sufixo e o empate fica com a
grafia de hoje. As 12 que recusam recusam por **contagem**, não por regra de tipo:

| motivo | colunas |
|---|---|
| 0 corridas de dígito literal — nada a economizar | `texto`, `frase`, `nomes`, `sem-digito`, `lineitem-comment`, `ibge-municipio` |
| escapes não pagam as transições + o sufixo | `email` (257), `binario-01` (2), `uma-linha` (1), `retail-description` (21) |
| coluna vazia / valor vazio | `vazia`, `so-vazio` |

O `email` é o caso instrutivo: **257 escapes e mesmo assim recusa**. Fluxo muito alternado —
`user1234@d5.com` troca de estado a cada valor. Não é o número de escapes que decide, é o
número de **transições**.

## C — os três gates byte-canônicos

| gate | pinado | medido |
|---|---:|---:|
| **D1-D9** | 1545 | **1545** |
| **D17a** (multi `.8M`) | 300 | **300** |
| **real-world** (3 × 2k) | 89430 | **89430** |

Dos 9 datasets do D1-D9, a polaridade tocou **2** (D5 −21, D6 −20). O `D17a` **não mudou** —
o `.8M` está fora do escopo declarado do weld, e o gate confirma que a solda ficou onde foi
dito que ficaria.

## D — a auditoria adversarial virou regressão

Os dois defeitos de eleição que a auditoria do lab `2126` reproduziu, re-rodados contra o
código soldado:

| caso | quebrava assim | agora |
|---|---|---|
| dígito eleito | `0` eleito **funde** com a corrida (`1\22.\33` → `1022.33`) | `#TCF.8:` — char `:`, RT OK |
| letra eleita | `b` eleito emite `#TCF.8b`, byte-idêntico ao cabeçalho de uma coluna **bool** | `#TCF.8{` — char `{`, RT OK |

`FAIXA` = ``!"#$%&'()+-./:;<=>?@[]_`{}`` — 26 chars, nem dígito nem letra nem gramática. A
exclusão é por **classe**, então continua fechada quando surgir tag nova.

Os dois wires estão em `outputs/adversarial-*.tcf`.

## Limites

- **Só o single-col stamp e o tipado.** `.8M`, `.8H`, spec e órfão (`stamp=False`) estão
  fora do weld — o `D17a` intacto é a evidência disso, não uma omissão.
- `n` de 200 (ou menos, onde a fixture é menor). Suficiente para comportamento e gate;
  não é benchmark.
- As colunas reais vêm de `datasets/samples/` — nenhum download.
- **Aberto** (ADR-0035): delimitador como grafia canônica **interna**, que exigiria o
  seq-RLE localizar o dígito incrementável pela polaridade em vez de pelo escape.

## Rodar

```
python run.py
```
Sai `0` só se: RT 33/33, pior caso ≤ 0, e os 3 gates batendo.
