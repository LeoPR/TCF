"""run.py — motor spec_bin: escape (domínio do dado) + RLE-vs-bitstream + overlay de exceções.

(1) domínio aproveita afixo (male→female='fe1').
(2) RLE vs bitstream vs textbits em distribuições (ordenado/bloco/alternado/aleatório/skew) → crossover.
(3) overlay de exceções: 99% male/female + null/other → RT + bytes.
(4) colunas REAIS (adult.sex, matriz_filial) → motor escolhe na ordem real.
(5) 'manter a quebra': RLE é explicável (grupos visíveis); bitstream é opaco → preferir RLE quando perto.

`python run.py` regenera artifacts/. Dados: Z:/tcf-data/interim/*.db. Não toca src/tcf.
"""
from __future__ import annotations
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(_ROOT / "src"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
import bin_engine as E                                 # noqa: E402

ART = HERE / "artifacts"
ART.mkdir(exist_ok=True)
INTERIM = Path("Z:/tcf-data/interim")


def w(name, text): (ART / name).write_text(text, encoding="utf-8", newline="\n")


# ---- distribuições sintéticas (o dado real depois; aqui o motor) ----
def dists(n, v0="A", v1="B"):
    return {
        "ordenado (2 runs)": [v0] * (n // 2) + [v1] * (n - n // 2),
        "bloco-10": [v0 if (i // 10) % 2 == 0 else v1 for i in range(n)],
        "alternado (pior RLE)": [v0 if i % 2 == 0 else v1 for i in range(n)],
        "pseudo-aleatorio": [v0 if (i * 1103515245 + 12345) % 2 == 0 else v1 for i in range(n)],
        "skew 99/1": [v1 if i % 100 == 50 else v0 for i in range(n)],
    }


def thread_dists(n=1000):
    L = [f"# MOTOR — RLE vs bitstream vs textbits por distribuição (N={n}); o motor escolhe o menor", "",
         "| distribuição | #runs | RLE | packed(N/8) | textbits | vencedor |", "|---|---|---|---|---|---|"]
    for name, col in dists(n).items():
        enc = E.encode_col(col)
        bits = enc["bits"]
        win, opts = E.best_body(bits)
        L.append(f"| {name} | {len(E.rle_runs(bits))} | {opts['rle']}B | {opts['packed']}B | "
                 f"{opts['textbits']}B | **{win}** |")
    L += ["",
          "LEITURA: ordenado/skew → RLE vence (poucos runs, e é EXPLICÁVEL). alternado/aleatório → packed",
          "vence (N/8 constante; RLE explode com ~N runs). O motor testa e escolhe — 'deixar preparado'."]
    w("01-motor-distribuicoes.txt", "\n".join(L) + "\n")


def thread_afixo():
    L = ["# DOMÍNIO uma vez, aproveitando o AFIXO do OBAT (o 2º relaciona ao 1º)", ""]
    for dom in (("male", "female"), ("1", "2"), ("<=50K", ">50K"), ("Ativo", "Inativo")):
        from tcf import encode
        blob = encode(list(dom))
        raw = sum(len(x) for x in dom)
        L.append(f"  {dom} -> encode {len(blob.encode())}B (raw {raw}B)  {blob!r}")
    L += ["", "male→female='fe1' (o owner previu): o domínio guardado uma vez já é afixo-comprimido.",
          "Domínios curtos (1/2) não ganham (overhead), mas é o header, guardado UMA vez — desprezível."]
    w("02-dominio-afixo.txt", "\n".join(L) + "\n")


def thread_excecoes(n=1000):
    """99% male/female + raros null/other → overlay de exceções, RT."""
    col = []
    for i in range(n):
        if i % 200 == 7:
            col.append("(null)")
        elif i % 200 == 99:
            col.append("other")
        else:
            col.append("male" if i % 3 else "female")
    enc = E.encode_col(col)
    back = E.decode_col(enc)
    ok = back == col
    win, opts = E.best_body(enc["bits"])
    total = E.domain_bytes(enc["domain"]) + opts[win] + E.exc_bytes(enc["exc"])
    L = ["# OVERLAY DE EXCEÇÕES — 99% male/female + raros null/other (RT + bytes)", "",
         f"  N={n}  domínio={enc['domain']}  #exceções={len(enc['exc'])} (frac={enc['exc_frac']:.3f})",
         f"  RT={'OK' if ok else 'FALHA'}",
         f"  domínio={E.domain_bytes(enc['domain'])}B + corpo({win})={opts[win]}B + exceções={E.exc_bytes(enc['exc'])}B  = {total}B",
         f"  (corpo bits: rle={opts['rle']}B packed={opts['packed']}B textbits={opts['textbits']}B)",
         "",
         "LEITURA: o domínio = os 2 dominantes; os raros (null/other) vão num canal esparso (posição,valor).",
         "O bit-stream cobre 100% (exceção=placeholder), a overlay corrige. Lossless. = def-level (1c) + binário."]
    w("03-overlay-excecoes.txt", "\n".join(L) + "\n")


def thread_real():
    L = ["# COLUNAS REAIS — o motor escolhe na ORDEM REAL do dado", ""]
    targets = [("adult-census.db", "adult", "sex"), ("adult-census.db", "adult", "class"),
               ("receita-cnpj.db", "estabelecimentos", "matriz_filial"),
               ("tpch-sf001.db", "lineitem", "l_linestatus")]
    for db, tbl, coln in targets:
        dbp = INTERIM / db
        if not dbp.exists():
            L.append(f"  {db} indisponível"); continue
        con = sqlite3.connect(f"file:{dbp}?mode=ro", uri=True)
        cur = con.cursor()
        try:
            vals = [str(r[0]) for r in cur.execute(f'SELECT "{coln}" FROM "{tbl}"').fetchall()]
        except Exception as e:
            L.append(f"  {db}.{tbl}.{coln}: erro {e}"); con.close(); continue
        con.close()
        enc = E.encode_col(vals)
        ok = E.decode_col(enc) == vals
        win, opts = E.best_body(enc["bits"])
        raw_hcc = len(__import__("tcf").encode(vals).encode())
        L.append(f"## {tbl}.{coln}  N={len(vals)}  domínio={enc['domain']}  exc={len(enc['exc'])}  RT={'OK' if ok else 'FALHA'}")
        L.append(f"  raw(HCC)={raw_hcc}B · RLE={opts['rle']}B · packed={opts['packed']}B · textbits={opts['textbits']}B  → **{win}**")
        L.append(f"  #runs={len(E.rle_runs(enc['bits']))} (ordem real)")
        L.append("")
    L += ["LEITURA: a ordem REAL decide. Se o dump vem agrupado → RLE (explicável) ganha; se espalhado →",
          "packed. O motor escolhe por bytes; 'manter a quebra' = preferir RLE quando ele fica perto (pilar)."]
    w("04-colunas-reais.txt", "\n".join(L) + "\n")


def main():
    thread_afixo(); thread_dists(); thread_excecoes(); thread_real()

    R = ["# Motor spec_bin (escape + RLE/bitstream + exceções) [resumo]", "",
         "## O motor (owner: 'deixar preparado, pensar no dado depois')",
         "- **escape**: sem catálogo — os 2 valores mais comuns SÃO o domínio (guardados 1×, afixo-comprimidos:",
         "  male→'fe1'). Header tipo `col:spec_bin`; corpo = bit-stream 0/1.",
         "- **2 corpos, escolhe o menor**: RLE (textual, EXPLICÁVEL, mantém a quebra) vence ordenado/skew;",
         "  bitstream packed (N/8, opaco) vence aleatório. Testado em 5 distribuições (01).",
         "- **overlay de exceções**: 99% dominantes + raros (null/other) → domínio=2 dominantes, raros num",
         "  canal esparso (pos,valor); bit-stream cobre tudo, overlay corrige. RT-OK (03). = def-level (1c).",
         "- **manter a quebra**: RLE preserva grupos visíveis (pilar explicabilidade); preferir quando perto.",
         "",
         "## Resultado",
         "- distribuição decide RLE×packed → o motor cobre os dois (01). Domínio afixo-comprimido (02).",
         "- exceções lossless via overlay (03). Colunas reais escolhem na ordem real (04).",
         "- serve p/ QUALQUER enum-2 sem catálogo (matriz_filial=1|2, Male/Female, F/O…).",
         "",
         "## Próximo (estudar o dado depois)",
         "- generalizar enum-k (k>2); medir combinações ordem×distribuição×skew em mais colunas reais;",
         "- bitstream real (bits empacotados na camada binária V2-L); ligar autoridade (typed→canonicaliza)."]
    w("00-resumo.txt", "\n".join(R) + "\n")

    print("artifacts em", ART)
    for p in sorted(ART.iterdir()):
        print(f"  {p.name:26s} {p.stat().st_size:6d} B")
    print("\n" + "\n".join(R))


if __name__ == "__main__":
    main()
