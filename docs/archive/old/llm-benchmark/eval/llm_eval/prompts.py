"""Question bank and prompt builder for TCF evaluation.

Organized by diagnostic layers:
  Layer 0 (math_control):  Plain arithmetic, no format — tests model arithmetic ability
  Layer 1 (decode_only):   Format given, list values — tests format comprehension
  Layer 2 (compute):       Format + operation — full pipeline test

Questions Q1–Q10 are defined with:
  - template: the actual question text (may have {param} placeholders)
  - layer: "math_control", "decode_only", or "compute"
  - required_params: set of {param} names that must be supplied
  - key: stable identifier for ground-truth lookup
"""

from typing import Any, Dict, Set

# ---------------------------------------------------------------------------
# System prompts by format
# ---------------------------------------------------------------------------

DEFAULT_SYSTEM_PROMPT = (
    "Você receberá um conjunto de dados tabulares."
    " Leia o formato informado e responda estritamente com base nele."
    " Nunca invente registros que não apareçam e jamais use conhecimento externo."
)

SYSTEM_PROMPTS: Dict[str, str] = {
    "math_control": (
        "Você é um assistente de cálculo. Dados números, realize operações aritméticas."
        " Responda SOMENTE com o resultado numérico, sem explicação."
    ),
    "tcf": (
        "Você receberá dados no formato TCF (Textual Columnar Format)."
        " Nesse formato, cada bloco começa com o nome da coluna seguido de ':' e os valores vêm um por linha."
        " A notação N*val significa que val se repete N vezes consecutivamente."
        " Dados podem estar ordenados para agrupar repetições."
        " Use apenas os dados fornecidos para responder."
    ),
    "tcf_L0": (
        "Você receberá dados em formato colunar."
        " Cada bloco começa com nome da coluna seguido de ':'."
        " Valores um por linha, mesma ordem entre colunas."
        " Responda com base apenas nos dados."
    ),
    "tcf_L2": (
        "Você receberá dados em formato colunar comprimido."
        " N*val = val repetido N vezes."
        " Dados ordenados para agrupar repetições."
        " Responda com base apenas nos dados."
    ),
    "csv": (
        "Você receberá dados no formato CSV."
        " A primeira linha traz o nome das colunas e as demais linhas são registros."
        " Respeite separadores de vírgula e aspas conforme o padrão CSV."
    ),
    "tsv": (
        "Você receberá dados no formato TSV (colunas separadas por TAB)."
        " A primeira linha contém os nomes das colunas."
    ),
    "jsonl": (
        "Você receberá linhas no formato JSON Lines (NDJSON)."
        " Cada linha é um objeto JSON independente."
    ),
    "ndjson": (
        "Você receberá linhas no formato NDJSON."
        " Cada linha é um objeto JSON independente."
    ),
    "token_object": (
        "Você receberá dados no formato TOON (Token-Oriented Object Notation)."
        " Este é um objeto JSON único contendo 'columns' (nomes das colunas) e 'rows' (matriz de valores)."
        " Use a lista 'columns' para interpretar a posição de cada valor em 'rows'."
    ),
    "mdtable": (
        "Você receberá uma tabela Markdown com cabeçalho."
        " Use apenas essa informação; este formato é menos preciso para tipos complexos."
    ),
}

# ---------------------------------------------------------------------------
# Questions Q0–Q10 (Layer 0, 1, 2)
# ---------------------------------------------------------------------------

QUESTION_DEFS: Dict[str, Dict[str, Any]] = {
    # ── Layer 0: math_control (arithmetic only, no data format) ─────────────
    "math_control_sum": {
        "layer":     "math_control",
        "key":       "sum_vl",  # ground-truth key
        "template":  "Some estes valores: {vl_list}",
    },
    "math_control_count": {
        "layer":     "math_control",
        "key":       "count",
        "template":  "Quantos números há nesta lista: {vl_list}?",
    },

    # ── Layer 1: decode_only (format comprehension, no math) ────────────────
    "decode_vl": {
        "layer":           "decode_only",
        "key":             "vl_values",
        "template":        "Liste TODOS os valores da coluna 'vl', separados por espaço. Apenas os números, sem explicação.",
        "required_params": set(),  # no params
    },

    # ── Layer 2: compute (full pipeline: format + operation) ────────────────

    # Aggregates on vl (no FK needed)
    "q1_sum_vl": {
        "layer":           "compute",
        "key":             "sum_vl",
        "template":        "Qual é a soma de todos os valores de 'vl'? Responda apenas com um número.",
        "required_params": set(),
    },
    "q2_avg_vl": {
        "layer":           "compute",
        "key":             "avg_vl",
        "template":        "Qual é a média de 'vl'? Responda apenas com um número (use ponto como separador decimal).",
        "required_params": set(),
    },
    "q3_max_vl": {
        "layer":           "compute",
        "key":             "max_vl",
        "template":        "Qual é o maior valor de 'vl'? Responda apenas com um número.",
        "required_params": set(),
    },
    "q4_min_vl": {
        "layer":           "compute",
        "key":             "min_vl",
        "template":        "Qual é o menor valor de 'vl'? Responda apenas com um número.",
        "required_params": set(),
    },
    "q5_count_rows": {
        "layer":           "compute",
        "key":             "count",
        "template":        "Quantas linhas existem no conjunto de dados? Responda com um número inteiro.",
        "required_params": set(),
    },

    # FK-dependent queries (person name — asks about Ana specifically)
    "q6_count_by_pessoa": {
        "layer":           "compute",
        "key":             "count_ana",   # scalar: count_by_pessoa["Ana"]
        "template":        "Quantas vendas Ana fez? Responda apenas com um número inteiro.",
        "required_params": set(),
    },
    "q7_sum_by_pessoa": {
        "layer":           "compute",
        "key":             "sum_ana",     # scalar: sum_by_pessoa["Ana"]
        "template":        "Qual foi o total gasto por Ana? Responda apenas com um número.",
        "required_params": set(),
    },

    # Frequency/distribution
    "q8_top_product": {
        "layer":           "compute",
        "key":             "top_product_name",
        "template":        "Qual produto aparece mais vezes nas vendas? Responda com o nome do produto.",
        "required_params": set(),
    },

    # Distinct count
    "q9_count_distinct_pessoa": {
        "layer":           "compute",
        "key":             "count_distinct_pessoa",
        "template":        "Quantas pessoas distintas compraram algo? Responda com um número inteiro.",
        "required_params": set(),
    },

    # Argmax aggregation
    "q10_top_spender": {
        "layer":           "compute",
        "key":             "top_spender_name",
        "template":        "Qual pessoa gastou o maior total? Responda com o nome da pessoa.",
        "required_params": set(),
    },
}

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_system_prompt(format_name: str) -> str:
    """Get the system prompt for a given format."""
    return SYSTEM_PROMPTS.get(format_name, DEFAULT_SYSTEM_PROMPT)


def list_questions() -> Dict[str, Dict[str, Any]]:
    """Return all question definitions."""
    return QUESTION_DEFS


def list_questions_by_layer(layer: str) -> Dict[str, Dict[str, Any]]:
    """Return questions filtered by diagnostic layer."""
    return {k: v for k, v in QUESTION_DEFS.items() if v.get("layer") == layer}


def build_question(question_name: str, **params: Any) -> str:
    """Build the actual question text from a template.

    Args:
        question_name: Key in QUESTION_DEFS
        **params: Template parameters (e.g., field='vl', vl_list='2.5 11.0 ...')

    Returns:
        The fully formatted question string
    """
    if question_name not in QUESTION_DEFS:
        raise ValueError(f"Pergunta desconhecida: {question_name!r}")
    qdef = QUESTION_DEFS[question_name]
    required = qdef.get("required_params", set())
    missing = [name for name in required if name not in params]
    if missing:
        raise ValueError(f"Pergunta '{question_name}' exige parâmetros: {missing}")
    template = qdef["template"]
    return template.format(**params)


def build_prompt(
    format_name: str,
    data_block: str,
    question_name: str,
    **question_params: Any,
) -> str:
    """Build a complete prompt: system + context + question.

    Args:
        format_name: One of "math_control", "tcf", "csv", "jsonl", etc.
        data_block: The formatted data (TCF text, CSV string, etc.)
        question_name: Key in QUESTION_DEFS
        **question_params: Parameters for the question template

    Returns:
        A complete prompt string ready to send to the LLM
    """
    system_prompt = get_system_prompt(format_name)
    question = build_question(question_name, **question_params)
    context = data_block.strip()

    if format_name == "math_control":
        # No data context for math_control — just system + question
        return (
            f"<s>SYSTEM> {system_prompt}</s>\n"
            f"<s>USER> {question}</s>\n"
            "<s>ASSISTANT>"
        )
    else:
        # Full structure: system + data context + question
        return (
            f"<s>SYSTEM> {system_prompt}</s>\n"
            f"<s>CONTEXT>\n{context}\n</s>\n"
            f"<s>USER> {question}</s>\n"
            "<s>ASSISTANT>"
        )


# ── Deprecated/legacy functions (kept for compatibility) ──────────────────

def build_question_legacy(question_name: str, **params: Any) -> str:
    """Deprecated. Use build_question() instead."""
    return build_question(question_name, **params)
