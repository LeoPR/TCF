# 2026-08-17-1200 — CEP REAL (Receita Federal), e o D5 que faltava

## O que muda em relação ao lab 1000

O lab [`1000`](../2026-08-17-1000-cep-decomposto/) mediu CEP **sintético** e declarou quatro
lacunas. Três caem aqui — e o dado real **inverte duas conclusões**.

## Procedência e coleta

- **Fonte**: Receita Federal, dado aberto. O CEP nunca faltou — a projeção de
  `scripts/setup_receita_cnpj.py` guardava 8 das 30 colunas e **descartava `cep` (índice 18),
  `bairro`, `ddd_1`, `telefone_1`**. Perfil novo `--profile enderecos` → dataset **separado**
  `receita-cnpj-enderecos` (200 000 linhas). O canônico ficou **intocado** (hash e mtime
  conferidos; `tests/test_nature_compete.py` 17 passed).
- **Coleta pelo Shaper** — 200k é teste de massa:
  `ShapeRequest(volume=20000, seed=42, stratify_by="uf")`. Não `LIMIT/OFFSET`.
- **Mix declarado**: SP 29,6% · MG 10,5% · RJ 7,9% · PR 7,3% · RS 6,0% · SC 5,9% · BA 4,4% ·
  GO 4,2% — 28 UFs, n=19 988, **86,9% de CEPs distintos**.

## O dado real confirma a estrutura dos Correios

| verificação | real |
|---|---|
| 8 dígitos numéricos | 99,9% |
| sufixo `000-899` (logradouro) | 98,7% |
| sufixo `900-959` (especiais) | 1,1% |
| `970-989` (unidades dos Correios) | 0,2% |

## Onde mora a entropia — e aqui o sintético estava **errado**

| | reg | sub | set | sse | div | sf1 | sf2 | sf3 | prefixo | sufixo |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| **real** (nacional) | 3,24 | 3,26 | 3,27 | 3,28 | 2,89 | 2,70 | 3,03 | **1,97** | 15,94 | **7,69** |
| sintético (nacional) | 3,31 | 3,14 | 3,21 | 3,32 | 3,32 | 3,31 | 3,32 | 3,32 | 16,30 | 9,95 |

No sintético eu disse: *"o prefixo tem a estrutura, o sufixo é uniforme"*. **No dado real é
quase o contrário.** O prefixo satura (~3,25 em todas as posições) porque a base é nacional; a
estrutura está no **sufixo**, que cai de 9,95 para **7,69 bits**.

A causa, medida:

```
último dígito: 0 -> 65,9%   1 -> 4,2%   2 -> 5,2%   ...
sufixo == '000': 22,2%
```

**Dois terços dos CEPs terminam em zero**, e 22,2% têm sufixo `000` — o *CEP geral* de
cidade/bairro sem logradouro próprio. É uma cauda de zeros que o dado real tem e nenhum
gerador sintético meu produziu.

## As estratégias, em dado real

Baseline **D1** = a grafia mascarada, que é o que o `split` explora.

| estratégia | bytes | B/valor | vs D1 | ordem | modo |
|---|--:|--:|--:|:-:|---|
| D0 opaco (8 dígitos, como a Receita entrega) | 179 891 | 9,00 | +9,4% | sim | `raw` |
| **D1 mascarado `NNNNN-NNN`** | **164 493** | **8,23** | **0,0%** | sim | `split` |
| D2 prefixo+sufixo | 164 463 | 8,23 | −0,0% | sim | `raw`,`dict` |
| **D3 hierárquico (6 colunas)** | 139 520 | 6,98 | **−15,2%** | sim | `tcf`,`dict`… |
| **D4a delta+sort** | **69 429** | **3,47** | **−57,8%** | **NÃO** | `dict` |
| D4b idem + permutação | 101 521 | 5,08 | −38,3% | sim | `dict` |
| D5 resto(7) **cru** + exceção | 173 166 | 8,66 | +5,3% | sim | `raw`,`tcf` |
| **D6 dígito como COLUNA + resto mascarado (sem UF)** | **131 896** | 6,60 | **−19,8%** | sim | `tcf`,`split` |
| D5′ resto MASCARADO + exceção (UF) | 130 259 | 6,52 | −20,8% | sim | `split`,`tcf` |

### As duas inversões

**D3 inverteu de sinal.** No sintético concentrado ele **piorava +20%**; em dado real
**ganha −15,2%**. Motivo: com a base nacional há entropia real em cada nível para o `dict`
explorar, e o overhead das 6 colunas se paga. O sintético concentrado não tinha isso.

**D5 ingênuo piora, D5′ ganha −20,8%.** E a diferença **não é a derivação** — é a máscara:

```
D1 mascarado NNNNN-NNN   164 493 B   modo=split
D0 cru 8 dígitos         179 891 B   modo=raw     <- sem hífen, o split já morre
D5 resto 7 dígitos crus  159 903 B   modo=raw     <- tirei o dígito E a estrutura
D5' resto NNNN-NNN       116 996 B   modo=split   <- máscara preservada, split vivo
```

Ao remover o 1º dígito eu entreguei sete dígitos crus e **matei o `split`**. Preservando o
hífen, a mesma derivação vira **−20,8%, preservando a ordem**.

### A atribuição — corrigida pelo controle D6 (revisão)

O D5′ mistura **dois** mecanismos: (a) separar o 1º dígito preservando a máscara do resto, e
(b) derivar esse dígito da UF. O controle D6 faz **só o (a)** — o dígito vira coluna própria,
sem UF nenhuma:

```
D6  dígito como coluna + resto NNNN-NNN (sem UF)   131 896 B   −19,8%
D5' exceção derivada da UF                         130 259 B   −20,8%
                                     derivação UF =   1 637 B   −1,0 pp  (e pagaria ~107 B de mapa)
```

**A derivação pela UF vale 1,0 pp, não 20,8.** O ganho real é do (a): **reestruturação
dentro da própria coluna** — separar o dígito de região faz os restos de 4 dígitos colidirem
entre regiões (`0 1310…` e `3 1310…` compartilham o resto `1310`), multiplicando a repetição
que o `split`+`dict` exploram. Sem o D6 eu teria repetido a classe de erro do lab 0800:
atribuir ao mecanismo o que é do arranjo.

### O D5 medido, não suposto

**27 de 28 UFs têm região única** — a única ambígua é **SP** (regiões `0` e `1`, capital e
interior), que é justamente 29,6% das linhas. A coluna de exceção custa 13 263 B e cobre isso.

## O que isto encaminha

1. **O empacotamento de raiz continua sendo a estratégia errada** para CEP: D0 = **+9,4%**
   contra o `split`. Confirmado agora em dado real.
2. **O achado acionável é o D6, não o D5′**: **−19,8%, preserva a ordem, e mora dentro da
   própria coluna** — separar o dígito de região e manter a máscara no resto. Não precisa de
   UF ao lado, não precisa de mapa, não cria dependência entre colunas. A redundância
   `uf` → 1º dígito **existe e está medida** (27/28 UFs determinísticas), mas acrescenta só
   **1,0 pp** por cima do D6 — cross-coluna fica registrado como direção, não como achado.
3. **D4a segue o maior ganho** (−57,8%), mas exige `sort_by` e **não preserva a ordem das
   linhas** — decisão de quem usa, não do formato.
4. **D3 passou a valer** em base nacional (−15,2%).

## Não alcançado (declarado)

- **Uma amostra, uma seed.** `seed=42`, `stratify_by="uf"`, n≈20k de 200k. Não varri seeds
  nem volumes — o lab 1000 mostrou que conclusão de mix único não é transferível.
- **A tabela inteira não foi medida** — só a coluna CEP isolada. O ganho dilui quando entra
  no meio das outras 11 colunas (foi o que aconteceu com a nature de telefone: −24,1% na
  coluna, −2,16% na tabela).
- **Telefone real (`ddd_1`/`telefone_1`) veio no mesmo dataset e ainda não foi medido.**
  Fecha a lacuna declarada no levantamento (o "telefone real" era TPC-H, não BR).
- **Custo do D5′ não avaliado**: exige que o encoder conheça a dependência entre colunas.
  Só bytes, nada de CPU.
- **SP ambíguo** é tratado por coluna de exceção; não testei alternativas (ex.: derivar de
  `municipio_cod` em vez de `uf`).

## Conexões

- Lab do sintético que este corrige: [`1000`](../2026-08-17-1000-cep-decomposto/)
- Levantamento: [`notas/2026-08-17-0900`](../../../notas/2026-08/2026-08-17-0900-o-que-falta-pro-8-e-cep-telefone.md)
- Estrutura: [Correios — Tudo sobre CEP](https://www.correios.com.br/enviar/precisa-de-ajuda/imagens/tudo-sobre-cep)
- Coleta: `src/shaper/` · Fonte: `scripts/setup_receita_cnpj.py --profile enderecos`

---

## Revisão (2026-08-17, mesmo dia)

Pedida pelo owner antes de seguir pro telefone. Dois defeitos reais, os dois consertados:

1. **A guarda degradou na cópia.** O `mede()` do lab 1000 validava o ramo `reordena=True`
   contra o **conjunto** (`_remonta_conjunto`); a cópia deste lab trocou isso por
   `assert remonta is None` — que não valida nada. O D4a de 20k valores rodou sem prova.
   Consertado: o ramo agora **exige** `remonta_conjunto` e compara os multiconjuntos; o
   D4a passa com a reconstrução do delta. Lição: **guarda não sobrevive a cópia** — ela
   tem de falhar quando falta, não quando lembrada.
2. **O D5′ estava superatribuído.** Sem o controle D6, os −20,8% iam inteiros pra conta da
   "redundância entre colunas". Medido o controle: **19,8 pp são da reestruturação
   dentro da coluna; 1,0 pp é da UF**. A conclusão do lab foi reescrita (§atribuição).

O que a revisão **não** mudou: os bytes de D0–D5 (idênticos após religar a guarda), a
inversão da entropia (sufixo, não prefixo), a inversão do D3, e as lacunas declaradas.

### Nota de leitura — por que alguns `.tcf` têm **dois** `#TCF.8` dentro

Achado pelo owner ao abrir a evidência. **É design, não defeito.** O modo `split` (V2-C,
[ADR-0026](../../../../../docs/adr/0026-structural-split-weld.md)) quebra a coluna pela máscara
e recomprime os campos resultantes como um **multi-col aninhado** — `split.py:8` descreve o
slot como *"template_blob + field_subtable (`#TCF.8M` — recursa em `_encode_multi`)"*.

Medido nos wires deste lab:

```
#TCF.8M!cep     modo=raw     '#TCF.8' x1
#TCF.8M%cep     modo=split   '#TCF.8' x2   <- o sub-table dos campos
#TCF.8M@delta   modo=dict    '#TCF.8' x1
```

**Só o `split` aninha**, e o wire fecha o round-trip normalmente (19 988 valores, verificado).
O `%` na posição do modo é o que sinaliza.
