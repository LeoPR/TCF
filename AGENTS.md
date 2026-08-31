# TCF: Guia canônico do projeto

> **Fonte única, agent-agnostic.** Os arquivos de marca de IA
> ([`CLAUDE.md`](CLAUDE.md), [`.github/copilot-instructions.md`](.github/copilot-instructions.md))
> **só apontam pra cá**, não duplicam conteúdo. Qualquer divergência: este arquivo vence.
>
> **Rota**: este guia = *regras* · [`MAP.md`](MAP.md) = *onde fica o quê* ·
> [`STATUS.md`](STATUS.md) = *estado vigente* · [`ROADMAP.md`](ROADMAP.md) = *o que vem*.
> Não repita entre eles; linke.

## 0. As invariantes: o que se repete até virar automático

**Autoridade única desta lista.** Se uma regra aparece aqui, as outras seções **apontam**
para cá em vez de re-narrar (Strata §5: autoridade única ≠ instância única; o antipadrão é
a cópia que finge ser fonte). As que estão marcadas com ⟳ o owner **já precisou repetir
várias vezes**. Se você está prestes a fazer o contrário, pare.

### I1 ⟳ A superfície carrega só o PRESENTE; o traço é o git

Vale para **código, documentação e índices**, sem exceção:

- **Comentário e docstring** dizem por que o código é como é, nunca `RE-PIN <data>`,
  `ERA: X`, "antes era Y", "weld de <data>". Rationale e invariante ficam (Chesterton);
  cronologia sai.
- **Doc de leitura** (`docs/algorithms`, `how-to`, `reference`, `tutorials`, READMEs) diz
  **o que vale**. Ponto. Nunca `CORRIGIDO <data>`, "esta seção dizia X", "os números aqui
  eram os de <data>". *Esses documentos não são publicação formal, logo não são errata de
  nada.*
- **Onde a história vive**: mensagem de commit (o porquê da mudança) · `CHANGELOG.md` (o
  que mudou entre versões) · ADR (a decisão e seu racional).
- **Ponteiro ≠ narrativa**: citar `ADR-NNNN` como autoridade vigente fica; contar a
  novela de como se chegou lá, não.

**O que NÃO se apaga** (é traço, não superfície): `docs/adr/` (ADR aceito nunca é editado;
vigência vai no Status do índice), `docs/archive/`, `docs/findings/`, labs em
`experiments/`, `CHANGELOG.md`, e o histórico do git.

**Não se apaga, mas se ARQUIVA por era** (owner, 2026-08-31): material de uma era fechada
vai para `docs/archive/era-<N>/` por `git mv`, com os ponteiros da superfície reescritos.
Não é perda, é dar um lugar único e datado, que é o que faz a busca ficar rápida sem
quebrar os ponteiros que vivem dentro de ADR imutável. Ver **I8**.

> Strata §3: o traço é *append-only*; a **superfície decai ativamente**. Aplicar
> *append-only* à superfície é o erro que faz a leitura apodrecer sob o peso do que já não
> vale. Apagar da superfície com autorização **não** é edição furtiva: o commit é o
> tombstone.

### I8 A era do wire tem prazo escrito: janela N-1, e o registro tem 2 linhas

Corolário do I1 aplicado ao **formato**, com mecanismo. A era do wire vive em
[`src/tcf/wire.py`](src/tcf/wire.py), e só ali: no máximo **duas** eras, a vigente e a
anterior com **data de sunset escrita no commit que promoveu a sucessora**.

**Esquecer tem três níveis, e eles não acontecem juntos:**

| nível | quando | o quê |
|---|---|---|
| parar de **servir** | no dia da virada, janela zero | emissão e decode da era anterior saem do `src`, com fail-loud nomeando o caminho de volta |
| parar de **citar** | na data de sunset | a superfície deixa de nomear a era. É este nível que dá velocidade de busca |
| apagar do **disco** | na data de sunset | só o regenerável: fixtures, blobs de lab, snapshots |

**A janela não custa código legado vivo.** O comparativo migratório entre duas eras roda com
a era anterior instalada do PyPI (`pip install tcf-format==0.N.*`) ou pela tag do git, em
ambiente à parte. É por isso que "parar de servir" não é perder o dado, e é o que torna o
esquecimento barato.

**Dois eixos.** A era do WIRE é o contrato on-disk; a versão do PACOTE é o que o PyPI guarda
para sempre, e é ela o leitor da era morta (a separação que o Apache Arrow faz entre Format
Version e Library Version). O minor do pacote acompanha o formato (ADR-0028).

O que sustenta, sem depender de alguém lembrar:
[`test_wire_eras.py`](tests/test_wire_eras.py) (limite de duas eras, e a catraca que impede
a grafia solta de crescer) e
[`test_superficie_sem_versao_morta.py`](tests/test_superficie_sem_versao_morta.py) (a janela,
com o relógio no commit do `HEAD` para a história não ficar vermelha retroativamente).

> Precedente: a regra número 1 do Kubernetes é *a versão antiga não se edita, ela para de ser
> servida*. Esta invariante é **pré-1.0** e morre no 1.0, quando a base instalada deixar de
> ser desprezível.

### I2 ⟳ Lab sem evidência em disco é lab NÃO FEITO

Todo lab grava `inputs/`, `intermediates/`, `outputs/` com **extensão real**
(`.json`/`.csv`/`.tcf`), e o `run.py` **falha** se faltar (portão anti-órfão). Wire só
existe se estiver gravado; medição sem arquivo não entrou. Detalhe da estrutura em §6.

### I3 ⟳ Teste de massa usa o Shaper

Volume/limpeza vêm de `src/shaper/`: amostra honesta é representatividade +
dimensionamento + distribuição. SQL direto só em teste pequeno de ajuste.

### I4 §RT: nunca reportar byte sem round-trip validado

`decode(encode(x)) == x` antes de qualquer número. Sem RT, o número não entra em lugar
nenhum: nem em prosa, nem em tabela, nem em commit.

### I5 `src/tcf/` só muda com aprovação explícita

E toda mudança passa nos gates byte-canônicos: os dois, D1-D9/D17a **e**
`test_real_world_snapshots.py` (§4 explica por que o mini-suite não basta).

### I7 Antes de registrar DIREÇÃO, varra os registries

Ideia de rumo (otimização, formato, integração) vai primeiro aos dois registries:
`roadmap-hipoteses.md` (hipóteses `H-*`) e `futuras-otimizacoes-formato.md` (`O-FMT-*`), em
`experiments/lab/dirty/notas/2026-05/`. Se já existe, **estenda** o registro, não abra ticket
paralelo, que vira segunda autoridade sobre o mesmo fato (Strata §5).

> Aconteceu em 2026-08-23: abri ticket de armazenamento que `O-FMT-20` (sidecar `.tcfx`,
> append, parquet) e `H-QUERY-04` (design de índices, com o princípio *derivável > sidecar >
> formato* já decidido) cobriam desde julho/junho. Revertido.

### I6 Antes de mudança grande, reconferir o L0 do Strata

Format change, weld em `src/tcf`, ADR novo aceito, release, reorg de docs: passada rápida
de aderência aos 10 princípios L0 **antes** de prosseguir. Proporcional ao esforço (§9 do
Strata): mudança pequena não exige.

## 1. O projeto em 1 parágrafo

**TCF** (Tabular Compact Format): formato **`#TCF.8` default** (ADR-0032; pacote
`0.8.1` no PyPI). Compressão de strings tabulares, **textual e inspecionável** (não compete com
gzip/brotli/zstd). Pipeline canonical delta-aware (M10 baseline, ADR-0011):

- **Pré-pass**: `analyze_column` (features) + `detect_cadence` (ADR-0008) + `detect_min_len` (ADR-0010)
- **OBAT** (Online Bidirectional Affix Tokenizer): `src/tcf/core/` + `obat_shape.py`
- **HCC** (Hierarchical Compositional Coding M8.A + seq-RLE): `src/tcf/composicional/`
- **Hierárquico** `#TCF.8H`: `src/tcf/hierarchical.py` (shredding L2/L3, reusa o L1)

API: `from tcf import encode, decode`.

**Números vivem nos TESTES, não na prosa.** Baselines byte-canônicos pinados em
`tests/test_regression_v1_baseline.py` e `tests/test_real_world_snapshots.py`.
Ao citar ganho real-world, **cite a fonte, nunca o número solto**: 9.87% weighted =
H-DA-11 isolado (ADR-0010); 11.73% = Pacote 1 completo (ADR-0011). Ambos vs M9 puro,
não conflitam. A prosa aponta; o teste mede.

## 2. Onde fica o quê

Árvore completa em [`MAP.md`](MAP.md). Aqui só as **regras de acesso** que o mapa não carrega:

| Área | Regra |
|---|---|
| `src/tcf/` | **CANONICAL: não modificar sem aprovação explícita.** Inclui `_core/detect.pyx` (acelerador Cython opcional; manter `.pyx` e fallback puro byte-equivalentes). |
| `src/shaper/`, `src/llm_query/` | **Gadgets auxiliares** (não-core): sob `src/` mas **fora do wheel/sdist**. Importam helpers que ficam em `scripts/`. |
| `scripts/` | Tooling de suporte: `dataset_reader`, `_paths`, `setup_*`, `benchmark_*` (formato/compressão), `schema_gadget/`, `index.py`. Não é TCF-core. |
| `<data_root>/` | Dados grandes via `config/storage.json`; hubs SQLite em `interim/`. **Nunca baixar externo se já existe aqui.** |
| `old/` | **Congelado-histórico**: `old/tcf` (motor v0.5) · `old/llm-benchmark` (Linha-A refutada). Não modificar, não importar. |
| `docs/adr/` | Decisões numeradas. `docs/findings/` = catálogo v0.5 (**histórico**; findings novos vão em `docs/theory/` ou ADR). |
| `experiments/lab/{dirty,clean}/` | Labs. `dirty/` aninha macros por `<YYYY-MM>/<YYYY-MM-DD>/` (§6); `dirty/notas/` = diário, checkpoints, registries (`roadmap-hipoteses.md`) + notas por mês. ⚠️ **`dirty/` e `archive/` NÃO são versionados** (desde 2026-08-22): existem no disco, fora do git. Ver a fronteira abaixo. |
| `datasets/` | `synthetic/` = CSVs D1-D17 no repo. `canonical/` = só metadata+README (dado real fora do repo). |

### Fronteira do que é publicado (owner, 2026-08-22)

O repositório é **público**. O que ele publica é a **lógica** e a **evidência que sustenta as
afirmações**; o **caderno de trabalho** fica reservado.

| publicado | reservado (existe no disco, fora do git) |
|---|---|
| `src/` · `tests/` · `docs/` (incl. ADRs) · `datasets/` · `scripts/` · `tickets/` | `experiments/lab/dirty/`: labs, **notas de direção**, **diários de sessão** |
| `experiments/lab/clean/`: experimentos publicáveis | `experiments/lab/archive/` |
| `experiments/results/evidencia-0.8/`: as medições do release | `.claude/` |
| `experiments/lab/framework/`: harness dos clean | |

Mecanismo: `git rm --cached` + `.gitignore`, some da versão atual, permanece no histórico (I1). Consequência prática: **a doc pública cita
caminhos de `dirty/` como ponteiro de evidência** (368 ocorrências, 112 só nos ADRs, que são
imutáveis). Esses ponteiros continuam válidos *localmente* e no histórico; para quem só vê o
GitHub de hoje, apontam para fora da árvore. É trade-off aceito: a alternativa seria reescrever
ADR imutável.

⚠️ Existem **4 `schema.py`** no repo (`src/tcf` core · `old/tcf` · `src/shaper/strategies` ·
`docs/archive`). **Nunca editar "todos os schema.py" por basename.**

## 3. Antes de agir: checklist obrigatório

**Propor download / recriar infra / sintetizar dataset**, nesta ordem:
`Glob scripts/**/*.py` → `Glob datasets/**` → `Grep` (dataset, reader, loader, fetch,
sampler, shaper) → `STATUS.md` → `MAP.md` → checar `<data_root>/`.
**Sintoma de falha**: dizer *"vou baixar X"* / *"vou criar Y do zero"* sem ter feito as
buscas. **PARE imediatamente.** (Incidente motivador: EXP-012.)

**Modificar lab existente**, marcado `closed`/`fechado`/`obsolete`/`superseded`:
**não modificar**; abrir novo sub-experimento.

**Criar doc novo**, buscar similar antes; escolher o local:
estável user-facing → `docs/{tutorials,how-to,reference,explanation}/` ·
decisão arquitetural → `docs/adr/NNNN-*.md` · lab → `experiments/lab/{dirty,clean}/` ·
notas contínuas → `experiments/lab/dirty/notas/`. Novo entry-point → registrar em `MAP.md`.

## 4. Gates de evidência

**Antes de declarar `confirmada-empirica`** (anti-incidente 2026-05-21: Pacote 2 deu
15.7% em sintéticos e 0.13 a 1.13% em real-world). As 5 perguntas:

1. **Real-world testado?** (Adult Census / TPC-H / lineitem, não só D1-D17)
2. **N ≥ 5 datasets** de fontes diferentes (sintéticos contam à parte)
3. Sintético vs real com ganho similar **ou** diferença explicada?
4. Sintéticos declaram o viés ("construído pra testar esta hipótese")?
5. **Bytes absolutos** relevantes (≥5% real-world weighted), não só % em dataset pequeno?

Algum **NÃO** → marcar com ressalva ou `A-revalidar`. Sub-exp em real-world antes de weld/ADR.

**GATE byte-canonical real-world** (T-REGRESSION-REAL-WORLD): mudança que toca HCC
`_detect_compositions` / pré-pass / qualquer prune **DEVE** passar
`tests/test_real_world_snapshots.py`. O mini-suite D1-D9 + D17a **não basta**: o
candidato prune-k-03 passou nele e regrediu +0.59% em real-world. Weld só com os dois verdes.

**§RT**: ver **I4**. Nunca reportar bytes sem round-trip validado.

## 5. Filosofia de design

TCF não compete com compressores binários (gzip/brotli/zstd), que ocupam **áreas cinzas**
(denso, opaco, exige descomprimir pra ler). TCF ocupa **áreas explicáveis**: textual,
inspecionável, com agrupamentos visíveis *enquanto comprimido*.

1. **Texto + explicabilidade**: `*N|linha` mostra N itens sem descomprimir (agrupamento
   natural, economiza memória). Mesma lógica em ranges `A..B` e seq-RLE `*N+delta|template`.
2. **Speed-first dentro do espaço textual**: pré-pass, índices, Cython são valorados;
   o output observável permanece textual.
3. **Binarização em camadas é INTERNA** (V2-L, ADR-0018), como Parquet tem row groups /
   page headers binários. Header textual mantido pra inspeção e roteamento.
4. **Anti-pattern**: buffer-over-buffer / cache-over-cache. Streaming (V2-J/K) prioriza
   latência (time-to-first-byte) e zero-copy IO.

**Dados "felizes"**: TCF supõe dados sadios; não entra no mérito de "por que essa data é
32 de fevereiro". Comprime o que receber, agnóstico de origem. **Exceção**: anomalia
detectável de graça (durante operação que já acontece) pode virar sinal: **só detecta,
NUNCA arruma**, e sai por `SideOutputs`.

**SideOutputs** (`src/tcf/side_outputs.py`) é a **ponte oficial** entre TCF e gadgets:
efeito colateral do encode (column_features, cadence_info, hcc_trace, per_col…) que
gadgets consomem a custo zero.

### Escopo: o que É e o que NÃO É TCF

- **É TCF**: pipeline canonical (pré-pass, OBAT, HCC, multi-col, hierárquico), naturezas
  opt-in (CPF/CNPJ/IP, ADR-0015), `PipelineConfig`, `build_schema` em `src/tcf/schema.py`,
  SideOutputs, detecção zero-cost de anomalia, roadmap V2.
- **NÃO é TCF** (gadgets externos, paralelos): schema gadget multi-tabela
  (`scripts/schema_gadget/`, FK/qualidade cross-table), LLM query gadget
  (`src/llm_query/`), Shaper (`src/shaper/`) + `dataset_reader`.

**Filosofia dos gadgets**: pequenos e focados (não platform plays) · **só alertam, NUNCA
arrumam** · paralelos (consomem SideOutputs sem bloquear) · spin-off quando crescerem.
Mapa de estratégias: [`docs/theory/strategies/INDEX.md`](docs/theory/strategies/INDEX.md).

## 6. Convenções

### Dirty × clean: camadas com PROPÓSITOS distintos (owner, 2026-08-10)

| | dirty | clean |
|---|---|---|
| compromisso | **nenhum**: destrói e refaz à vontade | é quase o protótipo que vai soldar |
| conteúdo | hipótese sem solução, N testes p/ a MESMA coisa, ferramenta descartável | o **melhor concluído** do dirty, ou o **soldado** adaptado às conclusões do dirty |
| conclusões | **orientativas** (ainda que concluam, pelo volume de teste) | **verificação com rigor + dados**: nada óbvio e grande quebrou? ainda melhora? |
| linguagem do relatório | "aponta para", "o teto é", "vale investigar" | "não quebrou", "ainda melhora em X", "o pin segurou" |

O ciclo **dirty ↔ clean vai e volta**; o último estágio é **soldar de fato** e testar com
mais dados se for o caso. No foco atual (ajustar o `.8`), o clean é um misto de *soldar* e
*testar que nada regrediu*. Um clean que só repete o dirty com mais casos não cumpriu o
papel: ele carrega o candidato de weld **e** o gate de regressão.

### Estrutura de lab: OBRIGATÓRIA (violar = refazer) · vale p/ **dirty E clean**

Fonte canônica: `experiments/lab/dirty/notas/2026-07/dirty-lab-convencoes.md`, **estendida aos
labs clean em 2026-08-10** (`.../2026-08/2026-08-10-labs-rastreabilidade-convencao.md`, auditoria
achou que 17 dos 20 EXP-* eram invisíveis ao git e só 2 gravavam contra-prova). Inegociável:

- Pastas por estágio, numeração DENTRO: **`inputs/` + `intermediates/` + `outputs/`**
  (+ `README.md`, `result.md`, `run.py`, `datasets-provenance.md`).
- **Extensão real sempre**: JSON→`.json` · tabular→`.csv` · wire TCF→**`.tcf`** ·
  `.txt` só pra prosa/debug/contraprova.
- **Roundtrip é ARQUIVO diffável**, byte-idêntico ao canônico de `intermediates/`
  (assert no `run.py`). Nunca só prosa/print.
- **Todo caso tem input em disco** (inclusive sintético) e **toda contra-prova é ARQUIVO**:
  `inputs/<caso>.entrada.json` e `outputs/<caso>.roundtrip.json` na MESMA formatação: `diff`
  vazio é a prova, e o runner roda esse mesmo diff.
- **O runner LIMPA `outputs/`/`intermediates/`** antes de gerar (órfão é indistinguível de
  resultado) e **o lab entra no `.gitignore` com exceção nominal no mesmo commit**: sem isso
  os artefatos não existem para quem revisa (`output*` na linha 49 engole tudo).
- **Nome curto e ESTÁVEL + `outputs/INDEX.md` GERADO** (nome → ideia → input → veredito → prova);
  o significado mora no índice, não no nome. Todo número publicado tem arquivo; número que veio
  de fora do runner leva a fonte atribuída no texto.
- Gabarito dirty: `experiments/lab/dirty/2026-07/2026-07-13/2026-07-13-2019-especiais-formatos-lado-a-lado/`.
  Gabarito clean: `experiments/lab/clean/EXP-017-data-alvos-mensais/`.

### Naming e organização de pastas

**Labs dirty**: nome `YYYY-MM-DD-HHMM-descricao/` (dia+hora; só o dia não ordena),
**aninhados por data** (nesting 2026-07-22, evita a `dirty/` flat com 60+ macros):
`experiments/lab/dirty/<YYYY-MM>/<YYYY-MM-DD>/<YYYY-MM-DD-HHMM-descricao>/`. Sub-exps
`NN-descricao/` dentro. `old/` tem layout próprio (welded/refuted/…), **não** aninhado por data.
**Notas** (`dirty/notas/`): agrupadas por **mês do 1º commit** (`<YYYY-MM>/`); `diario/` e
`checkpoints/` ficam fora do agrupamento. Duas naturezas de nota:
*registry/referência vivo* = **nome-nu estável** (ex. `roadmap-hipoteses.md`,
`tcf8-estrutura-plano.md`; datá-lo mente, ele vive) · *one-shot datado* (parecer/revisão de
sessão única) = `YYYY-MM-DD-HHMM-descricao.md`.
**Outros**: labs clean `EXP-NNN-nome/` · ADRs `NNNN-frase-imperativa.md` · datasets
`D<num><sufixo>-<descricao>.csv`.
Detalhe canônico + gabarito: `experiments/lab/dirty/notas/2026-07/dirty-lab-convencoes.md` §1.

### Formato TCF (wire)

- Magic `#TCF.<minor>`: **`#TCF.8` = default** (ADR-0032). `.6`/`.7` = legado cortado
  de `src/tcf` (git-as-compat). Major 0 omite o "0".
- **Discriminador de 1 char** após `#TCF.8` (ADR-0029/0031/0033/0036/0037/0039), **9 valores**:
  `\n` = version-stamp · `M` = multi-col (meta inline) · `H` = hierárquico (**soldado**,
  ADR-0033; não é mais reservado) · espaço = single+spec · `b`/`n`/`s` = single-col **tipado**
  (bool / número / string-explícita) · `B`/`C` = **bN de domínio** (ADR-0036: `B` domínio-primeiro,
  `C` domínio-por-último). Fora desses 9 → **fail-loud**.
  - **Assimetria emite × decoda**: `s` e `C` **decodam mas o encoder nunca os emite** (o `s` perde
    pra forma implícita sem tag; o `C` é ~1 B menor mas não streama, então só o `B` sai por default
    (ADR-0036)). Os outros 7 são emitidos.
  - Sob a tag `b`, o **índice 7** carrega o modo: `b1` denso (bool sem null) · `b2` ternário
    (bool com null, ADR-0037) · `bB` lazytype (união `{bool, str, None}`, ADR-0039) · **`b` puro**
    (sem char no índice 7) quando o denso perde o `min()`.
- **O carimbo `#TCF.8` é DEFAULT em 100% dos casos** no single-col (ADR-0034, 2026-07-24). O
  **órfão (body-only, 0 B de header) é ESCAPE explícito** via `stamp=False`, **não** é o default.
  Verificável: `encode(["abc","abcd"])` → `'#TCF.8\nabc\n1d\n'` (14 B) ·
  `encode(["abc","abcd"], stamp=False)` → `'abc\n1d\n'` (7 B).
- Multi-col `#TCF.8M<meta>`: byte-sizes em **HEX**, nomes com separador escapados com `\`,
  coluna `[!@%]<size>[=<nome>][:id]`, última sem size.
- Hierárquico `#TCF.8H<meta>`: shredding em colunas; folha escalar aceita nature via `:id`.
- **LF only, UTF-8.** Compat pré-1.0: versão antiga é ponto de comparação no git, não
  produção. No 1.0 o passado morre no git (sem `if .7`/`if .6`).

### Status markers (hipóteses)

`aberta` · `em-exp` · `confirmada-empirica` · `confirmada-conceitual` · `refutada`
(`-parcial`, `-real-world`) · `absorvida` · `subsumida` · `adiada` · `welded`.
Add `[VERIFICAR: YYYY-MM-DD]` em claim mutável e `confianca: Alta|Media|Baixa|A-revalidar`
em `confirmada-empirica`. Tickets: `closed-insufficient-gain` / `closed-adiado` / `closed-parcial`.

### Força do artefato: dispositivo vs probatório

Marcar **que ato** o artefato executa (ortogonal a status/confiança). Sem isso, um leitor
lê diretiva, hipótese e registro no mesmo plano e erra.

- **dispositivo**: CONSTITUI o que diz; é a fonte; desfazer exige novo ato:
  ADR `accepted`/`welded`, `src/tcf/` (código canonical), o formato, decisão do owner.
  Não se "revalida na fonte": ele É a fonte.
- **probatório**: REGISTRA fato verdadeiro alhures; revalida na fonte: resultado de
  experimento, hipótese, métrica, dataset, ticket de teste. Carrega proveniência + confiança.

`INDEX.md` (gerado por `scripts/index.py`) agrupa pelo `type` do frontmatter. Usar
`type: decision|experiment|report|dataset|…` já sinaliza a força.

### Camadas de conhecimento

**escopo-projeto** (este guia + `docs/adr/`, versionado em git) · **escopo-usuário**
(memória do agente, fora do repo: preferências pessoais e feedback de processo) ·
**diário** (`experiments/lab/dirty/notas/diario/`, cronológico) · **checkpoints**
(pausas explícitas pra retomada).

## 7. NUNCA

- Modificar `src/tcf/` sem aprovação explícita (I5)
- Baixar dados externos quando a infra `<data_root>/` já existe
- Push pra GitHub / pra `main` sem solicitação explícita
- Commit com `Co-Authored-By:`
- Superlativos ("incrível", "muito melhor", "campeão", "vencedor", "descoberta", "surpreendente")
- Deixar cronologia na superfície: `RE-PIN <data>`, `CORRIGIDO <data>`, "antes era X" (I1)
- Fechar lab sem `inputs/`+`outputs/` gravados em disco (I2)
- Teste de massa sem o Shaper (I3)
- Reportar byte sem round-trip validado (I4)
- `git rebase -i`, `git add -i` (interativo não suportado)
- `git reset --hard`, `git push --force` sem aprovação
- Skip hooks (`--no-verify`)
- Mexer em serviço rodando sem confirmação

## 8. Estado vigente

**Não duplicado aqui** (evita deriva). Ritual de reentrada, nesta ordem:
[`STATUS.md`](STATUS.md) → ticket de release vigente (`tickets/T-REL-08-CLOSEOUT.md`) →
checkpoint mais recente (`experiments/lab/dirty/notas/checkpoints/`) → último diário.
O ticket é **dispositivo**; checkpoint e memória são ponteiros **probatórios**.

> ⚠️ O repo vive dentro do OneDrive: `git log` com HEAD estranho ou arquivo `*-DESKTOP-*`
> é conflito de sync conhecido (ADR-0021).

## 9. Bibliografia metodológica

**Diataxis** (Procida) para `docs/` · **ADR/MADR** (Nygard) para `docs/adr/` ·
**Research Compendium** (Turing Way) para `experiments/` · **FAIR4RS** (metadata em READMEs) ·
**Information Architecture** (Morville) para wayfinding · **Threats to validity**
(Wohlin 2012), base do checklist §4 · **Ecological validity** (Brunswik 1956), separar
dataset de design (realista) de dataset de stress (artificial).

Doc-mãe cross-projeto (fora deste repo): `Methodologies/README.md`, com o Strata em
`Methodologies/recipe/knowledge-architecture.md`.
