"""Spec LAZY de data — protótipo fora do `src/tcf`, no molde da nature do CPF.

Copia a IDEIA da `natures/templated_checked.py`, não o código:

    classify_value(v)  ->  'compressible' | motivo
    encode_value(v)    ->  (payload, status);  não-compressível vira MARKER + v
    decode_value(p)    ->  string original, byte-idêntica

O que muda em relação ao CPF: data **não tem dígito verificador**. A validação é só
estrutural (o valor parseia no formato do spec?), e o alvo da transformação é o **ordinal**
— porque é ele que alcança o `*N+M|` do seq-RLE (medido no lab `2026-08-07-2311`: 120 datas
diárias saem de 97 B para 22 B).

## O ponto de design que este protótipo testa

**A ambiguidade BR × US não precisa ser resolvida.** A transformação tem de ser
*inversível*, não *correta*. Se o spec chuta BR e o dado era US, `01/02/2026` volta
`01/02/2026` — byte-idêntico — porque a inversa aplica o mesmo chute. E `02/13/2026` (mês 13
no chute BR) simplesmente **não parseia** e cai no literal, custando +1 byte.

Ou seja: **chute errado custa bytes, nunca dado.** Isso é o que torna o lazy seguro.

`src/tcf` NÃO é tocado.
"""
from __future__ import annotations

import datetime as _dt

#: Mesmo papel do `MARKER_LITERAL` do CPF: 1 char que diz "não mexi neste".
#: `_` é o do CPF; aqui usa-se o mesmo, pra deixar claro que é o mesmo mecanismo.
MARCADOR_LITERAL = "_"


class SpecData:
    """Um formato de data. `nome`, como parsear, como formatar de volta."""

    def __init__(self, nome: str, fmt: str, exemplo: str):
        self.nome, self.fmt, self.exemplo = nome, fmt, exemplo

    # ── classificação (o "olha e decide", igual ao CPF) ──────────────────────
    def classify_value(self, v) -> str:
        if v is None:
            return "nulo"                      # o slot nulo é do core, não do spec
        if not isinstance(v, str) or not v:
            return "vazio"
        if len(v) != len(self.exemplo):
            return "comprimento"               # descarta cedo, sem tentar parsear
        try:
            d = _dt.datetime.strptime(v, self.fmt).date()
        except ValueError:
            return "nao-parseia"
        # RE-EMISSÃO: a grafia tem de ser a que o próprio spec produziria. Sem isto,
        # `2026-1-01` e `2026-01-01` virariam o mesmo ordinal e o RT quebraria. É a mesma
        # técnica de canonicidade por re-emissão usada no header do bN e na grafia numérica.
        if d.strftime(self.fmt) != v:
            return "grafia-nao-canonica"
        return "compressible"

    # ── transformação ────────────────────────────────────────────────────────
    def encode_value(self, v) -> "tuple[str | None, str]":
        st = self.classify_value(v)
        if st == "nulo":
            return None, st                    # passa direto; quem cuida é o core
        if st != "compressible":
            return MARCADOR_LITERAL + v, st
        return str(_dt.datetime.strptime(v, self.fmt).date().toordinal()), st

    def decode_value(self, p):
        if p is None:
            return None
        if p.startswith(MARCADOR_LITERAL):
            return p[1:]
        return _dt.date.fromordinal(int(p)).strftime(self.fmt)


SPECS = {
    "iso": SpecData("iso", "%Y-%m-%d", "2026-01-01"),
    "br": SpecData("br", "%d/%m/%Y", "01/01/2026"),
    "us": SpecData("us", "%m/%d/%Y", "01/01/2026"),
    "compacto": SpecData("compacto", "%Y%m%d", "20260101"),
}


def aplica(spec: SpecData, coluna) -> "tuple[list, dict]":
    """Coluna -> coluna transformada + contagem por status."""
    saida, contagem = [], {}
    for v in coluna:
        p, st = spec.encode_value(v)
        saida.append(p)
        contagem[st] = contagem.get(st, 0) + 1
    return saida, contagem


def desfaz(spec: SpecData, coluna) -> list:
    return [spec.decode_value(p) for p in coluna]
