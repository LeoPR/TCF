# TCF.8 — registry de chars do header (fecha os fluxos) [reference→proposta]

**Data**: 2026-07-08. **Tipo**: reference/proposta. **A questão que faltava no header** (owner): o `.8`
roteia os fluxos por **caracteres** (discriminador + marcadores por-coluna), mas **não há registry nem
reserva** — nem no spec canônico [`TCF-format.md`](../../../../docs/algorithms/TCF-format.md) (grep vazio),
nem em ADR. Features vêm pegando char **ad-hoc** → **colisão**: o protótipo `#TCF.8H` pegou `H` (não
registrado no discriminador do [ADR-0029](../../../../docs/adr/0029-version-format-identification-semi-implicit.md));
o cross-dict pegou `&<G>`; o bN queria `#`. Sem registry, cada fluxo novo arrisca colidir. Este doc
**cataloga o namespace completo + um esquema de reserva** pra fechar isso.

## Eixo 1 — DISCRIMINADOR (o char logo após `#TCF.8`) — roteia a ESTRUTURA

| char | fluxo | estado | fonte |
|---|---|---|---|
| *(nada, body direto)* | órfão single-col (default, 0 bytes) | ✅ welded | ADR-0029 camada 1 |
| `M` | multi-col (meta inline: `#TCF.8M<meta>`) | ✅ welded | ADR-0029; `multi/core.py` |
| ` ` (espaço) | single-col + spec (`#TCF.8 [nome]:spec`) | ✅ welded | ADR-0029; `encoder.py` |
| `\n` | single-col version-stamp (`#TCF.8\n<body>`) | ✅ welded | ADR-0029; `decoder.py` |
| `H` | **multi-col hierárquico** (especialização de `M`; `#TCF.8H<meta-árvore>`, sem-espaço) | ✅ **welded** ([ADR-0033](../../../../docs/adr/0033-hierarchical-codec-weld.md), owner 2026-07-14) — codec no core (`src/tcf/hierarchical.py`, L2/L3 sobre L1); char + dispatch do [ADR-0031](../../../../docs/adr/0031-hierarchical-discriminator-H.md) | ADR-0031/0033 |
| *(livres)* | qualquer estrutura futura | reservável | — |

**Regra de dispatch** (ADR-0029): match EXATO no char do índice 6; `M`/` `/`\n` distintos; um nome de coluna
começando em `M` não colide (o discriminador é o char após `#TCF.8`, não dentro do meta).

### Propósito DUPLO do discriminador (dica, não `if` rígido) — HIPÓTESE (owner 2026-07-14)

Além de rotear a estrutura, o char do discriminador é uma **DICA** com dois usos futuros (H-DISC-ACCEL-01,
`aberta`, confiança Baixa — verificar antes de implementar):
1. **Aceleração por-forma**: SE o header traz `H`/`M`/espaço, o consumidor *pode* rotear pra um bloco de
   código **compilado/acelerado** específico daquela forma. **Não é do TCF**, **não é pra virar `if`s
   rígidos** — é pra o TCF ficar **modular** o bastante pra que a aceleração *seja possível* depois. Já
   parcialmente realizado: dispatch O(1) (ADR-0029/0031) + camadas L1/L2/L3 desacopladas (ADR-0033).
2. **Mimemagic externo**: o discriminador logo após `#TCF.8` facilita **identificar o arquivo por fora**
   (libmagic/mimemagic) sem parsear o corpo.

**Consequência de design (não de otimização)**: manter as peças **separadas por funcionalidade** e **não
"soldar" demais** — otimização é baixa prioridade, mas a modularidade que a habilita deve ser preservada
desde já. Otimizar tudo agora NÃO é o objetivo; **não fechar portas** é. Ver
[tcf-camadas-arquitetura](tcf-camadas-arquitetura.md) (camadas desacopladas) + roadmap H-DISC-ACCEL-01.

## Eixo 2 — MARCADORES POR-COLUNA (dentro do meta multi-col `#TCF.8M`)

Cada coluna = `<prefixo?><size>[=nome][:id]`. **Prefixo** = modo de representação; **sufixo `:id`** = nature.

| marcador | posição | fluxo | estado | fonte |
|---|---|---|---|---|
| *(sem prefixo)* | prefixo | tcf (HCC) | ✅ welded | `multi/core.py` |
| `!` | prefixo | raw (V2-A fallback) | ✅ welded | ADR-0022 |
| `@` | prefixo | dict (V2-B) | ✅ welded | ADR-0025 |
| `%` | prefixo | split estrutural | ✅ welded | ADR-0026 |
| `:id` | sufixo do nome | nature (cpf/cnpj/ip) | ✅ welded | ADR-0027 |
| `&<G>` | prefixo | **cross-dict / group-dict (H-GDICT B2)** | 🔭 protótipo (gate geral reprovado) | 2026-06-27 lab |
| `#` | prefixo | **bN (bit-packing enum)** — proposto | 🔭 research-track (gated H-TYPE-02/03) | tipos-meta-grupo-fluxo §5 |
| *(livres)* | prefixo | modo futuro por-coluna | reservável | — |

**Sub-namespace do bN** (nomenclatura owner 2026-07-08 — código reusado como rótulo, não largura):
`b1/b2/b4` = LARGURA FÍSICA (1/2/4 bits, únicas que tile-de-byte) · `b3` = trio "b2+null" (2 bits) ·
`b5/b6/b7` = tipos especiais reservados · **`B` maiúsculo** = bool com dict INTERNO congelado (não declara
referência). Opção "largura exata" descartada (3/5/6/7 bits não tile-de-byte). Ver
[bn-dict-perspectivas §resolução](bn-dict-perspectivas-e-dict-interno.md) + [F1 lab](../2026-07-08-2302-f1-bypass-latencia/result.md).

**Composição** (verificada no código): prefixo + sufixo compõem — `@7=doc:cnpj` (dict + nature),
`!7:cpf` (raw + nature, anônima). Colunas **anônimas** (`drop_names`) omitem `=nome`. `#` como prefixo é
seguro no `.8` (o meta NÃO carrega o prefixo `# ` do #TCF.6 legado — dispensado desde #TCF.7).

## Eixo 3 — chars estruturais em nomes de coluna → ESCAPADOS (não mais rejeitados)

**Atualizado 2026-07-09 (T-FMT-NAME-ESCAPING, M2)**: os separadores `,`/`=`/`:` (+ `\` + prefixo `!@%`
inicial) num nome são **escapados com backslash** (`\,`, `\:`, …) e des-escapados no decode — não mais
REJEITADOS. O tokenizer splita em separador NÃO-escapado. Único char proibido: `\n` (separador de linha
do meta, irrepresentável). Estudo de quoting-implícito (aspas CSV) e chars de hierarquia `{}[]` adiado.

## O esquema de RESERVA (o que fecha os fluxos)

Regra proposta pra qualquer fluxo `.8` novo **não colidir**:
1. **Estrutura nova** (novo layout de blob) → claim um char do **discriminador** (Eixo 1), registrado aqui +
   no ADR-0029 (ato dispositivo do owner). Ex.: hierárquico `H` **precisa** ser registrado antes de weldar.
2. **Modo por-coluna novo** (nova representação de body) → claim um char de **prefixo** (Eixo 2), registrado
   aqui + no ADR relevante. Ex.: bN `#`, cross-dict `&`.
3. **Anotação por-coluna nova** (metadado, não representação) → claim um **sufixo** (como `:id`), com um
   separador reservado no name-guard.
4. **Nenhum char é pego sem entrar neste registry** (evita o incidente `#TCF.8H`).

## Verdito — fecha os fluxos do `.8`?

- **Fluxos ATUAIS** (órfão / multi / single+spec / stamp / raw / dict / split / nature / anônima): **todos
  roteados sem ambiguidade** — o namespace atual é completo e consistente. ✅
- **Gap que este doc fecha**: faltava o **registry + esquema de reserva**. Com eles, os fluxos futuros
  (bN `#`, cross-dict `&`, hierárquico `H`, tcfx) têm slot e regra de claim → sem colisão.
- **Pendência dispositivo (owner)**: promover este registry pra o spec canônico
  [`TCF-format.md`](../../../../docs/algorithms/TCF-format.md). ~~registrar `H` no ADR-0029~~ **FEITO
  2026-07-09**: [ADR-0031](../../../../docs/adr/0031-hierarchical-discriminator-H.md) reservou `H` (char +
  semântica; codec segue gated) — ver Eixo 1 acima. Pendente só a promoção do registry à spec canônica.

## Cross-links

- Plano canônico: [`tcf8-estrutura-plano.md`](tcf8-estrutura-plano.md) · capacidade: [`specs-capacity-map.md`](specs-capacity-map.md).
- Contrato de omissão (deduzir/declarar por char): [T-FMT-OMIT-OR-DECLARE](../../../../tickets/T-FMT-OMIT-OR-DECLARE.md).
- ADRs: 0022 (`!`) · 0025 (`@`) · 0026 (`%`) · 0027 (`:id`) · 0029 (discriminador).
- Research-track que reserva chars: bN [`tipos-meta-grupo-fluxo.md`](tipos-meta-grupo-fluxo.md) (`#`) ·
  hierárquico [EXP-015](../../clean/EXP-015-tcf-hierarquico-csv-json/) (`H`).
