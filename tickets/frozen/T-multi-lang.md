---
title: Implementacoes TCF em JavaScript, C, Go — cross-language compat
type: task
status: OPEN
priority: HIGH
created: 2026-04-10
origin: Visao de TCF como protocol reference (qualquer um deve poder implementar)
---

# Implementacoes Cross-Language

## Objetivo

Para TCF virar referencia de protocolo, precisa ser **trivialmente
implementavel em qualquer linguagem**. JSON tem parser em C, Rust, JS, Go,
Python, Java etc. TCF precisa do mesmo.

## Linguagens prioritarias

| Linguagem | Por que | Dificuldade | Entregavel |
|-----------|---------|-------------|------------|
| **JavaScript** | Frontend, Node.js, APIs | Media | Pacote npm |
| **C** | Embarcados, wrappers, perf | Alta | lib estatica/dinamica |
| **Go** | Backend moderno, APIs | Baixa | pacote Go (go.mod) |
| **Rust** | Perf + seguranca | Media | crate |
| **Java** | Enterprise | Media | JAR Maven |

## Escopo minimo de cada implementacao

**Decoder (critico):**
- Parse header (`# TCF v0.2 level=N`)
- Parse table header (`## name n=N sorted_by=col`)
- Parse STATS lines (`# STATS col: n=... sum=...`)
- Parse dict lines (`# dict col: val1,val2,...`)
- Parse column blocks (`col:\n...`)
- Expand RLE (`N*val` → `[val, val, ..., val]`)
- Resolve dict (indice → valor)
- Retornar estrutura tabular (array de objetos ou similar)

**Encoder (opcional inicialmente):**
- Para protocolo HTTP, encoder e necessario no servidor.
- Para cliente (browser, app), so decoder e necessario.
- Priorizar decoder primeiro — encoder pode vir depois.

## Estrategia de implementacao

### Fase 1: Python reference (feito)
Ja temos Python em `src/tcf/`. Serve de especificacao executavel.

### Fase 2: Especificacao formal
Documentar gramática BNF-like do formato em `docs/SPEC.md`:
```
TCF_FILE = HEADER TABLE+
HEADER = "# TCF v0.2 level=" INT
TABLE = TABLE_HEADER DICT_LINE* STATS_LINE* COLUMN_BLOCK+
COLUMN_BLOCK = COL_NAME ":" NEWLINE VALUE+
VALUE = INT "*" RAW_VALUE | RAW_VALUE
```

### Fase 3: JS decoder (primeiro alvo)
- Node.js + browser compativel (vanilla JS ou TypeScript)
- Zero dependencias
- API: `const tables = TCF.decode(tcfText)`
- Package: `npm install tcf-format`
- Testes portados do Python (mesmo input → mesmo output)

### Fase 4: C decoder
- Single-file header-only library (`tcf.h`) — estilo stb
- Zero deps, C99 compativel
- API: `TCFTable* tcf_decode(const char* text)`
- Testes portados

### Fase 5: Go + Rust
- Go: standard library only
- Rust: via `serde`-compativel

## Conformance tests

Testes cross-language devem compartilhar fixtures:
```
tests/conformance/
  fixtures/
    simple_l0.tcf       # dados + expected.json
    sorted_l2.tcf
    dict_l3.tcf
    with_stats.tcf
    edge_empty.tcf
    edge_nulls.tcf
  python/test_conformance.py
  js/test_conformance.js
  c/test_conformance.c
```

Cada implementacao deve passar os mesmos testes — garante que TCF e
um formato bem definido, nao "o que o Python faz".

## Relacao com outros tickets

- **E-http-protocol**: JS decoder permite usar TCF em frontends (fetch + decode)
- **T-G41-cli-lib**: pip package — Python ja tem, falta npm
- **P-data-types**: se adicionar tipos declarados, spec precisa cobrir

## Tarefas

- [ ] Escrever `docs/SPEC.md` — especificacao formal
- [ ] Gerar fixtures de conformance (10-20 arquivos .tcf + expected.json)
- [ ] JS decoder (npm package) — prioridade maxima
- [ ] C decoder (single header) — prioridade alta
- [ ] Go decoder — prioridade media
- [ ] Rust decoder — prioridade baixa
- [ ] CI cross-language (GitHub Actions)
