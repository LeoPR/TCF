# 2026-07-06-2310 — tipos como specs (análise)

**Ticket**: [T-OPT-INFERENCE](../../../../tickets/T-OPT-INFERENCE.md) · nota-mãe
[tipos-como-specs](../notas/tipos-como-specs.md) · [H-TYPE-01](../notas/roadmap-hipoteses.md) ·
natures ADR-0015. Reframe do owner (2026-07-06) sobre os Ciclos 1a/1b.

## Estado

- **era**: tipos tratados como tags i/f/b/n (1a/1b) — um eixo à parte.
- **foi**: reenquadrados como **specs** (ponta mínima do espectro das natures); medidas 3 questões.
- **é**: **(1)** toda spec se justifica por **compressão OU aceleração**; **(2)** induz-se com segurança
  **⟺ round-trip** (regra universal, resolve self-description); **(3)** o **gabarito** (1ª amostra) propõe,
  o round-trip confirma. O número CORRIGIU a intuição: bool em texto ganha só ~6B flat (dict), não ~N.
- **será** (Ciclo 3): registro de specs no pre-pass; medir aceleração; bool-bitmap na camada binária (V2-L);
  hex (T-OPT-INFERENCE) como sub-spec numérica sob a mesma regra.

## O que mede (`artifacts/`)

- `01-bool-spec-compressao` — true/false (string) vs t/f (spec) em N={2,10,100}×3 distribuições.
- `02-inducao-roundtrip` — a regra round-trip por valor (30/01310/4.5/4.50/1e3/true/True/…).
- `03-numero-cadence` — número cadenciado vs espalhado (HCC comprime; cadence.rule_hit observado).
- `04-gabarito` — 1ª amostra induz a spec da coluna; guard pelo round-trip.

## Como rodar

```
python experiments/lab/dirty/2026-07-06-2310-tipos-como-specs/run.py
```

## Escopo

Dirty (análise conceitual com evidência). NÃO toca `src/tcf`. Grounding real:
`column_features.analyze_column` (indução), `natures.templated_checked.TemplatedCheckedSpec` (ponta rica),
`detect_cadence`/HCC (compressão do número).
