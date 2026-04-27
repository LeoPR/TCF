---
title: M8 — Safe-SQL flags isolados
type: experiment
status: DONE
finding: F-Q22
manifest: experiments/results/m8_safe_sql/manifest.jsonl
date_range: 2026-04
---

# M8 — Safe-SQL flags isolados

## O que foi feito

Testar 4 style hints (having/subquery_col/name_join/explicit_fk) em isolamento.

## Resultado-chave

safe_having +70pp em q_having; safe_explicit_fk -11pp em q_top_e1_best_e2.

## Findings registrados

- [F-Q22](../../docs/methodology/F-findings.md) — ver F-findings.md

## Reprodução



Manifest: 
