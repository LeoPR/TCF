---
title: T-SPEC-STATUS-08 — status dos specs (2 abordagens) antes do teste em massa; decisão do que fecha no .8
status: open
priority: P1
created: 2026-07-12
updated: 2026-07-12
blocked-by: []
related:
  - tickets/T-QA-8-material-comprobatorio.md
  - tickets/T-OPT-INFERENCE.md
  - tickets/META-TYPE-ENCODERS.md
  - docs/adr/0015-natures-templated-checked-weld.md
  - src/tcf/natures/templated_checked.py
  - experiments/lab/dirty/notas/specs-capacity-map.md
---

# T-SPEC-STATUS-08 — onde os specs estão, pra decidir o que fechar antes do teste em massa

**[dispositivo→registro]** Pedido do owner (2026-07-12): "quero ver o status dos specs, pra poder
lançar com os datasets. Os specs tinham duas abordagens: (1) revisão da LINGUAGEM pra ficar
generalista e fácil de adaptar a qualquer acoplamento; (2) usar algo mais 'encaixotado' como o CPF
já tem — clássicos: CNPJ, CEP, telefone, RG, CPF e outros códigos brasileiros. Quero fechar essas
coisas antes de partir pro teste em massa."

Fonte: survey de 3 agentes (2026-07-12, read-only, file:line verificado; 1 re-rodado por resposta
degenerada — o re-survey CORRIGIU um erro material do primeiro sobre o `check_fn`).

## Abordagem 1 — LINGUAGEM generalista (specs induzidas)

**Estado: mapeada, confirmada-CONCEITUAL, gated `.9`.** Não é código a rodar no teste em massa.

- Framework = `T-OPT-INFERENCE` (open, reframe owner 2026-07-06: tipo/base-hex/nature são a MESMA
  coisa, espectro de specs justificadas por COMPRESSÃO ou ACELERAÇÃO, induzidas com segurança sse
  round-trip). Nota-mãe: `tipos-como-specs.md` (escada string→int/float→enum-bN→nature rica; regra
  universal = RT; gabarito propõe-e-confirma). Meta-grupo `H-TYPE-00..05`; motor `spec_bin/bN`.
- Achado que calibra: em TCF TEXTUAL a compressão de tipo é modesta (bool ~6B); o forte é
  ACELERAÇÃO + espaço binário V2-L. Gate `H-TYPE-03` aberto (decisão de produto do owner:
  "terminal é representativo?"). Medições fechadas (D3 N=8: 8.8% terminal / 1.7% pós-brotli).
- **Trilho literal de DSL de spec** (a "linguagem generalista" no sentido estrito) = W4 "TCFL"
  (`resegmentacao-workstreams-2026-06-27.md`) + `filtros-dsl-plano.md` — registrado, deferido 2.0.
- **Pro teste em massa AGORA**: só o que está welded (natures ADR-0015 + self-describing `:id`
  ADR-0027 + SPEC_REGISTRY). Todo o resto = `.9`, gated. Nada a fazer aqui pro `.8`.

## Abordagem 2 — clássicos BR encaixotados

**Achado central (verificado): o gargalo NÃO é a máquina, é DADO.** As máquinas welded já cobrem
5 dos 7 clássicos por CONSTRUTOR, sem tocar o core — mas nenhum hub tem coluna de clássico BR além
de CPF/CNPJ, e o gerador só produz cpf/cnpj. Logo o gate de weld (≥15% em 2+ reais, sobrevive a
brotli) só é atingível HOJE por CNPJ.

### O que a máquina suporta (correção do re-survey)

- **`check_fn` é PARÂMETRO LIVRE do construtor** (`templated_checked.py:58`), NÃO um dict fechado.
  Plugar um DV novo (PIS pesos próprios, algoritmo custom da CNH, título sobre sub-fatias) =
  **só passar `check_fn=` no construtor**. Zero core, zero subclasse. (O dict fechado
  `CHECK_FNS = {mod11-cpf, mod11-cnpj, none}` existe SÓ no gadget DSL `scripts/natures_compiler/`
  — o primeiro agente errou ao chamar a máquina de "biblioteca fechada".)
- Restrição real: algoritmo tem de ser `list[int] -> list[int]` (dígito-int); Luhn/alfanumérico
  não cabe. `zfill(body_length)` no decode (`:104`) preserva zeros à esquerda (habilita CEP).
- **Único toque de core**: registrar o `:id` no `SPEC_REGISTRY` (`natures/__init__.py:56-60`, 1
  linha, SEM collision-check) — e SÓ se quiser o header self-describing público. Uso via
  `spec.encode_value/decode_value` direto = zero core. **Cuidado (meu BUG-13b, lote 4)**: id
  desconhecido no header AGORA É ERRO — um spec novo precisa estar no registry pra o
  `encode/decode` público round-tripar.

### Veredito por clássico (mecânico + dado)

| clássico | DV | cabe na máquina? | dado real? | PII? | veredito |
|---|---|---|---|---|---|
| **CNPJ** | 2× mod-11 | ✅ welded | ✅ receita-cnpj 200k | não | **(a) fecha o gate** — único confirmada-empirica |
| **CPF** | 2× mod-11 | ✅ welded | só sintético | sim | **(a) medível, synthetic-teto** (ressalva sempre) |
| **CEP** | nenhum | ✅ Checked `check_length=0` (zfill salva o zero) | ❌ nenhum hub | não | (b) precisa-gerador; ganho duvidoso |
| **PIS** | 1× mod-11 | ✅ `check_fn=` | ❌ | sim | (b) encaixe limpo, sem dado |
| **Renavam** | 1× mod-11 | ✅ `check_fn=` | ❌ | parcial (veículo) | (b) encaixe limpo, sem dado |
| **Título eleitor** | 2× mod-11 sub-fatia | ✅ `check_fn=` | ❌ | sim | (b) cabe, sem dado |
| **CNH** | 2× custom | ✅ `check_fn=` | ❌ | sim | (b) cabe, sem dado |
| **Telefone** | nenhum | ❌ largura 10/11 variável | ❌ | sim | (c) precisa máquina var-width OU 2 specs |
| **RG** | varia por estado | ❌ formato/DV per-estado | ❌ | sim | (c) precisa decisão de política; não-.8 |
| **Placa Mercosul** | nenhum | ❌ alfanumérico | ❌ | não | (c) precisa máquina alfanumérica nova |

## Decisão pendente do owner (o que "fechar" significa pro .8)

Como CPF/CNPJ já estão welded, "fechar os specs pro teste em massa" NÃO é abrir spec novo — é
escolher entre:

- **Opção A — conservador (recomendado pro fechamento do .8)**: o material comprobatório reporta
  só CPF/CNPJ (F4 já faz: receita-cnpj REAL fecha o gate; br-identidades sintético = teto). Os
  demais clássicos ficam REGISTRADOS aqui como "cabem por construtor, faltam dado+gerador" → `.9`.
  Zero core novo, zero risco no tail do .8.
- **Opção B — demonstração de capacidade**: adicionar ao F4 1-2 specs sintéticos (CEP/PIS/renavam
  via construtor, RT-provado) como DEMO da máquina — explicitamente rotulado "capability, NÃO
  passa o gate ≥15%/2-reais" (herda o critério do FILTRO-NUMERO). Custa: gerador sintético
  (fora de src/tcf) + 1 linha no SPEC_REGISTRY por spec + anonimizador §2.3 pros que têm DV. Mais
  superfície pra migrar no C1/C2 (rename/consolidação).
- **Opção C — abrir um clássico "de verdade"**: só faz sentido pós-`.8`, quando houver dataset
  real com a coluna (nenhum existe hoje) — senão repete o padrão "sintético não generaliza"
  (anti-incidente 2026-05-21).

## Pré-requisitos que QUALQUER spec novo com DV precisa (registrados)

- **Anonimizador** (§2.3): re-invalidar DV `(dv+1)%10` pra publicar exemplo — NÃO existe, criar em
  `scripts/`. Vale pra CPF/PIS/título/CNH/renavam/CNS.
- **Gerador sintético** estendido: `setup_br_identidades.py` só faz cpf/cnpj — sem `_gen_cep/
  _gen_telefone/_gen_rg`.
- **1 linha no SPEC_REGISTRY** por id novo (core) + collision-check inexistente (dict sobrescreve
  calado — anotar como risco se crescer).

## Critério de aceite

- [ ] Owner escolhe A/B/C pro `.8` (recomendação: A — fecha o `.8` sem core novo; B/C → `.9`).
- [ ] Se B: gerador + anonimizador + registro dos specs-demo antes de qualquer blob publicado.
- [ ] Clássicos (c) telefone/RG/placa registrados como "precisa decisão de formato/máquina" → `.9`
  (linha no ROADMAP Tier 1 FILTROS-POPULARES já cobre; cross-ref daqui).
