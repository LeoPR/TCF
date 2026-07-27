"""Lab 2026-07-27-1647 — domínio comprimido pelo core + alinhamento de bits.

    "dá pra pegar a lista e comprimir ela internamente. `M*ale / Fem2 / <b64>` — é uma
     compressão boba, mas parece que é aproveitando os índices inter tipos. faça um estudo
     disso e se dá pra aproveitar o que já tem pra fazer isso no cabeçalho, e também ver se a
     expansão está OK quando ela não casa com o número de bits, se a lista é ímpar (…) faça
     experimentos mais voltados a esse caso dos booleanos e variações de 3 até 7 tipos."

Quatro estudos:

  A. **ALINHAMENTO** — varredura exaustiva de `(n, w)`: os bits do rabo estragam algo?
  B. **DELIMITAÇÃO** — o seq-RLE **colapsa linhas do domínio**, então "leia k linhas" não
     funciona. Duas saídas: declarar o tamanho (`V-len`) ou pôr o b64 primeiro e **deduzir**
     (`V-b64`).
  C. **COMPRESSÃO DO DOMÍNIO** pelo core — quanto rende, e onde muda o cruzamento.
  D. **k de 2 a 8** — o foco pedido (bool + 3..7 tipos), com e sem null.

VALIDAÇÃO: leitores **independentes** (`le_v_len`, `le_v_b64`) reimplementam a semântica e
são comparados com os **dados originais**. Lição do lab `2026-07-26-0038`.

`src/tcf` intocado — estudo, não solda.
"""
import csv
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(RAIZ))

from dominio import (  # noqa: E402
    _b64_len, dom_core, dom_cru, dominio, largura, le_v_b64, le_v_len,
    monta_v_b64, monta_v_len,
)

from tcf import encode  # noqa: E402

for d in ("inputs", "intermediates", "outputs"):
    (RAIZ / d).mkdir(exist_ok=True)

SAMPLES = REPO / "datasets" / "samples"


def _wj(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    falhas = []
    out = ["# Domínio comprimido + alinhamento (2026-07-27-1647)", "",
           "Refino da escada bN (`2026-07-27-1608`) a partir de duas observações suas sobre "
           "`adult-sex-bn.tcfp`.", ""]

    # ================================================================ A: alinhamento
    out += ["## A — o alinhamento fecha? (varredura exaustiva)", "",
            "`n*w` quase nunca é múltiplo de 8, e o base64 ainda arredonda para múltiplos de "
            "3 bytes. Os bits do rabo são **lixo**. A pergunta é se o leitor para no lugar "
            "certo.", "",
            "Varrendo **todo** `n` de 1 a 40 × **todo** `w` de 1 a 6, nas duas montagens, "
            "com e sem compressão do domínio:", ""]
    total = ok = 0
    piores = []
    for w in range(1, 7):
        k = 1 << w
        for n in range(1, 41):
            vals = [f"v{i % k}" for i in range(n)]
            if len(set(vals)) < 2:
                continue
            for montar, ler, nome in ((monta_v_len, le_v_len, "V-len"),
                                      (monta_v_b64, le_v_b64, "V-b64")):
                for comp in (False, True):
                    wire, ww, kk = montar(vals, comp)
                    if wire is None:
                        continue
                    total += 1
                    try:
                        lido = ler(wire, comp)
                    except Exception as e:
                        piores.append(f"{nome} n={n} w={ww} comp={comp}: {type(e).__name__}")
                        continue
                    if lido == vals:
                        ok += 1
                    else:
                        piores.append(f"{nome} n={n} w={ww} comp={comp}")
    out += [f"- combinações testadas: **{total}**",
            f"- reconstruíram os dados originais: **{ok}/{total}**"
            + ("" if ok == total else f" — falham: {piores[:8]}"), ""]
    if ok != total:
        falhas.append("alinhamento")

    out += ["O rabo **não estraga** porque `n` viaja no cabeçalho e o leitor para nele. Mas "
            "isso é uma **obrigação do leitor**, não uma propriedade do formato: um leitor "
            "que desempacotasse até o fim do buffer devolveria valores fantasma.", "",
            "Quanto o rabo custa, em bits desperdiçados:", "",
            "| n | w=1 | w=2 | w=3 | w=4 | w=5 | w=6 |", "|---:|---:|---:|---:|---:|---:|---:|"]
    for n in (3, 5, 7, 10, 100, 200):
        cels = []
        for w in range(1, 7):
            nbytes = (n * w + 7) // 8
            b64 = _b64_len(n, w)
            desperdicio = b64 * 6 - n * w          # bits do b64 menos bits uteis
            cels.append(str(desperdicio))
        out.append(f"| {n} | " + " | ".join(cels) + " |")
    out += ["", "O desperdício é **constante em ordem de grandeza** (≤ 40 bits = 5 B), vindo "
            "do arredondamento do base64 para múltiplos de 4 chars. Em `n` grande é ruído; em "
            "`n` minúsculo é parte do porquê a proposta não se paga abaixo de ~5 linhas.", ""]

    # ================================================================ B: delimitação
    out += ["## B — onde o domínio termina? (o seq-RLE colapsa linhas)", "",
            "Este é o achado que a sua pergunta destravou. **\"Leia k linhas\" não funciona**, "
            "porque o core pode colapsar o domínio inteiro:", "",
            "| domínio | k | linhas emitidas | corpo |", "|---|---:|---:|---|"]
    for dom in (["Male", "Female"], ["100", "101", "102", "103"],
                ["A1", "A2", "A3", "A4", "A5"], ["ativo", "inativo", "suspenso"]):
        c = dom_core(dom)
        out.append(f"| `{dom}` | {len(dom)} | **{len(c.split(chr(10)))}** | `{c!r}` |")
    out += ["", "Quatro valores viram **uma** linha (`*4+1|\\100`). Duas saídas:", "",
            "| variante | como | custo de declaração |", "|---|---|---|",
            "| **V-len** | tamanho do domínio no cabeçalho (`:<hex>`) | 2-4 B |",
            "| **V-b64** | b64 **primeiro**; o resto é domínio | **0 B** |", "",
            "O comprimento do b64 é `4*ceil(ceil(n*w/8)/3)` — **deduzível de `n` e `w`, que já "
            "estão no cabeçalho**. É materialização mínima: deduz em vez de declarar.", "",
            "| coluna | V-len | V-b64 | Δ |", "|---|---:|---:|---:|"]
    for nome, vals in (("sex-100", ["Male", "Female"] * 50),
                       ("status-4-200", ["ativo", "inativo", "susp", "canc"] * 50),
                       ("num-4-200", ["100", "101", "102", "103"] * 50)):
        a = len(monta_v_len(vals, True)[0].encode())
        b = len(monta_v_b64(vals, True)[0].encode())
        out.append(f"| `{nome}` | {a} | {b} | **{b - a:+}** |")
    out.append("")

    # ================================================================ C: comprimir o domínio
    out += ["## C — comprimir o domínio com o core", "",
            "O domínio é uma mini-coluna. `_encode_column(dom)` — **zero código novo**, reusa "
            "OBAT, HCC e seq-RLE, que é exatamente o \"aproveitando os índices inter tipos\" "
            "que você viu.", "",
            "| domínio | cru | pelo core | Δ | grafia |", "|---|---:|---:|---:|---|"]
    doms = [["Male", "Female"], ["S", "N"], ["ativo", "inativo", "suspenso", "cancelado"],
            ["Private", "Self-emp-not-inc", "Local-gov", "State-gov", "Federal-gov",
             "Self-emp-inc"],
            ["2020-01-01", "2020-01-02", "2020-01-03"],
            ["AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES"]]
    for dom in doms:
        cru, cc = dom_cru(dom), dom_core(dom)
        out.append(f"| {len(dom)} valores, `{dom[0]}`… | {len(cru.encode())} | "
                   f"{len(cc.encode())} | **{len(cc.encode()) - len(cru.encode()):+}** | "
                   f"`{cc[:34]!r}` |")
    out += ["", "Rende pouco em `k` pequeno e valor curto (é onde a escada já ganhava fácil), "
            "e rende **mais** justamente onde a escada perdia: `k` grande com valor longo, "
            "porque lá o domínio é que dominava o custo.", ""]

    # ================================================================ D: k de 2 a 8
    out += ["## D — o foco: bool + 3 a 7 tipos", "",
            "Você perguntou se **7 seria o limite**. Com o `null` no slot 0, **7 valores de "
            "dado + null = 8 = 2³** — a fronteira natural é o `w` fechar em 3 bits.", "",
            "| k | w | usa o w inteiro? | sobra |", "|---:|---:|:-:|---:|"]
    for k in range(2, 10):
        w = largura(k)
        out.append(f"| {k} | {w} | {'**sim**' if k == (1 << w) else 'não'} | {(1 << w) - k} |")
    out += ["", "`k=3` e `k=5,6,7` **desperdiçam slots** (o `w` arredonda para cima). Isso não "
            "é bug — é o preço de largura fixa. `k` = potência de 2 é o caso justo.", "",
            "Medição, n=200, com e sem null, domínio cru × comprimido (variante V-b64):", "",
            "| coluna | k | w | hoje | bN cru | bN core | melhor Δ | RT |",
            "|---|---:|---:|---:|---:|---:|---:|:-:|"]
    focos = {}
    for k in range(2, 8):
        rot = ["ativo", "inativo", "suspenso", "cancelado", "revisao", "arquivado", "pendente"]
        focos[f"str-k{k}"] = [rot[i % k] for i in range(200)]
        focos[f"str-k{k}-null"] = [None if i % 9 == 0 else rot[i % k] for i in range(200)]
    focos["bool"] = ["true" if i % 2 else "false" for i in range(200)]
    focos["bool-null"] = [None if i % 9 == 0 else ("true" if i % 2 else "false")
                          for i in range(200)]
    for nome, vals in focos.items():
        hoje = len(encode([v for v in vals]).encode()) if all(
            v is not None for v in vals) else len(encode(vals).encode())
        wcru = monta_v_b64(vals, False)[0]
        wcor, w, k = monta_v_b64(vals, True)
        rt = le_v_b64(wcru, False) == vals and le_v_b64(wcor, True) == vals
        if not rt:
            falhas.append(nome)
        a, b = len(wcru.encode()), len(wcor.encode())
        _wj(RAIZ / "inputs" / f"{nome}-fonte.json",
            {"coluna": nome, "n": len(vals), "k": k, "w": w, "amostra": vals[:6]})
        _wj(RAIZ / "intermediates" / f"{nome}-dataset-consumido.json", vals)
        (RAIZ / "outputs" / f"{nome}-hoje.tcf").write_text(encode(vals), encoding="utf-8")
        (RAIZ / "outputs" / f"{nome}-bn-dominio-cru.tcfp").write_text(wcru, encoding="utf-8")
        (RAIZ / "outputs" / f"{nome}-bn-dominio-core.tcfp").write_text(wcor, encoding="utf-8")
        _wj(RAIZ / "outputs" / f"{nome}-dataset.roundtrip.json", le_v_b64(wcor, True))
        out.append(f"| `{nome}` | {k} | {w} | {hoje} | {a} | {b} | "
                   f"**{min(a, b) - hoje:+}** | {'OK' if rt else '**FALHOU**'} |")
    out.append("")

    # ================================================================ reais
    out += ["## Reais, no mesmo recorte", "",
            "| coluna | n | k | w | hoje | bN cru | bN core | melhor Δ | RT |",
            "|---|---:|---:|---:|---:|---:|---:|---:|:-:|"]
    reais = [("adult-sex", "adult-census/adult-sample.csv", "sex"),
             ("adult-race", "adult-census/adult-sample.csv", "race"),
             ("adult-workclass", "adult-census/adult-sample.csv", "workclass"),
             ("cnpj-situacao", "receita-cnpj/cnpj-2k.csv", "situacao"),
             ("cnpj-uf", "receita-cnpj/cnpj-2k.csv", "uf"),
             ("pm25-cbwd", "beijing-pm25/beijing-pm25-sample.csv", "cbwd")]
    for nome, rel, col in reais:
        p = SAMPLES / rel
        if not p.exists():
            continue
        with p.open(encoding="utf-8", newline="") as f:
            r = csv.DictReader(f)
            if col not in (r.fieldnames or []):
                raise KeyError(f"{col!r} nao existe em {rel}")
            vals = [row[col] for row in r if row[col] != ""][:2000]
        hoje = len(encode(vals).encode())
        wcru = monta_v_b64(vals, False)[0]
        wcor, w, k = monta_v_b64(vals, True)
        rt = le_v_b64(wcru, False) == vals and le_v_b64(wcor, True) == vals
        if not rt:
            falhas.append(nome)
        a, b = len(wcru.encode()), len(wcor.encode())
        (RAIZ / "outputs" / f"{nome}-bn-dominio-core.tcfp").write_text(wcor, encoding="utf-8")
        _wj(RAIZ / "outputs" / f"{nome}-dataset.roundtrip.json", le_v_b64(wcor, True))
        out.append(f"| **`{nome}`** | {len(vals)} | {k} | {w} | {hoje} | {a} | {b} | "
                   f"**{min(a, b) - hoje:+}** | {'OK' if rt else '**FALHOU**'} |")
    out += ["", f"RT pelos leitores independentes: **{'todos OK' if not falhas else falhas}**",
            ""]

    out += ["## O que fica", "",
            "1. **O alinhamento fecha**, mas por obrigação do leitor (parar em `n`), não por "
            "propriedade do formato. Merece um teste, não um comentário.",
            "2. **A delimitação do domínio era um buraco real** — o seq-RLE colapsa linhas. A "
            "saída `V-b64` custa **0 B** porque o tamanho do b64 é deduzível.",
            "3. **Comprimir o domínio pelo core não precisa de código novo** e rende mais "
            "justamente onde a escada perdia.",
            "4. **`k` potência de 2 é o caso justo**; 3, 5, 6, 7 desperdiçam slots — o preço "
            "de largura fixa. Largura variável fica pra outra conversa.", ""]

    (RAIZ / "result.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0 if not falhas else 1


if __name__ == "__main__":
    sys.exit(main())
