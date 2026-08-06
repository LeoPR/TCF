# Proveniência — T-BN-B64-VALIDATE

Todos os dados são **sintéticos mínimos**, gerados deterministicamente (sem seed, sem
aleatoriedade) e declarados em `inputs/<nome>-fonte.json`; a materialização consumida
pelo run está em `intermediates/<nome>-dataset-consumido.json`. Sem fonte externa, sem
download, sem dados de `Z:/tcf-data/`. O lab testa comportamento de decode sobre wire
adulterado — dados de design, não de stress nem real-world.

| coluna | gerador | rota que cobre |
|---|---|---|
| `bn-B` | `['0','1']*100` (n=200, w=1, payload 34 chars ≡ 2 mod 4) | bN flat modo `B` via FLOOR do `encode` |
| `bn-C` | `['x','y']*100` (n=200, w=1) | bN modo `C` via `dominio_bn.candidatos` (decodável-não-emitido, ADR-0036) |
| `denso-b1` | `[True, False]*100` | denso b1 (padrão-ouro) |
| `denso-b2` | `[True, None, False]*60` | denso b2 ternário (padrão-ouro) |
| `lazy-bB` | `[True, 'other', None, False]*50` | lazy bB (ADR-0039, padrão-ouro) |
| `ref-silencioso` | `['0','1']*96` (n=192, w=1, payload 32 chars ≡ 0 mod 4) | bN modo `B` — referência do caso silencioso (controle de tamanho do b64) |

**Viés declarado**: os domínios foram escolhidos com cardinalidade mínima (2 valores) e
tamanhos de payload calculados para exercitar as classes de resto mod 4 do b64 — o lab
foi construído para testar a hipótese "payload adulterado decodifica calado", não para
medir compressão. A escolha `'x'/'y'` (em vez de `'0'/'1'`) na coluna `bn-C` evita o
escape `\0` do `_grafa` — e revelou o comportamento data-dependente do modo `C`
(documentado no `result.md`, §matriz).

As sondas são mutações puramente sintáticas do payload b64 (char inválido, inserção,
padding, corte/extensão), declaradas no `run.py` (`SONDAS`) e materializadas uma a uma
em `outputs/sondas/*.tcf` (48 arquivos) — nenhum dado externo.
