"""Workbench sujo CICLO 2 — analise profunda de categoricos.

Foco do user: NAO alterar core. Refletir sobre:
1. Tipos — int como NUMERO vs CATEGORIA (s_nationkey e int mas e ID)
2. Ordenacao — sort vs group; RLE precisa de QUAL?
3. Determinismo — sort lex em int e bug; numeric corrige
4. Ambiguidade no header — `sorted_by=` mente quando e so grouped

NAO mexe no encoder TCF; apenas demonstra com calculos paralelos.

Saida: ./output-v2/
"""
from __future__ import annotations
import sys
from pathlib import Path
from collections import Counter, OrderedDict

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments" / "eval"))

from tcf import encode_rows, EncodeConfig
from data_sources import load_dataset


HERE = Path(__file__).resolve().parent
OUT = HERE / "output-v2"
OUT.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Helpers para experimentar varias estrategias de ordenacao
# ---------------------------------------------------------------------------

def is_int_str(s: str) -> bool:
    """Heuristica: '0', '24', '-3' sao ints. '0.5' nao."""
    s = s.strip()
    if not s:
        return False
    if s[0] in ("-", "+"):
        s = s[1:]
    return s.isdigit()


def detect_column_type(values: list) -> str:
    """Detecta tipo da coluna olhando valores.

    Retorna: 'int' | 'float' | 'str'
    """
    samples = [v for v in values if v is not None]
    if not samples:
        return "str"
    # Ja chega tipado?
    if all(isinstance(v, bool) for v in samples):
        return "bool"
    if all(isinstance(v, int) for v in samples):
        return "int"
    if all(isinstance(v, (int, float)) for v in samples):
        return "float"
    # Como string — tenta parsear
    str_samples = [str(v) for v in samples]
    if all(is_int_str(s) for s in str_samples):
        return "int"
    return "str"


def categorize_column(values: list, col_type: str) -> str:
    """Decide se coluna e CATEGORICA, NUMERICA ou TEXTO.

    Heuristicas:
    - cardinality / n < 0.3 e cardinality <= 50 -> categorica
    - tipo numerico mas categorica -> 'cat-numeric' (caso ambiguo!)
    - alta cardinalidade -> numeric (se int/float) ou text (se str)
    """
    n = len(values)
    cardinality = len(set(values))
    ratio = cardinality / n if n else 0

    is_low_card = ratio < 0.3 and cardinality <= 50

    if is_low_card:
        if col_type in ("int", "float"):
            return "cat-numeric"  # ambiguo — pode ser ID ou medicao
        return "cat-string"
    if col_type in ("int", "float"):
        return "numeric"
    return "text"


def sort_lex(values: list) -> list:
    """Sort string-style (atual TCF v0.2 — bug em ints)."""
    return sorted(values, key=lambda v: str(v))


def sort_numeric_aware(values: list, col_type: str) -> list:
    """Sort com tipo: int/float -> numeric; str -> lex."""
    if col_type in ("int", "float"):
        return sorted(values, key=lambda v: (float(v) if v is not None else float("inf")))
    return sorted(values, key=lambda v: str(v))


def sort_by_frequency(values: list) -> list:
    """Ordena por frequencia decrescente (mais frequente primeiro).

    Tie-break: ordem de primeira aparicao.
    """
    counts = Counter(values)
    first_seen = OrderedDict()
    for v in values:
        if v not in first_seen:
            first_seen[v] = len(first_seen)
    keys = sorted(counts.keys(), key=lambda k: (-counts[k], first_seen[k]))
    out = []
    for k in keys:
        out.extend([k] * counts[k])
    return out


def group_preserving_input_order(values: list) -> list:
    """Agrupa iguais sem ordenar — preserva ordem da PRIMEIRA aparicao.

    Ex: [B, A, B, A, C] -> [B, B, A, A, C]
    """
    first_seen = OrderedDict()
    buckets: dict = {}
    for v in values:
        if v not in first_seen:
            first_seen[v] = len(first_seen)
            buckets[v] = []
        buckets[v].append(v)
    out = []
    for k in first_seen:
        out.extend(buckets[k])
    return out


# ---------------------------------------------------------------------------
# RLE simulator — conta bytes finais
# ---------------------------------------------------------------------------

def rle_encode(values: list) -> list[str]:
    """Encoda em formato N*val (igual TCF L2)."""
    if not values:
        return []
    out = []
    cur = values[0]
    cnt = 1
    for v in values[1:]:
        if v == cur:
            cnt += 1
        else:
            out.append(f"{cnt}*{cur}" if cnt > 1 else str(cur))
            cur, cnt = v, 1
    out.append(f"{cnt}*{cur}" if cnt > 1 else str(cur))
    return out


def rle_byte_size(values: list) -> int:
    """Tamanho em bytes do payload RLE (so values, sem header)."""
    lines = rle_encode(values)
    return len("\n".join(lines).encode("utf-8"))


def rle_run_count(values: list) -> int:
    """Quantos runs (segmentos contiguos iguais) — proxy de qualidade RLE."""
    return len(rle_encode(values))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 76)
    print("CICLO 2 — analise profunda de categoricos (so coluna nationkey)")
    print("=" * 76)

    # Dados
    print("\n[1] Carregando TPC-H supplier (volume=100)...")
    tables, _ = load_dataset("canonical:tpch-sf001",
                              volume=100, seed=42, schema=["supplier"])
    nk = [s["s_nationkey"] for s in tables.get("supplier", [])]
    print(f"    {len(nk)} valores; tipo Python: {type(nk[0]).__name__}")
    print(f"    Distinct: {len(set(nk))} valores -> {sorted(set(nk))}")

    # ---- 2. Deteccao de tipo + classificacao ----
    print("\n" + "=" * 76)
    print("[2] Deteccao automatica de tipo e classificacao")
    print("=" * 76)
    col_type = detect_column_type(nk)
    col_class = categorize_column(nk, col_type)
    print(f"  type detected:  {col_type}")
    print(f"  classification: {col_class}")
    print()
    print("  Interpretacao:")
    print("    - type='int' -> Python ja entrega como int")
    print("    - class='cat-numeric' -> AMBIGUO: pode ser categoria ID")
    print("      ou pode ser numero real com low cardinality (ex: idade 0-24)")
    print()
    print("  Sinais que pendem para CATEGORIA (ID):")
    print("    - cardinality alta concentrada em valores pequenos: 0,1,...,24")
    print("    - sem 'gaps' obvios entre minimo/maximo")
    print("    - nome da coluna: 'nationkey' tem 'key' no nome")
    print()
    print("  Sinais que pendem para NUMERO real (medicao):")
    print("    - distribuicao continua (avg ~ media de pop)")
    print("    - faz sentido somar/multiplicar")
    print()
    print("  CONCLUSAO: a heuristica nao consegue distinguir sozinha.")
    print("  Decisao: oferecer FLAG opt-in. Default: trata como tipo nativo.")

    # ---- 3. Tres estrategias de ordenacao ----
    print("\n" + "=" * 76)
    print("[3] Tres estrategias de organizar valores antes do RLE")
    print("=" * 76)
    strategies = {
        "A-sort-lex (TCF v0.2 atual)":
            sort_lex(nk),
        "B-sort-numeric (proposta v0.4)":
            sort_numeric_aware(nk, col_type),
        "C-sort-by-freq (categorica pura)":
            sort_by_frequency(nk),
        "D-group-only (preserva ordem original)":
            group_preserving_input_order(nk),
        "E-natural (sem reordenar)":
            list(nk),
    }

    print(f"  {'estrategia':<42} {'runs':>5} {'bytes':>6}")
    print(f"  {'-'*42} {'-'*5} {'-'*6}")
    for name, vals in strategies.items():
        runs = rle_run_count(vals)
        bytes_ = rle_byte_size(vals)
        print(f"  {name:<42} {runs:>5} {bytes_:>6}")

    print()
    print("  Observacoes:")
    print("    A: sort lex em int gera ordem confusa (0,1,10,..,19,2,20,..)")
    print("       MAS RLE comprime igual — agrupamento e o que importa.")
    print("    B: sort numerico arruma a ordem visual. RLE = mesmo resultado.")
    print("    C: sort por frequencia poe os MAIS comuns no inicio.")
    print("       Util se LLM le 'top-k' primeiro. RLE pode = igual.")
    print("    D: grouped sem sort — preserva 'qual aparece antes'.")
    print("       Util quando ordem original e SEMANTICA (ex: timestamp).")
    print("    E: natural sem reordenar — RLE quase nao comprime.")

    # ---- 4. Sort vs Group — sao a MESMA coisa para RLE? ----
    print("\n" + "=" * 76)
    print("[4] Sort vs Group — qual e necessario para RLE?")
    print("=" * 76)
    runs_lex = rle_run_count(strategies["A-sort-lex (TCF v0.2 atual)"])
    runs_num = rle_run_count(strategies["B-sort-numeric (proposta v0.4)"])
    runs_freq = rle_run_count(strategies["C-sort-by-freq (categorica pura)"])
    runs_group = rle_run_count(strategies["D-group-only (preserva ordem original)"])
    runs_nat = rle_run_count(strategies["E-natural (sem reordenar)"])

    print(f"  runs (RLE comprime contiguos):")
    print(f"    sort-lex:    {runs_lex}")
    print(f"    sort-num:    {runs_num}")
    print(f"    sort-freq:   {runs_freq}")
    print(f"    group-only:  {runs_group}")
    print(f"    natural:     {runs_nat}")
    print()
    print("  Insight do user: 'RLE e orientado por ordenacao mas tem")
    print("  caracteristicas de agrupamento'.")
    print()
    print("  Provando: sort-lex, sort-num, sort-freq, group-only TODOS")
    if runs_lex == runs_num == runs_freq == runs_group:
        print(f"  produzem {runs_lex} runs (mesma compressao).")
    else:
        print(f"  produzem RUNS DIFERENTES: lex={runs_lex} num={runs_num} "
              f"freq={runs_freq} group={runs_group}")
    print()
    print("  CONCLUSAO: para RLE, GROUPED e suficiente.")
    print("  SORT e GROUPED + ordem total — info A MAIS do que RLE precisa.")
    print()
    print("  Quando vale SORT (ordem total)?")
    print("    - STATS condicionados (binary search por valor)")
    print("    - Diff/idempotencia entre versoes")
    print("    - LLM le 'em ordem' (mas LLM nao precisa — so se prompt pedir)")
    print()
    print("  Quando vale GROUPED apenas?")
    print("    - Manter 'ordem de aparicao' como informacao semantica")
    print("    - Streams/lotes — ordem original importa")
    print("    - Time series com categoricas — manter time-locality")

    # ---- 5. Header v0.4 — vocabulario sem ambiguidade ----
    print("\n" + "=" * 76)
    print("[5] Header v0.4 — vocabulario para nao mentir")
    print("=" * 76)
    print()
    print("  Problema atual:")
    print("    `## supplier n=100 sorted_by=s_nationkey`")
    print()
    print("    Mas o sort e LEXICOGRAFICO (\"10\" < \"2\"), nao numeric.")
    print("    E RLE so precisava de grouped — sort total e overkill.")
    print()
    print("  Proposta v0.4: separar dimensoes ortogonais")
    print()
    print("    grouped_by   = TRUE/FALSE (RLE precisa disso)")
    print("    sorted_by    = TRUE/FALSE (info adicional, opcional)")
    print("    sort_kind    = lex|numeric|frequency|input (so se sorted=true)")
    print("    type-hint    = int|float|str|categorical|datetime|...")
    print()
    print("  Variantes possiveis para o header:")
    print()
    print("    v0.4-A  (verboso, autoexplicativo):")
    print("      ## supplier n=100")
    print("      # col s_nationkey: type=int role=categorical")
    print("      #   layout=grouped+sorted sort=numeric")
    print()
    print("    v0.4-B  (compacto, decoder ainda parseia):")
    print("      ## supplier n=100")
    print("      s_nationkey:int:cat:gs/n:")
    print("      3*0\\n3*1\\n2*2\\n...")
    print()
    print("    v0.4-C  (minimalista — assume default 'grouped')")
    print("      ## supplier n=100 grouped=s_nationkey")
    print("      # se faltar 'grouped=', decoder assume natural order")
    print()
    print("  Comparativo de bytes do header (so 1 col simples):")
    samples = [
        ("v0.2 (sorted_by=)",
         "## supplier n=100 sorted_by=s_nationkey"),
        ("v0.4-A (verboso)",
         "## supplier n=100\n# col s_nationkey: type=int role=cat layout=gs sort=num"),
        ("v0.4-B (compacto)",
         "## supplier n=100\ns_nationkey:int:cat:gs/n:"),
        ("v0.4-C (minimal)",
         "## supplier n=100 grouped=s_nationkey"),
    ]
    for label, txt in samples:
        nb = len(txt.encode("utf-8"))
        print(f"    {label:<30} {nb:>3}B")

    # ---- 6. Determinismo + tipo: o que o decoder ganha sabendo? ----
    print("\n" + "=" * 76)
    print("[6] O que o DECODER ganha sabendo o tipo/categoria?")
    print("=" * 76)
    print()
    print("  Sem informacao de tipo (v0.2 atual):")
    print("    - decoder retorna str ('0', '1', '10', ...)")
    print("    - usuario precisa converter manualmente")
    print("    - STATS no header sugerem int (sum/avg) mas valores sao str")
    print()
    print("  Com type=int + role=categorical (v0.4 proposta):")
    print("    - decoder retorna int (0, 1, 10)")
    print("    - role='categorical' avisa: NAO faca arithmetic")
    print("    - STATS pode ser opcional (avg de IDs nao faz sentido)")
    print()
    print("  Com type=int + role=numeric (v0.4 proposta):")
    print("    - decoder retorna int")
    print("    - role='numeric' avisa: pode somar/agregar")
    print("    - STATS faz sentido (avg=42.43 para hours-per-week)")
    print()
    print("  Esta separacao type vs role resolve a ambiguidade do nationkey.")

    # ---- 7. Demonstracao concreta — escreve 5 arquivos com diferentes ordens ----
    print("\n" + "=" * 76)
    print("[7] Demonstracao: 5 arquivos com diferentes ordenacoes")
    print("=" * 76)
    files_written = []
    for name, vals in strategies.items():
        slug = name.split(" ")[0].lower()
        # Gera saida no formato '# TCF v0.4 lv=2 + RLE'
        body = "\n".join(rle_encode(vals))
        text = (
            f"# TCF v0.4-lab lv=2\n"
            f"# layout-experiment: {name}\n"
            f"## supplier n={len(vals)}\n"
            f"# col s_nationkey: type=int role=categorical layout=grouped\n"
            f"s_nationkey:\n"
            f"{body}\n"
        )
        path = OUT / f"{slug}.tcf"
        path.write_bytes(text.encode("utf-8"))
        files_written.append((name, path, len(text.encode("utf-8"))))

    for name, path, nb in files_written:
        print(f"  {name:<42} -> {path.name} ({nb}B)")

    print()
    print(f"[OK] Inspecione visualmente em: {OUT}")

    # ---- 8. Reflexao final + decisoes pendentes ----
    print("\n" + "=" * 76)
    print("[8] Decisoes pendentes para v0.4 (anotar em ticket)")
    print("=" * 76)
    print()
    print("  Q1) sorted_by ou grouped_by no header?")
    print("      -> grouped_by e tecnicamente mais correto para RLE.")
    print("      -> sorted_by e info adicional, so se realmente sortou.")
    print()
    print("  Q2) Sort lex vs sort numeric?")
    print("      -> Detectar tipo e usar sort apropriado.")
    print("      -> Default: tipo nativo.")
    print()
    print("  Q3) Tipo: auto-detect, flag explicita ou ambos?")
    print("      -> Detectar tipo basico (int/float/str) eh facil e seguro.")
    print("      -> Distinguir categorical vs numeric e AMBIGUO -> flag.")
    print("      -> API proposta:")
    print("           EncodeConfig(")
    print("             auto_detect_types=True,")
    print("             column_roles={'s_nationkey': 'categorical'},")
    print("           )")
    print()
    print("  Q4) STATS para categoricas?")
    print("      -> avg/sum/min/max nao fazem sentido em IDs.")
    print("      -> count + cardinality + top-k mais frequentes fazem.")
    print()
    print("  Q5) Preservar ordem do input (group-only) vs forcar sort?")
    print("      -> Default v0.2: forcou sort (perde ordem).")
    print("      -> v0.4 deveria ter flag preserve_input_order.")


if __name__ == "__main__":
    main()
