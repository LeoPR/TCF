"""Protótipo dos alvos de data — os candidatos que o `min()` receberia.

**Protótipo de lab. `src/tcf` NÃO é tocado.** Cada alvo segue o MESMO protocolo das
natures soldadas (`src/tcf/natures/`): per-valor, com válvula — valor que não casa passa
cru com `MARCADOR` e não contamina a coluna.

    A1  ordinal-dia    o SOLDADO (`SPEC_DATA_ISO`) — baseline, entra pelo `encode(nature=)`
    A4  mês×31+dia     alvo mensal GERAL, sem convenção; injetivo p/ toda data
    A2f fim-de-mês     convenção `dia == último do mês` (fecho contábil)
    YM  ano-mês        grafia `YYYY-MM` (spec IRMÃO: parser e re-emissão próprios)

Por que A2 (mês-época com `dia==01`) não está aqui: o lab dirty `1853` mediu que o A4 o
cobre por 2 B de diferença nos regimes de convenção, com cobertura muito maior. A2 fica
registrado como variação, não como candidato.

Por que A3 (`YYYYMM`) não está aqui: **refutado** no `1853` — a legibilidade do payload
custa a aritmética (a virada `…12 → +89 → …01` quebra os runs).

## O contrato de cada alvo

    nome            tag hipotética no header (custo contado no FLOOR)
    encode_value    str -> str (payload) ; valor fora do padrão -> MARCADOR + original
    decode_value    str -> str (o valor ORIGINAL, byte a byte)

A grafia de re-emissão é **uma por alvo**: dois alvos não podem compartilhar payload com
grafias diferentes na mesma coluna, senão o round-trip quebra. É o mesmo guard de
re-emissão do `DataIsoSpec` e do ADR-0040.
"""
from __future__ import annotations

import calendar
import datetime as _dt

MARCADOR = "_"
_FROM_ISO = _dt.date.fromisoformat


def _iso_canonica(v):
    """A data, se `v` é ISO extendida canônica. `None` caso contrário.

    O guard `d.isoformat() != v` é obrigatório: desde 3.11 o `fromisoformat` aceita mais
    do que o `isoformat` emite (`20191204`, `2021-W01-1`), e sem ele o decode devolveria
    uma grafia diferente da que entrou.
    """
    if not isinstance(v, str) or len(v) != 10:
        return None
    try:
        d = _FROM_ISO(v)
    except ValueError:
        return None
    return d if d.isoformat() == v else None


class AlvoBase:
    nome = "?"
    tag = "?"

    def encode_value(self, v):
        raise NotImplementedError

    def decode_value(self, p):
        raise NotImplementedError

    # `None` NÃO é assunto do alvo: o slot 0 é do core (`src/tcf/natures/
    # templated_checked.py` faz exatamente isto nas 4 natures soldadas — antes do fix de
    # 2026-08-08, `MARCADOR + None` estourava `TypeError` nas quatro). O protótipo tem de
    # espelhar o protocolo real, senão o lab mede um contrato que não existe.
    def encode_col(self, vals):
        return [None if v is None else self.encode_value(v) for v in vals]

    def decode_col(self, payloads):
        return [None if p is None else self.decode_value(p) for p in payloads]


class AlvoMes31Dia(AlvoBase):
    """A4 — `(ano*12 + mês-1) * 31 + (dia-1)`.

    Sem convenção: injetivo para QUALQUER data. Qualquer dia-do-mês constante vira delta
    uniforme `+31`; dias que alternam viram período curto. É o alvo mensal geral.
    """

    nome = "mes31dia"
    tag = ":data-mes"

    def encode_value(self, v):
        d = _iso_canonica(v)
        if d is None:
            return MARCADOR + str(v)
        return str((d.year * 12 + d.month - 1) * 31 + d.day - 1)

    def decode_value(self, p):
        if p.startswith(MARCADOR):
            return p[len(MARCADOR):]
        q, r = divmod(int(p), 31)
        return _dt.date(q // 12, q % 12 + 1, r + 1).isoformat()


class AlvoFimDeMes(AlvoBase):
    """A2f — mês-época, com a CONVENÇÃO `dia == último do mês`.

    Existe porque o fecho contábil é o único regime em que o dia varia *e* é dedutível.
    Nele o A4 falha (dias 28..31 quebram a uniformidade) e este colapsa.
    """

    nome = "fimdemes"
    tag = ":data-mes-fim"

    def encode_value(self, v):
        d = _iso_canonica(v)
        if d is None or d.day != calendar.monthrange(d.year, d.month)[1]:
            return MARCADOR + str(v)
        return str(d.year * 12 + d.month - 1)

    def decode_value(self, p):
        if p.startswith(MARCADOR):
            return p[len(MARCADOR):]
        m = int(p)
        y, mo = m // 12, m % 12 + 1
        return _dt.date(y, mo, calendar.monthrange(y, mo)[1]).isoformat()


class AlvoAnoMes(AlvoBase):
    """YM — grafia `YYYY-MM` (sem dia). Spec IRMÃO: parser e re-emissão próprios.

    Não é um parser a mais do spec ISO: o payload é o mesmo mês-época, mas a grafia de
    volta é `YYYY-MM`. Duas grafias no mesmo spec quebrariam o round-trip.
    """

    nome = "anomes"
    tag = ":data-ym"

    def encode_value(self, v):
        if isinstance(v, str) and len(v) == 7 and v[4] == "-" \
                and v[:4].isdigit() and v[5:].isdigit():
            m = int(v[5:])
            if 1 <= m <= 12:
                p = str(int(v[:4]) * 12 + m - 1)
                # GUARD DE RE-EMISSÃO — 4ª ocorrência da classe no projeto (DataIsoSpec,
                # ADR-0040 ×2, e agora aqui). A caçada adversarial pegou: `str.isdigit()`
                # e `int()` aceitam dígitos Unicode (fullwidth `２００６-０１`, etc.) —
                # 5 grafias distintas colapsavam no MESMO payload e o decode devolvia a
                # ASCII: não-injetivo. A regra: só é payload o que RE-EMITE byte a byte.
                if self.decode_value(p) == v:
                    return p
        return MARCADOR + str(v)

    def decode_value(self, p):
        if p.startswith(MARCADOR):
            return p[len(MARCADOR):]
        m = int(p)
        return f"{m // 12:04d}-{m % 12 + 1:02d}"


ALVOS = [AlvoMes31Dia(), AlvoFimDeMes(), AlvoAnoMes()]
