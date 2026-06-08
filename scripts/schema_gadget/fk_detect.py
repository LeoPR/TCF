"""FK candidate detector — Fase 1 do schema/quality gadget.

Descobre relações de chave estrangeira candidatas por **overlap de valores**:
uma coluna `child` é FK candidata de `parent` se os valores não-nulos de
child são (quase) um subconjunto dos valores de parent.

ALERT-ONLY: emite candidatos com confiança; NUNCA modifica dados nem declara
FK no schema. O dev/arquiteto decide. Não usa metadata.fk — DESCOBRE do dado
(o ponto é detectar FKs não-declaradas / validar as declaradas).

Entrada genérica (desacoplada do TCF-core e do dataset_reader):
    tables: dict[str, dict[str, list]]   # {tabela: {coluna: [valores]}}

Heurística (parâmetros default conservadores):
    - parent candidato: coluna com alta unicidade (parece chave) — cobre PK
      e colunas únicas. child: qualquer coluna do MESMO domínio de valores.
    - overlap = |distinct(child) ∩ distinct(parent)| / |distinct(child)|
    - emite se overlap >= min_overlap E parent_uniqueness >= min_parent_uniq
    - 1.0 = FK íntegra; 0.88..0.99 = candidata com órfãos (alerta).

Custo: NAO é zero-custo (precisa materializar conjuntos de valores e cruzar
tabelas). É scan dedicado do gadget — esperado pela natureza cross-table.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FKCandidate:
    """Uma relação FK candidata descoberta por overlap de valores."""
    child_table: str
    child_col: str
    parent_table: str
    parent_col: str
    overlap: float          # fração de valores distintos de child que existem em parent
    n_child_distinct: int
    n_orphans: int          # valores distintos de child ausentes em parent
    parent_uniqueness: float  # n_unicas/n_rows do parent (quão "chave" ele é)
    name_match: bool        # nome de child/parent sugere relação (sufixo compatível)
    confidence: str         # 'alta' | 'media' | 'baixa' — força do sinal combinado

    @property
    def is_clean(self) -> bool:
        """True se integridade referencial perfeita (sem órfãos)."""
        return self.n_orphans == 0

    def alert(self) -> str:
        """Mensagem de alerta human-readable (o gadget só alerta)."""
        tag = "FK íntegra" if self.is_clean else f"FK candidata ({self.n_orphans} órfãos)"
        return (f"[{tag}|conf={self.confidence}] {self.child_table}.{self.child_col} -> "
                f"{self.parent_table}.{self.parent_col} "
                f"(overlap={self.overlap:.3f}, "
                f"child_distinct={self.n_child_distinct})")


def _distinct_non_null(values: list) -> set:
    """Conjunto de valores distintos, descartando nulos/vazios."""
    out = set()
    for v in values:
        if v is None:
            continue
        if isinstance(v, str) and v == "":
            continue
        out.add(v)
    return out


def _name_match(child_col: str, parent_col: str) -> bool:
    """True se os nomes sugerem relação FK (sufixo/raiz compatível).

    Ex: n_regionkey ↔ r_regionkey (sufixo 'regionkey'); socio_cpf ↔ cpf
    (sufixo 'cpf'); o_custkey ↔ c_custkey (sufixo 'custkey').
    """
    a = child_col.split("_")[-1]
    b = parent_col.split("_")[-1]
    return a == b or child_col.endswith(parent_col) or parent_col.endswith(child_col)


def _confidence(overlap: float, name_match: bool, n_child_distinct: int) -> str:
    """Gradua a confiança combinando overlap + nome + cardinalidade do child.

    Racional (validado em TPC-H + br-identidades):
    - overlap puro em INTEIROS DENSOS pequenos gera falsos positivos por
      coincidência numérica (l_quantity cai no range de p_partkey). Esses
      casos tem name_match=False E baixa cardinalidade → 'baixa'.
    - name_match desambigua fortemente (TPC-H: 0 FP com nome compatível).
    - alta cardinalidade do child reduz chance de coincidência (CPF/UUID).
    """
    if name_match and overlap >= 0.99:
        return "alta"
    if name_match or (overlap >= 0.99 and n_child_distinct >= 1000):
        return "media"
    return "baixa"


def detect_fk_candidates(
    tables: dict[str, dict[str, list]],
    *,
    min_overlap: float = 0.85,
    min_parent_uniqueness: float = 0.98,
    min_child_distinct: int = 2,
    min_confidence: str = "baixa",
) -> list[FKCandidate]:
    """Detecta FK candidates por overlap de valores entre colunas.

    Descoberta por VALOR (não usa metadata.fk) + graduação de confiança que
    combina overlap, compatibilidade de NOME, e cardinalidade do child.

    Args:
        tables: {tabela: {coluna: [valores]}}.
        min_overlap: fração mínima de valores distintos de child presentes em
            parent (default 0.85 — pega FKs com até 15% órfãos).
        min_parent_uniqueness: parent precisa parecer chave (n_unicas/n_rows).
            Default 0.98 (PKs e colunas únicas).
        min_child_distinct: ignora colunas com pouquíssimos distintos (flags).
        min_confidence: 'baixa'|'media'|'alta' — filtra por confiança mínima.
            Default 'baixa' (emite tudo que passa overlap; confiança no campo).
            Use 'media'/'alta' para reduzir falsos positivos em chaves inteiras
            densas (validado TPC-H: 'alta' → 9/9 recall, 0 FP).

    Returns:
        Lista de FKCandidate ordenada por (confiança desc, parent, overlap desc).
        ALERT-ONLY: não modifica `tables`.
    """
    _rank = {"baixa": 0, "media": 1, "alta": 2}
    floor = _rank.get(min_confidence, 0)

    distinct: dict[tuple[str, str], set] = {}
    uniqueness: dict[tuple[str, str], float] = {}
    for t, cols in tables.items():
        for c, vals in cols.items():
            d = _distinct_non_null(vals)
            distinct[(t, c)] = d
            n = len([v for v in vals if not (v is None or v == "")])
            uniqueness[(t, c)] = (len(d) / n) if n else 0.0

    parents = [
        (t, c) for (t, c), u in uniqueness.items()
        if u >= min_parent_uniqueness and len(distinct[(t, c)]) >= min_child_distinct
    ]

    candidates: list[FKCandidate] = []
    for ct, cols in tables.items():
        for cc, _ in cols.items():
            child_set = distinct[(ct, cc)]
            if len(child_set) < min_child_distinct:
                continue
            for pt, pc in parents:
                if pt == ct and pc == cc:
                    continue
                parent_set = distinct[(pt, pc)]
                inter = child_set & parent_set
                if not inter:
                    continue
                overlap = len(inter) / len(child_set)
                if overlap < min_overlap:
                    continue
                nm = _name_match(cc, pc)
                conf = _confidence(overlap, nm, len(child_set))
                if _rank[conf] < floor:
                    continue
                candidates.append(FKCandidate(
                    child_table=ct, child_col=cc,
                    parent_table=pt, parent_col=pc,
                    overlap=round(overlap, 4),
                    n_child_distinct=len(child_set),
                    n_orphans=len(child_set - parent_set),
                    parent_uniqueness=round(uniqueness[(pt, pc)], 4),
                    name_match=nm,
                    confidence=conf,
                ))

    candidates.sort(key=lambda fk: (-_rank[fk.confidence], fk.parent_table,
                                    fk.parent_col, -fk.overlap))
    return candidates


def _self_demo() -> None:
    """Demo mínima sem dependências (não precisa de Z:/dataset)."""
    tables = {
        "region": {"r_regionkey": [0, 1, 2, 3, 4]},
        "nation": {"n_nationkey": [0, 1, 2, 3],
                   "n_regionkey": [0, 1, 1, 2]},  # FK -> region
        "orders": {"o_orderkey": [10, 11, 12],
                   "o_custkey": [1, 2, 99]},       # 99 órfão (sem customer)
        "customer": {"c_custkey": [1, 2, 3]},
    }
    for fk in detect_fk_candidates(tables, min_parent_uniqueness=0.9):
        print(" ", fk.alert())


if __name__ == "__main__":
    _self_demo()
