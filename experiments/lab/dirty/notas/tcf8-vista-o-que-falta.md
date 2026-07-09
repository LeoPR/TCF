# TCF.8 — como o trabalho da sessão 2026-07-06/08 se relaciona ao .8 (subordinada) [probatório]

> **SUBORDINADA + CORRIGIDA (2026-07-08, na reorganização)**: o **plano canônico da família #TCF.8** é
> [`tcf8-estrutura-plano.md`](tcf8-estrutura-plano.md) (fonte única, 2026-06-25) + capacidade em
> [`specs-capacity-map.md`](specs-capacity-map.md). Esta nota **NÃO é o plano** — mapeia só como o trabalho
> da sessão (bN/specs/TCF.8H) se relaciona (tudo research-track, FORA do release). **Correção de erro meu**:
> a versão original abaixo dizia "fechar 0.8.0 = weldar cross-dict B2". **ERRADO** — pelo plano canônico:
> (a) `0.8.0` = RELEASE da família self-describing **já welded** (natures+discriminador+anônimas+lazy), ato
> administrativo; (b) o **cross-dict (H-GDICT) teve o gate GERAL REPROVADO** (2026-06-27: 1/5 ≥15%, nicho
> estreito, B3/B4 suspensos; pivô = **H-DICT-HIGHCARD**) — não é "a carga a weldar". As seções abaixo ficam
> como registro, lidas por esta chave.
>
> **ATUALIZAÇÃO 2026-07-09 ([ADR-0032](../../../../docs/adr/0032-tcf8-default-format.md))**: o `#TCF.8`
> deixou de ser opt-in — virou o formato **DEFAULT** (multi-col emite `#TCF.8M` sempre; legado .6/.7
> cortado). Logo as linhas abaixo que dizem "opt-in estrito byte-neutro / default nunca emite #TCF.8 / .8
> é o desvio / 0.8.0 = cross-dict" estão **duplamente superadas** — o `0.8.0` = release do `.8`-default
> (não cross-dict). O único opt-in que resta são as FEATURES dentro do .8 (natures, hierarquia).

# (original) TCF.8 — vista + o que falta pra fechar (revisão 2026-07-08) [probatório]

> Pedido do owner: revisão + vista de tudo que precisa pra prosseguir com o `.8`, antes de avançar mais.
> Levantado por workflow (formato-ADRs + release/roadmap + contribuições-da-sessão) + **spot-check manual**
> (o crítico do workflow falhou/retornou stub; verifiquei os claims load-bearing à mão). **Correção
> importante**: a síntese pegou o escopo do 0.8.0 ao contrário — o cabeçalho de retificação do STATUS.md
> (o mais novo, autoritativo) corrige.

## O `#TCF.8` tem DOIS sentidos (manter separados)

| sentido | estado |
|---|---|
| **formato-minor `#TCF.8`** (scaffold) | **WELDADO** em `src/tcf` desde 2026-06-24, shipado no repo sob 0.7.1, **opt-in estrito byte-neutro** (default nunca emite `#TCF.8`; D1-D9=1523B intactos) |
| **release `0.8.0`** do pacote | **NÃO saiu**. Por ADR-0028 (retificação STATUS.md linha 5-8): **`0.8.0` = `#TCF.8` = cross-dict**; "onde as notas dizem '#TCF.8 → 0.9', leia '#TCF.8 = 0.8.0'". PyPI segura em 0.7.1. |

## O que o `#TCF.8` (formato) JÁ É — welded (verificado)

Scaffold pronto e testado (`tests/test_natures.py`), tudo opt-in byte-neutro:
- **Discriminador de 1 char** após `#TCF.8`: `M`=multi inline · ` `(espaço)=single+spec · `\n`=version-stamp (ADR-0029, `decoder.py:55-152`).
- **Natures self-describing** — sufixo `:id` no meta (cpf/cnpj/ip, `SPEC_REGISTRY` fechado); magic emitido **SSE há nature** (ADR-0027 accepted/welded; `natures/__init__.py`, `multi/core.py`).
- **Single-col + spec** (`#TCF.8 nome:spec`), **colunas anônimas** (`drop_names`, força `#TCF.8M`), **version-stamp** opt-in (`#TCF.8\n`, magic-number p/ `file`/libmagic).
- **Órfão default** (single-col plano = body puro, 0 bytes de header) preservado — o `#TCF.8` é o **desvio** opt-in, não mexe no comum.

## O que FALTA pra fechar `0.8.0` (= release da família self-describing; NÃO cross-dict — corrigido)

O scaffold está pronto e welded; `0.8.0` é ato ADMINISTRATIVO (go do owner). Higiene + pendências:
1. ~~Cross-dict H-GDICT B2 — a feature que "paga" o `#TCF.8`~~ **REFUTADO como escopo do 0.8.0**: o gate
   GERAL do cross-dict FALHOU (2026-06-27: 1/5 ≥15%, nicho estreito SNAP-like; B3/B4 suspensos; pivô =
   H-DICT-HIGHCARD). O B1 −19.3% é nicho same-domain-refs, não paga bump geral. Se um dia voltar, entra
   como extensão opt-in própria (ADR + gate + aprovação src/tcf), FORA do 0.8.0. [corrigido 2026-07-08]
2. **Slot do discriminador** pra a feature nova: hoje só `M`/espaço/`\n`. Cross-dict precisa de um char
   reservado no ADR-0029 **antes** de weldar. [decisão de formato/owner]
3. **ADR-0028 `proposed` → `accepted`** — reconciliar a regra `0.N↔#TCF.N` com o fato de que o magic
   `#TCF.8` já shipou sob 0.7.1 (scaffold opt-in). [decisão/owner]
4. **Sanear drift do STATUS.md** — o **corpo** (linha 99 "Pacote 0.8.0 != #TCF.8", linha 145 "#TCF.8 → 0.9")
   contradiz o **cabeçalho de retificação** (linha 6 "0.8.0 = #TCF.8"). Linha 78/80 diz ADR-0027 "proposed"/
   "Não implementado" (stale — está accepted/welded). [higiene; STATUS.md é doc do owner → revisão dele]
5. **Release** — `0.7.2` (lazy, workstream A pronto+endurecido) vem **antes**; `0.8.0` publica quando o
   cross-dict pagar. Ambos = go explícito do owner (T-DIST-RELEASE, blocked). [ato administrativo/owner]

## Research-track — FORA do release `.8` (o que esta sessão gerou)

**Nada da sessão 2026-07-06/08 entra no release `.8`** — tudo é insumo de roadmap futuro:
- **bN** (H-TYPE-02): gated — 8.8% terminal / 1.7% pós-brotli, N=8; confirmada-empírica **só terminal**,
  weld barrado por H-TYPE-03 (decisão de produto). Se weldar um dia = extensão `#TCF.8` opt-in (char-prefixo novo no `min()`).
- **TCF.8H hierárquico** (EXP-015): protótipo externo; discriminador `H` **REGISTRADO 2026-07-09**
  (ADR-0031: `H` = multi-col hierárquico, especialização de `M`, sem-espaço, dispatch O(1)) — char + semântica
  reservados. O **codec** segue research-track (RT só em amostras minúsculas); welding = ticket próprio gated.
- **hex/base-94** (subsume em O-FMT-18), **contrato-de-omissão** (pré-1.0, generaliza ADR-0029),
  **espectro de specs + meta-grupo H-TYPE-\*** (confirmada-conceitual): design/roadmap, não código.

## Bottom line (corrigido 2026-07-08 — o original desta seção nasceu com o escopo errado)

**Fechar o `#TCF.8` como FORMATO = feito** (scaffold welded, byte-neutro). **Fechar `0.8.0` como RELEASE =
ato ADMINISTRATIVO** (go do owner) da família self-describing JÁ welded (natures + discriminador + anônimas
+ lazy) — NÃO "weldar cross-dict" (gate geral reprovado 2026-06-27; ver item 1 riscado acima). Fila:
`0.7.2` (lazy) antes. Higiene restante: ADR-0028 proposed→accepted (item 3) + saneamento STATUS.md (feito
2026-07-08). Fonte canônica do plano: [tcf8-estrutura-plano.md](tcf8-estrutura-plano.md).

**Cross-links**: STATUS.md · ROADMAP.md · ADR-0027/0028/0029/0030 · T-EXP-H-GDICT-01 (cross-dict) ·
[roadmap-hipoteses](roadmap-hipoteses.md) · [tipos-meta-grupo-fluxo](tipos-meta-grupo-fluxo.md).
