# Result — T-BN-B64-VALIDATE

**Pergunta**: o `decode_bn` (modos `B`/`C`, `dominio_bn.py:206`) decoda payload b64 sem
`validate=True` — o que acontece sob adulteração, comparado ao denso b1/b2 e ao lazy bB
(que já validam)? E a proposta (`validate=True` + wrap TCF) resolve?

**Resposta curta**: o buraco é real e a proposta resolve a classe sintática inteira — mas
a suspeita de **corrupção de valores** não se materializou (0 células
`SILENCIOSO-CORROMPIDO`), e o lab achou uma **sobra**: dados extras *válidos* (payload
longo, padding canônico a mais) passam pelo `validate=True` calados. A checagem de
tamanho exato que o denso já faz (`len(raw) == ceil(n*w/8)`) fecha 2 das 3 sobras.

## A matriz (8 sondas × 6 colunas; completa em `outputs/matriz-sondas.csv`)

Toda célula é rastreável a um arquivo: `outputs/sondas/<coluna>-<sonda>.tcf` (48 wires
adulterados). Contagens por coluna de decode:

| decode | FAIL-LOUD TCF | BINASCII CRU | SILENCIOSO-IGUAL | SILENCIOSO-CORROMPIDO |
|---|:-:|:-:|:-:|:-:|
| **atual** | 29 | **13** | **6** | 0 |
| **proposto** (validate) | 45 | 0 | 3 | 0 |
| **proposto + tamanho exato** | 47 | 0 | 1 | 0 |

- As 13 células `BINASCII CRU` são **todas bN** (`bn-B`/`bn-C`/`ref-silencioso` × sondas
  s01/s02/s03/s05/s07) — vaza `binascii.Error` cru ("Invalid base64-encoded string…",
  "Incorrect padding") onde o denso/lazy respondem `#TCF.8b…: payload … nao e' base64
  canonico: …`. Suspeita 1 **confirmada**.
- Denso `b1`/`b2` e lazy `bB`: **FAIL-LOUD TCF em 48/48 células** — o padrão-ouro segura
  a bateria inteira, incluindo `!!!!`, padding e corte/extensão.
- **Comportamento atual é data-dependente no modo `C`** (achado acessório): a sonda s07
  (corta 2 chars do payload) vaza `binascii.Error` com domínio `x/y` mas dava erro TCF
  ("payload denso curto") com domínio `0/1` — a fatia fixa do modo `C` engole o 1º char
  do domínio no payload, e como `0` é escapado (`\0`, 2 chars descartáveis) a contagem
  restante muda de classe. Mesma sonda, mesma rota, diagnóstico diferente conforme o
  dado — mais um sintoma da fragilidade, não design. (É a única divergência de números
  vs a 1ª versão do lab: 13/29 vs 12/30 — a coluna bn-C trocou `'0'/'1'` por `'x'/'y'`
  na reconstrução, a pedido da materialização por coluna.)

## O "caso silencioso" — confirmado com nuance (ver `outputs/caso-silencioso.txt`)

A hipótese literal ("`!!!!` inserido → contagem segue múltiplo de 4 → **bits errados
calados**") **não se confirmou**: o b64decode do Python **descarta** os chars inválidos
preservando o stream válido, então os valores voltam **idênticos** (s04 × `bn-B`/
`ref-silencioso` = `SILENCIOSO-IGUAL`, não corrompido). E o `unpack_w` trava payload
curto com mensagem TCF ("payload denso curto"), o que bloqueia a via de corrupção por
remoção.

O que existe de verdade é **aceitação silenciosa de wire adulterado** (6 células, todas
bN modo `B`): o wire foi mexido e o decode não reclama —

| sonda | atual | +validate | +validate&tamanho |
|---|:-:|:-:|:-:|
| s04 insere `!!!!` (`bn-B`, `ref-silencioso`) | SILENCIOSO-IGUAL | FAIL-LOUD TCF | FAIL-LOUD TCF |
| s06 padding `==` a mais (`bn-B`) | SILENCIOSO-IGUAL | SILENCIOSO-IGUAL | SILENCIOSO-IGUAL |
| s06 padding `==` a mais (`ref-silencioso`) | SILENCIOSO-IGUAL | FAIL-LOUD TCF | FAIL-LOUD TCF |
| s08 payload longo +`AA` (`bn-B`, `ref-silencioso`) | SILENCIOSO-IGUAL | SILENCIOSO-IGUAL | FAIL-LOUD TCF |

- **s08** é a célula que o `validate=True` puro **não pega**: chars válidos a mais decodam
  bytes a mais, e o `unpack_w` lê só os `n` símbolos — wire concatenado/adulterado aceito
  calado. O denso pega exatamente isto com o tamanho exato ("Excess data after padding" /
  `len(raw) != esperado`). **Achado do lab: a proposta mínima deveria incluir a checagem
  de tamanho exato** (1 conta, já exemplar no `_decode_denso`).
- **s06 × `bn-B`** é a célula que nem isso pega — e é **benigna**: 34 chars sem padding +
  `==` é a forma *padded canônica dos mesmos 25 bytes* (no `ref-silencioso`, com 32
  chars, já falha). Não há corrupção; há **grafias duplas aceitas** (bN armazena
  unpadded por convenção). Se a canonicidade S1.2 for estendida ao payload bN, a regra
  seria "rejeitar `=` no payload" — decisão do owner, registrada aqui como nota, não
  tratada.

## Fora de escopo (registrado)

**Char trocado por outro char VÁLIDO** decodifica silencioso em **todas** as rotas
(inclusive denso/lazy) — é integridade de *conteúdo*, não de sintaxe; nenhum validate
sintático pega. Solução seria checksum, outro ticket.

## Byte-neutralidade (contraprova em arquivo)

`outputs/<nome>-dataset.roundtrip.json` × `intermediates/<nome>-dataset-consumido.json`:
**byte-idênticos nas 6 colunas** (assert `read_bytes` no `run.py`; `cmp` confirma). O
proposto (com e sem tamanho exato) devolve os mesmos valores nos wires válidos — a
mudança só toca caminho de erro. Byte-neutro por construção.

## Conexões

- **T-GRAFIA-CHECKLIST**: regra nova proposta — *"todo payload b64 decoda com
  `validate=True` + mensagem nível TCF"*. O bN era a única rota fora dela (denso b1/b2 e
  lazy bB já cumprem).
- **T-DENSO-PADDING**: fazer o VALIDATE antes facilita — com o b64 saneado na entrada, a
  normalização de padding vira decisão de grafia, não de robustez.
- **Consequência para o weld** (se aprovado): troca de 1 linha em `decode_bn` + wrap
  (fraseologia `#TCF.8<disc>: payload bN nao e' base64 canonico: …`, alinhada ao
  denso/lazy) + **recomendação do lab**: incluir a checagem de tamanho exato (fecha
  s06/`ref-silencioso` e s08). Testes: sondas desta bateria viram casos em
  `test_dominio_bn.py` — os 18 wires de sonda bN estão materializados em
  `outputs/sondas/bn-*` / `ref-silencioso-*` para transcrição direta.
