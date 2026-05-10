# Dicionario maleavel — principio unificador das tecnicas de compressao TCF

**Data**: 2026-05-12
**Origem**: insight do user — RLE, DICT, prefix-DICT, suffix-DICT,
trie sao todos **variacoes de um mesmo processo fundamental**.

## 1. Tese central

> Todas as tecnicas de compressao por repeticao em TCF (RLE, DICT,
> prefix-DICT, suffix-DICT, trie, affix bidirecional, LZ-family) sao
> **casos particulares de um unico processo**: construir um **dicionario
> maleavel** que descreve padroes recorrentes nos dados, e referenciar
> os dados como combinacoes de entradas do dicionario.

O que varia nao eh o **algoritmo central**, sao **3 parametros**:

1. **Quantidade** de itens a identificar (cardinalidade do dict)
2. **Forma de match** (substring, prefix, suffix, full, n-gram)
3. **Avaliacao de repeticao** (count, frequencia, LCP, contiguidade)

## 2. Mapeamento de tecnicas conhecidas como casos particulares

| Tecnica | Match | Avaliacao | Buffer |
|---------|-------|-----------|--------|
| **RLE** | full + contiguo | count >= 2 contiguos | 1 (streaming) |
| **DICT por valor** (flag D) | full | count >= 2 | N (todo input) |
| **Front Coding** (flag P) | prefix | LCP >= 4 chars | N (sorted) |
| **Suffix sharing** | suffix | LCP-rev >= 4 | N (sorted-rev) |
| **Trie multi-prefix** | prefix hierarquico | count + depth | N (full trie) |
| **LZ77** | substring | janela deslizante | W (window) |
| **Re-Pair** | par mais frequente | freq global | N (greedy) |
| **Sequitur** | par + utility | online | 1 + estado |

**Observacao matematica importante**:

- DICT por valor + matching `full` + buffer infinito = **maximo possivel**
  para padroes exatos.
- RLE = DICT restrito a "match contiguo apenas".
- Prefix-DICT = DICT restrito a "match prefix-only".
- Trie = DICT com **multiplos** prefixos hierarquicos.

Cada tecnica eh um **filtro** sobre o que o DICT geral consideraria.
Filtros mais restritivos = encoder mais simples + decoder mais
simples + razao menor de compressao.

## 3. Modelo unificado

### 3.1 Funcao do encoder

```
encode(values, dict_policy) -> tokens

dict_policy define:
  - match_kind: full | prefix | suffix | substring | ngram | hierarchical
  - eval_threshold: min count, min LCP, min depth
  - buffer_size: 1 (streaming) ate N (batch full)
  - search_direction: forward | backward | bidirectional
  - declaration_strategy: inline | header | ordered_by_first_use
  - reuse_policy: greedy | optimal-batch
```

### 3.2 Funcao do decoder

Decoder reconstroi valores a partir dos tokens + dict. **NAO importa
qual policy o encoder usou** — decoder eh o mesmo.

```
decode(tokens, dict) -> values
```

Single-pass se declaracoes vem antes de refs; 2-pass se refs podem
vir antes (ver secao 5).

## 4. Insight do user — RLE e DICT sao a mesma coisa

User notou:
> "se parar pra pensar, apenas estamos vendo uma variacao do dicionario
> no final das contas"

**Verdadeiro matematicamente**:

- `5*Ana` (RLE) eh equivalente a 5 entradas do dict apontando para "Ana"
- `2*1` (RLE de ref) eh equivalente a 2 refs ao mesmo idx
- `Ana / 1 / 1 / 1 / 1` (DICT puro sem RLE) eh equivalente a `5*Ana`

A diferenca eh **sintatica** — bytes economizados ao agrupar.

**Implicacao para TCF**: nao precisamos de RLE e DICT como "tecnicas
distintas". Podemos ter **um motor unico** que decide se agrupa
contiguos ou nao.

## 5. Decoder out-of-order — refs antes de declaracoes

User observou:
> "o decoder consegue 'esperar' o 2 acontecer"

Cenario:
```
2 bel       # ref idx 2 + "bel"  ← ref antes da decl!
Ana         # decl idx 1 = "Ana"
Anabel      # decl idx 2 = "Anabel"  ← so agora idx 2 existe
1 a         # ref idx 1 + "a"
```

**Possivel se decoder fizer 2-pass**:
1. **Pass 1**: percorrer todas as linhas, colecionando declaracoes
   (linhas que introduzem novo valor literal)
2. **Pass 2**: resolver cada linha tokenizada usando dict completo

**Custo**:
- Memoria: O(N) (guarda linhas pre-tokenizadas)
- Tempo: 2× single-pass (linear)

**Beneficio**:
- Encoder pode emitir na ordem que **mais comprime**, nao na ordem
  literal
- Permite **reordenacao livre** dos tokens

**Tradeoff**: decoder fica ligeiramente mais complexo (2-pass),
encoder ganha flexibilidade.

**Decisao para TCF**: priorizar **decoder simples (1-pass)** como
default. Decoder 2-pass como **opt-in** quando ganho real justificar.

## 6. Orientacao via schema vs heuristica

User identificou 2 modos de operacao:

### Modo A — Schema-orientado (preempt zero)

Schema declara:
```
column: cpf
  type: structured
  pattern: "XXX.XXX.XXX-XX"
  metadata: brazil_cpf
```

Encoder ja sabe:
- Aplicar mascara fixa (separadores `.`, `-`)
- Extrair so dígitos como variaveis
- Sem heuristica = sem custo de adivinhacao

### Modo B — Heuristica-orientado (preempt buffer)

Sem schema, encoder analisa primeiros B itens:
1. Calcula LCP (prefix candidate)
2. Calcula LCP-rev (suffix candidate)
3. Conta cardinalidade dos primeiros B
4. Decide policy baseada nos achados

**Custo computacional do preempt**:
- O(B·L) tempo
- O(B·L) memoria temporaria
- Decisao em ms para B = 100-1000

### Quando usar cada modo

| Cenario | Modo | Razao |
|---------|------|-------|
| Banco relacional com schema | A | esquema sabe metatipos |
| API com OpenAPI / JSON Schema | A | tipos declarados |
| CSV import sem metadata | B | encoder adivinha |
| Stream de logs heterogeneos | B | tipos variam |
| Producao critica | A (forcar schema) | reproduzibilidade |

**Convergencia**: ambos modos chamam **a mesma ferramenta** (motor
unificado). O que muda eh **quem alimenta a policy** (humano via
schema, ou heuristica via buffer).

## 7. Hierarquia de metatipos (Schema-orientado avancado)

User propos: schema com **metatipos** alem de tipo Python:

```
column types:
  base: int | float | str | bool | datetime
  meta: cpf | cnpj | uuid | email | url | mac | ip | code | name | text
```

Cada metatipo tem **policy default**:

| Metatipo | match | direcao | mascara |
|----------|-------|---------|---------|
| cpf | structured-mask | XXX.XXX.XXX-XX | sim |
| cnpj | structured-mask | XX.XXX.XXX/XXXX-XX | sim |
| uuid | structured-mask | 8-4-4-4-12 hex | sim |
| email | suffix | (pelo `@`) | nao |
| url | prefix | (`https://...`) | parcial |
| mac | structured-mask | XX:XX:XX:XX:XX:XX | sim |
| ip | structured-mask | X.X.X.X | sim |
| code | prefix-or-trie | LCP | nao |
| name | full-DICT | nenhuma | nao |
| text | RLE-only | nenhuma | nao |

Encoder usa metatipo para escolher policy direta, sem heuristica.

## 8. Algebra do "buffer tamanho ajustavel"

User formalizou: buffer pode ser **1** (streaming puro) ate **N**
(batch full). Tradeoff:

```
B = 1  → streaming, O(N) tempo, O(1) memoria, razao sub-otima
B = √N → buffer medio, O(N·√N) tempo, O(√N) memoria, razao 80-90%
B = N  → batch full, O(N·log N) tempo, O(N) memoria, razao otima-greedy
```

**Insight do user**: nao ha tradeoff real para N pequeno (< 100k em
RAM moderna) — batch full eh viavel em ms.

Tradeoff aparece em:
- N >= 1M (memoria pode estourar)
- Hard real-time (microsegundos)
- Streams continuos (nao tem "fim do dataset")

## 9. Versao rapida vs versao otima — a mesma ferramenta

```
ferramenta(values, schema=None, buffer=auto, latencia_max=None)
```

Decisao do `buffer`:
- Se `latencia_max` definido: escolher maior B que cabe no orcamento
- Se `schema` define metatipo: pular preempt, ir direto para policy
- Senao: B = min(N, 1024) com preempt heuristico

A **mesma chamada** retorna:
- **modo rapido** se latencia eh tight
- **modo otimo** se ha tempo

Sem dois algoritmos diferentes — **um motor parametrizavel**.

## 10. Convergencia: TCF v0.5 unifica tudo via flags + policy

A gramatica atual ja tem flags:

```
S — sort
R — RLE
D — DICT
M — auto-discrim
P — prefix-DICT (Etapa 1)
A — alfabeto adaptativo
δ — delta
Π — packed
I — inline
```

A nova teoria sugere: **todas essas flags sao policies do motor
unificado**. Encoder escolhe quais ativar baseado em:
1. Schema fornecido (metatipo guia)
2. Heuristica de preempt (buffer pequeno)
3. Override do usuario (flag explicita)

A ferramenta **nao muda** — muda **a politica**.

## 11. Implicacao para implementacao

### O que NAO precisa mudar

- `encoder.py` ja tem estrutura de flags
- `decoder.py` ja tem 1-pass linear
- Gramatica formal ja eh consistente

### O que pode evoluir

1. **Refatorar** encoder para que cada flag seja uma "policy plugin"
2. **Adicionar** `preempt(values)` que decide policy automatico
3. **Adicionar** suporte a `schema={"col": {"meta": "email"}}`
4. **Adicionar** `latency_budget` parameter

### O que NAO precisa fazer agora

- Refatoracao prematura — deixar para quando ferramenta amadurecer
- Implementar todos os metatipos — comecar com 2-3 (cpf, email, code)

## 12. Pendencias para investigar (proxima sessao)

1. **Heuristica de preempt** — qual buffer minimo descobre tipo
   confiavelmente? (testar B = 10, 50, 100, 1000)
2. **Custo do preempt** — em que ponto a sobrecarga compensa o ganho?
3. **Decoder 2-pass para refs out-of-order** — vale a pena?
4. **Hierarquia de metatipos** — onde declarar (schema) e como
   resolver default
5. **API publica** — `encode(values, schema=...)` ou
   `encode(values, policy=...)` ou ambos?

## 13. Sintese — visao unificada

O que estamos construindo nao eh "varias tecnicas de compressao", eh
**uma ferramenta de dicionario maleavel** com policies parametrizadas.

```
Input: values + (schema | buffer)
        ↓
preempt: decide policy (ou usa schema)
        ↓
motor unificado: aplica policy
  ├── match_kind (RLE / DICT / prefix / suffix / mask)
  ├── eval (count / freq / LCP)
  ├── buffer (1 / W / N)
  ├── direction (forward / backward / bidirectional)
  └── declaration (inline / header / first-use)
        ↓
emit tokens + dict
        ↓
Output: TCF v0.5 conforme gramatica
```

Decoder reconstroi sem se importar com a policy — mesmo motor de
parsing.

**Esta visao simplifica o pensamento e a implementacao**: em vez de
debater "qual algoritmo eh melhor", debatemos **qual policy aplicar
quando**.

## 14. Proximas etapas (apos esta teorizacao)

Conforme protocolo do documento de teoria anterior:

- **Etapa 1 (algebra)**: ESTE DOCUMENTO concluido
- **Etapa 2 (lab dirty)**: ja temos labs com RLE/DICT/prefix/suffix/trie.
  Falta lab que **demonstra unificacao** com policy parametrizavel.
- **Etapa 3 (lab clean)**: matriz formal com 5 classes × 3 seeds.
  Fazer **apos** lab unificador da Etapa 2.
- **Etapa 4 (escala)**: stress test em datasets reais grandes.
- **Etapa 5 (promover)**: integrar ao core como "policy-based encoder".

## 15. Decisao registrada

NAO promover trie/affix/etc ao core como flags separadas. Em vez
disso:

1. **Aceitar** que existe **um motor unico** com policies
2. **Mapear** flags atuais (R, D, P, etc.) como policies pre-definidas
3. **Adicionar** schema-orientacao como caminho preferencial
4. **Implementar** preempt heuristico como fallback

Isso **simplifica** implementacao + **abstrai** decisoes
algoritmicas + **prepara** para v0.6+ com mais metatipos.

## 16. Documentos relacionados

- [2026-05-12-teoria-compressao-strings.md](2026-05-12-teoria-compressao-strings.md) — fundamentacao teorica + literatura
- [2026-05-09-padroes-estruturais-em-strings.md](2026-05-09-padroes-estruturais-em-strings.md) — insight inicial sobre CPF/UUID/etc
- [experiments/lab/dirty/2026-05-12-affix-trie/](../../experiments/lab/dirty/2026-05-12-affix-trie/) — implementacao trie 6 variantes
- [experiments/lab/dirty/2026-05-11-affix-implicit-bidir/](../../experiments/lab/dirty/2026-05-11-affix-implicit-bidir/) — implementacao bidir simples
