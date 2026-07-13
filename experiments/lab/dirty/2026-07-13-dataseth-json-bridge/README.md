# R0/R1 — ponte JSON para DatasetH

**Status**: pesquisa/POC · **Data**: 2026-07-13

Este lab testa a primeira fronteira do caminho hierárquico:

```text
JSON -> DatasetH -> JSON
```

Ele não implementa `#TCF.8H`, não importa `src/tcf` e não propõe `encode_json`. O objetivo é separar a
semântica de uma árvore intermediária do parser da fonte e do codec TCF.

`NaN` e `Infinity` são rejeitados neste POC apenas para manter a baseline do JSON padrão. Essa rejeição não
é o contrato final do DatasetH: o estudo aberto em
[dataseth-hierarquia-completa-plano.md](../notas/dataseth-hierarquia-completa-plano.md) compara folhas
tipadas, domínio `bN` e strings especiais escapadas antes de qualquer mudança neste código ou no core.

## Modelo provisório

`DatasetH` tem um único `root`, que pode ser:

- `HObject`: sequência ordenada de campos `(nome, filho)`;
- `HArray`: sequência ordenada de itens;
- `HScalar`: folha `string`, `integer`, `number`, `boolean` ou `null`.

A ausência de um campo é diferente de uma folha `null`. Objetos vazios, arrays vazios e arrays com objetos
ragged são valores presentes. O adaptador JSON rejeita chaves duplicadas para evitar que a política de
"última chave vence" fique escondida no contrato. `NaN` e `Infinity` também são rejeitados porque não são
valores JSON padrão.

A construção com `from_python` representa uma segunda origem possível. Ela não é uma API do TCF: é apenas
uma forma de provar que o mesmo DatasetH pode ser alimentado sem passar por `json.loads`.

## O que o POC preserva

- topologia de objeto, array e folha;
- ordem dos campos e itens;
- tipos básicos dos escalares;
- `null` versus ausência;
- vazios e arrays ragged;
- strings com LF após o parse.

A saída JSON é normalizada por `json.dumps`; whitespace, escape equivalente e forma lexical original de
números não são preservados. Isso é equivalência estrutural/semântica, não byte identity do documento.

## Executar

Na raiz do repositório:

```powershell
python experiments/lab/dirty/2026-07-13-dataseth-json-bridge/run.py
```

Saída esperada:

```text
DatasetH root: HObject
JSON -> DatasetH -> JSON: PASS
Python source -> DatasetH equivalence: PASS
duplicate-field policy: reject
NaN/Infinity policy: reject
TCF codec: intentionally not exercised
```

## Próxima etapa

Este lab fecha apenas o entendimento inicial do parser e do intermediário. A próxima etapa é comparar a
representação com flatten (`pandas.json_normalize`), arrays nested de Arrow e eventos de `ijson`, depois
construir `DatasetH -> TCF.H -> DatasetH` fora de `src/tcf`. O modelo e as políticas acima permanecem
provisórios até essa comparação.

## Stage 1 (2026-07-13) — codec TCF.H: **hierarquia primeiro, tipos depois**

Realiza a metade "construir `DatasetH -> TCF.H -> DatasetH` fora de `src/tcf`" da próxima etapa, na
ordem do owner: **primeiro a lógica de hierarquia** (topologia + identidade de folha, RT-exato);
tipos/variações ficam para o stage 2. Arquivos (aditivos; não tocam `dataset_h.py`/`run.py`/`src/tcf`):

- **`codec_h.py`** — `encode_h(DatasetH) -> str` (`#TCF.8H`) e `decode_h(str) -> DatasetH`, **fail-loud**
  (`TCFHDecodeError`, nunca corrompe calado).
- **`run_codec.py`** — RT nos fixtures R0/R1 + **matriz de falsificação** (22 casos de topologia/presença/
  escalar básico) + distinctness + fail-loud. Gera `artifacts/`.

Rodar (raiz do repo): `python experiments/lab/dirty/2026-07-13-dataseth-json-bridge/run_codec.py`.

**Forma de wire (provisória — POC, NÃO a gramática weldada; isso é decisão P5)**: stream **por-instância**,
preorder, length-prefixed onde o conteúdo é arbitrário:

```
#TCF.8H\n
  O<n>\n (K<blen>\n<key> node){n}   objeto (campos ordenados)
  A<n>\n (node){n}                  array (itens ordenados)
  Z\n | T\n | F\n                   null / true / false
  I<digits>\n | N<repr>\n           integer / number (RT-exato via repr)
  S<blen>\n<utf8-bytes>             string (blen = BYTES; conteúdo arbitrário)
```

Por que **por-instância** e não o header-schema do EXP-015/ADR-0031: árvores JSON gerais são
**irregulares** (ragged, arrays mistos, array-de-array) — um schema estático no header só serve *nesting
regular*. O header-schema (com def/repetition levels à la Dremel) é uma **representação de stage 2** para
dados regulares; a correção vem primeiro.

**Coberto (RT-exato, 22/22 + fixtures)**: objetos/arrays/nesting/ordem, containers vazios (`{}` vs `[]`),
`null` vs ausência vs `""` vs `"null"`, `1`(int) vs `1.0`(number) vs `"1"`(string), ragged, array-de-array,
strings que soletram estrutura, **`\n` dentro de string** (a lacuna que o `#TCF.8M` rejeita — resolvida
por length-prefix), Unicode, raiz escalar, deep-nesting.

**Adiado para stage 2 (tipos & variações)** — alinhado ao plano
[dataseth-hierarquia-completa-plano.md](../notas/dataseth-hierarquia-completa-plano.md) (P2/P5):

- escalares especiais `NaN`/`+Inf`/`-Inf` (POC rejeita) e identidade de `-0.0` / `NaN` reflexivo;
- formas lexicais de número (`1e3` → valor `1000.0`; preserva **valor**, não léxico);
- **compressão/fatoração** (OBAT/HCC por folha, dedup de subárvore repetida, RLE) — o stage 1 é
  correção, não bytes;
- a **representação mínima** (bracket-header/def-levels do ADR-0031) e base/hex (cross
  `T-FMT-HEADER-BASE-HEX`);
- comparação A/C/B/D das representações de tipo (P2 do plano).

Contra-prova completa em `artifacts/02-rt-counterproof.txt`; wire de amostra em `01-wire-sample.txt`;
matriz valor→wire em `03-falsification-matrix.txt`.
