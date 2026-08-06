# `dataset → json lib → dataset` × `dataset → TCF → dataset` (2026-08-01-0309)

Régua empírica pro futuro **modo-json** do TCF. Dados: `outputs/matriz.csv`, `outputs/alteracoes.json`, `outputs/knobs-nan-medidos.json`.

## A matriz, em 4 grupos (+ exceções)

**(a) ambos preservam — 15**: `col-int`, `col-float`, `col-bool`, `col-str`, `col-null`, `int-x-float`, `neg-zero`, `int-gigante`, `dict-vazio`, `lista-vazia`, `str-unicode`, `chave-unicode-nfd`, `escalar-none`, `escalar-int`, `escalar-str`

**(b) json ALTERA/perde e TCF PRESERVA — 0**: nenhum

**(c) json aceita e TCF REJEITA — 11**: `nan`, `inf`, `uniao-bool-str`, `uniao-num-str`, `chave-int`, `chave-none`, `chave-bool`, `tuple-em-lista`, `str-lf`, `chave-float`, `chave-nan`

**(d) ambos rejeitam — 1**: `bytes-em-lista`

**⚠ fora da malha esperada — 2**: `chave-duplicada`, `chave-vazia` — ver detalhe na matriz.

### Detalhe dos casos que NÃO são (a)

| caso | json lib | TCF |
|---|---|---|
| `nan` | PRESERVA: — | ERRO: HierarchicalError: NaN/Infinity fora do JSON (RFC 8259) — não é P2 |
| `inf` | PRESERVA: — | ERRO: HierarchicalError: NaN/Infinity fora do JSON (RFC 8259) — não é P2 |
| `uniao-bool-str` | PRESERVA: — | ERRO: HierarchicalError: tipos escalares MISTOS {'s', 'b'} numa coluna — union/tipo-misto no mesmo slot está fora do #TCF.8H (fronteira declarada, ratificada 2026-07 |
| `uniao-num-str` | PRESERVA: — | ERRO: HierarchicalError: tipos escalares MISTOS {'s', 'n'} numa coluna — union/tipo-misto no mesmo slot está fora do #TCF.8H (fronteira declarada, ratificada 2026-07 |
| `chave-int` | ALTERA: obtido={'1': 'a'} | ERRO: HierarchicalError: chave de objeto deve ser str, veio int (1) — fora da classe D_json (o json coage chaves p/ str e o round-trip perde: loads(dumps(x)) != x) |
| `chave-none` | ALTERA: obtido={'null': 'a'} | ERRO: HierarchicalError: chave de objeto deve ser str, veio NoneType (None) — fora da classe D_json (o json coage chaves p/ str e o round-trip perde: loads(dumps(x)) |
| `chave-bool` | ALTERA: obtido={'true': 'a'} | ERRO: HierarchicalError: chave de objeto deve ser str, veio bool (True) — fora da classe D_json (o json coage chaves p/ str e o round-trip perde: loads(dumps(x)) !=  |
| `chave-duplicada` | PRESERVA: texto='{"a": 1, "a": 2}' -> parse={'a': 2} | NÃO-EXPRESSÁVEL: dict Python nao tem chave duplicada |
| `tuple-em-lista` | ALTERA: obtido=[[1, 2], [3, 4]] | ERRO: HierarchicalError: valor escalar de tipo não suportado: tuple |
| `bytes-em-lista` | ERRO: TypeError: Object of type bytes is not JSON serializable | ERRO: HierarchicalError: valor escalar de tipo não suportado: bytes |
| `chave-vazia` | PRESERVA: — | ALTERA: obtido={'0': ['a', 'b']} [warning: coluna com nome vazio '' tratada como ANONIMA — o decode retorna o nome posicion] |
| `str-lf` | PRESERVA: — | ERRO: ValueError: valor com quebra de linha (\n) nao e' representavel no TCF (LF delimita linhas): indice 0: 'a\nb' |
| `chave-float` | ALTERA: obtido={'1.5': 'a'} | ERRO: HierarchicalError: chave de objeto deve ser str, veio float (1.5) — fora da classe D_json (o json coage chaves p/ str e o round-trip perde: loads(dumps(x)) !=  |
| `chave-nan` | ALTERA: obtido={'NaN': 'a'} | ERRO: HierarchicalError: chave de objeto deve ser str, veio float (nan) — fora da classe D_json (o json coage chaves p/ str e o round-trip perde: loads(dumps(x)) !=  |

## 1. A matriz comentada

- **(a) ambos preservam — 15 casos.** O núcleo estável: tipados puros, `int × float` (o Python distingue `1` de `1.0` na volta E o TCF preserva pela grafia — `_cast_tipo` tenta `int` antes de `float`), `-0.0` (ambos preservam o sinal — o json via grafia `"-0.0"`, o TCF idem), int gigante (ambos preservam em Python), vazios, unicode NFD, escalares na raiz.
- **(b) json ALTERA e TCF PRESERVA — 0 casos.** **VAZIO — e isso é o achado central**: TODAS as perdas da lib Python (coerção de chave, tuple→list, dup-key last-wins) acontecem em casos que o TCF **rejeita**, não preserva. O conjunto onde o modo-json alertaria 'TCF preserva o que o json perde' é hoje vazio no single-shot; ele só ganha corpo com as rotas NOVAS (lazytype união, futuro modo-json) e com a leitura cross-ecossistema (ver §2).
- **(c) json aceita e TCF REJEITA — 11 casos.** O TCF é mais estrito que a lib Python em 3 famílias: **NaN/±Inf** (a lib emite `NaN`/`Infinity`, EXTENSÃO fora da RFC 8259, e lê de volta — o default é permissivo; o TCF é RFC-strict), **união mista** (a lib preserva de graça; o `.8H` recusa escalares mistos — o caso central do lazytype `bB`), **tuple** (a lib serializa como array perdendo o tipo; o TCF fail-loud), **chave não-string** (a lib COAGE silenciosamente `1`→`"1"`, `None`→`"null"`, `True`→`"true"`, `1.5`→`"1.5"`, `nan`→`"NaN"` — perda DENTRO do Python; o TCF fail-loud com mensagem que já cita a coerção do json), **str com `\n`** (a lib escapa `"\n"` de graça; o TCF recusa LF embutido porque LF delimita linha).
- **(d) ambos rejeitam — 1 caso.** `bytes`: lib `TypeError` ('not JSON serializable'); TCF `HierarchicalError` ('tipo não suportado').

### ⚠ Os 2 casos fora da malha

- **`chave-vazia` `{"": [...]}` — o único caso onde o TCF ALTERA**: o encoder trata nome vazio como coluna ANÔNIMA e **avisa** (`UserWarning`), e o decode devolve o nome posicional `"0"` — `{"": ...}` volta `{"0": ...}`. Não é corrupção silenciosa (há warning), mas é **perda com RT quebrado**: candidato a ticket (fail-loud em vez de warning, ou preservar `""` como nome).
- **`chave-duplicada` `{"a": 1, "a": 2}`**: a lib faz **last-wins silencioso** (`{'a': 2}`) — perda que o TCF nem deixa EXPRESSAR (dict Python não tem chave duplicada). Categoria própria: perda da lib sem equivalente no dataset.

## 2. O catálogo de alertas do modo-json (filosofia SideOutputs: só ALERTA, nunca arruma)

O grupo (b) vazio desloca o catálogo: os alertas úteis são sobre o que o TCF **preserva e um consumidor json TIPICO perderia ou rejeitaria** (lib estrita, outro ecossistema) — detectável DE GRAÇA no encode (pré-pass/`column_features` já varrem a coluna):

- **união mista por coluna** — hoje fail-loud; quando uma rota a aceitar (lazytype), alertar: 'json lib preserva, mas consumidores tipados (schemas estritos) rejeitam união'. Detecção: `len({type(x) for x in col}) > 1`.
- **distinção int × float** (`1` × `1.0`) — TCF e lib Python preservam; **JS/**number fundem os dois. Alerta cross-ecossistema: 'coluna mista int/float; fora do Python a distinção se perde'. Detecção: presença de ambos os tipos numa coluna `n`.
- **int > 2^53** — TCF e lib preservam; JS/number perde precisão. Alerta: 'inteiro acima de 2^53; cross-ecossistema, usar string'. Detecção: `abs(x) > 2**53` no pré-pass.
- **NaN/±Inf** — TCF rejeita (RFC-strict); a lib Python ACEITA por default. Alerta simétrico no modo-json: 'input contém NaN/Inf; o json de referência (allow_nan=False, RFC) também rejeitaria — rejeitando como ele'.
- **chave não-string / tuple / chave duplicada** — a lib coage/perde silenciosamente; o TCF já rejeita. No modo-json o alerta é o próprio fail-loud, com mensagem citando a perda que o json faria (o TCF já faz isso na mensagem de chave não-str).
- **string com `\n`** — a lib escapa de graça; o TCF rejeita. Alerta: 'json serializaria com `\\n`; TCF não representa LF embutido'.

## 3. Ambíguos — onde 'fugir pro json' é a resposta

- **Ordenação de chaves de dict**: lib Python preserva a ordem de inserção; a RFC não garante; o TCF multi-col preserva a ordem das colunas. Se um dia houver reordenação (sort_by), o comportamento json (ordem de inserção) é a âncora.
- **int → float coercion** (`loads('1.0')` é float, `loads('1')` é int; nenhum coage): o TCF segue a mesma regra pela grafia — já alinhado, manter.
- **Escalar solto na raiz**: lib aceita (`42`, `"x"`, `null`); o TCF aceita e preserva (medido). Alinhado.
- **Chave unicode NFC × NFD**: a lib preserva os CODE POINTS (não normaliza); o TCF idem (medido: NFD preservado). A âncora é 'não normalizar', como a lib.

## 4. RFC × lib × dataset — onde o corpus evidenciou divergência

- **NaN/±Inf: lib > RFC.** A RFC 8259 não tem `NaN`/`Infinity`; a lib Python emite e lê por default (extensão). Knobs medidos (`outputs/knobs-nan-medidos.json`): `allow_nan=False` rejeita no dumps; `parse_constant` rejeita no loads. **A lib tem os dois comportamentos; o default é o permissivo.** TCF hoje = RFC-strict.
- **Chave duplicada: RFC permite, lib perde.** A gramática não proíbe (é 'SHOULD' de unicidade); a lib faz last-wins calada. O dataset Python nem expressa.
- **Chave não-string: dataset Python permite, lib mutila.** `{1: 'a'}` é Python válido; o dumps COAGE a chave pra `"1"` e o loads não reverte — a perda é DENTRO do Python, sem aviso. O TCF fail-loud com mensagem que cita exatamente isso ('o json coage chaves p/ str e o round-trip perde').
- **tuple: dataset permite, lib converte.** tuple → array, sem aviso e sem volta.

## Notas de método

- Vereditos por `cmp_estrito`: deep `==` + tipo, chaves inclusas; `-0.0` por `copysign`; NaN==NaN aceito.
- json lib = `json` do Python 3 (default permissivo). Cross-ecossistema (JS, schemas estritos) é NOTA, não medido aqui.
- `src/tcf` intocado; nada soldado.

