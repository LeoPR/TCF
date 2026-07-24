# A lógica do `~` (modo) — forma EXPLÍCITA (o `var` visível)

Tudo já existe (FLOOR/`min`, dispatch posicional) — só nomeamos as etapas. Codado na forma GERAL/explícita (variável `modo` visível no encode E no decode). O `~` NÃO é byte de wire; é essa variável. A função é acionada PELA VARIÁVEL. Otimização (colapsar o `var`) = `.9`.

| perfil | n | wire (linha-0) | modo (var) | bytes | RT-tipado |
|---|---:|---|:---:|---:|:---:|
| all-true | 64 | `#TCF.8b` | core | 17 | ✅ |
| all-false | 64 | `#TCF.8b` | core | 18 | ✅ |
| alt | 64 | `#TCF.8b164` | denso(w=1) | 23 | ✅ |
| runs | 64 | `#TCF.8b164` | denso(w=1) | 23 | ✅ |
| p10 | 64 | `#TCF.8b164` | denso(w=1) | 23 | ✅ |
| p50 | 64 | `#TCF.8b164` | denso(w=1) | 23 | ✅ |
| p90 | 64 | `#TCF.8b164` | denso(w=1) | 23 | ✅ |
| n1 | 1 | `#TCF.8b` | core | 13 | ✅ |

## As etapas nomeadas (o que o código mostra)

- **camada 1 — caractere**: o byte no índice 6 (tag) e no índice 7 (fronteira de modo).
- **camada 2 — significado**: `tag→tipo` (`b`→bool) e `char→largura` (`1`→w=1). Registros `TAG_TIPO`, `LARGURA_DE_MODO`. O `~` NÃO está aqui (nunca é byte).
- **camada 3 — presença/decisão**: a variável `modo`. No ENCODE ela é o FLOOR (`var=core; if denso menor→var=denso`). No DECODE ela é deduzida da posição (`if c7=='\n'→core; elif c7 é largura→denso`). **É o `var` explícito — o `~` conceitual.**
- **função**: acionada PELA variável `modo`, não pelo caractere (`if modo==core → decode core; else → decode denso`).

## Mapa pro weld #4 (1:1)

- `encode_typed` → ramo no dispatch de `encoder.py` (antes do `.8H`), reusando `_encode_column` (core) e o pack bN. A variável `modo` = o FLOOR que já existe.
- `decode_typed` → ramo no discriminador de `decoder.py`: hoje `disc8 not in (M, ,'')` é fail-loud; add `elif tag in whitelist`. A variável `modo` = a dispatch posicional que já existe.
- **Explícito agora, íntimo no `.9`**: mantemos `modo` visível; a fusão (colapsar o `var` na condição) fica pro `.9`/compilador — em código ajudamos só se o compilador limitar.
- **Escopo do protótipo**: bool (`w=1`, domínio implícito). n/s densos exigem domínio embutido (fora daqui). Larguras 2/4/8 e subtipos = namespace preparado, não exercido.

---
**8 perfis · 0 falhas de RT-tipado.** Artefatos: `inputs/` · `intermediates/` · `outputs/*-wire.tcfp`. Regenera: `python run.py`.
