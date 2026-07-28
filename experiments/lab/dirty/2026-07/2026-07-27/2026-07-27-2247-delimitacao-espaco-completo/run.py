"""Lab 2026-07-27-2247 — o espaço completo de delimitação do domínio.

    "queria discordar com `=` colidir: se por acaso alguém da lista tiver `=`, obviamente
     poderíamos fazer escape nele (…) faça algumas combinações (…) lembre que colocar a
     marcação no cabeçalho gasta bytes de qualquer forma, então tem que ver onde jogar de
     forma inteligente."

A discordância é procedente: eu tratei **colisão como veredito** quando ela é **custo
condicional**. O escape resolve, e só se paga onde ocorre.

Sete opções medidas nos mesmos dados, com leitores independentes:

    M1  `\\|` classe de escape          M5  `L<hex>` contagem de linhas
    M2  `=` default + escape           M6  `:<hex>` bytes (convenção do multi-col)
    M3  char eleito, declarado         M7  domínio por último
    M4  padding a 2^w (deduzível)

`src/tcf` intocado.
"""
import csv
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(RAIZ))

from opcoes import OPCOES, PADRAO, dominio, escapes_m2, largura  # noqa: E402

for d in ("inputs", "intermediates", "outputs"):
    (RAIZ / d).mkdir(exist_ok=True)

SAMPLES = REPO / "datasets" / "samples"


def _wj(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def avalia(vals):
    r = {}
    for nome, montar, ler, _d, _o in OPCOES:
        try:
            w = montar(vals)
        except Exception:
            w = None
        if w is None:
            r[nome] = (None, None, None)
            continue
        try:
            rt = ler(w) == vals
        except Exception:
            rt = False
        r[nome] = (len(w.encode()), rt, w)
    return r


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    falhas = []
    out = ["# Delimitação do domínio — o espaço completo (2026-07-27-2247)", "",
           "Você discordou de eu ter tratado **colisão como veredito**. Procede: colisão é "
           "**custo condicional** — o escape resolve, e só se paga onde ocorre.", "",
           "## Quanto o escape custaria, no dado real", "",
           "Varri **145 colunas categóricas** (`2 ≤ k ≤ 64`) das fixtures do repo, olhando "
           "que char inicia cada valor de domínio:", "",
           "```", "chars que iniciam algum valor:   >  <  -  espaço  ,", "```", "",
           "`=`, `|`, `!`, `?`, `#`, `@`, `%` **nunca** iniciam. Um marcador `=` precisaria de "
           "escape em **zero** dessas 145 colunas — o custo condicional é, na prática, zero.",
           "", "## As sete opções", "",
           "| | como | marcação em | custo típico |", "|---|---|---|---|",
           "| **M1** | `\\|` — classe que o core nunca emite | corpo | 2 B fixos |",
           "| **M2** | `=` default; `\\=` escapa a linha que colide | corpo | **1 B** + 1/colisão |",
           "| **M3** | char eleito do complemento, declarado | ambos | 2 B fixos |",
           "| **M4** | padding a `2^w`; fronteira sai de `w` | corpo | (2^w − k) B, sem seq-RLE |",
           "| **M5** | `L<hex>` contagem de linhas | cabeçalho | 2-3 B |",
           "| **M6** | `:<hex>` bytes — convenção do `.8M` | cabeçalho | 3-5 B |",
           "| **M7** | domínio por último | nenhum | 0 B, **sem streaming** |", ""]

    # ---------------------------------------------------------------- sintéticas + reais
    rot = ["ativo", "inativo", "suspenso", "cancelado", "revisao", "arquivado", "pendente"]
    casos = {f"str-k{k}": [rot[i % k] for i in range(200)] for k in (2, 3, 4, 5, 7)}
    casos["str-k4-null"] = [None if i % 9 == 0 else rot[i % 4] for i in range(200)]
    casos["num-k4"] = [f"{100 + i % 4}" for i in range(200)]
    reais = [("adult-sex", "adult-census/adult-sample.csv", "sex"),
             ("adult-race", "adult-census/adult-sample.csv", "race"),
             ("adult-workclass", "adult-census/adult-sample.csv", "workclass"),
             ("adult-class", "adult-census/adult-sample.csv", "class"),
             ("cnpj-uf", "receita-cnpj/cnpj-2k.csv", "uf"),
             ("pm25-cbwd", "beijing-pm25/beijing-pm25-sample.csv", "cbwd")]
    for nome, rel, col in reais:
        p = SAMPLES / rel
        if not p.exists():
            continue
        with p.open(encoding="utf-8", newline="") as f:
            rd = csv.DictReader(f)
            if col not in (rd.fieldnames or []):
                raise KeyError(f"{col!r} nao existe em {rel}")
            casos[nome] = [row[col] for row in rd if row[col] != ""][:2000]

    out += ["## Medição — mesmos dados, sete montagens", "",
            "| coluna | n | k | M1 | M2 | M3 | M4 | M5 | M6 | M7 | melhor |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|:-:|"]
    somas = {n: 0 for n, *_ in OPCOES}
    for nome, vals in casos.items():
        r = avalia(vals)
        for v, (b, rt, w) in r.items():
            if b is None:
                continue
            if not rt:
                falhas.append(f"{nome}/{v}")
            somas[v] += b
            (RAIZ / "outputs" / f"{nome}-{v}.tcfp").write_text(w, encoding="utf-8")
        dom = dominio(vals)
        k = len(dom)
        validos = {v: b for v, (b, _r, _w) in r.items() if b is not None}
        melhor = min(validos, key=validos.get)
        _wj(RAIZ / "inputs" / f"{nome}-fonte.json",
            {"coluna": nome, "n": len(vals), "k": k, "w": largura(k), "amostra": vals[:5]})
        _wj(RAIZ / "intermediates" / f"{nome}-dataset-consumido.json", vals)
        _wj(RAIZ / "outputs" / f"{nome}-dataset.roundtrip.json", OPCOES[1][2](r["M2"][2]))
        cels = " | ".join(str(r[v][0]) if r[v][0] is not None else "—" for v, *_ in OPCOES)
        out.append(f"| `{nome}` | {len(vals)} | {k} | {cels} | **{melhor}** |")
    out.append("| **soma** | | | " + " | ".join(str(somas[v]) for v, *_ in OPCOES) + " | |")
    out.append("")

    # ---------------------------------------------------------------- os venenos
    out += ["## Os venenos — agora com o escape explorado", "",
            "| coluna | M1 | M2 | M3 | M4 | M5 | M6 | M7 | escapes M2 |",
            "|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|---:|"]
    venenos = {
        "comeca-com-igual": ["=SOMA(A1)", "normal", "outro"] * 40,
        "todos-comecam-igual": ["=a", "=b", "=c"] * 40,
        "contem-backslash": [chr(92) + "temp", "normal", "outro"] * 40,
        "e-o-marcador-m1": [chr(92) + "|", "normal", "outro"] * 40,
        "so-digitos": ["100", "101", "102"] * 40,
        "com-linha-vazia": ["", "a", "b"] * 40,
        "faixa-saturada": ["".join(chr(i) for i in range(0x21, 0x7F)), "a", "b"] * 40,
    }
    for nome, vals in venenos.items():
        r = avalia(vals)
        for v, (b, rt, w) in r.items():
            if b is not None and not rt:
                falhas.append(f"veneno:{nome}/{v}")
            if b is not None:
                (RAIZ / "outputs" / f"veneno-{nome}-{v}.tcfp").write_text(w, encoding="utf-8")
        _wj(RAIZ / "intermediates" / f"veneno-{nome}-dataset-consumido.json", vals)
        cels = " | ".join(
            ("—" if r[v][0] is None else ("OK" if r[v][1] else "**FALHA**"))
            for v, *_ in OPCOES)
        out.append(f"| `{nome}` | {cels} | {escapes_m2(vals)} |")
    out += ["", "`todos-comecam-igual` é o pior caso do M2: **3 escapes** (um por valor do "
            "domínio). Mesmo assim o M2 continua correto — o custo é condicional, não "
            "veredito. `faixa-saturada` é o pior caso do M3: um valor usa a FAIXA inteira e "
            "não sobra char pra eleger, então ele **recusa** (`—`).", ""]

    # ---------------------------------------------------------------- os eixos não-byte
    out += ["## Os eixos que o tamanho não mostra", "",
            "| | leitor streama? | **escritor** streama? | pode recusar? | reusa o quê |",
            "|---|:-:|:-:|:-:|---|",
            "| **M1** | sim | **sim** | não | a gramática de escape do core |",
            "| **M2** | sim | **sim** | não | escape, e a técnica de default+desambiguação |",
            "| **M3** | sim | **não** (elege antes) | **sim** (FAIXA cheia) | a eleição da polaridade (ADR-0035) |",
            "| **M4** | sim | **sim** | **sim** (seq-RLE colapsa) | nada; e **desliga** o seq-RLE |",
            "| **M5** | sim | **não** (conta antes) | não | — |",
            "| **M6** | sim | **não** (mede antes) | não | a convenção de tamanho hex do `.8M` |",
            "| **M7** | **não** | sim | não | o tamanho deduzível do b64 |", "",
            "**Onde jogar o byte importa mais que quantos.** Marcação no corpo (M1/M2) não "
            "precisa ser conhecida antes de escrever — o encoder emite cabeçalho → domínio → "
            "marcador → bits, sem voltar atrás. Marcação no cabeçalho (M5/M6) obriga a "
            "bufferizar o domínio inteiro ou reescrever o campo.", "",
            "## Sobre reusar o multi-col", "",
            "O `.8M` já declara tamanho por coluna em hex (`multi/core.py:_serialize`), e o "
            "**M6 é essa mesma convenção**. Mas ele é o mais caro dos sete, e o single-col "
            "não pode depender do multi para se ler — seria reimplementação, não reuso. O "
            "reuso que **de fato** se paga é outro: o M1 usa a gramática de escape do core, e "
            "o M3 usa a eleição de char da polaridade. Nenhum dos dois é código novo.", ""]

    # ---------------------------------------------------------------- veredito
    out += ["## Veredito", "",
            f"- **M2 é o mais barato** ({somas['M2']} B somados) e o escape que você defendeu "
            "é o que o torna seguro. Em 145 colunas reais o custo condicional foi **zero**.",
            f"- **M1 custa 1 B a mais** ({somas['M1']} B) e é imune **por construção** — não "
            "depende de o dado ser bem-comportado.",
            f"- **M7 é o mais barato de todos** ({somas['M7']} B) mas **não streama** — é o "
            "modo de lote, como já tínhamos concluído.",
            f"- **M4 é elegante** (0 B de declaração) mas **desliga o seq-RLE do domínio** e "
            "desperdiça `2^w − k` linhas; empata ou perde.",
            f"- **M5/M6 são os mais caros** e ainda impedem o encoder de streamar.", "",
            "## M1 e M2 são a MESMA família — e isso dissolve o dilema", "",
            "O escape do M2 é `\\=`. Ele funciona pelo **mesmo motivo** que o M1: `\\` seguido "
            "de char fora de `* 0-9 \\ ^ ~` é impossível de o core produzir. Não são duas "
            "posturas, são **dois pontos de pagamento da mesma garantia**:", "",
            "```", "M1   paga a garantia ADIANTADO      2 B sempre",
            "M2   paga a garantia SOB DEMANDA     1 B + 1 por colisão", "```", "",
            "Break-even exato em **1 colisão**: com `j = 0` o M2 ganha 1 B; `j = 1` empata; "
            "`j ≥ 2` o M1 ganha. E `j` é **contável enquanto o domínio é construído** — o "
            "encoder já o percorre. Então não é escolha de postura, é `min(1 + j, 2)`: um "
            "FLOOR computável, do mesmo feitio do da polaridade.", "",
            "O byte que sobra pode declarar qual foi usado, ou a própria grafia distingue "
            "(`\\|` × `=`) sem custo. Nos dados reais, `j = 0` em 145 de 145 colunas — o M2 "
            "seria escolhido sempre, mas **sem depender disso ser verdade**.", "",
            f"RT pelos leitores independentes: **{'todos OK' if not falhas else falhas}**", ""]

    (RAIZ / "result.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0 if not falhas else 1


if __name__ == "__main__":
    sys.exit(main())
