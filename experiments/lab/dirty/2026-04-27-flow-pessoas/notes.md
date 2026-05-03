# Workbench sujo — flow inicial com pessoas

**Data**: 2026-04-27
**Status**: em exploracao

## O que estamos testando

O flow basico **antes de virar experimento formal**:

1. Pegar dados reais via Shaper (nao sintetico)
2. Extrair APENAS uma coluna simples (nome de pessoa-like)
3. Encode em 4 formatos: CSV, JSON, TCF L0, TCF L2, TCF L3
4. Cada encode gera arquivo `.txt`/`.csv`/`.tcf`/`.json` para inspecao visual
5. Decode cada um (exceto L3 que e schema-only)
6. Output decodificado vira novo arquivo
7. Comparar input × output

## Por que workbench sujo

- Estamos validando o **flow**, nao gerando resultado cientifico ainda
- Pode quebrar, pode ser refeito
- Se funcionar, vira EXP-003 ou similar no `clean/`
- Apagar essa pasta nao perde nada importante

## Decisoes desta exploracao

### Dataset
- TPC-H sf001 supplier (`s_name`) — 100 linhas
- Nomes sao `Supplier#000000001..` (pseudo-formato canonical TPC-H)
- Nao tem overlaps tipo "ana/banana" — ok para flow, nao para
  testar compressao interdados ainda

### Single column
- Comecando MUITO simples: 1 coluna `name` (str)
- Sem tipos mistos (sem int/bool) — descobrir overhead minimo
- Linha 1: cabecalho/header. Linha 2..N: nomes.

### Pipe duplo (tee)
- Implementado no script do workbench (nao no TCF core)
- Cada encode escreve em arquivo + retorna string para decode
- Permite inspecao visual lado-a-lado de todos os formatos

## Compressao "interdados" (ideia futura, NAO fazer agora)

User mencionou: se temos "ana" e "banana", potencial de compressao
ao detectar substring repetida ("an", "na").

**Registrado para futuro**:
- Tipo de compressao avancada (pos-RLE/DICT atuais)
- Nao implementar ainda; precisa primeiro estabilizar o resto
- Se for pra fazer, ficaria como **"BWT-like"** ou **"LZ77 char-level"**
  no encoder TCF v0.4+ ou v0.5

## Tipagens (proximo workbench)

Apos este workbench validar o flow simples, criar outro com:
- Multipla colunas com tipos (int, str, bool, float)
- Comparar:
  - CSV (sem tipos) + dedutor
  - JSON (com tipos)
  - TCF (sem tipos no v0.2; com `# TYPES` header em v0.4 proposto)

## Como rodar este workbench

```bash
python experiments/lab/dirty/2026-04-27-flow-pessoas/run.py
```

Saida em `output/` com todos os arquivos gerados (encoded + decoded).

## Achados do workbench (apos rodar)

### Flow funcionou — pipe duplo simples implementado
A funcao `tee_write(path, text)` escreve em arquivo E retorna a string,
permitindo encadear inspecao + decode. Conceito provado.

### Roundtrip 4/4 OK em formatos com dados
- csv, json, tcf-L0, tcf-L2: roundtrip EXATO em 10 nomes Supplier#NNN
- tcf-L3: schema-only — retornou 10 rows com indices DICT, nao
  os nomes originais. Comportamento esperado.

### Bytes (10 nomes simples, 1 coluna)
| Formato | Bytes | vs CSV |
|---------|-------|--------|
| **csv** | **217B** | baseline |
| tcf-L0 | 247B | +13% |
| tcf-L2 | 294B | +35% |
| json | 301B | +46% |
| tcf-L3 | 328B | +51% |

**Observacao**: nesse cenario MIN (1 coluna, 10 strings unicas), CSV
vence todos. Faz sentido:
- json repete `{"name":` 10 vezes
- tcf-L0 adiciona header + nome de coluna em linha (overhead constante)
- tcf-L2 = L0 + linha "# N*val ..." extra (sem RLE acionar — strings
  unicas)
- tcf-L3 inclui DICT verbose (todos os 10 nomes inteiros) + indices

### TCF L2 sem ganho aqui — por que?
- Nomes sao **todos unicos** (Supplier#000000001 != #00000002)
- RLE precisa de runs iguais consecutivos. Nao ha
- DICT tambem nao ajuda — cardinalidade = N
- STATS para coluna string e so cardinality + samples — pouco util

**Cenario ideal para TCF nao foi este.** Para 10 strings unicas, CSV
vence. TCF brilha em **categoricos baixa cardinalidade** (vimos isso
em EXP-002 com `categorical_heavy`).

### Compressao "interdados" mencionada pelo user

Ana/banana exemplo. Nesta amostra ha overlap claro:
- "Supplier#" repete em todos os 10 nomes (10 prefixos identicos)
- "00000000" + digito final repete (8 zeros depois "Supplier#")

Compressao char-level (BWT, LZ77) capturaria isso. **TCF v0.2 nao
captura** (RLE eh por valor, nao por substring).

Para v0.4 ou v0.5: pensar se vale ter compressao char-level antes
de emitir. Hoje, esse trabalho fica para gzip/brotli (que fazem LZ77
em texto).

### Inspecao visual dos arquivos

`output/03-tcf-L0.tcf` e o mais legivel — bem proximo de CSV mas com
header columnar. `output/05-tcf-L3.tcf` e mais "denso" (DICT na linha
de cabecalho + indices na coluna).

**Boa decisao de design**: o usuario pode abrir qualquer arquivo
gerado em editor e entender. Validacao da legibilidade.

### Decisoes para proximo workbench

1. Usar dataset com **categoricos repetidos** (ex: 'sex', 'workclass'
   do Adult Census) para mostrar onde TCF brilha
2. Usar dataset com **multiplas colunas** para validar layout columnar
3. Adicionar **tipos**: int + float + bool + str para testar
   detect_types do CSV/JSON e como TCF lida com numerica

### Ideia validada: workbench pattern

Esta pasta `dirty/2026-04-27-flow-pessoas/` cumpre seu papel:
- Comprovou flow basico
- Detectou que cenario 1-coluna-strings-unicas e MIN para TCF
- Gerou arquivos para inspecao manual
- Custo: 0 (sem dependencias novas)

Quando promover para `clean/`: criar EXP-003 com hipotese mais clara
e datasets adequados (multi-coluna + categoricos).

