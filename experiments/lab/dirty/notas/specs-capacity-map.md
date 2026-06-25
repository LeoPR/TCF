# Mapa de capacidade — natures / SPECS (ponto de entrada único)

**Data**: 2026-06-24. **Tipo**: reference [consolida fontes dispersas; aponta, não
substitui]. Origem: revisão de capacidade (workflow read-only). Consolida o que
está espalhado em [ADR-0015](../../../../docs/adr/0015-natures-templated-checked-weld.md)
(weld), [ADR-0027](../../../../docs/adr/0027-nature-mark-header-self-describing.md)
(self-describing, parado), [T-EXP-PACOTE5-T03](../../../../tickets/T-EXP-PACOTE5-T03-ENUMERATED.md)
(EnumSpec no-go) e o gadget `scripts/natures_compiler/`.

## Como funciona (ponta-a-ponta)

**Camada 0 (pré-transform) opt-in**, roda ANTES do OBAT+HCC. Cada nature é um
`@dataclass(frozen=True)` puro-dado (Protocol implícito duck-typed) com 3 métodos:
- `classify_value(v) -> str`: `'compressible'` ou razão de rejeição (taxonomia Kim 2003:
  empty_value, format_mismatch, length_wrong, check_invalid, format_unmasked, ...).
- `encode_value(v) -> (payload, status)`: se não-compressible → `MARKER_LITERAL('_')+v`
  (fallback literal, RT garantido); se compressible → forma densa.
- `decode_value(payload) -> str`: reconhece a forma comprimida (`len==encoded_length`
  + alfabeto BASE94 no Checked; slots digit-only no Padded) e reverte; senão passthrough.

Duas "máquinas" paramétricas: **TemplatedCheckedSpec** (ID + check-digit derivável —
CPF/CNPJ, descarta máscara+DV, corpo em base-94) e **TemplatedPaddedSpec** (slots
digit-only fixed-width por padding — IPv4).

**Invariantes**:
- **Opt-in duplo**: por spec (caller passa `nature=`/`nature_per_col=`; default = M10
  byte-idêntico, D1-D9=1523B/D17a=303B) e por valor (cada valor comprime-ou-cai-literal).
- **RT byte-canônico sempre**, inclusive coluna mista (válidos + lixo).
- **Out-of-band**: o blob NÃO carrega qual spec foi usado; decode precisa do spec
  (`decode(text, nature=SPEC)`); spec errado → lixo silencioso. ← é o que [ADR-0027](../../../../docs/adr/0027-nature-mark-header-self-describing.md)
  e a exploração de design abaixo atacam.

## O que expressa hoje

- IDs **templated + check mod-11** (CPF −64%, CNPJ −61% vs M10; confirmado ADR-0015).
- IDs **templated + padded** sem check (normaliza p/ fixed-width → ativa seq-RLE; IP-subnet 1.71%).
- **Gadget DSL** `scripts/natures_compiler/`: pra ID da mesma família (dígito+mod11/padded),
  um `.dsl` de ~5 linhas **deriva `encoded_length` automaticamente + gera regex/formatter
  + valida round-trip em compile-time**. Baixa muito a barra (não é "à mão").
  **MAS `CHECK_FNS` é biblioteca fechada** (mod11-cpf/cnpj/none) — check diferente
  (Luhn/IBAN) ou hex (UUID/MAC) ainda exige código no core.

## Limites (verificados na fonte)

| Limite | Por quê |
|---|---|
| **Não é self-describing** (spec out-of-band; decode errado corrompe em silêncio) | single-col não tem header; multi-col tem mas o carry (ADR-0027 `:id`) está parado em (A) |
| **Seleção 100% manual** (zero auto-detect; `ColumnSchema.natures=[]` placeholder) | ADR-0015 rejeitou auto-detect: quebraria "mesmo input→mesmo output" + falsos positivos |
| **Só forma canônica** (CPF cru de 11 díg → literal; IP com zeros → literal) | regex `^...$`; aceitar forma crua tornaria a reconstrução ambígua → quebraria RT (decisão de segurança) |
| **`check_fn` é dígito-int** (Luhn/IBAN/hex não cabem) | classify extrai digits via isdigit; check opera sobre list[int] |
| **Não valida faixa semântica** (IP octeto 256-999 "comprime"; CPF inexistente com DV válido comprime) | filosofia "dados felizes / só detecta, nunca arruma"; check é gate de COMPRESSIBILIDADE, não de validade |
| **Rigidez de params** (BASE94/`_` globais; Padded só width-por-padding, não slots variáveis) | frozen dataclass; mudar BASE94/`_` quebra RT de outputs já gerados |

**Dívida de telemetria — FECHADA 2026-06-24** (commit `6ea6344`): `encode()` descartava
o `status` do `encode_value`; agora, com `side_outputs=`, agrega apply-rate por coluna em
`SideOutputs.nature_apply` (`{col: {spec, total, compressible, apply_rate, by_status}}`),
byte-neutro. Habilita auto-detect informado no futuro (Fase 3 schema natures).

## EnumSpec — veredicto: NÃO construir

Gap **fechado empiricamente** (T-EXP-PACOTE5-T03, no-go): M10 (dedup + seq-RLE) vence
low-card por **−6.52%** vs encoder explícito; **−2.28% weighted** (regressão). O M10 já
é encoder enumerated implícito. Além disso, enum seria a 1ª nature **column-aware**
(precisa do dict da coluna inteira, não cabe na assinatura per-value) → exigiria estender
o protocolo. Subsumido. Energia zero.

## Custo de estender (candidatas)

| Nature | Cabe? | Veredicto |
|---|---|---|
| **ISO-date `YYYY-MM-DD`** | Sim (Padded slots [4,2,2]) | **Melhor candidato** — mesma mecânica do IP, sweet-spot de seq-RLE em datas com cadência. **PRÉ-REQUISITO: medir overlap com `detect_cadence`/`detect_min_len`** (o pré-pass já pode capturar → redundante). |
| UUID (hex) | Parcial | Precisa 3ª máquina (hex packing); UUIDv4 é aleatório → ganho some sob binário. Não. |
| monetary-string | Não bem | Layout variável + semântica numérica que o pré-pass delta-aware já cobre. Duplicaria. Não. |
| enum/categorical | Não | Já medido contraproducente (acima). Não. |

## Conclusões

1. **Framework pronta pra estender** (boilerplate baixo, menor via DSL) — **o bloqueio é
   empírico, não arquitetural**: faltam datasets reais com ganho ≥15%/2 reais (CNPJ só
   rende em Receita = 1 real; CPF/IP só em sintéticos).
2. Único acionável feito: **telemetria** (nature_apply). Próximo natural seria ISO-date
   (medindo overlap antes) OU o self-describing (abaixo).
3. EnumSpec/UUID/monetary/enum: **não construir**.

## Self-describing — interpretação pelo header

Pergunta do owner (2026-06-24): SPECS interpretáveis pelo header, **byte-neutro** —
indicador EXPLÍCITO (tipo a flag `M`) OU identificação IMPLÍCITA. Exploração de design
(workflow read-only `w9f1pbp90`, crítico adversarial rodou o código real).

### O que "byte-neutro" significa aqui (precisão)
NÃO é "o blob nunca muda". É: (1) **não-regressão do default-off** — o caminho SEM
nature não muda 1 byte (D1-D9=1523B, D17a=303B intactos); (2) **leitura de #TCF.6/7
intacta**. O caminho COM nature **já produz bytes diferentes hoje** por design (o pré-tx
muda o body antes do pipeline). Então "neutro" só se aplica ao default-off + legado.

### Rota IMPLÍCITA — INSEGURA por construção (descartar)
O decode adivinharia o spec dos valores reconstruídos, sem tag. **Inviável byte-seguro**:
o predicado de `decode_value` (`len==encoded_length AND alfabeto BASE94`; `len==total_padded
AND isdigit`) **pressupõe** o spec — não o descobre — e é satisfeito por dado comum trivial.
Confirmado executando o código real:
- `decode_value(SPEC_CPF, 'hello') → '240.424.182-562'`; `'12345' → '456.788.335-70'`
- `decode_value(SPEC_IP, '192168001001') → '192.168.1.1'`; qualquer 12 dígitos (telefone, código de barras, YYYYMMDDHHMM) vira IP
- `decode_value(SPEC_CPF, '_foo') → 'foo'` (prefixo `_` literal-stripped engole `_private`/`__init__`)

Causa-raiz estrutural: `len`+alfabeto é condição **necessária mas longe de suficiente**;
BASE94 inclui dígitos → colisão enorme, não residual. Probe-só-no-decode adivinha (lossy);
probe-no-encode muda bytes de colunas que ninguém pediu (regride baseline) **e** ainda
precisaria gravar tag pro decode reproduzir → vira a rota explícita. **Veredicto: descartar.**

### Rota EXPLÍCITA (ADR-0027 `:id`) — única byte-neutra
Design já fechado: sufixo `:id` no nome da coluna no meta-line (`!15=cpf,doc:cnpj`), magic
`#TCF.8 M` emitido **SSE** `bool(nature_ids)`; encoding do spec = a STRING `spec.name`
(cpf/cnpj/ip), vocabulário fechado; decode resolve via dict fixo core-only (`SPEC_REGISTRY`,
zero eval), id desconhecido → cru + `SideOutputs.unknown_nature_ids` (forward-compat).

**Ponto MÍNIMO byte-neutro** (o invariante-chave): a subida pra `#TCF.8` e o append do
`:id` condicionados **EXCLUSIVAMENTE a `bool(nature_ids)`**, NUNCA a `min_header`/`used_v2`
— senão arrastaria nature pra colunas que não pediram. Com `nature_ids` vazio = codepath
literalmente o de hoje → zero delta.

**Em qual ponto implementar** (9 pontos, todos em multi-col; ADR-0027 tem o diff, mas
**corrigir a localização**: é `src/tcf/multi/core.py` (pacote), não `multi.py`):
`natures/__init__.py` (SPEC_REGISTRY + `_resolve_nature_id` tolerante — NÃO reusar
`registry.py:get()` que faz `raise`) · `encoder.py` ramo dict (coletar `nature_ids =
{name: spec.name}`) · `multi/core.py` (MAGIC_MULTI_V3, escolha de magic por `bool(nature_ids)`,
append `:id` na meta-line, proibir `:` no validador de nome, parse do `:`, decode resolve+aplica)
· `decoder.py` (aceitar `#TCF.8 M`). GATE: real-world snapshots + D1-D9 + D17a + RT com-nature,
os DOIS suites verdes.

### Single-col — fica PARKADO
Single-col não tem header (body puro até EOF); qualquer tag nova ali quebra o byte-canônico
de TODO single-col. O gap "nome viaja no blob" permanece aberto pra single-col mesmo se a
rota multi-col for feita. Decisão separada com gate próprio.

### Status — IMPLEMENTADO (MVP welded 2026-06-24)
O owner autorizou implementar a rota explícita (antes parada em (A)). MVP em `src/tcf`:
`#TCF.8 M` + `:id` no meta-line, 3 ids core, opt-in estrito, **byte-neutro default-off**
(D1-D9=1523B/D17a=303B/real-world=89616B intactos). encode coleta `nature_ids={col:
spec.name}`; decode (`_decode_multi_impl` parseia, `decode()` resolve via `SPEC_REGISTRY`
fixo + precedência header-vence). id desconhecido → cru + `warnings.warn` (forward-compat).
9 testes; ADR-0027 → accepted. **Single-col TAMBÉM welded** (2026-06-24): `#TCF.8` sem
flag `M` (= single → `list`), `[nome]:spec_id` com nome opcional; `encode(list, nature=,
name=)`; opt-in (sem nature = body puro byte-idêntico); +9 testes test-first.
**Parkado**: lazy-view #TCF.8 (`view.py` rejeita com erro claro). Rota implícita
**descartada** (insegura). Release: pacote segue 0.7.1; format #TCF.8 → próximo release
seria 0.8.0 (ADR-0028), decisão à parte.

## Cross-links

- [ADR-0015](../../../../docs/adr/0015-natures-templated-checked-weld.md) (weld natures),
  [ADR-0027](../../../../docs/adr/0027-nature-mark-header-self-describing.md) (self-describing parado),
  [T-EXP-PACOTE5-T03](../../../../tickets/T-EXP-PACOTE5-T03-ENUMERATED.md) (EnumSpec no-go).
- `src/tcf/natures/` (código), `scripts/natures_compiler/` (gadget DSL).
- [docs/algorithms/core-data-model.md](../../../../docs/algorithms/core-data-model.md) (natures = CAMADA 0 no pipeline).
