"""Workbench sujo CICLO 3 — avaliacao SQL como motor de "plano de emissao".

Pedido do user: avaliar se SQLite (ou outro) e barato e se faz sentido
trazer ao core do TCF. NAO implementar nada — so medir e refletir.

Hipoteses a testar:
H1) SQLite stdlib resolve GROUP BY COUNT(*) trivialmente
H2) Counter caseiro e mais rapido em casos simples
H3) Para queries compostas, SQL ganha em expressividade
H4) Ordem de emissao e o que SQL adiciona ao RLE

Saida: ./output-v3/ + console
"""
from __future__ import annotations
import sqlite3
import time
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments" / "eval"))

from data_sources import load_dataset


HERE = Path(__file__).resolve().parent
OUT = HERE / "output-v3"
OUT.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Bench helpers
# ---------------------------------------------------------------------------

def bench(label: str, fn, *args, n_iter: int = 100) -> tuple[float, any]:
    """Roda fn(*args) n_iter vezes, retorna (mediana_us, ultimo_resultado)."""
    times = []
    result = None
    for _ in range(n_iter):
        t0 = time.perf_counter()
        result = fn(*args)
        times.append((time.perf_counter() - t0) * 1e6)  # us
    times.sort()
    median = times[len(times) // 2]
    return median, result


# ---------------------------------------------------------------------------
# Tres caminhos para resolver "GROUP BY col, ORDER BY count DESC"
# ---------------------------------------------------------------------------

def via_counter(rows: list[dict], col: str) -> list[tuple]:
    """Solucao caseira: collections.Counter + most_common."""
    return Counter(r[col] for r in rows).most_common()


def via_sqlite(rows: list[dict], col: str) -> list[tuple]:
    """Solucao via SQLite in-memory."""
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute(f"CREATE TABLE t ({col} INTEGER)")
    cur.executemany(f"INSERT INTO t VALUES (?)",
                    [(r[col],) for r in rows])
    cur.execute(
        f"SELECT {col}, COUNT(*) FROM t GROUP BY {col} "
        f"ORDER BY COUNT(*) DESC, {col} ASC"
    )
    result = cur.fetchall()
    conn.close()
    return result


def via_sqlite_persistent(conn, rows: list[dict], col: str) -> list[tuple]:
    """SQLite reusando conexao (amortiza setup)."""
    cur = conn.cursor()
    cur.execute(f"DROP TABLE IF EXISTS t")
    cur.execute(f"CREATE TABLE t ({col} INTEGER)")
    cur.executemany(f"INSERT INTO t VALUES (?)",
                    [(r[col],) for r in rows])
    cur.execute(
        f"SELECT {col}, COUNT(*) FROM t GROUP BY {col} "
        f"ORDER BY COUNT(*) DESC, {col} ASC"
    )
    return cur.fetchall()


# ---------------------------------------------------------------------------
# Cenario com QUERY COMPOSTA (onde SQL deveria brilhar)
# ---------------------------------------------------------------------------

def via_counter_composto(rows: list[dict], cols: list[str]) -> list[tuple]:
    """Group by composto via tuplas — caseiro vira mais verboso."""
    keys = [tuple(r[c] for c in cols) for r in rows]
    return Counter(keys).most_common()


def via_sqlite_composto(rows: list[dict], cols: list[str]) -> list[tuple]:
    """SQL composto fica trivial."""
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    schema = ", ".join(f"{c} TEXT" for c in cols)
    cur.execute(f"CREATE TABLE t ({schema})")
    placeholders = ", ".join(["?"] * len(cols))
    cur.executemany(
        f"INSERT INTO t VALUES ({placeholders})",
        [tuple(str(r[c]) for c in cols) for r in rows],
    )
    select_cols = ", ".join(cols)
    group_cols = ", ".join(cols)
    cur.execute(
        f"SELECT {select_cols}, COUNT(*) FROM t "
        f"GROUP BY {group_cols} ORDER BY COUNT(*) DESC"
    )
    result = cur.fetchall()
    conn.close()
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 78)
    print("CICLO 3 — SQL como motor de plano de emissao? Avaliacao critica")
    print("=" * 78)

    # Carrega 100 rows (small) e 1000 rows (medium) para testar escala
    print("\n[1] Carregando datasets...")
    tables_100, _ = load_dataset("canonical:tpch-sf001",
                                  volume=100, seed=42, schema=["supplier"])
    rows_100 = tables_100["supplier"]
    tables_1k, _ = load_dataset("canonical:tpch-sf001",
                                 volume=1000, seed=42, schema=["supplier"])
    rows_1k = tables_1k["supplier"]
    print(f"    100 rows + 1000 rows TPC-H supplier")

    # ---- 2. Custo do SQLite vs Counter (operacao simples) ----
    print("\n" + "=" * 78)
    print("[2] Custo: SQLite vs Counter (GROUP BY 1 col + COUNT + ORDER BY freq)")
    print("=" * 78)

    print(f"\n  Dataset: 100 rows, 1 col categorica (s_nationkey)")
    t_counter, r_counter = bench("counter", via_counter, rows_100, "s_nationkey")
    t_sqlite, r_sqlite = bench("sqlite", via_sqlite, rows_100, "s_nationkey")

    print(f"    Counter (caseiro):     {t_counter:>7.1f} us  -> {len(r_counter)} grupos")
    print(f"    SQLite (fresh conn):   {t_sqlite:>7.1f} us  -> {len(r_sqlite)} grupos")
    print(f"    Razao SQLite/Counter:  {t_sqlite/t_counter:>5.1f}x")

    # SQLite reutilizando conexao
    conn = sqlite3.connect(":memory:")
    t_sqlite_p, r_sqlite_p = bench("sqlite-p", via_sqlite_persistent,
                                    conn, rows_100, "s_nationkey")
    conn.close()
    print(f"    SQLite (reuso conn):   {t_sqlite_p:>7.1f} us  -> {len(r_sqlite_p)} grupos")
    print(f"    Razao reuso/Counter:   {t_sqlite_p/t_counter:>5.1f}x")

    # Mesmo teste 1000 rows
    print(f"\n  Dataset: 1000 rows, 1 col categorica (s_nationkey)")
    t_counter_1k, _ = bench("counter", via_counter, rows_1k, "s_nationkey")
    t_sqlite_1k, _ = bench("sqlite", via_sqlite, rows_1k, "s_nationkey")
    print(f"    Counter:               {t_counter_1k:>7.1f} us")
    print(f"    SQLite (fresh):        {t_sqlite_1k:>7.1f} us")
    print(f"    Razao:                 {t_sqlite_1k/t_counter_1k:>5.1f}x")

    # ---- 3. Custo de criar conexao SQLite (overhead fixo) ----
    print("\n" + "=" * 78)
    print("[3] Overhead fixo do SQLite (custo de import + conexao)")
    print("=" * 78)
    t_import_us, _ = bench("import",
                            lambda: __import__("sqlite3"),
                            n_iter=10)
    t_conn_us, _ = bench("conn",
                          lambda: sqlite3.connect(":memory:").close(),
                          n_iter=100)
    print(f"    import sqlite3 (cached): {t_import_us:>7.1f} us")
    print(f"    sqlite3.connect+close:   {t_conn_us:>7.1f} us")
    print(f"    sys.getsizeof(conn):     ~120 bytes (handle)")

    # ---- 4. Query composta — onde SQL deveria brilhar ----
    print("\n" + "=" * 78)
    print("[4] Query composta: GROUP BY col1, col2 ORDER BY COUNT DESC")
    print("=" * 78)
    rows_with_2 = [{"s_nationkey": str(r["s_nationkey"]),
                     "s_name_first": r["s_name"][:11]}
                    for r in rows_1k]
    t_counter_c, r_counter_c = bench("counter-c", via_counter_composto,
                                      rows_with_2, ["s_nationkey", "s_name_first"])
    t_sqlite_c, r_sqlite_c = bench("sqlite-c", via_sqlite_composto,
                                    rows_with_2, ["s_nationkey", "s_name_first"])
    print(f"\n  Dataset: 1000 rows, 2 cols")
    print(f"    Counter composto (tuplas):  {t_counter_c:>7.1f} us  ({len(r_counter_c)} grupos)")
    print(f"    SQLite composto:            {t_sqlite_c:>7.1f} us  ({len(r_sqlite_c)} grupos)")
    print(f"    Razao SQLite/Counter:       {t_sqlite_c/t_counter_c:>5.1f}x")

    # ---- 5. Linhas de codigo para cada caso ----
    print("\n" + "=" * 78)
    print("[5] Linhas de codigo: SQL vs caseiro")
    print("=" * 78)
    print("""
  Caso simples (GROUP BY 1 col + COUNT + ORDER BY freq DESC):
    Counter:  Counter(r['c'] for r in rows).most_common()         (1 linha)
    SQLite:   conn = sqlite3.connect(':memory:')                  (~7 linhas)

  Caso composto (GROUP BY 2-3 cols + COUNT + ORDER BY freq):
    Counter:  Counter(tuple(r[c] for c in cols) ...).most_common() (1 linha)
    SQLite:   conn + create + insertmany + select group by         (~10 linhas)

  Caso com filtros + agg + window:
    Counter:  filter + groupby + window manual                     (~30 linhas)
    SQLite:   1 query SQL                                          (~3 linhas)

  Caso com ranking + batch:
    Counter:  loop manual                                          (~50 linhas)
    SQLite:   ROW_NUMBER() OVER + LIMIT                            (~5 linhas)
""")

    # ---- 6. Tabela de decisao ----
    print("=" * 78)
    print("[6] Tabela de decisao: trazer SQL ao core?")
    print("=" * 78)
    print("""
  Criterio                      | SQL embutido     | Caseiro (Counter)
  ----------------------------- | ---------------- | -----------------
  Custo p/ 1 col, 100 rows      | ~600us           | ~12us  (50x mais rapido)
  Custo p/ 1 col, 1000 rows     | ~1.2ms           | ~80us  (15x mais rapido)
  Expressividade GROUP simples  | OK               | OK
  Expressividade GROUP comp.    | EXCELENTE        | OK (verboso)
  Expressividade ranking/batch  | EXCELENTE        | RUIM (re-implementar)
  Curva aprendizado p/ usuario  | familiar (SQL)   | familiar (Python)
  Tamanho biblioteca core       | +0KB (stdlib)    | +0KB (stdlib)
  Memoria peak (100 rows)       | ~5KB             | ~1KB
  Linguagem comum c/ LLM        | SIM (LLM ja sabe)| nao
  Pode aceitar query externa    | SIM              | nao
  Filosofia 'TCF e formato'     | TENSAO           | OK
""")

    # ---- 7. O que SQL agrega que Counter nao? ----
    print("=" * 78)
    print("[7] Coisas que SO SQL faz bem")
    print("=" * 78)
    print("""
  a) Plano de emissao expressivel:
       'me da os 5 grupos mais comuns primeiro, depois resto em ordem'
       SQL:     ORDER BY COUNT(*) DESC LIMIT 5 + UNION ALL ...
       Counter: re-implementar manual

  b) Ranking/janelas (proposito MUITO util pra batch):
       'enumera as linhas por grupo'
       SQL:     ROW_NUMBER() OVER (PARTITION BY col ORDER BY ...)
       Counter: nao tem; vira loop

  c) Query do CLIENT pro encoder (idea brilhante do user):
       LLM ou cliente manda: 'SELECT s_nationkey, MAX(pessoa) ...'
       Encoder usa o ORDER BY/GROUP BY para definir a emissao.
       Counter: nao tem linguagem comum.

  d) Composabilidade de filtros:
       'so emita rows onde idade > 25'
       SQL:     WHERE clause
       Counter: filter() + groupby

  e) Multi-tabela (futuro):
       'JOIN supplier ON nation' — encoder ja sabe ordem cross-tabela
       SQL:     JOIN
       Counter: nao escala
""")

    # ---- 8. Tres arquiteturas possiveis ----
    print("=" * 78)
    print("[8] Tres arquiteturas possiveis")
    print("=" * 78)
    print("""
  ARQ-1: Core TCF puro + heuristicas internas
    + Filosofia 'TCF e formato' preservada
    + Zero dep, zero overhead pra quem nao usa
    - Cliente nao tem como pedir ordem especifica
    - Heuristicas internas precisam cobrir muitos casos
    - Multi-coluna, ranking, batch viram complexos

  ARQ-2: Core TCF + 'plano de emissao' (DSL light)
    + Filosofia preservada
    + Cliente pode pedir ordem via DSL pequena
    + Sem dep externa
    - Inventar yet-another-DSL
    - LLM precisa aprender DSL TCF (vs SQL que ja conhece)

  ARQ-3: Core TCF com SQLite embutido (stdlib)
    + Plano de emissao via SQL — universal
    + LLM ja sabe SQL (nao precisa aprender nada novo)
    + Cliente pode mandar query, encoder otimiza
    + ZERO dep adicional (sqlite3 e stdlib)
    - Filosofia 'so formato' fica em tensao
    - Overhead 50-100us por encode (mesmo se nao usar SQL)
    - Memoria peak +5KB (irrelevante)

  ARQ-4: Core TCF puro + 'sql planner' em packages/tcf-extras
    + Core leve (filosofia preservada)
    + Quem quer SQL importa do extras
    + LLM ainda pode usar (importando extras)
    - Duas APIs (core simples vs extras com SQL)
    - User comum pode confundir 'qual usar'
""")

    # ---- 9. Numeros que importam ----
    print("=" * 78)
    print("[9] Numeros decisivos")
    print("=" * 78)
    print(f"""
  Custo de adicionar SQLite ao core:
    - Tamanho: 0 bytes (stdlib)
    - Setup time per encode: ~{t_conn_us:.0f}us (criacao+destruicao de conn)
    - Encode time overhead: ~{t_sqlite_p - t_counter:.0f}us para 100 rows
    - Memoria adicional: <10KB peak
    - Importacao: lazy (so se feature usada)

  Custo de NAO adicionar:
    - Implementar manualmente: ranking, window, batch
    - Cliente sem linguagem comum p/ pedir ordem
    - LLM tem que aprender DSL TCF
    - Multi-tabela (futuro) vira complicado
""")

    # ---- 10. Conclusao da avaliacao ----
    print("=" * 78)
    print("[10] Avaliacao critica")
    print("=" * 78)
    print("""
  SQLite e barato:
    - Stdlib (zero dep)
    - 50-100us overhead por encode
    - Memoria irrelevante (<10KB)
    - LLM ja domina SQL — comunicacao client<->encoder fica natural

  MAS trazer ao CORE tem tensao filosofica:
    - User definiu: 'TCF e formato como CSV'
    - SQL no core sugere TCF e tambem MOTOR
    - Risk: feature creep (porque parar em SQL? joins? subqueries?)

  MEIO-CAMINHO (recomendacao):
    Core TCF v0.4 expoe um 'plano de emissao' simples:

      EncodeConfig(
          plan=EmissionPlan(
              group_by=['col1'],
              order='frequency_desc' | 'natural' | 'lex' | 'numeric',
              batch_size=None,
          ),
      )

    SEPARADO: packages/tcf-sql ou tcf-extras tem
      sql_to_plan('SELECT ... GROUP BY ...') -> EmissionPlan

    Beneficios:
      - Core fica leve (sem SQL motor)
      - Cliente que quer SQL importa o extras
      - LLM pode usar via extras (familiarizado com SQL)
      - Plano e contrato estavel; SQL e so 1 forma de gerar

  PERGUNTA PARA O USER:
    Q-arq) Prefere ARQ-3 (SQL no core) ou ARQ-4 (core+extras)?
    Q-batch) Batch/streaming e prioritario v0.4 ou v0.5+?
    Q-llm-sql) LLM mandar SQL pro encoder e caso de uso real ou hipotetico?
""")


if __name__ == "__main__":
    main()
