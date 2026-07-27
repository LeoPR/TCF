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

    # --- o par critico, agora com escapes suficientes para o FLOOR ATIVAR.
    # Achado da auditoria: nas 4 colunas acima o decide() RECUSA, entao o RT delas era
    # IDENTIDADE -- nao exercia o bug do slot nulo. Esta coluna tem "0" como dado, null, e
    # 5 corridas de digito por linha para o ganho pagar o prefixo.
    c["zero-null-ATIVO"] = [None if i % 6 == 0 else
                            ("0" if i % 5 == 0 else
                             f"{L(1000):03d}.{L(1000):03d}.{L(1000):03d}-{L(100):02d}")
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
    """Le uma coluna de fixture. **Fail-loud** em nome de coluna inexistente.

    Achado da auditoria: `row.get(nome)` devolvia `None` para nome errado, a coluna saia
    100% null e era listada no result.md como medicao valida -- sem medir nada.
    """
    p = SAMPLES / rel
    if not p.exists():
        return None
    with p.open(encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        if nome not in (r.fieldnames or []):
            raise KeyError(f"coluna {nome!r} nao existe em {rel} (tem: {r.fieldnames})")
        vals = []
        for row in r:
            v = row[nome]
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
    r["pres"] = presentes
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

    # A regra RECUSOU? entao `volta is corpo` e o RT abaixo e' IDENTIDADE, nao prova do
    # mecanismo. A auditoria pegou isso: reportar "30/30" misturava as duas coisas.
    r["transformou"] = modo == "delim"
    r["exato"] = volta == corpo
    # RT ESTRITO: valor E tipo, elemento a elemento (bool nao pode virar int, "0" nao pode
    # virar None, e vice-versa)
    if r["exato"]:
        obtido = decode(cab + "\n" + volta)
        # GUARDA DE COMPRIMENTO (achado da auditoria): `zip` TRUNCA, entao um decode que
        # devolvesse menos elementos passaria no teste de tipo, e a linha "divergencia de
        # TIPO: 0" mentiria ao lado de um RT falhado.
        mesmo_n = len(obtido) == len(dados)
        r["rt_tipo_ok"] = mesmo_n and all(type(a) is type(b) for a, b in zip(obtido, dados))
        r["rt"] = mesmo_n and obtido == dados and r["rt_tipo_ok"]
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
           f"Escala pequena de propósito: **até {N} linhas por coluna** (2 fixtures reais "
           f"têm menos — a coluna `n` da tabela diz o real), "
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
            f"- **RT com transformação real** (a regra ativou, o corpo foi para o "
            f"delimitador e voltou): **{len(usa) - len([f for f in falhas if f in {r['nome'] for r in usa}])}/{len(usa)}**",
            f"- RT das colunas que **recusaram** — é IDENTIDADE, não prova do mecanismo: "
            f"**{len(ok) - len(usa)}**",
            f"- divergência de TIPO: **{len(tipo_ruim)}**"
            + (f" — {tipo_ruim}" if tipo_ruim else " (nenhuma)"),
            f"- Δ somado: **{sum(r['delta'] for r in ok)} B**", "",
            "**O decoder REAL nunca recebe a grafia da proposta.** Ele recebe o corpo "
            "canônico *reconstruído* — que é o desenho (camada de borda), mas precisa ser "
            "dito: o que está provado é a **reconstrução**, não que um `.tcfp` seja um wire "
            "válido. Alimentar o `.tcfp` direto ao `decode` **falha alto** (`ValueError`), "
            "graças ao fail-loud soldado antes nesta sessão — não corrompe em silêncio.", ""]

    # ---------------------------------------------------------- o null como referência
    com_null = [r for r in ok if r["nulls"] > 0]
    out += ["## O `0` do null: dígito que não é dado", "",
            "O slot nulo é escrito como `0` cru — grafia otimizada de `^0`. Ele é **dígito** "
            "no corpo, mas é **referência**, não dado. Se o mecanismo o tratasse como corrida "
            "literal, a reconstrução emitiria `\\0` = a string `\"0\"`, e um RT frouxo não "
            "veria: o tamanho bate, o tipo da lista bate.", "",
            "A correção foi **tirar** a regra especial: o null é referência ao slot 0, e a "
            "máquina de polaridade classifica dígito nu como `R` = referência. Ela acerta "
            "sozinha.", "",
            "A coluna que importa é a que tem `\"0\"` como **dado**, `null` na mesma coluna, "
            "**e** a regra ATIVADA — sem as três coisas juntas o RT é identidade e não prova "
            "nada. Foi um achado da auditoria: as 4 primeiras abaixo **recusam**.", "",
            "| coluna | nulls | `\"0\"` como dado? | regra ativou? | RT |",
            "|---|---:|:-:|:-:|:-:|"]
    for r in com_null:
        zero = "sim" if "zero" in r["nome"] or "binario-01" in r["nome"] else "não"
        at = "**sim**" if r["modo"] == "delim" else "não (identidade)"
        out.append(f"| `{r['nome']}` | {r['nulls']} | {zero} | {at} | "
                   f"{'OK' if r['rt'] else '**FALHOU**'} |")
    ativo = [r for r in com_null if r["modo"] == "delim"
             and ("zero" in r["nome"] or "binario-01" in r["nome"])]
    out += ["", "`zero-null-ATIVO` foi construída depois da auditoria exatamente para fechar "
            "esse buraco: `\"0\"` como dado, `null`, e corridas de dígito suficientes para o "
            "FLOOR ativar. "
            + (f"Ela ativa (`{ativo[0]['delta']:+} B`) e o RT passa."
               if ativo else "**Ela não ativou — o buraco continua aberto.**"), ""]

    # ------------------------------------------------- o alfabeto livre com a FAIXA reduzida
    from cruzado import FAIXA, elege
    out += ["## A FAIXA encolheu — ainda sobra char?", "",
            "A auditoria adversarial reproduziu dois bugs de eleição: **dígito** eleito funde "
            "com a corrida vizinha (`1\\\\22.\\\\33` → `1022.33`, e a volta deixa de ser "
            "exata), e **letra** eleita colide com o slot do discriminador — uma coluna de "
            "STRING emitia `#TCF.8b`, byte-idêntico ao cabeçalho canônico de uma coluna "
            "bool. A correção exclui por **classe**, não por lista: só pontuação.", "",
            f"```\nFAIXA = {''.join(FAIXA)}\n{len(FAIXA)} chars (era 88 — caiu 70%)\n```", "",
            "Isso encolhe muito o espaço, então a pergunta vira empírica:", "",
            "| coluna | usados da FAIXA | livres | eleito |", "|---|---:|---:|:-:|"]
    livres_min, pior = len(FAIXA) + 1, None
    for r in todas:
        if not r["aplicavel"] or not r.get("pres"):
            continue
        nl = sum(1 for c in FAIXA if c not in r["pres"])
        if nl < livres_min:
            livres_min, pior = nl, r["nome"]
        out.append(f"| `{r['nome']}` | {len(FAIXA) - nl} | {nl} | "
                   f"`{elege(r['pres']) or '—'}` |")
    out += ["", f"Mínimo de chars livres: **{livres_min} de {len(FAIXA)}** (em `{pior}`). "
            + ("Nenhuma coluna ficou sem opção nesta amostra — mas a margem caiu, e é uma "
               "amostra pequena." if livres_min > 0 else
               "**Alguma coluna ficou sem char livre.**"), ""]

    (RAIZ / "result.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0 if not falhas else 1


if __name__ == "__main__":
    sys.exit(main())
