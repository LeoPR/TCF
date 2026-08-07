"""A validação canônica de payload base64 — a mesma regra para as três rotas.

Refaz o estudo do `T-BN-B64-VALIDATE` (lab `2026-08-06-2006`) a partir de uma correção de
classificação e de uma convergência que faltava.

## O que o lab anterior estabeleceu, e continua valendo

`decode_bn` decodava o payload sem `validate=True`, vazando `binascii.Error` cru onde o denso
responde com mensagem de nível TCF. Suspeita confirmada, 13 células.

## O que ele classificou ERRADO

Ele deu ao lazy `bB` o rótulo de **padrão-ouro, 48/48 fail-loud**. Não é: o `bB` valida mas
**não confere o tamanho**, e aceita em silêncio um payload estendido com **bytes zero**:

    lazy bB, payload + "AAAA"  ->  SILENCIOSO-IGUAL

A sonda de payload longo do lab anterior não separou os dois porque a extensão que ela usou
caía na checagem de bits-de-padding do `unpack_w` (que exige padding zerado). Estender com
bytes que **são** zero atravessa essa checagem.

Consequência: **a correção vai em DUAS rotas**, não em uma.

## O que ele deixou sem convergir

Ele apresentou `tamanho exato` como **variante opcional** ("recomendação"), e deixou a
questão do padding `==` como "decisão do owner". As duas coisas se resolvem medindo:

    validate + re-codifica-e-compara   pega char invalido, padding errado, caixa trocada
                                       NAO pega extensao com bytes zero, NAO pega truncamento
    tamanho exato                      pega extensao e truncamento
                                       NAO pega char invalido

**Nenhuma subsome a outra.** As duas são load-bearing — que é exatamente o par que o denso
(`decoder._decode_denso`) já faz desde sempre. Não é recomendação, é o mínimo.

E a re-codificação resolve o padding sem decisão nova: ela **é** a extensão natural da regra
de canonicidade que o cabeçalho já usa (`f"{n:x}" != nhex`, ADR-0036). Mesma técnica, outro
campo.

## A regra, então

```
1. base64.b64decode(payload, validate=True)          -> ValueError de nivel TCF
2. re-codifica e compara com o que veio no wire      -> grafia canonica unica
3. len(raw) == ceil(n*w/8)                           -> tamanho exato
```

`src/tcf` INTOCADO neste módulo — é a proposta para o owner inspecionar.
"""
import base64
import binascii
import math


def valida_payload(b64: str, n: int, w: int, rotulo: str, padded: bool = False) -> bytes:
    """As três checagens, na ordem. Devolve os bytes ou levanta `ValueError` de nível TCF.

    `padded` diz qual é a forma canônica DESTA rota: o denso emite com `=`, o bN e o lazy
    emitem sem. A checagem é sempre "bate com a forma canônica desta rota", não "tem ou não
    tem padding" — assim a regra é uma só e cada rota declara a sua convenção.
    """
    # 1 — e' base64 mesmo?
    try:
        raw = base64.b64decode(b64 + "=" * (-len(b64) % 4), validate=True)
    except (ValueError, binascii.Error) as e:
        raise ValueError(f"{rotulo}: payload nao e' base64 canonico: {e}") from e

    # 2 — a grafia e' a CANONICA? (re-codifica e compara — a tecnica do cabecalho)
    volta = base64.b64encode(raw).decode("ascii")
    if not padded:
        volta = volta.rstrip("=")
    if volta != b64:
        raise ValueError(
            f"{rotulo}: payload base64 nao-canonico — recebido {b64[:20]!r}…, "
            f"canonico {volta[:20]!r}… (duas grafias para os mesmos bytes)"
        )

    # 3 — o TAMANHO bate? (o que a re-codificacao NAO pega: extensao com bytes zero)
    esperado = math.ceil(n * w / 8)
    if len(raw) != esperado:
        raise ValueError(
            f"{rotulo}: payload = {len(raw)} bytes, esperado {esperado} p/ n={n} w={w} "
            f"(wire truncado, estendido ou concatenado)"
        )
    return raw


def por_que_cada_uma(b64: str, n: int, w: int, padded: bool = False) -> dict:
    """Qual das três checagens pega este payload? Serve para provar que nenhuma é redundante."""
    r = {"validate": True, "canonica": True, "tamanho": True}
    try:
        raw = base64.b64decode(b64 + "=" * (-len(b64) % 4), validate=True)
    except (ValueError, binascii.Error):
        return {"validate": False, "canonica": None, "tamanho": None}
    volta = base64.b64encode(raw).decode("ascii")
    if not padded:
        volta = volta.rstrip("=")
    r["canonica"] = volta == b64
    r["tamanho"] = len(raw) == math.ceil(n * w / 8)
    return r
