# Lab — T-BN-B64-VALIDATE: payload b64 sem `validate` no `decode_bn`

- **Data**: 2026-08-06 (sessão 2006) · **Ticket**: T-BN-B64-VALIDATE (fila de fechamento bool/bN)
- **Status**: `em-exp` — medido; aguardando inspeção do owner antes de qualquer weld
- **`src/tcf` INTOCADO**
- **Histórico**: 1ª versão (inline, sem evidência em arquivo) **reprovada** pelo owner
  ("fictício, falta contraprova"); reconstruída na mesma sessão com a evidência
  materializada conforme `experiments/lab/dirty/notas/2026-07/dirty-lab-convencoes.md` —
  o conteúdo científico (sondas, classificações, achados) se manteve.

## Pergunta

`composicional/dominio_bn.py::decode_bn` (modos `B` e `C`) decoda o payload bit-packed com
`base64.b64decode(b64 + pad)` **sem `validate=True`** (linha 206). O denso b1/b2
(`decoder.py::_decode_denso`) e o lazy bB (`_decode_lazy_bool`, ADR-0039) já usam
`validate=True` + `ValueError` nível TCF — o padrão-ouro. Duas suspeitas (sondas ao vivo
do owner): (1) vaza `binascii.Error` cru; (2) como o b64decode sem validate **descarta**
chars inválidos, um wire adulterado pode decodificar **calado**.

## Método

Bateria de 8 sondas de mutação do payload b64 × 6 colunas cobrindo as 4 rotas (bN modo
`B`, bN modo `C`, denso `b1`/`b2`, lazy `bB`), classificando cada célula como
`FAIL-LOUD TCF` / `BINASCII CRU` / `SILENCIOSO-IGUAL` / `SILENCIOSO-CORROMPIDO`.
Três decodes comparados: **atual** (`decode` público), **proposto** e
**proposto+tamanho-exato** — ambos em [`decode_bn_fixed.py`](decode_bn_fixed.py)
(módulo do lab, cópia 1:1 do `decode_bn` com a proposta linha a linha inspecionável).

## Fluxo de evidência (tudo em arquivo; `python run.py` regenera, exit 0)

```
inputs/<nome>-fonte.json                     gerador/parâmetros declarados (6 colunas)
        ↓  materialização
intermediates/<nome>-dataset-consumido.json  o dado que o run CONSOME (relido do disco)
        ↓  encode
outputs/<nome>-valido.tcf                    wire válido de referência
        ↓  decode (público)
outputs/<nome>-dataset.roundtrip.json        BYTE-IDÊNTICO ao consumido
                                             (assert read_bytes no run.py; `cmp` confirma)
        ↓  mutação do payload (8 sondas)
outputs/sondas/<nome>-<sonda>.tcf            48 wires adulterados — um por célula
        ↓  decode × 3 variantes (relendo os .tcf do disco)
outputs/matriz-sondas.csv                    sonda × rota × arquivo × 3 comportamentos
outputs/caso-silencioso.txt                  as 6 células silenciosas, antes/depois
outputs/rt-validos.txt                       resumo dos roundtrips (não substitui os .json)
```

## Resultado

Ver [`result.md`](result.md). Resumo: suspeita 1 **confirmada** (13 células BINASCII CRU,
todas bN); corrupção de valores **não reproduzida** (0 `SILENCIOSO-CORROMPIDO`), mas
6 células de **aceitação silenciosa de wire adulterado** no bN atual, das quais 3
sobrevivem ao `validate=True` puro — fechadas pela checagem de tamanho exato do denso
(recomendação do lab). Proveniência: [`datasets-provenance.md`](datasets-provenance.md).
