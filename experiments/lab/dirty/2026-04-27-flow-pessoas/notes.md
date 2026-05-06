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

---

## CICLO 2 — analise critica das observacoes do usuario

Rodado com `run-2.py`. Saida em `output-v2/`.

### Achado 1 — Bug do CSV com line endings (cycle 1)

**Causa**: `csv.DictWriter` default coloca `lineterminator='\r\n'`.
Em Windows, `Path.write_text(text)` em modo texto **traduz cada `\n`
para `\r\n`**. Resultado: cada `\r\n` no buffer vira `\r\r\n` ou `\r\n\n`
no arquivo. **Cada linha ficava com 1 byte extra.**

**Demonstracao** (10 linhas + header):

| Variante | Bytes | Line endings observados |
|----------|-------|------------------------|
| **Bug ciclo 1** | 217B | `\r\n\n` (3 bytes/linha — bugado) |
| LF puro | 195B | `\n` (1 byte/linha — Linux) |
| CRLF puro | 206B | `\r\n` (2 bytes/linha — RFC 4180 / Windows) |

**Solucao**: `io.StringIO(newline="")` + `csv.DictWriter(buf,
lineterminator="\n")`. **Sempre forcar line ending explicito.**

### Achado 2 — JSON variantes

| Variante | Bytes | Uso |
|----------|-------|-----|
| `json.dumps(rows, separators=(",", ":"))` | 301B | producao / minimo |
| `json.dumps(rows, indent=2)` | 422B | inspecao humana (+40%) |
| JSONL (1 obj/linha) | 299B | streaming, append-friendly |

**Boa pratica**: usar JSON compact por default (`separators=(",", ":")`).
Pretty so quando humano vai ler. **JSONL e melhor que JSON array para
datasets grandes** — permite append sem reler tudo.

### Achado 3 — TCF L3 forcado vs SMART (auto-bypass) — IMPORTANTE

**Caso atual** (10 strings unicas, 1 coluna):

| Modo | Effective level | Bytes |
|------|-----------------|-------|
| TCF L0 | L0 | 229B |
| TCF L2 (forcado) | L2 | 275B (+46B vs L0) |
| TCF L3 (forcado) | L3 | 308B (+79B vs L0) |
| **TCF L3 SMART** | **L0 (auto-bypass)** | **229B** |

**Decisao**: encoder pediu L3 mas detectou que DICT **piora** o
resultado nesse cenario. Fallback automatico para L0 mantendo o
**conteudo mais compacto**.

**Razao**: para 10 strings unicas, DICT inclui todos os 10 valores
verbatim na linha de cabecalho + 10 indices na coluna. Bytes totais:
overhead-cabecalho-DICT + bytes-indices > bytes-strings-diretas.

**Proposta para v0.4**:
```python
EncodeConfig(level=3, auto_bypass=True)
# Encoder tenta L3, mede; tenta L2, mede; usa o menor.
# Marca o nivel efetivo no header: "level=2 (requested=3, auto-bypass)"
```

Conceito "compressao adaptativa" — usuario pede max, encoder usa
inteligencia. Default `auto_bypass=True` em v0.4 talvez.

### Achado 4 — Cabecalho v0.4 com encoding/line-ending

**Proposta**:
```
# TCF v0.4 level=2 encoding=utf-8 line-ending=LF
# (legacy v0.2 body follows)
... corpo TCF v0.2 ...
```

**Por que**:
- `encoding=utf-8` explicito permite consumidores em outras linguagens
  (JS, Go, Rust) saber sem assumir
- `line-ending=LF|CRLF|CR` permite consumidor saber se eh
  Windows/Linux/Mac legacy
- Versao explicita (`v0.4`) para tooling fazer parsing correto

**Custo**: +59B no header. Pequeno em datasets reais (vol >100), mas
pesado em datasets nano. Talvez:
- v0.4 default: header expandido
- Flag `--terse-header` para nano/micro: header so com `# TCF v0.4 L=2`

### Achado 5 — Quando emitir cada line-ending

Encoder TCF (v0.4) deveria aceitar:
```python
EncodeConfig(line_ending="auto")    # detect platform (default)
EncodeConfig(line_ending="LF")       # Linux/macOS — recomendado
EncodeConfig(line_ending="CRLF")     # Windows tools / RFC 4180
EncodeConfig(line_ending="CR")       # Mac legacy (raramente)
```

`"auto"` na pratica deveria ser **LF** sempre — eh universal e mais
compacto. CRLF so quando explicitamente pedido para integrar com
ferramentas Windows-only.

### Achado 6 — Tabela completa final (10 supplier names, 1 coluna)

| Formato | Bytes | Observacao |
|---------|-------|------------|
| **CSV LF puro** | **195** | menor de todos |
| CSV CRLF | 206 | RFC 4180 (Windows tools) |
| CSV bug ciclo 1 | 217 | line endings duplicados (corrigir) |
| TCF L0 | 229 | raw columnar |
| TCF L3 SMART | 229 | auto-bypass para L0 (correto!) |
| TCF L2 | 275 | RLE+STATS sem ganho aqui |
| JSONL | 299 | stream-friendly |
| JSON compact | 301 | overhead de keys |
| TCF L3 forcado | 308 | DICT verbose (sem ganho real) |
| TCF v0.4 c/ header | 334 | +cabecalho explicito |
| JSON pretty | 422 | so para humanos |

**CSV LF e ainda o vencedor neste cenario MIN** (1 coluna, 10 strings
unicas). TCF nao deveria ser usado aqui — recomendacao do encoder
inteligente: "para este dataset, considere CSV simples".

### Decisoes para TCF v0.4 (lista consolidada)

1. **auto_bypass=True por default**: encoder decide nivel real
2. **line_ending="LF" por default** (universal, compacto)
3. **encoding=utf-8 explicito** no cabecalho v0.4
4. **terse_header=False por default**, mas opt-in para datasets nano
5. **Documentar quando NAO usar TCF** (ex: 1 coluna single-row)
6. Validacao: encoder pode emitir warning quando outputs sao maiores
   que CSV equivalente

### Compressao "interdados" (char-level overlap)

Confirmado:
- **TCF v0.2 atual nao captura** overlap "Supplier#" repetido
- Capturar isso seria **char-level compression** (BWT, LZ77, suffix
  arrays)
- **Decisao**: NAO incluir no TCF core — gzip/brotli fazem isso bem
  via meta-programa
- Se quisermos no TCF, e v0.5+, nao v0.4

### Quebras de linha — analise para v0.4

CSV/TCF dependem de linhas como delimitador estrutural. Quebras de
linha "bagunca" (mistura LF + CRLF + CR) **quebra parsers**. Logo:

- **Encoder v0.4** deve sempre emitir line_ending **uniforme** (sem
  mistura)
- **Decoder v0.4** deve aceitar **qualquer line_ending** (ler tanto
  LF quanto CRLF; CR legacy opcional)
- **Cabecalho v0.4** declara qual o consumidor deve esperar

Esta e a discrepancia entre **what we EMIT** vs **what we ACCEPT**.
Robust principle (Postel's Law): "be conservative in what you do,
liberal in what you accept".

### Proximo ciclo (sugestao)

Antes de virar EXP-003 formal:

- **Workbench 3**: dataset com **categoricals repetidos** (ex: extrair
  `s_nationkey` em vez de `s_name` — so 24 valores em 100 linhas).
  Aqui RLE deveria realmente acionar e TCF L2 deveria vencer CSV.
- **Workbench 4**: testar **multi-coluna** com tipos mistos. Validar
  que CSV perde tipos no roundtrip mas JSON e TCF v0.4 (com `# TYPES`
  header) preservam.

Se workbenches 3+4 confirmarem hipoteses, ai sim promover para
**EXP-003-format-comparison-real** com hipoteses limpas.

