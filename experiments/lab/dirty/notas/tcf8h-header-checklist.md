# TCF.8H — Checklist do cabeçalho (5 camadas)

> **[probatório]** Enumera **tudo que o cabeçalho TCF.8H aborda**, das coisas escritas literalmente
> até as escolhas com perda-e-ganho. Estrutura pedida pelo owner (2026-07-06): **explícito → inferências →
> always-win → by-choice → cobertor-curto**. Fonte: EXP-015 (`../../clean/EXP-015-tcf-hierarquico-csv-json/`,
> RT-medido em amostras minúsculas S4/S6/C1) + tickets
> [T-FMT-TCF8H-HEADER](../../../../tickets/T-FMT-TCF8H-HEADER.md),
> [T-OPT-INFERENCE](../../../../tickets/T-OPT-INFERENCE.md),
> [T-FLOW-…-TELEMETRY](../../../../tickets/T-FLOW-ENCODE-STRATEGIES-TELEMETRY.md).
> Construído por levantamento exaustivo (142 elementos) + crítico de completude.
>
> **Legenda do checkbox**: `[x]` = **consagrado** (decidido + em código, RT-medido) · `[ ]` = **pendente**
> (condicional / aberto / futuro — decisão ou welding pra frente). TCF.8H é **protótipo externo opt-in**;
> nada disto está weldado em `src/tcf` ainda (welding = gate real-world).

## Anatomia — o header inteiro, pra situar (S6, RT-exato, 153B)

```
#TCF.8H nome:9,endereco{rua:19,cidade:9,geo{lat:8,lon:8}},telefones[tel
└──┬───┘ └──┬─┘ └───┬──┘└──────┬───────┘└──────┬──────┘ └┘ └───┬───┘ └┬┘
 magic   folha+size  grupo{}   folhas         grupo{}   ││  array[]  folha
 (C1)     (C1)      obj 1:1    (C1)          obj 1:1(aninh)││ 1:N     ÚLTIMA
                                            closes INTERIORES┘└ (C1, load-bearing)
                                                            sem size (C3) ┘
      ...e o `]` final de telefones foi DROPADO (omit-closes, C3); o `\n` fecha.
```
- `nome:9,endereco{rua:19,...}` — **C1** (magic, nomes, sizes, `{}`/`[]`, `:`/`,` escritos).
- os **dois `}}`** depois de `lon:8` fecham `geo` e `endereco` — **closes interiores, escritos** (só a
  corrida FINAL de closes é dropável).
- `tel` sem `:28` — **C3** última-folha-sem-size (o EOF reconstrói).
- o `]` que fecharia `telefones` sumiu — **C3** omit-closes (o `\n` + parse EOF-bounded auto-fecham).
- M/N/cardinalidade/kind/nº-de-linhas/ordem — **C2**, nada escrito.
- (S4 = `#TCF.8H nome:9,telefones[tel`, 66B. C1-CSV cai pra `#TCF.7 M` plano, 107B — **sem** colchete-meta.)

---

## C1 — Header EXPLÍCITO (o primeiro padrão)

*Escrito literal, sempre presente, irredutível. ELE é a fonte; não se deduz.*

- [x] **magic `#TCF.8H`** — 7 bytes que abrem o header: formato + minor 8 + flag hierárquico `H`; roteia pro codec hierárquico. *(codec.py:21,125,152)*
- [x] **espaço magic→meta** — único ASCII entre magic e colchete-meta; delimitador de parse load-bearing (`head[len(MAGIC)+1:]`). *(codec.py:125,153)*
- [x] **nomes de folha inline** — nome de cada coluna verbatim (`nome`, `tel`, `rua`…); reconstrói a chave-campo do JSON (self-describing; sem `drop_names` em v0). *(codec.py:44,53)*
- [x] **nomes de grupo/container inline** — nome antes do colchete (`endereco{…}`, `telefones[…]`, `geo{…}`). *(codec.py:44,50)*
- [x] **sizes inline `:N`** — byte-size do corpo TCF de cada coluna (`len(body.encode())`) após `:`, em toda folha **exceto a última**; habilita byte-split/salto sem descomprimir. *(codec.py:121-122,169-172)*
- [x] **`:` nome→size** — fronteira nome↔tamanho; troca de estado no parser. *(codec.py:49,72-77)*
- [x] **`{}` objeto / `[]` array** — glifos de agrupamento (a *abertura* é sempre escrita; a semântica 1:1/1:N cai na C2). *(codec.py:44,50,78-104)*
- [x] **closes INTERIORES `}`/`]`** — os closes que **não** estão na corrida final ficam escritos e são load-bearing (ex.: `geo{…}}` fecha geo+endereco). *(evidência RT: meta de S6; crítico de completude)*
- [x] **`,` entre irmãos** — separa nós irmãos no mesmo nível. *(codec.py:54,63-68)*
- [x] **`\n` terminador do header** — separa meta dos bodies **e** ancora o omit-closes; LF-only. *(codec.py:125,151)*
- [x] **arestas de hierarquia (contenção pai→filho)** — "quem contém quem": o **único** item de schema irredutível (array-vs-objeto sai dos dados; a contenção não). *(estudo P9; T-STUDY)*
- [ ] **marcador de tipo na divergência** — quando o tipo diverge de string, uma **letra escrita** no colchete (`i`/`f`/`b`/`n`/`s` colada no size: `idade:4i`) dá fidelidade de tipo; elemento C1, só emitido na colisão. **Prototipado + medido (Ciclos 1a/1b, RT)** — [1a](2026-07-06-2221-tcf8h-fidelidade-tipos/result.md) · [1b](2026-07-06-2238-tcf8h-escala-formas-e-tipos/result.md); H-TYPE-01. **Estratégia decidida (1b, do número): C-híbrida** — deduz número/bool de graça, tag só a colisão (string-ambígua→`s`, null→`n`); **A-explícita** (tudo taggeado) é fallback quando strings-ambíguas dominam. Análogo do hex-default (C4). Custo: folha DFS-última tipada perde a última-sem-size (liga com C5). *(dirty proto; report.md:33)*

## C2 — Header COM INFERÊNCIAS (deduz e comprime; sem escolha, sem perda)

*Determinado pela forma/dados, NUNCA escrito, custo zero.*

- [x] **`M` implícito** — sem flag multi-col: o `H`/árvore já implica ≥2 colunas. *(codec.py:21; T-FMT)*
- [x] **`N`/hierarquia implícito** — sem flag de aninhamento: a presença de colchete/chave aninhada já sinaliza (ausência = multi-col plano). *(estudo 1830-bracket-meta)*
- [x] **cardinalidade 1:1 vs 1:N** — deduzida do glifo (`{}` 1:1, `[]` 1:N) / nº de linhas dos filhos; nunca rotulada. *(codec.py:175-186; P5/P7)*
- [x] **kind objeto/array/escalar** — inferido pelo char que segue o nome (`{`→obj, `[`→arr, `:` ou nada→escalar); escalar não escreve marcador. *(codec.py:72-107)*
- [x] **`N` (nº de linhas do array)** — reconstruído como `len` do body decodificado da 1ª coluna-filho; nunca no header. *(codec.py:184)*
- [x] **nº de linhas por coluna / escalar=1-linha** — emerge ao decodar o body (RLE `*N|` expande); folha escalar/objeto tem multiplicidade implícita 1 (`[0]`). *(codec.py:36,170-173,179)*
- [x] **ordem DFS folhas ↔ ordem bodies** — o DFS das folhas mapeia posicionalmente os bodies concatenados; o decoder re-anda o mesmo DFS, nenhum índice escrito (load-bearing). *(codec.py:27-37,157-166)*
- [x] **offsets por soma cumulativa** — offsets de fatiamento derivados como soma corrente dos sizes (`off += sz`), não armazenados. *(codec.py:168-172)*
- [x] **bodies contíguos sem delimitador** — corpos gravados grudados, fatiáveis só pelos sizes (o último pelo EOF). *(codec.py:125,169-172)*
- [x] **agrupamento de colunas do array** — colunas dentro de `[]` zipadas em N row-objects; inferido do colchete, não tagueado por coluna. *(codec.py:182-185)*
- [x] **raiz é objeto** — a raiz é objeto de instância única (dict no topo); nenhuma marca de raiz escrita. *(codec.py:175-187)*
- [x] **hierarquia opt-in / fronteira modo-plano** — o colchete-meta só existe se o RT-alvo é a árvore JSON; no CSV (RT-alvo = tabela plana) o header vira `#TCF.7 M` sem colchete (RLE já colapsa o pai, dual de fk); a presença/ausência dos brackets decide, zero byte extra. *(C1=`#TCF.7 M`; run.py csv_deduce; report.md)*
- [x] **tipo default = string** — tipos não aparecem: string por default, deduzido, custo zero (v0 tudo string). Divergência → C1 `:tipo` (futuro) ou inferência via `analyze_column`/`is_numeric` (SideOutputs, zero-cost). *(report.md:33; codec.py:34-36)*
- [ ] **cardinalidade por FD (CSV→árvore)** — ao construir árvore de CSV plano, a cardinalidade é deduzida por dependência funcional (álgebra de distinct-count) e popularia os `{}`/`[]`; a hierarquização **multi-pai NÃO fecha RT em v0** (precisa de link posicional, peça 10). *(codec.py:221-239; run.py:51-74)*

## C3 — Inferências ALWAYS-WIN (nunca perde bytes, RT-exato)

*Byte-drops opcionais, sem tradeoff (streaming preservado). Default-on.*

- [x] **omit-closes** — dropa a corrida **final** de `}`/`]`; o `\n` + parse EOF-bounded auto-fecham os grupos abertos. Economiza `depth(última-folha)` closes. **RT-exato, −1B** (S4 21→20B, S6 64→63B no meta). *(codec.py:114-125, `rstrip('}]')` default True; outputs/04; T-FMT CONSAGRAR)*
- [x] **última-folha-sem-size** — omite o `:size` da última folha em DFS; o EOF (`raw[off:]`) reconstrói. Economiza 1 `:` + `digits(size)` da última folha (custo isolado de **repor** = **+3B** medido, ex. `tel:28`). *(codec.py:49,53,170-172; herdado ADR-0023 / O-FMT-15)*

## C4 — Inferências BY CHOICE (win-or-tie, mas escolha de perspectiva)

*Ganha ou empata em bytes, mas é uma ESCOLHA com default; custa legibilidade/auto-descrição (contrato/convenção fora-de-banda). Detalhe em [T-OPT-INFERENCE](../../../../tickets/T-OPT-INFERENCE.md).*

- [ ] **base HEX-default nos sizes** — ler byte-sizes em HEX por convenção fixa: `len(hex(s)) ≤ len(str(s))` sempre; encurta nas fronteiras 16ᵏ; o arquivo se auto-explica **por convenção** sem marcador — custa legibilidade do size. Medido: sizes 201/13 → **−2B**. (o codec hoje emite **decimal**; hex é proposto.) *(T-OPT-INFERENCE Item 1; analise_header.py; outputs/05)*
- [ ] **decimal por comando externo** — base decimal opt-in só out-of-band; nesse modo o arquivo **não** é auto-descritivo (byte-mínimo sob contrato). *(T-OPT-INFERENCE)*
- [ ] **rede de dedução da base** — sem flag: (1) letra `[a-f]` num size → HEX inequívoco; (2) quebra-na-expansão (split decimal não fecha o body) → HEX; (3) ambíguo all-digit → default HEX. *(T-OPT-INFERENCE; tcf8h-proximas-ideias §4)*
- [ ] **um arquivo, uma base** — invariante: um blob nunca mistura dec/hex (habilita a dedução). *(T-OPT-INFERENCE)*
- [ ] **escolha do portador-de-forma** — usar `{}`/`[]` como portador da topologia (vs `> <` descend/ascend, `nome*N` contagem, `nome:d` profundidade); bytes ~empatam entre notações, a escolha é por parse/stream. Glifo a cravar no welding. *(estudo 1840-notacoes; peça 6)*
- [ ] **drop-names (anônimo)** — omitir nomes de folha/grupo quando o consumo é posicional; win-or-tie mas custa a auto-descrição (schema fora-de-banda). Futuro. *(header-minimal flat 23→13B análogo; report.md:33)*
- [ ] **header-derivável-por-contrato (O-FMT-14)** — esquema pré-acordado → header colapsa pra assinatura (~6B) ou 0B out-of-band; maior lever restante, custa auto-descrição; só paga em payload minúsculo. *(header-minimal/result.md)*
- [ ] **enriquecimento por natureza/spec** — specs pré-tx (CPF/CEP/telefone): tag `:cpf` no header + body encolhe (corta o BODY, ortogonal ao header); +1 tag, ganha auto-descrição. Futuro. *(tcf8h-proximas-ideias §3; ADR-0015)*
- [ ] **gabarito = 1º item como template** — em coluna com spec, o 1º item vira molde (como a 1ª string no OBAT: literal/molde, resto = afixo/delta). Futuro. *(tcf8h-proximas-ideias §3)*
- [ ] **spec padrão deixa gabarito implícito** — spec no formato mais padrão deixa o molde implícito (o spec É o template); só valor divergente carrega gabarito próprio. Futuro. *(tcf8h-proximas-ideias §3)*

## C5 — Inferências COBERTOR-CURTO (+compressão × −memória/processamento)

*Tradeoff real: mais compressão, mas custa memória/processamento/latência (quebra streaming, ou custo offline).*

- [ ] **reorder profundo-por-último (S2)** — reordena irmãos (order-free) por profundidade pra a folha `argmax(digits(size)+depth)` cair por ÚLTIMO, maximizando closes-omitidos + size-dropado; **materializa a árvore inteira + sort O(f·log f), quebra o streaming**. Vale **SSE** `argmax ≠ natural-última` (+4B em caso construído; **+0B em S6** — a natural-última já é o argmax). *(codec.py:128-147; outputs/05; T-FLOW S2 / T-FMT CONDICIONAL)*
- [ ] **telemetria sugestiva (S3)** — camada offline que amostra (não cada payload), consome SideOutputs (zero-custo), aprende a ordem/forma ótima por schema e **sugere ao produtor** emitir dados já ótimos (alert-only); move o custo do reorder pra offline (1×/schema), encode por-payload fica barato (S1). Só ticket, sem código. *(T-FLOW S3)*

---

## Fora das camadas — MODELOS e contexto (não são elementos do header)

*Regem ONDE/QUANDO as otimizações pagam; não são byte-drops nem inferências (custo computacional zero, ou meta-descrição de fluxo). Separados por consistência (crítico de completude).*

- **SAVING(L) = digits(size(L)) + depth(L)** — identidade de contabilidade: última-sem-size dá os `digits`, omit-closes dá a `depth`. Rege onde reorder/hex pagam ("não é só profundidade": folha rasa de size grande pode ganhar de profunda pequena). Custo computacional zero. *(analise_header.py; report.md:47-58)*
- **break-even payload-minúsculo** — o header é ~fixo (13-14B) e o body cresce → encolher o header só move a agulha em N pequeno (N=1 ~39%, N=5 ~9.8%, N=20 ~4.6%, N=100 ~1.3%). É a REGRA de quando as otimizações de header importam (foco byte-level / transmissões minúsculas). *(header-minimal/run.py; [project_byte_level_compression_focus])*
- **S1 = fluxo default** — as-is + omit-closes (empacota os drops C3), nunca reordena; O(N) streaming, memória ~1 coluna. Rótulo de pipeline, não membro de camada. *(T-FLOW S1)*

## Estado de implementação (proveniência)

| bloco | em código (RT-medido, EXP-015) | proposto / não-em-código |
|---|---|---|
| **C1** | magic, seps, nomes, sizes, `{}`/`[]`, closes interiores, `\n` | `:tipo` na divergência |
| **C2** | M/N implícito, cardinalidade, kind, nº-linhas, DFS, offsets, bodies-contíguos, str-default, fronteira-plana | FD-CSV→árvore (multi-pai não fecha RT em v0) |
| **C3** | omit-closes, última-sem-size | — |
| **C4** | — (codec emite **decimal** hoje) | hex-default + rede de dedução + decimal-por-comando; drop-names; O-FMT-14; nature-spec; gabarito |
| **C5** | `reorder_deepest_last` (condicional) | telemetria S3 (só ticket) |

**Números-âncora (RT-exato, amostras minúsculas)**: S4=66B · S6=153B · C1=107B (`#TCF.7 M` plano) ·
omit-closes −1B · última-sem-size repor +3B · reorder +4B construído / +0B S6 · hex 201/13 −2B.

## Links

- Tickets: [T-FMT-TCF8H-HEADER](../../../../tickets/T-FMT-TCF8H-HEADER.md) (estrutural: C1/C2/C3 + reorder condicional) ·
  [T-OPT-INFERENCE](../../../../tickets/T-OPT-INFERENCE.md) (C4 hex-default + dedução) ·
  [T-FLOW-…-TELEMETRY](../../../../tickets/T-FLOW-ENCODE-STRATEGIES-TELEMETRY.md) (C5 S1/S2/S3).
- Protótipo: [EXP-015](../../clean/EXP-015-tcf-hierarquico-csv-json/report.md) · mapa do estudo:
  [estudo-tcf-hierarquico-mapa](estudo-tcf-hierarquico-mapa.md) · teoria: [teoria-cardinalidade](teoria-cardinalidade.md) ·
  ideias: [tcf8h-proximas-ideias](tcf8h-proximas-ideias.md).
