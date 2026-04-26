"""Naturalness taxonomy for NL2SQL / data analysis questions (M-natural).

4 levels of question phrasing on the same ground truth:

    N0 — Schema-aware:    explicit table/column names, hints about quoting,
                          NULL handling. Mirrors the questions in M3..M9.
    N1 — System-aware:    domain-aware but uses natural prose for entities.
                          Drops literal column names but keeps domain terms.
    N2 — Business-intent: business semantics. No column refs, fuzzy operators.
    N3 — Business+ctxt:   business with implicit scope/context that requires
                          mapping fuzzy terms to dataset operations.

Each :class:`Question` carries 4 wordings + the same GT key/type. Runners pick
a level and consume the result as `dict[name -> {text, key, type}]` —
backwards compatible with `build_questions_adult()` from run_m9_adult.

The N0 wordings are kept VERBATIM from the existing runners so that a run with
``--naturalness N0`` reproduces M9-Adult / M-Alocal / M-Acomm exactly.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class NaturalnessLevel(str, Enum):
    N0 = "N0"
    N1 = "N1"
    N2 = "N2"
    N3 = "N3"


ALL_LEVELS: tuple[NaturalnessLevel, ...] = (
    NaturalnessLevel.N0,
    NaturalnessLevel.N1,
    NaturalnessLevel.N2,
    NaturalnessLevel.N3,
)


@dataclass(frozen=True)
class Question:
    """A question with 4 wordings sharing a single ground-truth key.

    Attributes
    ----------
    name
        Slug used in manifests / results (e.g. ``q_count``).
    key
        GT lookup key — must exist in the value returned by the dataset's
        ``compute_gt_*`` function.
    type
        Scoring type: ``count``, ``numeric`` or ``string`` — same vocabulary
        used by :func:`llm_eval.metrics.score_response`.
    wordings
        Mapping from :class:`NaturalnessLevel` to the prompt text at that
        level.
    ambiguity_note
        Optional caveat about why N2/N3 are inherently fuzzy. Recorded as
        documentation only — not used for scoring.
    """

    name: str
    key: str
    type: str
    wordings: dict[NaturalnessLevel, str]
    ambiguity_note: str | None = None

    def text(self, level: NaturalnessLevel | str) -> str:
        if isinstance(level, str):
            level = NaturalnessLevel(level)
        return self.wordings[level]

    def at(self, level: NaturalnessLevel | str) -> dict:
        """Return a runner-compatible dict for the given level."""
        return {"text": self.text(level), "key": self.key, "type": self.type}


# ---------------------------------------------------------------------------
# Adult Census — 7 questions × 4 levels = 28 wordings
#
# N0 wordings are byte-identical to build_questions_adult() in run_m9_adult.
# ---------------------------------------------------------------------------

ADULT_QUESTIONS: tuple[Question, ...] = (
    Question(
        name="q_count",
        key="count",
        type="count",
        wordings={
            NaturalnessLevel.N0: "Quantas linhas existem na tabela adult?",
            NaturalnessLevel.N1: "Quantas pessoas estao registradas no censo?",
            NaturalnessLevel.N2: "Quantos registros temos no total?",
            NaturalnessLevel.N3: "Qual o tamanho da amostra que estamos analisando?",
        },
    ),
    Question(
        name="q_avg_age",
        key="avg_age",
        type="numeric",
        wordings={
            NaturalnessLevel.N0: "Qual e a media da coluna age na tabela adult?",
            NaturalnessLevel.N1: "Qual e a idade media das pessoas no censo?",
            NaturalnessLevel.N2: "Em media, quantos anos as pessoas tem?",
            NaturalnessLevel.N3: "Qual a idade media dessa populacao de adultos trabalhadores?",
        },
        ambiguity_note=(
            "N3 ainda mapeia para mean(age); 'idade tipica' poderia ser "
            "interpretada como mediana ou moda — evitamos esse termo."
        ),
    ),
    Question(
        name="q_max_age",
        key="max_age",
        type="count",
        wordings={
            NaturalnessLevel.N0: "Qual e o maior valor da coluna age na tabela adult?",
            NaturalnessLevel.N1: "Qual a maior idade registrada no censo?",
            NaturalnessLevel.N2: "Qual a idade da pessoa mais velha?",
            NaturalnessLevel.N3: "Quantos anos tem o adulto mais velho da nossa base?",
        },
    ),
    Question(
        name="q_distinct_workclass",
        key="distinct_workclass",
        type="count",
        wordings={
            NaturalnessLevel.N0: (
                "Quantos valores distintos de workclass aparecem na tabela adult? "
                "Ignore valores nulos."
            ),
            NaturalnessLevel.N1: "Quantas categorias diferentes de classe trabalhista existem?",
            NaturalnessLevel.N2: "Quantos tipos distintos de vinculo empregaticio temos na amostra?",
            NaturalnessLevel.N3: "Em quantas modalidades de trabalho as pessoas se enquadram?",
        },
        ambiguity_note=(
            "N1-N3 nao mencionam 'ignore nulos' — esperamos que o modelo "
            "infira pelo dominio da pergunta. GT exclui nulos."
        ),
    ),
    Question(
        name="q_top_education",
        key="top_education",
        type="string",
        wordings={
            NaturalnessLevel.N0: (
                "Qual valor de education aparece mais vezes na tabela adult? "
                "Responda com o valor exato."
            ),
            NaturalnessLevel.N1: "Qual o nivel de escolaridade mais comum entre as pessoas?",
            NaturalnessLevel.N2: "Qual a formacao predominante na amostra?",
            NaturalnessLevel.N3: "Qual e o perfil educacional mais frequente dessa populacao?",
        },
        ambiguity_note=(
            "GT e o valor categorico exato (ex.: 'HS-grad'). N2/N3 podem "
            "induzir o modelo a parafrasear ('ensino medio') — esperamos "
            "queda de accuracy especificamente por isso."
        ),
    ),
    Question(
        name="q_count_high_class",
        key="count_high_class",
        type="count",
        wordings={
            NaturalnessLevel.N0: "Quantas linhas têm class igual a '>50K' na tabela adult?",
            NaturalnessLevel.N1: "Quantas pessoas ganham mais de 50K por ano?",
            NaturalnessLevel.N2: "Quantos individuos estao na faixa de renda alta (>50K)?",
            NaturalnessLevel.N3: (
                "Na nossa amostra, quantos sao considerados de alta renda "
                "segundo o criterio do dataset?"
            ),
        },
        ambiguity_note=(
            "N3 depende do modelo conhecer/inferir que o dataset usa o "
            "threshold >50K como definicao de alta renda."
        ),
    ),
    Question(
        name="q_avg_hours_male",
        key="avg_hours_male",
        type="numeric",
        wordings={
            NaturalnessLevel.N0: (
                "Qual e a media de hours-per-week para linhas com sex igual a 'Male'?"
            ),
            NaturalnessLevel.N1: "Qual a media de horas trabalhadas por semana entre os homens?",
            NaturalnessLevel.N2: "Em media, quantas horas semanais os homens trabalham?",
            NaturalnessLevel.N3: (
                "Quanto tempo, em horas semanais, a forca de trabalho "
                "masculina dedica ao trabalho?"
            ),
        },
    ),
)


# ---------------------------------------------------------------------------
# TPC-H subset (customer + orders + lineitem) — placeholder for Phase 2.5
#
# The 7 questions used in M9-canonical are SQL-stats style and very
# schema-aware. We will populate this catalog in a follow-up commit once
# Adult-only M-natural runs and we know the protocol stabilizes.
# ---------------------------------------------------------------------------

TPCH_QUESTIONS: tuple[Question, ...] = ()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_CATALOGS: dict[str, tuple[Question, ...]] = {
    "adult-census": ADULT_QUESTIONS,
    "adult": ADULT_QUESTIONS,
    "tpch": TPCH_QUESTIONS,
    "tpch-sf001": TPCH_QUESTIONS,
}


def get_catalog(dataset: str) -> tuple[Question, ...]:
    if dataset not in _CATALOGS:
        raise ValueError(
            f"Unknown dataset {dataset!r}. "
            f"Known: {sorted(set(_CATALOGS))}"
        )
    cat = _CATALOGS[dataset]
    if not cat:
        raise ValueError(
            f"Catalog for {dataset!r} is empty (not yet defined)."
        )
    return cat


def get_questions(dataset: str, level: NaturalnessLevel | str) -> dict:
    """Return ``dict[name -> {text, key, type}]`` for the given level.

    Backwards compatible with ``build_questions_adult()`` — runners can swap
    the call without touching downstream code.
    """
    if isinstance(level, str):
        level = NaturalnessLevel(level)
    return {q.name: q.at(level) for q in get_catalog(dataset)}


def iter_levels(spec: str) -> Iterable[NaturalnessLevel]:
    """Parse a CLI flag value into the levels to iterate.

    ``"N0"`` → just N0; ``"all"`` → all 4 levels; ``"N0,N2"`` → those two.
    """
    spec = spec.strip()
    if spec.lower() == "all":
        return ALL_LEVELS
    parts = [p.strip() for p in spec.split(",") if p.strip()]
    return tuple(NaturalnessLevel(p) for p in parts)


__all__ = [
    "NaturalnessLevel",
    "ALL_LEVELS",
    "Question",
    "ADULT_QUESTIONS",
    "TPCH_QUESTIONS",
    "get_catalog",
    "get_questions",
    "iter_levels",
]
