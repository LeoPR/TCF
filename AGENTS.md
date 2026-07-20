# TCF — Guia canônico do projeto

> **Fonte única, agent-agnostic.** Os arquivos de marca de IA
> ([`CLAUDE.md`](CLAUDE.md), [`.github/copilot-instructions.md`](.github/copilot-instructions.md))
> **só apontam pra cá** — não duplicam conteúdo. Qualquer divergência: este arquivo vence.
>
> **Rota**: este guia = *regras* · [`MAP.md`](MAP.md) = *onde fica o quê* ·
> [`STATUS.md`](STATUS.md) = *estado vigente* · [`ROADMAP.md`](ROADMAP.md) = *o que vem*.
> Não repita entre eles; linke.

## 1. O projeto em 1 parágrafo

**TCF** (Tabular Compact Format) — formato **`#TCF.8` default** (ADR-0032; pacote 0.8.0
em curso). Compressão de strings tabulares, **textual e inspecionável** (não compete com
gzip/brotli/zstd). Pipeline canonical delta-aware (M10 baseline, ADR-0011):

- **Pré-pass** — `analyze_column` (features) + `detect_cadence` (ADR-0008) + `detect_min_len` (ADR-0010)
- **OBAT** (Online Bidirectional Affix Tokenizer) — `src/tcf/core/` + `obat_shape.py`
- **HCC** (Hierarchical Compositional Coding M8.A + seq-RLE) — `src/tcf/composicional/`
- **Hierárquico** `#TCF.8H` — `src/tcf/hierarchical.py` (shredding L2/L3, reusa o L1)

API: `from tcf import encode, decode`.

**Números vivem nos TESTES, não na prosa.** Baselines byte-canônicos pinados em
`tests/test_regression_v1_baseline.py` e `tests/test_real_world_snapshots.py`.
Ao citar ganho real-world, **cite a fonte, nunca o número solto**: 9.87% weighted =
H-DA-11 isolado (ADR-0010); 11.73% = Pacote 1 completo (ADR-0011) — ambos vs M9 puro,
não conflitam. A prosa aponta; o teste mede.

## 2. Onde fica o quê

Árvore completa em [`MAP.md`](MAP.md). Aqui só as **regras de acesso** que o mapa não carrega:

| Área | Regra |
|---|---|
| `src/tcf/` | **CANONICAL — não modificar sem aprovação explícita.** Inclui `_core/detect.pyx` (acelerador Cython opcional; manter `.pyx` e fallback puro byte-equivalentes). |
| `src/shaper/`, `src/llm_query/` | **Gadgets auxiliares** (não-core): sob `src/` mas **fora do wheel/sdist**. Importam helpers que ficam em `scripts/`. |
| `scripts/` | Tooling de suporte: `dataset_reader`, `_paths`, `setup_*`, `benchmark_*` (formato/compressão), `schema_gadget/`, `index.py`. Não é TCF-core. |
| `Z:/tcf-data/` | Dados grandes via `config/storage.json`; hubs SQLite em `interim/`. **Nunca baixar externo se já existe aqui.** |
| `old/` | **Congelado-histórico**: `old/tcf` (motor v0.5) · `old/llm-benchmark` (Linha-A refutada). Não modificar, não importar. |
| `docs/adr/` | Decisões numeradas. `docs/findings/` = catálogo v0.5 (**histórico**; findings novos vão em `docs/theory/` ou ADR). |
| `experiments/lab/{dirty,clean}/` | Labs. `dirty/notas/` = diário, checkpoints, `roadmap-hipoteses.md`. |
| `datasets/` | `synthetic/` = CSVs D1-D17 no repo. `canonical/` = só metadata+README (dado real em Z:). |

⚠️ Existem **4 `schema.py`** no repo (`src/tcf` core · `old/tcf` · `src/shaper/strategies` ·
`docs/archive`). **Nunca editar "todos os schema.py" por basename.**

## 3. Antes de agir — checklist obrigatório

**Propor download / recriar infra / sintetizar dataset** — nesta ordem:
`Glob scripts/**/*.py` → `Glob datasets/**` → `Grep` (dataset, reader, loader, fetch,
sampler, shaper) → `STATUS.md` → `MAP.md` → checar `Z:/tcf-data/`.
**Sintoma de falha**: dizer *"vou baixar X"* / *"vou criar Y do zero"* sem ter feito as
buscas. **PARE imediatamente.** (Incidente motivador: EXP-012.)

**Modificar lab existente** — marcado `closed`/`fechado`/`obsolete`/`superseded`:
**não modificar**; abrir novo sub-experimento.

**Criar doc novo** — buscar similar antes; escolher o local:
estável user-facing → `docs/{tutorials,how-to,reference,explanation}/` ·
decisão arquitetural → `docs/adr/NNNN-*.md` · lab → `experiments/lab/{dirty,clean}/` ·
notas contínuas → `experiments/lab/dirty/notas/`. Novo entry-point → registrar em `MAP.md`.

## 4. Gates de evidência

**Antes de declarar `confirmada-empirica`** (anti-incidente 2026-05-21 — Pacote 2 deu
15.7% em sintéticos e 0.13–1.13% em real-world). As 5 perguntas:

1. **Real-world testado?** (Adult Census / TPC-H / lineitem — não só D1-D17)
2. **N ≥ 5 datasets** de fontes diferentes (sintéticos contam à parte)
3. Sintético vs real com ganho similar **ou** diferença explicada?
4. Sintéticos declaram o viés ("construído pra testar esta hipótese")?
5. **Bytes absolutos** relevantes (≥5% real-world weighted), não só % em dataset pequeno?

Algum **NÃO** → marcar com ressalva ou `A-revalidar`. Sub-exp em real-world antes de weld/ADR.

**GATE byte-canonical real-world** (T-REGRESSION-REAL-WORLD): mudança que toca HCC
`_detect_compositions` / pré-pass / qualquer prune **DEVE** passar
`tests/test_real_world_snapshots.py`. O mini-suite D1-D9 + D17a **não basta** — o
candidato prune-k-03 passou nele e regrediu +0.59% em real-world. Weld só com os dois verdes.

**§RT** — nunca reportar bytes sem round-trip validado (`decode(encode(x)) == x`).

## 5. Filosofia de design

TCF não compete com compressores binários (gzip/brotli/zstd), que ocupam **áreas cinzas**
(denso, opaco, exige descomprimir pra ler). TCF ocupa **áreas explicáveis**: textual,
inspecionável, com agrupamentos visíveis *enquanto comprimido*.

1. **Texto + explicabilidade** — `*N|linha` mostra N itens sem descomprimir (agrupamento
   natural, economiza memória). Mesma lógica em ranges `A..B` e seq-RLE `*N+delta|template`.
2. **Speed-first dentro do espaço textual** — pré-pass, índices, Cython são valorados;
   o output observável permanece textual.
3. **Binarização em camadas é INTERNA** (V2-L, ADR-0018) — como Parquet tem row groups /
   page headers binários. Header textual mantido pra inspeção e roteamento.
4. **Anti-pattern**: buffer-over-buffer / cache-over-cache. Streaming (V2-J/K) prioriza
   latência (time-to-first-byte) e zero-copy IO.

**Dados "felizes"** — TCF supõe dados sadios; não entra no mérito de "por que essa data é
32 de fevereiro". Comprime o que receber, agnóstico de origem. **Exceção**: anomalia
detectável de graça (durante operação que já acontece) pode virar sinal — **só detecta,
NUNCA arruma**, e sai por `SideOutputs`.

**SideOutputs** (`src/tcf/side_outputs.py`) é a **ponte oficial** entre TCF e gadgets:
efeito colateral do encode (column_features, cadence_info, hcc_trace, per_col…) que
gadgets consomem a custo zero.

### Escopo — o que É e o que NÃO É TCF

- **É TCF**: pipeline canonical (pré-pass, OBAT, HCC, multi-col, hierárquico), naturezas
  opt-in (CPF/CNPJ/IP — ADR-0015), `PipelineConfig`, `build_schema` em `src/tcf/schema.py`,
  SideOutputs, detecção zero-cost de anomalia, roadmap V2.
- **NÃO é TCF** (gadgets externos, paralelos): schema gadget multi-tabela
  (`scripts/schema_gadget/` — FK/qualidade cross-table), LLM query gadget
  (`src/llm_query/`), Shaper (`src/shaper/`) + `dataset_reader`.

**Filosofia dos gadgets**: pequenos e focados (não platform plays) · **só alertam, NUNCA
arrumam** · paralelos (consomem SideOutputs sem bloquear) · spin-off quando crescerem.
Mapa de estratégias: [`docs/theory/strategies/INDEX.md`](docs/theory/strategies/INDEX.md).

## 6. Convenções

### Estrutura de lab dirty — OBRIGATÓRIA (violar = refazer)

Fonte canônica: `experiments/lab/dirty/notas/dirty-lab-convencoes.md`. Inegociável:

- Pastas por estágio, numeração DENTRO: **`inputs/` + `intermediates/` + `outputs/`**
  (+ `README.md`, `result.md`, `run.py`, `datasets-provenance.md`).
- **Extensão real sempre**: JSON→`.json` · tabular→`.csv` · wire TCF→**`.tcf`** ·
  `.txt` só pra prosa/debug/contraprova.
- **Roundtrip é ARQUIVO diffável**, byte-idêntico ao canônico de `intermediates/`
  (assert no `run.py`). Nunca só prosa/print.
- Gabarito: `experiments/lab/dirty/2026-07-13-2019-especiais-formatos-lado-a-lado/`.

### Naming

Labs dirty `YYYY-MM-DD-HHMM-nome/` (dia+hora — só o dia não ordena) · labs clean
`EXP-NNN-nome/` · sub-exps `NN-descricao/` · ADRs `NNNN-frase-imperativa.md` ·
datasets `D<num><sufixo>-<descricao>.csv`.

### Formato TCF (wire)

- Magic `#TCF.<minor>` — **`#TCF.8` = default** (ADR-0032). `.6`/`.7` = legado cortado
  de `src/tcf` (git-as-compat). Major 0 omite o "0".
- **Discriminador de 1 char** após `#TCF.8` (ADR-0029/0031): `M` = multi-col (meta inline) ·
  `H` = hierárquico · espaço = single+spec · `\n` = version-stamp · nada = single-col órfão
  (default, 0 B). Desconhecido/reservado → **fail-loud**.
- Multi-col `#TCF.8M<meta>`: byte-sizes em **HEX**, nomes com separador escapados com `\`,
  coluna `[!@%]<size>[=<nome>][:id]`, última sem size.
- Hierárquico `#TCF.8H<meta>`: shredding em colunas; folha escalar aceita nature via `:id`.
- **LF only, UTF-8.** Compat pré-1.0: versão antiga é ponto de comparação no git, não
  produção — no 1.0 o passado morre no git (sem `if .7`/`if .6`).

### Status markers (hipóteses)

`aberta` · `em-exp` · `confirmada-empirica` · `confirmada-conceitual` · `refutada`
(`-parcial`, `-real-world`) · `absorvida` · `subsumida` · `adiada` · `welded`.
Add `[VERIFICAR: YYYY-MM-DD]` em claim mutável e `confianca: Alta|Media|Baixa|A-revalidar`
em `confirmada-empirica`. Tickets: `closed-insufficient-gain` / `closed-adiado` / `closed-parcial`.

### Força do artefato — dispositivo vs probatório

Marcar **que ato** o artefato executa (ortogonal a status/confiança) — sem isso, um leitor
lê diretiva, hipótese e registro no mesmo plano e erra.

- **dispositivo** — CONSTITUI o que diz; é a fonte; desfazer exige novo ato:
  ADR `accepted`/`welded`, `src/tcf/` (código canonical), o formato, decisão do owner.
  Não se "revalida na fonte" — ele É a fonte.
- **probatório** — REGISTRA fato verdadeiro alhures; revalida na fonte: resultado de
  experimento, hipótese, métrica, dataset, ticket de teste. Carrega proveniência + confiança.

`INDEX.md` (gerado por `scripts/index.py`) agrupa pelo `type` do frontmatter — usar
`type: decision|experiment|report|dataset|…` já sinaliza a força.

### Camadas de conhecimento

**escopo-projeto** (este guia + `docs/adr/`, versionado em git) · **escopo-usuário**
(memória do agente, fora do repo — preferências pessoais e feedback de processo) ·
**diário** (`experiments/lab/dirty/notas/diario/`, cronológico) · **checkpoints**
(pausas explícitas pra retomada).

## 7. NUNCA

- Modificar `src/tcf/` sem aprovação explícita
- Baixar dados externos quando a infra `Z:/tcf-data/` já existe
- Push pra GitHub / pra `main` sem solicitação explícita
- Commit com `Co-Authored-By:`
- Superlativos ("incrível", "muito melhor", "campeão", "vencedor", "descoberta", "surpreendente")
- `git rebase -i`, `git add -i` (interativo não suportado)
- `git reset --hard`, `git push --force` sem aprovação
- Skip hooks (`--no-verify`)
- Mexer em serviço rodando sem confirmação

## 8. Estado vigente

**Não duplicado aqui** (evita deriva). Ritual de reentrada, nesta ordem:
[`STATUS.md`](STATUS.md) → ticket de release vigente (`tickets/T-REL-08-CLOSEOUT.md`) →
checkpoint mais recente (`experiments/lab/dirty/notas/checkpoints/`) → último diário.
O ticket é **dispositivo**; checkpoint e memória são ponteiros **probatórios**.

> ⚠️ O repo vive dentro do OneDrive — `git log` com HEAD estranho ou arquivo `*-DESKTOP-*`
> é conflito de sync conhecido (ADR-0021).

## 9. Bibliografia metodológica

**Diataxis** (Procida) para `docs/` · **ADR/MADR** (Nygard) para `docs/adr/` ·
**Research Compendium** (Turing Way) para `experiments/` · **FAIR4RS** (metadata em READMEs) ·
**Information Architecture** (Morville) para wayfinding · **Threats to validity**
(Wohlin 2012) — base do checklist §4 · **Ecological validity** (Brunswik 1956) — separar
dataset de design (realista) de dataset de stress (artificial).

Doc-mãe cross-projeto: [`../Methodologies/README.md`](../Methodologies/README.md), com o
Strata em [`recipe/knowledge-architecture.md`](../Methodologies/recipe/knowledge-architecture.md).
