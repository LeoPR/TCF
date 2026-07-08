# TCF.8 — vista + o que falta pra fechar (revisão 2026-07-08) [probatório]

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

## O que FALTA pra fechar `0.8.0` (= #TCF.8 = cross-dict)

O scaffold está pronto; falta a **carga de compressão que paga o bump** + higiene + release:
1. **Cross-dict H-GDICT B2** — a feature que "paga" o `#TCF.8`. **Caracterizada** (B1: −19.3% textual
   same-domain-refs em grafo real) mas **NÃO weldada**; `src/tcf` intocado. → precisa: **B2** (híbrido V2
   dicts-por-grupo) + **ADR** + **gate real-world** (`test_real_world_snapshots.py`) + **aprovação src/tcf**.
   [dispositivo/owner + research]
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
- **TCF.8H hierárquico** (EXP-015): protótipo externo; magic `#TCF.8H` **não registrado** no discriminador
  do ADR-0029; RT só em amostras minúsculas. Weld exigiria ato dispositivo do owner + gate.
- **hex/base-94** (subsume em O-FMT-18), **contrato-de-omissão** (pré-1.0, generaliza ADR-0029),
  **espectro de specs + meta-grupo H-TYPE-\*** (confirmada-conceitual): design/roadmap, não código.

## Bottom line

**Fechar o `#TCF.8` como FORMATO = feito** (scaffold welded, byte-neutro). **Fechar `0.8.0` como RELEASE =
weldar o cross-dict (H-GDICT B2)** — a carga que o owner reservou pro `#TCF.8` — que é um esforço
**gated** (src/tcf + ADR + gate real-world), OU o owner **re-escopa** o 0.8.0. O próximo release na fila é
`0.7.2` (lazy). O que dá pra fazer **sem gate** agora: sanear o drift do STATUS.md (com tua revisão) e
confirmar no roadmap que a sessão é research-track. O resto é decisão tua.

**Cross-links**: STATUS.md · ROADMAP.md · ADR-0027/0028/0029/0030 · T-EXP-H-GDICT-01 (cross-dict) ·
[roadmap-hipoteses](roadmap-hipoteses.md) · [tipos-meta-grupo-fluxo](tipos-meta-grupo-fluxo.md).
