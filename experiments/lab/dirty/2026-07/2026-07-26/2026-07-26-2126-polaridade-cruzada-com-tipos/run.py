"""Lab 2026-07-26-2126 — polaridade × tipos (bool, binário, null), escala pequena.

    "faça uma avaliação com o que já temos, combinado com os dados booleanos, binários, null
     até o momento. vamos vendo essas situações, a variedade de dados reais pode ser usada,
     mas faça em uma escala pequena, não é um teste de resistência nem de benchmark real é só
     pra ver comportamento e pequenos bugs, precisamos testar muita coisa."

Os labs `1853`/`1913`/`1954` trataram o corpo como declarações de string. Desde as soldas
recentes ele carrega mais: tag de tipo (`b`/`n`/`s`), modo denso (`b15` + base64), o slot nulo
pré-alocado (`0` cru) e o hierárquico (`H`). Este lab cruza tudo, **em escala pequena**, para
ver comportamento e bugs — não para medir ganho.

O ponto de atenção declarado antes de rodar: **o `0` do null é um dígito que NÃO é dado**. Se
o mecanismo o tratasse como corrida, a reconstrução emitiria `\\0` = a string `"0"` — corrupção
que um RT de tipo não pegaria. Por isso o RT aqui compara **valor e tipo**, elemento a
elemento.
"""
import csv
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(RAIZ))

from cruzado import (  # noqa: E402
    aplicavel, decide, de_grafia, de_v3, eh_base64, parte_wire, resolve, v3, varredura_unica,
)

from tcf import decode, encode  # noqa: E402

for d in ("inputs", "intermediates", "outputs"):
    (RAIZ / d).mkdir(exist_ok=True)

SAMPLES = REPO / "datasets" / "samples"
N = 50                                    # escala pequena, de propósito


def _lcg(seed=7):
    x = seed
    while True:
        x = (1103515245 * x + 12345) % (2 ** 31)
        yield x


# ---------------------------------------------------------------- colunas sintéticas
def sinteticas():
    g = _lcg()
    L = lambda m: next(g) % m                                      # noqa: E731
    c = {}

    # --- booleanos e binários
    c["bool-puro"] = [bool(L(2)) for _ in range(N)]
    c["bool-constante"] = [True] * N
    c["bool-null"] = [None if i % 5 == 0 else bool(L(2)) for i in range(N)]
    c["bool-null-maioria"] = [None if i % 3 else bool(L(2)) for i in range(N)]
    c["binario-01"] = [str(L(2)) for _ in range(N)]                # "0"/"1" como STRING
    c["binario-01-null"] = [None if i % 4 == 0 else str(L(2)) for i in range(N)]
    c["binario-sn"] = ["S" if L(2) else "N" for _ in range(N)]

    # --- null
    c["null-puro"] = [None] * N
    c["null-quase-tudo"] = [None if i else "x" for i in range(N)]
    c["null-esparso"] = [None if i == 7 else str(L(10000)) for i in range(N)]

    # --- inteiros / floats tipados
    c["int-null"] = [None if i % 6 == 0 else L(100000) for i in range(N)]
    c["int-ordenado-null"] = [None if i % 9 == 0 else i * 7 + 3 for i in range(N)]
    c["int-negativo-null"] = [None if i % 8 == 0 else L(2000) - 1000 for i in range(N)]
    c["float-null"] = [None if i % 7 == 0 else round(L(10000) / 100, 2) for i in range(N)]

    # --- o caso que pode confundir null com dado
    c["str-zero-e-null"] = [None if i % 3 == 0 else "0" for i in range(N)]
    c["str-zero-misto"] = [None if i % 4 == 0 else ("0" if i % 2 else str(L(100)))
                           for i in range(N)]

    # --- formatadas com null (o regime onde a polaridade ganha)
    c["cpf-mascara-null"] = [None if i % 10 == 0 else
                             f"{L(1000):03d}.{L(1000):03d}.{L(1000):03d}-{L(100):02d}"
                             for i in range(N)]
    c["cartao-null"] = [None if i % 11 == 0 else
                        "-".join(f"{L(10000):04d}" for _ in range(4)) for i in range(N)]
    return c


# ---------------------------------------------------------------- colunas reais (pequenas)
def _col(rel, nome, n=N, mapa=None):
    p = SAMPLES / rel
    if not p.exists():
        return None
    with p.open(encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        vals = []
        for row in r:
            v = row.get(nome)
            if mapa:
                v = mapa(v)
            vals.append(v)
            if len(vals) >= n:
                break
    return vals


def _vazio_null(v):
    return None if v in ("", None) else v


def _na_null(v):
    return None if v in ("", "NA", None) else v


def reais():
    c = {}
    fontes = [
        ("real-adult-sex-bool", "adult-census/adult-sample.csv", "sex",
         lambda v: None if not v else v.strip() == "Male"),
        ("real-adult-class-bool", "adult-census/adult-sample.csv", "class",
         lambda v: None if not v else ">" in v),
        ("real-adult-age-int", "adult-census/adult-sample.csv", "age",
         lambda v: None if not v else int(v)),
        ("real-adult-capgain-int", "adult-census/adult-sample.csv", "capital-gain",
         lambda v: None if not v else int(v)),
        ("real-pm25-com-NA", "beijing-pm25/beijing-pm25-sample.csv", "pm2.5", _na_null),
        ("real-pm25-Iws-float", "beijing-pm25/beijing-pm25-sample.csv", "Iws",
         lambda v: None if not v else float(v)),
        ("real-cnpj-matriz-bin", "receita-cnpj/cnpj-2k.csv", "matriz_filial", _vazio_null),
        ("real-cnpj-fantasia-null", "receita-cnpj/cnpj-2k.csv", "nome_fantasia", _vazio_null),
        ("real-cnpj-doc", "receita-cnpj/cnpj-2k.csv", "cnpj", _vazio_null),
        ("real-pessoas-cpf", "br-identidades/pessoas-sample.csv", "cpf", _vazio_null),
        ("real-pessoas-email-null", "br-identidades/pessoas-sample.csv", "email", _vazio_null),
        ("real-ibge-id", "ibge-municipios/ibge-municipios-sample.csv", "id",
         lambda v: None if not v else int(v)),
        ("real-retail-stockcode", "online-retail/stockcode-2k.csv", "StockCode", _vazio_null),
        ("real-tpch-phone", "tpch-sf001/customer-sample.csv", "c_phone", _vazio_null),
        ("real-tpch-acctbal", "tpch-sf001/customer-sample.csv", "c_acctbal",
         lambda v: None if not v else float(v)),
    ]
    for nome, rel, coluna, mapa in fontes:
        vals = _col(rel, coluna, mapa=mapa)
        if vals:
            c[nome] = vals
    return c


def _wj(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str) + "\n",
                 encoding="utf-8")


def caso(nome, dados):
    wire = encode(dados)
    cab, tag, corpo = parte_wire(wire)
    r = {"nome": nome, "n": len(dados), "tag": tag or "(nenhuma)",
         "wire": len(wire.encode()), "corpo": len(corpo.encode()),
         "nulls": sum(1 for x in dados if x is None),
         "aplicavel": aplicavel(tag), "b64": eh_base64(corpo)}

    if not r["aplicavel"]:
        r.update({"modo": "N/A", "motivo": "corpo nao e' declaracao (denso/hierarquico)",
                  "rt": None, "exato": None, "delta": 0})
        _wj(RAIZ / "outputs" / f"{nome}-NAO-APLICAVEL.json", r)
        return r

    toks, presentes, tR, tL, literais = varredura_unica(corpo)
    modo, char, inicial, custo = decide(presentes, tR, tL, literais)
    r.update({"lit": literais, "tR": tR, "tL": tL, "modo": modo, "char": char,
              "inicial": inicial, "custo": custo})

    if modo == "delim":
        corpo_d = resolve(toks, char, inicial)
        texto = v3(cab, corpo_d, char, inicial)
        # LEITURA CEGA: char e polaridade saem do sufixo posicional, nao da variavel
        c3, p3, corpo3 = de_v3(texto, tag)
        volta = de_grafia(corpo3, c3, p3)
        r["delta"] = len(corpo_d.encode()) + (1 if inicial == "R" else 2) - len(corpo.encode())
        (RAIZ / "outputs" / f"{nome}-wire-V3.tcfp").write_text(texto, encoding="utf-8")
    else:
        volta, r["delta"] = corpo, 0

    r["exato"] = volta == corpo
    # RT ESTRITO: valor E tipo, elemento a elemento (bool nao pode virar int, "0" nao pode
    # virar None, e vice-versa)
    if r["exato"]:
        obtido = decode(cab + "\n" + volta)
        r["rt"] = (obtido == dados
                   and all(type(a) is type(b) for a, b in zip(obtido, dados)))
        r["rt_tipo_ok"] = all(type(a) is type(b) for a, b in zip(obtido, dados))
    else:
        r["rt"] = r["rt_tipo_ok"] = False

    (RAIZ / "outputs" / f"{nome}-wire-normal.tcf").write_text(wire, encoding="utf-8")
    _wj(RAIZ / "outputs" / f"{nome}-dataset.roundtrip.json", decode(wire))
    return r


def tabela(titulo, itens, out):
    out += [f"## {titulo}", "",
            "| coluna | n | tag | nulls | corpo | escapes | tR | tL | decisão | Δ | RT |",
            "|---|---:|:-:|---:|---:|---:|---:|---:|---|---:|:-:|"]
    for r in itens:
        if not r["aplicavel"]:
            out.append(f"| `{r['nome']}` | {r['n']} | `{r['tag']}` | {r['nulls']} | "
                       f"{r['corpo']} | — | — | — | **N/A** ({'base64' if r['b64'] else 'nao-decl'}) "
                       f"| — | — |")
            continue
        dec = (f"delim `{r['char']}`{r['inicial']}" if r["modo"] == "delim"
               else f"recusa ({r['lit']} esc)")
        rt = {True: "OK", False: "**FALHOU**", None: "—"}[r["rt"]]
        out.append(f"| `{r['nome']}` | {r['n']} | `{r['tag']}` | {r['nulls']} | "
                   f"{r['corpo']} | {r['lit']} | {r['tR']} | {r['tL']} | {dec} | "
                   f"{r['delta']:+} | {rt} |")
    out.append("")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cols_s, cols_r = sinteticas(), reais()
    for nome, dados in list(cols_s.items()) + list(cols_r.items()):
        _wj(RAIZ / "inputs" / f"{nome}-fonte.json",
            {"coluna": nome, "n": len(dados), "amostra": dados[:6]})
        _wj(RAIZ / "intermediates" / f"{nome}-dataset-consumido.json", dados)

    res_s = [caso(n, d) for n, d in cols_s.items()]
    res_r = [caso(n, d) for n, d in cols_r.items()]
    todas = res_s + res_r

    out = ["# Polaridade × tipos — bool, binário, null (2026-07-26-2126)", "",
           f"Escala pequena de propósito: **{N} linhas por coluna**, "
           f"**{len(res_s)} sintéticas** + **{len(res_r)} reais**. Não é benchmark — é "
           "observação de comportamento e caça a bug.", "",
           "`RT` compara **valor E tipo**, elemento a elemento: um `\"0\"` virando `None` "
           "(ou o contrário) passaria num RT frouxo.", ""]
    tabela("Sintéticas", res_s, out)
    tabela("Reais (fixtures do repo, 50 linhas)", res_r, out)

    ok = [r for r in todas if r["aplicavel"]]
    na = [r for r in todas if not r["aplicavel"]]
    usa = [r for r in ok if r["modo"] == "delim"]
    falhas = [r["nome"] for r in ok if r["rt"] is False or r["exato"] is False]
    tipo_ruim = [r["nome"] for r in ok if r.get("rt_tipo_ok") is False]

    out += ["## Resultado", "",
            f"- colunas medidas: **{len(todas)}** ({len(res_s)} sintéticas + {len(res_r)} reais)",
            f"- **N/A** (corpo não é declaração): **{len(na)}** — "
            + (", ".join(f"`{r['nome']}` (`{r['tag']}`)" for r in na) if na else "nenhuma"),
            f"- delimitador ativa: **{len(usa)} de {len(ok)}** aplicáveis",
            f"- RT estrito (valor **e** tipo): "
            f"**{len(ok) - len(falhas)}/{len(ok)}**"
            + (f" — falha em {falhas}" if falhas else ""),
            f"- divergência de TIPO: **{len(tipo_ruim)}**"
            + (f" — {tipo_ruim}" if tipo_ruim else " (nenhuma)"),
            f"- Δ somado: **{sum(r['delta'] for r in ok)} B**", ""]

    # ---------------------------------------------------------- o null como referência
    com_null = [r for r in ok if r["nulls"] > 0]
    out += ["## O `0` do null: dígito que não é dado", "",
            "O slot nulo é escrito como `0` cru — grafia otimizada de `^0`. Ele é **dígito** "
            "no corpo, mas é **referência**, não dado. Se o mecanismo o tratasse como corrida "
            "literal, a reconstrução emitiria `\\0` = a string `\"0\"`, e um RT frouxo não "
            "veria: o tamanho bate, o tipo da lista bate.", "",
            "Este lab trata a linha `0` como **opaca** (junto de `^N` e da linha vazia) e "
            "compara tipo elemento a elemento. As colunas que exercem isso:", "",
            "| coluna | nulls | tem `\"0\"` como dado? | RT |", "|---|---:|:-:|:-:|"]
    for r in com_null:
        zero = "sim" if "zero" in r["nome"] or "binario-01" in r["nome"] else "não"
        out.append(f"| `{r['nome']}` | {r['nulls']} | {zero} | "
                   f"{'OK' if r['rt'] else '**FALHOU**'} |")
    out += ["", "`str-zero-e-null` e `binario-01-null` são o par crítico: o mesmo char `0` "
            "aparece como **dado** e como **slot nulo** na mesma coluna.", ""]

    (RAIZ / "result.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0 if not falhas else 1


if __name__ == "__main__":
    sys.exit(main())
