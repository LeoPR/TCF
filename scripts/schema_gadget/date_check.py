"""Date/format consistency checker — Fase 2 do schema/quality gadget.

Detecta, em colunas que PARECEM data:
- impossible_date: calendário-inválido (mês>12, dia>31, 32-fev, dia/mês=0,
  29-fev em ano não-bissexto)
- format_mix: formatos de data incompatíveis na MESMA coluna (ISO vs BR vs US)
- suspicious_date: futuro distante ou passado absurdo (heurística leve)

ALERT-ONLY: nunca corrige. O dev/arquiteto decide.

⚠️ NÃO é zero-custo (ao contrário da Fase 3). Varre TODOS os valores e
parseia cada um — é um scan dedicado com conhecimento de domínio (calendário).
Justificado: validar data exige semântica que o pré-pass do TCF não tem.
Por isso roda só sobre colunas auto-detectadas como data (não a tabela toda).

Sem dependências externas: parser próprio por regex (stdlib only), para não
herdar a permissividade de dateutil (que "conserta" 32/13 silenciosamente).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Formatos reconhecidos -> regex com grupos nomeados (y/m/d). Ordem importa
# só para rotular o "formato dominante"; a detecção tenta todos.
_FORMATS = {
    "ISO":      re.compile(r"^(?P<y>\d{4})-(?P<m>\d{2})-(?P<d>\d{2})(?:[ T]\d{2}:\d{2}(:\d{2})?)?$"),
    "BR_slash": re.compile(r"^(?P<d>\d{2})/(?P<m>\d{2})/(?P<y>\d{4})$"),
    "US_slash": re.compile(r"^(?P<m>\d{1,2})/(?P<d>\d{1,2})/(?P<y>\d{4})(?:\s+\d{1,2}:\d{2})?$"),
    "compact":  re.compile(r"^(?P<y>\d{4})(?P<m>\d{2})(?P<d>\d{2})$"),  # YYYYMMDD
}

_DAYS_IN_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


@dataclass(frozen=True)
class DateAlert:
    column: str
    kind: str        # 'impossible_date' | 'format_mix' | 'suspicious_date'
    severity: str
    detail: str
    zero_cost: bool = False  # scan dedicado — NÃO zero-custo (declarado)

    def alert(self) -> str:
        return f"[{self.severity}|{self.kind}] {self.column}: {self.detail}"


def _is_leap(y: int) -> bool:
    return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)


def _valid_ymd(y: int, m: int, d: int) -> bool:
    if not (1 <= m <= 12):
        return False
    dmax = _DAYS_IN_MONTH[m - 1] + (1 if (m == 2 and _is_leap(y)) else 0)
    return 1 <= d <= dmax


def _parse(value):
    """Tenta casar value contra os formatos. Retorna (fmt, y, m, d) ou None.

    Type-safe: aceita qualquer valor (DatasetReader devolve int/float pra
    colunas numéricas); só strings podem casar um formato de data. Retorna o
    formato casado MESMO se a data for impossível (validade fica em _valid_ymd).
    """
    if not isinstance(value, str):
        return None
    for fmt, rx in _FORMATS.items():
        mt = rx.match(value)
        if mt:
            return fmt, int(mt["y"]), int(mt["m"]), int(mt["d"])
    return None


def _looks_like_date_column(sample: list[str], threshold: float = 0.7) -> bool:
    """Heurística: a coluna parece conter datas? (>=threshold do sample casa)."""
    non_empty = [v for v in sample if v not in (None, "")]
    if len(non_empty) < 3:
        return False
    matched = sum(1 for v in non_empty if _parse(v) is not None)
    return matched / len(non_empty) >= threshold


def check_dates(
    tables: dict[str, dict[str, list]],
    *,
    sample_for_detection: int = 50,
    future_year_limit: int = 2100,
    past_year_limit: int = 1900,
    max_examples: int = 5,
) -> dict[str, list[DateAlert]]:
    """Verifica datas em colunas auto-detectadas como data.

    Args:
        tables: {tabela: {coluna: [valores]}}.
        sample_for_detection: quantos valores olhar pra decidir se é coluna data.
        future_year_limit / past_year_limit: limites pra suspicious_date.
        max_examples: máx. exemplos citados por alerta.

    Returns:
        {tabela: [DateAlert]}. ALERT-ONLY (não muta tables). NÃO zero-custo.
    """
    out: dict[str, list[DateAlert]] = {}
    for tname, cols in tables.items():
        alerts: list[DateAlert] = []
        for cname, values in cols.items():
            sample = values[:sample_for_detection]
            if not _looks_like_date_column(sample):
                continue

            impossible: list[str] = []
            suspicious: list[str] = []
            fmts_seen: dict[str, int] = {}

            for v in values:
                if v in (None, ""):
                    continue
                parsed = _parse(v)
                if parsed is None:
                    # numa coluna-data, valor que não parseia é format anomaly
                    fmts_seen["?desconhecido"] = fmts_seen.get("?desconhecido", 0) + 1
                    continue
                fmt, y, m, d = parsed
                fmts_seen[fmt] = fmts_seen.get(fmt, 0) + 1
                if not _valid_ymd(y, m, d):
                    if len(impossible) < max_examples:
                        impossible.append(v)
                elif y > future_year_limit or y < past_year_limit:
                    if len(suspicious) < max_examples:
                        suspicious.append(v)

            if impossible:
                alerts.append(DateAlert(
                    column=cname, kind="impossible_date", severity="alta",
                    detail=f"{len(impossible)}+ data(s) calendário-inválida(s): {impossible}",
                ))
            # format_mix: >1 formato real (ignora '?desconhecido' isolado raro)
            real_fmts = {f: c for f, c in fmts_seen.items() if f != "?desconhecido"}
            if len(real_fmts) > 1:
                alerts.append(DateAlert(
                    column=cname, kind="format_mix", severity="media",
                    detail=f"formatos de data misturados: {real_fmts}",
                ))
            if suspicious:
                alerts.append(DateAlert(
                    column=cname, kind="suspicious_date", severity="baixa",
                    detail=(f"{len(suspicious)}+ data(s) fora de [{past_year_limit}.."
                            f"{future_year_limit}]: {suspicious}"),
                ))
        if alerts:
            out[tname] = alerts
    return out


def _self_demo() -> None:
    tables = {
        "pedidos": {
            "data_ok": ["2024-01-15", "2024-02-29", "2023-12-31"],  # 2024 bissexto: 29-fev OK
            "data_ruim": ["2026-02-30", "2026-13-01", "2026-00-15", "2023-02-29"],  # todas inválidas
            "data_mista": ["2024-01-15", "15/01/2024", "2024-03-01"],  # ISO + BR
            "data_futuro": ["2024-01-01", "2999-01-01", "2025-06-15"],  # suspeita (1 fora de range)
            "nome": ["ana", "bia", "cris"],  # não é data — ignorada
        },
    }
    for t, alerts in check_dates(tables).items():
        print(f"[{t}]")
        for a in alerts:
            print("  ", a.alert())


if __name__ == "__main__":
    _self_demo()
