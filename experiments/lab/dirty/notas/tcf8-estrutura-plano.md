# TCF.8 — estrutura e plano (consolidado) [plano]

**Data**: 2026-06-25. **Tipo**: plano (fonte única da família `#TCF.8`). Consolida e
reconcilia: [ADR-0027](../../../../docs/adr/0027-nature-mark-header-self-describing.md)
(natures self-describing), [ADR-0029](../../../../docs/adr/0029-version-format-identification-semi-implicit.md)
(identificação versão/formato), [ADR-0028](../../../../docs/adr/0028-pre-1.0-versioning-minor-format-coupling-release-cadence.md)
(versionamento) e o [`v08-plano-etapas.md`](v08-plano-etapas.md) (lazy + cross-dict —
**parcialmente superado** pra a parte de formato; ver §Reconciliação). Spec canônica do
formato em [TCF-format.md](../../../../docs/algorithms/TCF-format.md).

## O que é o `#TCF.8`

A **família de formato self-describing** do TCF. Não é "uma" feature — é o guarda-chuva
sob a estratégia **semi-implícita** ([ADR-0029](../../../../docs/adr/0029-version-format-identification-semi-implicit.md)):
- **órfão default** (0 bytes): single-col simples = body puro, sem shebang (camada 1);
- **header no desvio** (opt-in): qualquer capacidade NÃO-default marca-se no header `#TCF.8`;
- **chamada explícita** (sempre disponível): `encode`/`decode` podem declarar.

Major version = externo; minor de formato = in-file; byte-neutro no default (D1-D9=1523B
intacto). **Linchpin**: congelar o body single-col no 1.0 (pré-requisito do órfão).

## Princípio organizador: features são "desvios" opt-in marcáveis

Toda capacidade #TCF.8 é um **desvio opt-in** do default, marcado no header. O
**discriminador de 1 char** (char após `#TCF.8`) roteia a estrutura; dentro dela, sufixos/
flags marcam as features. Catálogo:

| feature | marca no header | estado |
|---|---|---|
| **discriminador** estrutura | `M` (multi) / ` ` (single+spec) / `\n` (stamp) / (nada=órfão) | ✅ feito |
| **natures self-describing** | `:spec` no nome da coluna (cpf/cnpj/ip) | ✅ feito |
| **colunas anônimas** | omissão do `=nome` (posicional) — `drop_names` | ✅ feito |
| **version-stamp** | `#TCF.8\n` (single plano carimbado) — magic-number p/ `file` | ✅ feito |
| **cross-dict (H-GDICT)** | dict global no header (valores compartilhados entre colunas) | 🔭 futuro (era workstream B do v08; agora é feature #TCF.8) |
| *(futuras)* | — | conforme surgirem, cada uma um desvio marcável |

Forma vigente (resumo; spec em TCF-format.md):
```
#TCF.8M!7=doc:cnpj,!x     multi (meta inline; nomeado/anônimo via drop_names; :spec nature)
#TCF.8 docs:cpf           single + spec (nome opcional)
#TCF.8                    single version-stamp (body single-col puro)
<body>                    órfão (default, sem shebang)
```

## Plano / sequência

```
[FEITO] discriminador + natures + anônimas + version-stamp + ADR-0027/0029
   |
   v
1. LAZY-VIEW #TCF.8  ✅ FEITO (2026-06-25): view.py lê #TCF.8M + natures lazy + anônimas
   |
   v
2. Congelar body single-col @1.0 (compromisso, ADR — linchpin do órfão)
   |
   v
3. Release 0.8.0 (formato #TCF.8; pacote 0.7.1 -> 0.8.0; PyPI segura até go)
   |
   v
4. Cross-dict (H-GDICT): B1 caracterizar -> (se pagar gate) weldar opt-in no #TCF.8
   |
   v
5. [0.9] tcfx index / lazy avançado (H-QUERY-04): pushdown + índices
```

### 1. Lazy-view #TCF.8 ✅ FEITO (2026-06-25)
`LazyTCF._parse` ([view.py](../../../../src/tcf/view.py)) passou a aceitar `#TCF.8M`:
meta **inline** (linha 1) + `:id` + colunas anônimas (nome posicional) — espelha
`_decode_multi_impl`. `_col` aplica `decode_value` ao materializar coluna com nature
(**lazy preservado** — só a coluna consultada). Read-only, aditivo. Single (spec/stamp)
fora (LazyTCF é multi-col). +3 testes test-first; suíte 414.

### 2. Congelar single-col @1.0 ✅ FEITO (ADR-0030, 2026-06-25)
Política decidida ([ADR-0030](../../../../docs/adr/0030-freeze-single-col-body-at-1.0.md)):
o body single-col vira contrato imutável NO 1.0 → órfão decodável pra sempre. Disciplina:
otimizações futuras (EI, H-INTRA…) viram desvios opt-in marcados, não mutação da base.
Pré-1.0 ainda refinável (ADR-0024). Efeito no 1.0.

### 3. Release 0.8.0
ADR-0028: formato #TCF.8 → release 0.8.0. Pacote em 0.7.1; bump + CHANGELOG + tag só com
go explícito (PyPI segura).

### 4. Cross-dict (H-GDICT) — feature opt-in dentro do #TCF.8
Era o workstream B do v08-plano (reservava "#TCF.8" pra isto). **Reconciliado**: cross-dict
é UM desvio opt-in na família #TCF.8 (dict global no header = leitura única; sinergia com o
lazy). B1 caracterizar (lab read-only, gate ≥15%/2-reais OU justificativa estrutural de
latência); se pagar, B2 design + B3 weld opt-in (default off = byte-idêntico) + B4 integrar
com o lazy. Anti-incidente 2026-05-21: medir real + sob brotli.

### 5. tcfx index / lazy avançado (futuro, "com calma")
Ideia do owner: um índice **`.tcfx`** (sidecar ou in-blob) pra pushdown/consulta sem
materializar. Base existente: [`hquery01-decode-dag-indices-design.md`](hquery01-decode-dag-indices-design.md)
(decode-DAG + índices escondidos, H-QUERY-04, deferido 0.9) + [`patricia-trie-exploration.md`](../../../../docs/theory/patricia-trie-exploration.md).
Encaixe natural: o índice é mais um "desvio" (in-blob) OU um artefato externo (sidecar) que
o lazy consome. **Decisão de design adiada** — registrar quando chegar a vez.

## Reconciliação com o v08-plano-etapas.md

- **Workstream A (lazy)**: A4 (promover → `src/tcf/view.py`) **feito**. O **lazy-view #TCF.8**
  é um sub-item NOVO (o v08-plano é de 2026-06-19, anterior ao #TCF.8 desta sessão).
- **Workstream B (cross-dict)**: o plano reservava "#TCF.8" pro cross-dict. **Agora** #TCF.8 é
  a família self-describing; cross-dict é UMA feature dentro dela (§4). Sem conflito.
- **Versão (ADR-0028)**: lazy (formato #TCF.7) seria 0.7.2; mas o #TCF.8 desta sessão já
  mudou o formato → o próximo release é **0.8.0** (engloba natures+discriminador+anônimas+lazy-#TCF.8).

## Invariantes (guardião)
- `src/tcf` só com aprovação. byte-neutro no default (D1-D9=1523B / D17a=303B intactos).
- Toda feature #TCF.8 = opt-in (default órfão/#TCF.7 byte-idêntico).
- Antes de mudança grande de formato (cross-dict): reconferir L0 (Strata).
- Cross-reference (MAP/STATUS/ROADMAP) + GATE real-world.

## Cross-links
- Specs: [TCF-format.md](../../../../docs/algorithms/TCF-format.md), ADR-0027/0028/0029.
- Capacidade SPECS: [specs-capacity-map.md](specs-capacity-map.md).
- Lazy: [view.py](../../../../src/tcf/view.py), [docs/reference/lazy-view.md](../../../../docs/reference/lazy-view.md),
  design 0.9 [hquery01-decode-dag-indices-design.md](hquery01-decode-dag-indices-design.md).
- Cross-dict: [v08-plano-etapas.md](v08-plano-etapas.md) §B, roadmap-hipoteses (H-GDICT).
