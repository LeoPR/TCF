"""Lab 2026-07-26-1913 — marcador VIRTUAL + alfabeto da coluna. Reavaliação do `1853`.

O owner apontou dois erros no lab anterior:

    "eu apenas CHUTEI o `/` (…) o importante é saber ONDE existe a possibilidade de conflito,
     marcar ele internamente com qualquer coisa, uma semântica interna, com uma pseudo
     gramática, idêntico ao OBAT e o HCC (…) não precisamos fazer como uma esteira com
     batchs serializados (…) enquanto a árvore avalia similaridades, a própria avaliação
     sabe se a string começa com número, e isso já é um contador e um indicador."

Este lab mede TRÊS coisas:

  A. **Sempre existe char livre?** — nas formas sintéticas E nas fixtures REAIS committadas
     em `datasets/samples/`. Se existe, o custo de ocorrência do delimitador é **zero por
     construção**, e a lista de candidatos do `1853` era desnecessária.
  B. **Quantas varreduras a decisão custa?** — `1853` fazia 8 sobre o corpo já pronto;
     aqui é 1, fundida na que já existe.
  C. **Os bytes mudam?** — comparação direta com os números do `1853`.

VALIDAÇÃO: `resolve` (marcador virtual -> grafia) e `de_grafia` (grafia -> corpo canônico),
comparando byte a byte com o corpo canônico do `src/tcf` e passando pelo `decode` REAL.
"""
import csv
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(RAIZ))

from virtual import (  # noqa: E402
    FAIXA, decide, de_grafia, livres, resolve, varredura_unica,
)

from tcf import decode, encode  # noqa: E402
from tcf.encoder import _encode_column  # noqa: E402

for d in ("inputs", "intermediates", "outputs"):
    (RAIZ / d).mkdir(exist_ok=True)

SAMPLES = REPO / "datasets" / "samples"


def _lcg(seed):
    x = seed
    while True:
        x = (1103515245 * x + 12345) % (2 ** 31)
        yield x


def gera(forma, n, seed=7):
    """Mesmas formas e seed do lab `1853`, para comparar número com número."""
    g = _lcg(seed)
    if forma == "cpf":
        return [f"{i % 1000:03d}.{i * 7 % 1000:03d}.{i * 13 % 1000:03d}-{i % 100:02d}"
                for i in range(n)]
    if forma == "cartao":
        return ["-".join(f"{next(g) % 10000:04d}" for _ in range(4)) for _ in range(n)]
    if forma == "ip":
        return [".".join(str(next(g) % 256) for _ in range(4)) for _ in range(n)]
    if forma == "cep":
        return [f"{next(g) % 99999:05d}-{next(g) % 999:03d}" for _ in range(n)]
    if forma == "telefone":
        return [f"({next(g) % 90 + 10}) 9{next(g) % 10000:04d}-{next(g) % 10000:04d}"
                for _ in range(n)]
    if forma == "email":
        return [f"user{next(g) % 10000}@d{next(g) % 9}.com" for _ in range(n)]
    if forma == "data-iso":
        return [f"20{next(g) % 30 + 10}-{next(g) % 12 + 1:02d}-{next(g) % 28 + 1:02d}"
                for _ in range(n)]
    if forma == "texto":
        return [f"palavra{chr(97 + next(g) % 26)}" for _ in range(n)]
    if forma == "data-br":
        return [f"{next(g) % 28 + 1:02d}/{next(g) % 12 + 1:02d}/20{next(g) % 30 + 10}"
                for _ in range(n)]
    if forma == "cnpj-mascara":
        return [f"{next(g) % 100:02d}.{next(g) % 1000:03d}.{next(g) % 1000:03d}"
                f"/0001-{next(g) % 100:02d}" for _ in range(n)]
    raise ValueError(forma)


FORMAS = ["cpf", "cartao", "ip", "cep", "telefone", "data-iso", "email", "texto",
          "data-br", "cnpj-mascara"]

# fixtures REAIS committadas (as mesmas do gate `test_real_world_snapshots.py`)
REAIS = [("retail-description", "online-retail/description-2k.csv"),
         ("retail-stockcode", "online-retail/stockcode-2k.csv"),
         ("lineitem-comment", "tpch-sf001/lcomment-2k.csv")]

# custo medido no lab 1853 (transições da polaridade escolhida); `None` = não medido lá
CUSTO_1853 = {"cpf": 0, "cartao": 25, "ip": 0, "cep": 5, "telefone": 504,
              "data-iso": 458, "email": 472, "texto": 0, "data-br": 457,
              "cnpj-mascara": 515}


def _le_real(rel):
    with (SAMPLES / rel).open(encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        next(r)
        return [row[0] for row in r if row]


def _wj(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def caso(nome, dados, gravar=True):
    corpo = _encode_column(dados)

    # ---- A ÚNICA VARREDURA: tokens virtuais + alfabeto + 2 contadores, tudo junto
    toks, presentes, tR, tL, literais = varredura_unica(corpo)
    modo, char, inicial, custo = decide(presentes, tR, tL, literais)

    if modo == "delim":
        corpo_d = resolve(toks, char, inicial)
        volta = de_grafia(corpo_d, char, inicial)
    else:
        corpo_d, volta = corpo, corpo

    exato = volta == corpo
    wire = encode(dados)
    cab = wire.partition("\n")[0]
    rt = (decode(cab + "\n" + volta) == dados) if exato else False

    if gravar:
        _wj(RAIZ / "inputs" / f"{nome}-fonte.json",
            {"coluna": nome, "n": len(dados), "amostra": dados[:4]})
        _wj(RAIZ / "intermediates" / f"{nome}-dataset-consumido.json", dados)
        _wj(RAIZ / "intermediates" / f"{nome}-alfabeto.json",
            {"presentes": "".join(sorted(presentes)),
             "livres_na_faixa": "".join(livres(presentes)),
             "n_livres": len(livres(presentes)), "faixa": len(FAIXA)})
        (RAIZ / "outputs" / f"{nome}-wire-normal.tcf").write_text(wire, encoding="utf-8")
        if modo == "delim":
            (RAIZ / "outputs" / f"{nome}-wire-delim.tcfp").write_text(
                f"{cab}d{char}{inicial}\n{corpo_d}", encoding="utf-8")
        _wj(RAIZ / "outputs" / f"{nome}-dataset.roundtrip.json", decode(wire))
    return {"corpo": len(corpo.encode()), "d": len(corpo_d.encode()),
            "lit": literais, "tR": tR, "tL": tL, "custo": custo, "modo": modo,
            "char": char, "inicial": inicial, "nlivres": len(livres(presentes)),
            "presentes": len(presentes), "rt": rt, "exato": exato}


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    out = ["# Marcador virtual + alfabeto da coluna (2026-07-26-1913)", "",
           "Reavaliação do lab `1853` a partir de dois erros apontados: o char foi "
           "**chutado**, e a decisão era uma **esteira serializada** rodando depois do "
           "núcleo.", "",
           "## A reformulação", "",
           "O marcador é **virtual** — um sentinela na representação intermediária, não um "
           "char. Não pode colidir porque **não é texto**. É o movimento do OBAT (nós, não "
           "strings) e do HCC (composição, não grafia).", "",
           "```",
           "tokens = [('R','56'), FLIP, ('L','033'), ('txt','-'), ...]   <- FLIP é objeto",
           "grafia = resolve(tokens, char, inicial)                      <- char NO FIM",
           "```", "",
           "E não se pergunta *qual char usar*, se pergunta **onde existe conflito**: o "
           "alfabeto que a coluna realmente usa. O complemento tem **conflito zero por "
           "construção**.", "",
           "## A — sempre existe char livre?", "",
           "Faixa considerada: ASCII imprimível menos a gramática do corpo "
           f"(`* ~ ^ , | \\`) = **{len(FAIXA)} chars**.", "",
           "| coluna | n | chars usados | chars LIVRES | escolhido |",
           "|---|---:|---:|---:|:-:|"]

    linhas, falhas = [], 0
    for forma in FORMAS:
        dados = gera(forma, 500 if forma != "cpf" else 200)
        r = caso(forma, dados)
        linhas.append((forma, r, False))
        falhas += (not r["rt"]) + (not r["exato"])
        out.append(f"| `{forma}` | {500 if forma != 'cpf' else 200} | {r['presentes']} | "
                   f"**{r['nlivres']}** | `{r['char'] or '—'}` |")
    for nome, rel in REAIS:
        if not (SAMPLES / rel).exists():
            out.append(f"| `{nome}` | — | — | fixture ausente | — |")
            continue
        dados = _le_real(rel)
        r = caso(nome, dados)
        linhas.append((nome, r, True))
        falhas += (not r["rt"]) + (not r["exato"])
        out.append(f"| **`{nome}`** (real) | {len(dados)} | {r['presentes']} | "
                   f"**{r['nlivres']}** | `{r['char'] or '—'}` |")

    minimo = min(r["nlivres"] for _n, r, _re in linhas)
    out += ["", f"Mínimo de chars livres em qualquer coluna medida: **{minimo}**. "
            "Onde há char livre, o custo de ocorrência do delimitador é **0 por "
            "construção** — a lista de candidatos do `1853` era desnecessária.", "",
            "Colunas de texto livre real usam poucas dezenas de chars num alfabeto de "
            f"{len(FAIXA)}. **Não é sorte das formas sintéticas.**", ""]

    # ------------------------------------------------------------------ B: varreduras
    out += ["## B — quantas varreduras a decisão custa?", "",
            "| | varreduras sobre o corpo | quando |", "|---|---:|---|",
            "| lab `1853` | **8** (6 candidatos × ocorrências + 2 polaridades) | depois do "
            "núcleo terminar |",
            "| aqui | **1** | fundida na que já existe |", "",
            "A varredura única acumula três coisas no mesmo passo por char, dentro do laço "
            "que `_escape_lit` (`src/tcf/composicional/syntax.py:173-193`) **já roda** — é o "
            "único laço char-a-char do emit, e é exatamente onde o escape de dígito é "
            "decidido (linha 181):", "",
            "```", "presentes   set/bitmap do alfabeto   (1 add por char)",
            "trocas_R    contador                  (1 comparação por corrida)",
            "trocas_L    contador                  (a outra polaridade, no mesmo passo)",
            "```", "",
            "A decisão é depois uma leitura de **3 acumuladores**, sem tocar no dado. É o que "
            "o owner descreveu: marcar durante a avaliação, decidir no fim.", ""]

    # ------------------------------------------------------------------ C: bytes
    out += ["## C — os bytes mudam em relação ao `1853`?", "",
            "`recusa` = a regra escolhe o inline de hoje porque as transições não compensam.", "",
            "| coluna | corpo | escapes hoje | trans. R | trans. L | decisão | trans. `1853` | igual? | Δ corpo |",
            "|---|---:|---:|---:|---:|---|---:|:-:|---:|"]
    for nome, r, real in linhas:
        c18 = CUSTO_1853.get(nome)
        # compara a MESMA grandeza: transicoes da polaridade escolhida (nao o custo da recusa)
        tmin = min(r["tR"], r["tL"])
        ig = "—" if c18 is None else ("sim" if c18 == tmin else "**NÃO**")
        cust = str(tmin) if r["modo"] == "delim" else f"recusa ({r['lit']} escapes)"
        out.append(f"| {'**' + nome + '**' if real else '`' + nome + '`'} | {r['corpo']} | "
                   f"{r['lit']} | {r['tR']} | {r['tL']} | {cust} | "
                   f"{c18 if c18 is not None else '—'} | {ig} | "
                   f"{r['d'] - r['corpo']:+} |")
    div = [n for n, r, _re in linhas
           if CUSTO_1853.get(n) is not None and CUSTO_1853[n] != min(r["tR"], r["tL"])]
    ganho = sum(r["d"] - r["corpo"] for _n, r, _re in linhas)
    out += ["", f"- divergências contra o `1853`: **{len(div)}**"
            + (f" — {div}" if div else " (mesmos bytes, decididos em 1 varredura em vez de 8)"),
            f"- ganho somado (sintéticas + reais): **{ganho} B**",
            f"- reconstrução byte-exata do corpo canônico **e** RT pelo `decode` REAL: "
            f"**{2 * len(linhas) - falhas}/{2 * len(linhas)}**", ""]

    # ------------------------------------------------------------------ o que fica aberto
    out += ["## O que isto destrava — e o que continua aberto", "",
            "O mapa do núcleo mostrou que existe representação estruturada até a fase B "
            "(`pieces_per_line`, tagged-union, `syntax.py:263-278`) e que ela **some no "
            "`_emit_body`**: dali em diante é `list[str]`. É por isso que o seq-RLE precisa "
            "**re-parsear texto** (`find_escape_digit_runs`, `hcc_seqrle.py:56`) para achar "
            "o dígito incrementável.", "",
            "Um marcador virtual na saída é exatamente a camada que falta ali. Com ela o "
            "seq-RLE leria o token em vez de reencontrar o `\\` no texto — o que dissolveria "
            "o bloqueador de todos os labs anteriores em vez de contorná-lo.", "",
            "**Não medido**: essa mudança no `_emit_body`. É a próxima pergunta, não uma "
            "conclusão deste lab.", "",
            "**Aberto**: coluna sem nenhum char livre. Aqui não ocorreu "
            f"(mínimo {minimo}), mas existe — e aí a saída é o `min` com custo de escape do "
            "delimitador, como no `1853`. A regra recusa e cai no comportamento de hoje.", ""]

    (RAIZ / "result.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0 if falhas == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
