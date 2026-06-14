# Futuras otimizacoes de formato — registro central

**Criado**: 2026-05-17
**Origem**: discussao apos EXP-010 (single-column prototype welded);
user listou varias direcoes pra multi-column/ordering/streaming que
**nao misturamos com a implementacao atual** mas precisam ser
registradas pra retomada futura.

**Regra**: este doc e' o ponto de registro de **otimizacoes ortogonais
ao compressor core**. Cada uma e' candidata a sub-experimento, lab
proprio, ou ticket formal quando o trabalho core estiver concluido.

## Categoria 1 — Ordenacao de colunas / linhas

### O-FMT-01 — Ordenacao reversivel pra compressao

**Ideia**: se formato de entrada e' fixo, aplicar ordenacao de
colunas/linhas que **aumenta a chance de compressao** antes do
encode, com **mapeamento reverso** salvo no .tcf pra reverter no
decode.

**Trade-off**: bytes extras no header (pra mapeamento) vs bytes
economizados no body. Vale se body savings > header cost.

**Status**: aberta, nao testada. Registrada aqui.

**Antecedentes**:
- [`docs/workbench/_archive/tickets/closed/17-T-shaper-ordering.md`](../../../../docs/workbench/_archive/tickets/closed/17-T-shaper-ordering.md)
  — ticket de shaper distinguia "ordem de apresentacao" (consumer)
  de "ordem interna de compressao" (TCF). A interna nao foi tratada
  no shaper; fica pra ca'.

### O-FMT-02 — Ordenacao natural (sem mapeamento reverso)

**Ideia**: quando user nao se importa com ordem, ordenar linhas pra
maximizar compressao. **Bytes nao ficam identicos byte-a-byte** ao
input, mas **dados ficam iguais** (mesma row, ordem livre).

Caso comum: relatorios analiticos onde ordem nao tem semantica
(ex: lista de produtos).

**Status**: aberta. Decisao tem que ser explicita do user (qual
ordem aceitar).

### O-FMT-03 — Multi-order

**Ideia**: tentar varias ordens (natural, sort col A, sort col B,
etc.), escolher menor body. **Multi-pass** pelo dataset.

**Trade-off**: viola single-pass. So' vale se o ganho compensar.
Pode-se limitar a N orders pre-determinadas.

**Status**: aberta. Custo alto (multi-pass).

### O-FMT-04 — Coluna agnostica vs coluna-aware

**Ideia**: ordenar baseado em UMA coluna pode ajudar OUTRAS colunas
(se ha' correlacao). Ex: ordenar por "estado" pode beneficiar
"cidade" (cidades agrupadas).

**Status**: aberta. Depende de detectar correlacoes (custo).

## Categoria 2 — Multi-column variantes

### O-FMT-05 — encode_columns() API (legacy)

**Ideia**: API antiga sugeria `encode_columns(dict[str, list[str]])`.

**Antecedentes**:
- [`docs/workbench/_archive/tickets/closed/25-T-encode-columns.md`](../../../../docs/workbench/_archive/tickets/closed/25-T-encode-columns.md)
  — proposta pra v0.5; pendente em v0.6.

**Status**: parcialmente capturada em EXP-011 (basico, sem
header rico nem niveis de compressao).

### O-FMT-06 — Compactacao cross-column

**Ideia**: se colunas A e B tem padroes parecidos, compartilhar
fragmentos (cross-column dictionary).

**Trade-off**: complexidade decoder ↑↑. Possivel ganho em
datasets com schemas redundantes.

**Status**: aberta. Pouco explorada na literatura tabular.

### O-FMT-07 — Type-aware multi-column

**Ideia**: por coluna, escolher pipeline diferente (delta-aware
para timestamps, dict-encoding para categoricos, etc.).

**Status**: aberta. Pacote 1 ja' fez pipeline-decision por coluna
(auto-detect cadencia). Extensao natural pra mais tipos.

## Categoria 3 — Streaming / batch / online

### O-FMT-08 — Streaming encoder/decoder

**Ideia**: dividir input em chunks de N rows, comprimir cada chunk
independente, transmitir online. Decoder reconstrói chunk a chunk.

**Antecedentes**:
- [`docs/workbench/_archive/tickets/frozen/H-streaming-encoder.md`](../../../../docs/workbench/_archive/tickets/frozen/H-streaming-encoder.md)
  — ticket frozen com design detalhado (HTTP chunked, memoria
  O(chunk_size), TTFB constante).

**User insight novo**: "a ordem permite que a transmissao dos
dados possa ser comprimida online em lotes que podem ser
descomprimidos tambem". Ordering + streaming combinam.

**Status**: aberta. Reativar quando core estiver maduro.

### O-FMT-09 — Chunk-level type detection

**Ideia**: em streaming, cada chunk pode ter tipo detectado
independente. Permite adaptacao a mudancas no stream.

**Status**: aberta. Decorrente de O-FMT-08.

## Categoria 4 — Format-level optimizations

### O-FMT-10 — Escape supressao implicita (Pacote 2)

**Ideia**: ver [`roadmap-hipoteses.md`](roadmap-hipoteses.md) Pacote 2
(H-ED-01..04). Reducao de overhead de backslash quando contexto
permite deducao.

**Status**: registrada, lab dedicado nao iniciado.

### O-FMT-11 — Cabecalho compacto

**Ideia**: header deve seguir convencao shebang TCF v0.5
(`#TCF.5 SRDM`) — magic + flags, sem texto livre, byte-precise.

**Status (revisada 2026-05-17 pos critica do user)**: PARCIAL
aplicada em EXP-011 multi-column:
- Magic + flag: `#TCF6 M` (5+2 bytes)
- Meta compacto: `# 61=timestamp,28=id,...` (pares size=name)
- Bodies concatenados sem delimitador (byte-precise)
- Save: 72 bytes vs ad-hoc original em D17a (-46.6% vs raw)

**Pendente** (registrar antes de generalizar):
1. Single-column adicionar shebang `#TCF6` (uniformizar)? Hoje
   single-col nao emite header.
2. Nomes com `,` ou `=` precisam escaping
3. Flag system pra v0.6: quais flags alem de `M`?
   (v0.5 tinha SRDM)
4. Multi-tabela (multiplas tabelas no mesmo arquivo) precisa de
   convenção separada?

**Antecedentes**:
- [`docs/workbench/research-notes/_archive/2026-05-09-formato-header-shebang.md`](../../../../docs/workbench/research-notes/_archive/2026-05-09-formato-header-shebang.md)
  — decisao original v0.5 (EXP-004c)
- [`docs/workbench/_archive/tickets/open/S-header-inline-vs-explicito.md`](../../../../docs/workbench/_archive/tickets/open/S-header-inline-vs-explicito.md)
  — decisao inline vs explicito em decls de fragmento

### O-FMT-11b — Header uniformizado (RESOLVIDA)

**Decisao (2026-05-17 apos critica user)**: TODO arquivo TCF v0.6
emite shebang por default.
- Single-column: `#TCF.6` (7 bytes incluindo LF)
- Multi-column: `#TCF.6 M` + linha de meta (`# size=name,...`)
- Excecao: `include_shebang=False` quando caller garante formato
  out-of-band (raro)

**Convencao da versao** (welded de
[`docs/workbench/research-notes/_archive/2026-05-09-formato-header-shebang.md`](../../../../docs/workbench/research-notes/_archive/2026-05-09-formato-header-shebang.md)):
- Major 0 → omite `0`, escreve `.<minor>` → `#TCF.6`
- Minor 0 → omite `.0`, escreve so' `<major>` → `#TCF1`
- Caso geral → `<major>.<minor>` → `#TCF1.3`

**Custo medido**: +7 bytes por arquivo single-col (EXP-010
re-rodado: 2272 → 2412 bytes em 20 datasets, RT 20/20 OK).
Aceito como custo de identificacao do formato.

### O-FMT-13 — Mobile / per-channel header para transmissao paralela

**Ideia (user, 2026-05-17)**: pra transmissao paralela, pode ser
necessario que CADA CANAL leve seu proprio cabecalho indicando "que
e' quem" (qual coluna, qual chunk, qual tipo). Permite re-montagem
no destino sem coordenacao central.

**Casos de uso**:
- Multi-canal HTTP/gRPC streaming (cada canal = 1 coluna)
- Pipelines distribuidos onde colunas vao por workers diferentes
- Reconstrucao tolerante a falha (chunks chegam fora de ordem)

**Design conceitual** (pra registrar, NAO implementar agora):
```
# canal A:
#TCF.6 C name=timestamp chunk=1/3 of=table_X
<body chunk 1>

# canal B:
#TCF.6 C name=email chunk=2/3 of=table_X
<body chunk 2>
```

Cada canal leva: nome da coluna, indice do chunk, total de chunks,
identificador da tabela. Permite re-assembly.

**Status**: registrada, **nao implementar agora**. Tem que ficar
**modular no codigo** pra acomodar esta extensao (encoder ja' opcao
`include_shebang`; multi-col ja' separa header de body). Welding
quando casos de uso real aparecerem.

**Antecedentes relacionados**:
- [`docs/workbench/_archive/tickets/frozen/H-streaming-encoder.md`](../../../../docs/workbench/_archive/tickets/frozen/H-streaming-encoder.md)
  — streaming chunked v0.4 (compativel)
- [`docs/workbench/_archive/tickets/frozen/E-http-protocol.md`](../../../../docs/workbench/_archive/tickets/frozen/E-http-protocol.md)
  — HTTP chunked transfer

### O-FMT-12 — Auto-detect schema do CSV

**Ideia**: detectar dialect (delimitador, quote, encoding) +
schema (tipos por coluna) automaticamente. Permite encode_file()
mais conveniente.

**Status**: aberta. Tangencial ao core.

### O-FMT-14 — Header desacoplavel / opcional / derivavel (registrado 2026-05-24)

**Observacao do owner pos-ADR-0014**: o header atual
(`#TCF.6 M\n# size=name,...\n`) faz parte do fluxo welded mas
**ainda precisa melhorar bem mais**. Por ora "se contenta" com
o desenho atual pra fazer funcionar.

**Direcoes registradas**:

1. **Desacoplavel**: header pode ser **separado do body** (header em
   sidecar / canal proprio / metadata externa) e **reconectado depois**.
   Use cases: distribuir bodies por workers diferentes sem precisar
   replicar header em cada canal; cachear header separado do body
   quando schema muda raramente.

2. **Derivavel de stats/schema**: hoje o meta line `# 61=timestamp,28=id,...`
   carrega sizes explicitos. Se sizes forem **derivaveis de schema
   prévio** (ex: contrato Plan + ColumnFeatures pre-acordados), header
   pode ser reduzido a so' uma assinatura. Conecta com
   T-CODE-SCHEMA-BUILDER (consume SideOutputs pra produzir schema rico
   que pode substituir parte do header).

3. **Opcional**: minimo absoluto pode ser apenas `#TCF.6` (version
   signature). Resto deriva de:
   - schema externo (canal out-of-band)
   - convencao default (single-col, nome `val`)
   - heuristica do decoder (parse meta line se presente, senao default)

4. **Apenas mandatorio**: version signature inicial (`#TCF.<minor>`)
   pra identificar formato e versionamento. Tudo mais opcional.

**Status**: registrada 2026-05-24. NAO implementar agora — fluxo
atual ja' funcional e validado em real-world. Welding eventual
quando T-CODE-SCHEMA-BUILDER e T-CODE-ENCODER-MANAGER amadurecerem
(sao pre-requisitos pra header "derivavel").

**Conexoes**:
- [ADR-0014](../../../../docs/adr/0014-unified-api-side-outputs.md) — API atual
- [T-CODE-SCHEMA-BUILDER](../../../../tickets/T-CODE-SCHEMA-BUILDER.md) — produziria schema que substitui header
- [T-CODE-ENCODER-MANAGER](../../../../tickets/T-CODE-ENCODER-MANAGER.md) — sinks que podem distribuir header separado
- O-FMT-13 (per-channel) — caso especial onde header desacopla por canal

### O-FMT-15 — Omitir o size da ultima coluna (boundary implicito por EOF) (registrado 2026-06-14)

**Ideia (owner, 2026-06-14)**: no header `# <s1>=<n1>,<s2>=<n2>,...,<sN>=<nN>`,
o size da ULTIMA coluna e' redundante — o corpo dela vai do seu inicio ate' o
EOF. Logo `# <s1>=<n1>,...,<nN>` (ultima sem size) basta. Tres efeitos
levantados pelo owner:
1. **Economia**: o ultimo nao precisa de numero (o fim deduz pelo resto).
2. **Habilita deducoes**: boundary implicito limita repeticao "sem fim" — o
   proprio EOF para a expansao, sem precisar contar de antemao.
3. **Efeito colateral (integridade)**: sem o numero, nao da' pra saber se a
   ultima coluna foi truncada/corrompida — mas, dependendo do meio, integridade
   e' responsabilidade da **camada de transporte**, nao do formato.

**Analise critica:**

- **Magnitude (ponto 1)**: economiza UM inteiro por TABELA (os digitos do size
  da ultima coluna) — nao por linha nem por coluna. Em tabela grande (body MB)
  e' ruido (<0.001%); em tabela pequena (README: 182B, size `20`) ~2B (~1%).
  So' o ultimo e' omissivel "de graca" (os demais precisam de size porque os
  bodies sao concatenados sem delimitador; so' o ultimo e' EOF-bounded).
  Daria pra omitir QUALQUER um (deduzir = filesize − soma dos outros − header),
  mas o ultimo e' o natural (EOF, sem aritmetica). **Ganho real, porem pequeno
  e O(1) por tabela** — nao justifica isolado por bytes (§9).

- **Coerencia com o formato (forte)**: o **single-col TCF ja' e' isto** — sem
  header, sem size, corpo ate' EOF. "Ultima coluna sem size" e' a generalizacao
  multi-col do que o single-col ja' faz. Nao e' excecao arbitraria; e' regra ja'
  existente estendida. (Precedente interno: [ADR-0001](../../../../docs/adr/0001-tcf-format-shebang.md) single-col.)

- **Ponto 2 (deferred sizing — o valor real)**: boundary implicito = nao precisa
  saber o tamanho ANTES de escrever. Hoje o header e' header-first (exige TODOS
  os sizes antes do body). A ultima coluna EOF-bounded permite "fluir" o ultimo
  body em streaming sem conhecer seu tamanho final → menos buffering. E' o degrau
  ZERO de deferred-sizing que [O-FMT-08](#o-fmt-08--streaming-encoderdecoder) e
  V2-J (ADR-0018) exploram via trailer / header-reescrito. Sobre repeticao "sem
  fim": hoje RLE tem count explicito (`*N|`), entao e' teorico — mas abre espaco
  pra um marcador "repete ate' o fim" (sem count) so' valido na ultima posicao.

- **Ponto 3 (integridade) — menor do que parece**: o decoder atual **ja' NAO
  valida sizes** — `raw[cursor:cursor+size]` em Python nao erra em arquivo
  truncado (slice retorna menos bytes, leitura parcial silenciosa). Ou seja,
  omitir o ultimo size nao PERDE uma checagem que existe; perde uma checagem
  POTENCIAL (futura: `header + Σ sizes == filesize` seria um cross-check barato;
  omitir o ultimo tira um termo). Owner esta' certo: truncamento/checksum e'
  trabalho do transporte (TLS, HTTP content-length, CRC) — o formato nao deve
  duplicar. Registrar so' que os sizes explicitos SAO uma redundancia que
  PODERIA virar integrity-check opt-in; o ultimo-sem-size renuncia a parte disso.

- **Custo de impl**: trivial (~3 linhas). Decode da ultima coluna vira
  `raw[cursor:]` em vez de `raw[cursor:cursor+size]`.

- **Versao de formato**: muda a gramatica do meta line → decoder v1 quebra
  (tenta parsear `=nN` / `int("")`) → **breaking, #TCF.7 / v2.0, opt-in**.
  Compoe com V2-A (`!size=name`): ultima raw sem size = definir gramatica
  (`!=name` ou `!name`).

**Prior art (checado 2026-06-14)**: NAO abordado. [ADR-0004](../../../../docs/adr/0004-multi-column-header-compacto.md)
(decisao do header) nao considerou — "Em aberto" lista escaping/flags/multi-tabela,
nao isto. [O-FMT-14](#o-fmt-14--header-desacoplavel--opcional--derivavel-registrado-2026-05-24)
e' diferente (deriva sizes de schema EXTERNO; este e' deducao INTERNA por EOF).
Vizinho: O-FMT-08 / V2-J (streaming / deferred sizing).

**Status**: aberta, registrada 2026-06-14. **Nao weldar isolado** (ganho de
bytes nao justifica vs. irregularidade de gramatica + breaking change). O valor
esta' no deferred-sizing (ponto 2) — **reavaliar junto com O-FMT-08 / V2-J**
(streaming) como variante opt-in #TCF.7, onde boundary implicito e' o ponto.

**Conexoes**: O-FMT-08 (streaming), O-FMT-14 (header reduzido), ADR-0004 (header),
ADR-0018 V2-J (pipeline streaming), ADR-0001 (single-col EOF-bounded = precedente).

### O-FMT-16 — Espaco apos `#` no meta line e' dispensavel (registrado 2026-06-14)

**Ideia (owner, 2026-06-14)**: o meta line e' `# <s1>=<n1>,...`. O espaco apos
o `#` nao e' necessario. Combinado com O-FMT-15 (ultima sem size):

    # 45=nome,42=email,28=cidade,20=plano   (atual)
    #45=nome,42=email,28=cidade,plano        (O-FMT-16 + O-FMT-15)

**Analise critica:**
- **Magnitude**: 1 byte por TABELA (o espaco). Trivial. Decode: `META_PREFIX`
  vira `b"#"` em vez de `b"# "`. Sem ambiguidade — o meta line e' a linha 2
  (apos o shebang line 1); o `#` so' marca, a POSICAO ja' identifica.
- **Adjacente (registrar)**: pela mesma logica, o proprio `#` do meta line e'
  dispensavel — a linha 2 ja' e' o meta por posicao. Dropar `#`+espaco = **2
  bytes**. O `#` e' um marcador-sanidade barato; manter ou nao e' decisao de
  gosto vs. byte. (NAO confundir com o `#` do shebang line 1, esse fica.)
- **Versao**: breaking (decoder v1 espera `# `) → **#TCF.7 / v2.0, opt-in**.
  Compoe com O-FMT-15 e V2-A.

**Prior art**: NAO abordado. ADR-0004 fixou `# ` sem discutir dispensa-lo.

**Status**: aberta, registrada 2026-06-14.

### Bundle "header v2 minimo" (O-FMT-15 + O-FMT-16) — reframe 2026-06-14

**Diretriz do owner (2026-06-14)**: foco em **detalhes de compressao byte-a-byte**
— "cada byte importa, principalmente se o TCF for substituir transmissoes
MINUSCULAS". Isso **muda o calculo de §9** pros micro-opts de header: num payload
minusculo, o header de tamanho fixo DOMINA o total, entao economias O(1)-por-tabela
(espaco, ultimo size, talvez o `#`) deixam de ser ruido e viram fracao relevante.

Ex (cadastro do README, TCF 182B, header `#TCF.6 M\n# 45=nome,42=email,28=cidade,20=plano\n`):
- O-FMT-16 (sem espaco): −1B
- O-FMT-15 (sem ultimo size `20`): −2B (so' os digitos; o `=` some junto se a
  gramatica deixar a ultima como `,nome`)
- dropar `#` do meta: −1B
→ ~−4B de ~55B de header (~7% do header; ~2% do arquivo). Em tabelas com
header proporcionalmente maior (poucas linhas, varias colunas), o efeito sobe.

**Acao proposta**: tratar O-FMT-15 + O-FMT-16 (+ possivel drop do `#`) como UM
pacote "header v2 minimo" opt-in (#TCF.7), nao tres welds isolados. Reavaliar
prioridade ALTA dado o foco em transmissoes minusculas (antes: "nao weldar
isolado"; agora: candidato a pacote dedicado). Ainda assim, validar o ganho real
em datasets pequenos antes de weldar (checklist confirmada-empirica).

### Nota geral — fluxo atual (2026-05-24)

Owner registra explicitamente que **o pipeline atual ainda tem muito
a melhorar** mas que **se contentamos com ele por enquanto pra fazer
funcionar**. Itens pendentes alem das O-FMT-* listadas:
- Header desacoplavel/opcional (O-FMT-14, acima)
- Paralelismo de `_encode_column` (T-CODE-ENCODER-MANAGER P2)
- Sinks pluggable (T-CODE-OUTPUT-SINKS P2)
- Plan contract (T-CODE-PLAN-CONTRACT P3)
- Schema builder (T-CODE-SCHEMA-BUILDER P3)
- Naturezas templated/checksummed (CPF/IP/telefone) — ver
  [`naturezas-templated-2026-05-24.md`](naturezas-templated-2026-05-24.md)

Filosofia: **viavel agora > otimo eventual**. Funciona, valida em
real-world (9 tabelas, RT 9/9), suite verde (117 passed). Otimos
ficam pra depois quando preconditons forem atendidos.

---

## Ordem proposta de exploracao

Quando voltar pra estas otimizacoes:

1. **Pacote 2 (escape-deduction)** — H-ED-01..04. Mais maduro
   conceitualmente, antecedente formal (S-supressao ticket).
2. **O-FMT-07 (type-aware multi-column)** — extensao natural do
   Pacote 1; cada nova natureza vira um sub-pacote.
3. **O-FMT-02 (ordenacao natural)** — quando user permite,
   ganho potencial grande.
4. **O-FMT-08 (streaming)** — quando dataset scale exigir.
5. **O-FMT-01/03/04 (ordenacao reversivel/multi-order)** —
   complexidade alta; ROI depende de cenario.
6. **O-FMT-06 (cross-column)** — explorar so' depois de O-FMT-07
   maduro.

## Atualizacao

Atualizar quando: nova ideia chegar, ou alguma O-FMT-* mudar de
status (testada/iniciada/refutada).

**Ultima atualizacao**: 2026-06-14 (O-FMT-15 ultima-coluna-sem-size + O-FMT-16
espaco-do-meta-dispensavel + bundle "header v2 minimo" / reframe transmissoes
minusculas). Antes: 2026-05-24 (O-FMT-14 header desacoplavel), 2026-05-17
(criacao + 12 entries).
