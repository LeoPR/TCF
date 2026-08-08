"""Os ALVOS de transformação de data — cada um com a sua inversa.

Um "alvo" é a forma pra qual a data é reescrita antes de ir pro core. A escolha do alvo é o
que decide qual mecanismo do core vai pegar o dado:

    decimal  ->  `*N+M|` (seq-RLE multi-delta) enxerga a progressão aritmética
    denso    ->  nada enxerga aritmética, mas cada valor ocupa menos chars
    delta    ->  a coluna vira quase-constante, e o RLE simples pega

Todos são **bijetivos sobre o domínio de datas** — o lab confere o RT de cada um.
`src/tcf` NÃO é tocado.
"""
from __future__ import annotations

import base64
import datetime as _dt

#: Alfabeto do CPF (`natures/templated_checked.py`). O nome diz 94, mas são 80 chars:
#: `chr(33..126)` menos os reservados da gramática.
_RESERVADOS = set('*^~\\|#=@!%:," \'')
ALFA = "".join(chr(c) for c in range(33, 127) if chr(c) not in _RESERVADOS)

MIN_ORD = _dt.date.min.toordinal()          # 1
MAX_ORD = _dt.date.max.toordinal()          # 3652059
EPOCA = _dt.date(1970, 1, 1)

#: Largura fixa que cobre todo o domínio de datas no alfabeto denso.
LARG_DENSO = 1
while len(ALFA) ** LARG_DENSO < MAX_ORD:
    LARG_DENSO += 1


def _dense(n: int) -> str:
    c = []
    for _ in range(LARG_DENSO):
        c.append(ALFA[n % len(ALFA)])
        n //= len(ALFA)
    return "".join(reversed(c))


def _undense(s: str) -> int:
    n = 0
    for ch in s:
        n = n * len(ALFA) + ALFA.index(ch)
    return n


# ── os alvos: (nome, para(datas)->list[str], de(list[str])->datas, o que explora) ──
def _iso(ds):
    return [d.isoformat() for d in ds]


def _de_iso(vs):
    return [_dt.date.fromisoformat(v) for v in vs]


def _ord_dec(ds):
    return [str(d.toordinal()) for d in ds]


def _de_ord_dec(vs):
    return [_dt.date.fromordinal(int(v)) for v in vs]


def _ord_denso(ds):
    return [_dense(d.toordinal()) for d in ds]


def _de_ord_denso(vs):
    return [_dt.date.fromordinal(_undense(v)) for v in vs]


def _ord_b64(ds):
    #: 3 bytes cobrem 16,7M > 3,65M ordinais; b64 de 3 bytes = 4 chars exatos, sem padding.
    return [base64.b64encode(d.toordinal().to_bytes(3, "big")).decode("ascii") for d in ds]


def _de_ord_b64(vs):
    return [_dt.date.fromordinal(int.from_bytes(base64.b64decode(v), "big")) for v in vs]


def _epoch_seg(ds):
    return [str((d - EPOCA).days * 86400) for d in ds]


def _de_epoch_seg(vs):
    return [EPOCA + _dt.timedelta(seconds=int(v)) for v in vs]


def _compacto(ds):
    return [d.strftime("%Y%m%d") for d in ds]


def _de_compacto(vs):
    return [_dt.datetime.strptime(v, "%Y%m%d").date() for v in vs]


def _delta(ds):
    """1ª data por extenso + diferenças em dias. Vira quase-constante em passo regular."""
    out = [ds[0].isoformat()]
    out += [str((ds[i] - ds[i - 1]).days) for i in range(1, len(ds))]
    return out


def _de_delta(vs):
    d = _dt.date.fromisoformat(vs[0])
    out = [d]
    for v in vs[1:]:
        d = d + _dt.timedelta(days=int(v))
        out.append(d)
    return out


ALVOS = {
    "iso": (_iso, _de_iso, "linha de base — o que o TCF faz hoje"),
    "ordinal-dec": (_ord_dec, _de_ord_dec, "decimal: o `*N+M|` enxerga a aritmética"),
    "ordinal-denso": (_ord_denso, _de_ord_denso, f"base-{len(ALFA)} largura {LARG_DENSO} — o alvo do CPF"),
    "ordinal-b64": (_ord_b64, _de_ord_b64, "base64 de 3 bytes = 4 chars, sem padding"),
    "epoch-seg": (_epoch_seg, _de_epoch_seg, "segundos desde 1970 — o formato timestamp"),
    "compacto": (_compacto, _de_compacto, "YYYYMMDD: numérico E legível"),
    "delta-dias": (_delta, _de_delta, "1ª por extenso + diferenças"),
}


# ── DECLARAÇÃO DA GRAFIA: as três opções, e o que cada uma custa ─────────────
GRAFIAS = {
    "iso": "%Y-%m-%d", "br": "%d/%m/%Y", "us": "%m/%d/%Y",
    "compacto": "%Y%m%d", "ponto": "%d.%m.%Y", "iso-invertido": "%d-%m-%Y",
}


def infere_do_primeiro(v: str) -> list[str]:
    """Quais grafias explicam o primeiro valor? Uma só = o 1º registro basta.

    É o teste da opção "o primeiro registro é o formatador, de graça": só funciona quando
    ele DESAMBIGUA sozinho.
    """
    ok = []
    for nome, fmt in GRAFIAS.items():
        try:
            d = _dt.datetime.strptime(v, fmt).date()
        except ValueError:
            continue
        if d.strftime(fmt) == v:               # re-emissão: grafia canônica do formato
            ok.append(nome)
    return ok
