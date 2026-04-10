---
title: CLI, biblioteca Python e distribuicao (pip + npm)
type: task
status: OPEN
priority: MEDIUM
---

# CLI e Biblioteca — Distribuicao Publica

## Estado atual

**Python:**
- `from tcf import encode, decode, EncodeConfig` — funciona
- CLI `python -m tcf encode/decode/info` — funciona
- Nao publicado no PyPI
- Zero deps externas

## Melhorias planejadas

### pip package publico
- [ ] Revisar `pyproject.toml` — metadados, classifiers, keywords
- [ ] Criar `tcf/__init__.py` com `__version__`
- [ ] Build e publicacao no PyPI: `python -m build && twine upload`
- [ ] Nome: `tcf-format` (tcf sozinho pode estar tomado)

### Modos auto no CLI
- [ ] `tcf encode --auto` detecta o melhor nivel baseado nos dados
- [ ] `tcf compare data.csv` mostra tamanho em todos os formatos
- [ ] `tcf roundtrip data.csv` verifica encode→decode lossless

### Integracoes
- [ ] `tcf encode --from sqlite://db.sqlite3 --table vendas`
- [ ] `tcf encode --from parquet://file.parquet`
- [ ] `tcf encode --from json file.jsonl`

### Features de diagnostico
- [ ] `tcf stats file.tcf` — mostra compressao por coluna, estatisticas
- [ ] `tcf validate file.tcf` — roundtrip + checagem de integridade

## Cross-language (ver T-multi-lang)

- [ ] Pacote npm: `tcf-format` (decoder JS)
- [ ] Single-file C header: `tcf.h`
- [ ] Pacote Go, Rust

## Versionamento

Semver:
- v0.2.x — atual, bugs only
- v0.3.0 — schema extension (P-schema-extension) se aprovado
- v1.0.0 — primeira versao estavel publica

## Tarefas

- [ ] Revisar pyproject.toml completo
- [ ] Testar build wheel em ambiente limpo
- [ ] Rascunho do README do PyPI
- [ ] Publicar no TestPyPI primeiro
- [ ] Publicar no PyPI real (so apos paper aceito)
