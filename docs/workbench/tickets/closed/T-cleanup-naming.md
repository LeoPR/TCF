---
title: Limpar nomes de desenvolvimento — remover _v02, V02Config, etc
type: task
status: CLOSED (2026-04-09)
priority: HIGH (antes de publicar)
---

# Limpar nomes de desenvolvimento — CONCLUIDO

Renomeados:
- `encoder_v02.py` → `encoder.py`
- `decoder_v02.py` → `decoder.py`
- `encode_v02()` → `encode()`
- `decode_v02()` → `decode()`
- `V02Config` → `EncodeConfig`

Atualizado:
- `__init__.py` — imports diretos (sem alias)
- `cli.py` — imports de encoder/decoder
- `docs/ARCHITECTURE.md` — nomes de arquivos
- `docs/SOURCE_MAP.md` — nomes de arquivos

Verificacao:
- 112 testes passaram
- `from tcf import encode, decode, EncodeConfig` OK
- `python -m tcf encode --help` OK
- Nenhum `_v02` ou `V02` restante em src/tcf/
