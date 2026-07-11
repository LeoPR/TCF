---
title: T-CODE-PARALLEL-BUDGET — flag de controle de paralelismo e uso de CPU (budget do host)
status: open
priority: P2
created: 2026-07-10
updated: 2026-07-10
blocked-by: []
related:
  - tickets/T-QA-8-material-comprobatorio.md
  - tickets/T-CODE-ENCODER-MANAGER.md
  - docs/adr/0018-v2-format-roadmap.md
---

# T-CODE-PARALLEL-BUDGET — flag pra controlar paralelismo e uso de CPU

**[dispositivo→registro]** Pedido do owner (2026-07-10): "já registre um flag pra controlar
paralelismo e uso de cpu por exemplo". Registrado aqui; implementação decidida junto com o F3
do material comprobatório (que vai MEDIR o comportamento paralelo antes de expor knob novo).

## Estado atual (o que já existe)

- `encode(parallel=False|True|N)` per-call (T-CODE-ENCODER-MANAGER fases 1+1b, welded):
  ProcessPoolExecutor por coluna, work-stealing, byte-idêntico ao serial.
- Lote 3 do T-QA-8 F0: `parallel` validado na porta (negativo/tipo → erro) e **`parallel=1` →
  serial deduzido** (sem spawn). `parallel=True` → `os.cpu_count()`.
- NÃO existe: controle GLOBAL (env/config), cap de CPU, nem knob no decode (decode é serial).

## Esboço do flag (pra discussão na implementação)

1. **Env var de teto**: `TCF_MAX_WORKERS` — clampa qualquer `parallel=` (inclusive `True`);
   `TCF_MAX_WORKERS=1` = desliga paralelismo globalmente (CI, containers com cota, benchmarks
   de baseline). Precedência: env (teto do HOST) > kwarg (pedido do caller).
2. **`parallel=True` mais educado**: default `cpu_count()` toma a máquina inteira — considerar
   `max(1, cpu_count - 1)` ou fração; MEDIR no F3 antes (o speedup satura ~1.3x no Windows
   spawn — teto alto não paga).
3. **Uso de CPU além de workers** (registrar, avaliar depois): prioridade/nice do pool,
   `max_tasks_per_child`, e futuro paralelismo intra-coluna (V2-J, ADR-0018) — o budget deve
   ser UM conceito só pro host inteiro, não um knob por camada.
4. Telemetria: `multi_info['parallel_workers']` já expõe o efetivo; o flag deve aparecer lá
   também (workers pedidos vs concedidos) — zero-cost, filosofia SideOutputs.

## Critérios de aceite

- [ ] Decisão de design pós-F3 (com números de speedup/porção-serial medidos).
- [ ] Env var respeitada em encode paralelo (teto), com teste.
- [ ] Documentado no reference (F6/pós-.8) — knob de HOST, não de formato (bytes idênticos sempre).
