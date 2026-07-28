"""Lab 2026-07-27-2211 — domínio PRIMEIRO: o eixo de streaming ao lado do de bytes.

    "se deixar a lista depois e a transmissão for em stream, tem que esperar carregar tudo pra
     saber que é a lista. (…) a lista no final é só pra uma questão de lote total. Eu gostei
     desse formato, poderíamos ter os dois, e esse como formato de compressão extra."

O lab `2026-07-27-1647` escolheu **b64 primeiro** porque custa 0 B de declaração. Media o eixo
errado sozinho. Aqui os dois eixos aparecem juntos:

    bytes      quanto o wire ocupa
    prefixo    quanto o leitor precisa BUFFERIZAR antes de emitir o 1o valor

Quatro montagens: F1 (contagem de linhas), F2 (marcador `=`, padding dropado), F3 (b64
primeiro — o do lab anterior), F4 (tamanho em bytes).

VALIDAÇÃO: cada montagem tem seu **leitor independente**, comparado com os dados originais.

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

from montagens import (  # noqa: E402
    _b64_len_com_pad, _b64_len_sem_pad, le_f1, le_f2, le_f3, le_f4,
    monta_f1, monta_f2, monta_f3, monta_f4, prefixo_ate_1o_valor,
)

from tcf import encode  # noqa: E402

for d in ("inputs", "intermediates", "outputs"):
    (RAIZ / d).mkdir(exist_ok=True)

SAMPLES = REPO / "datasets" / "samples"

VARIANTES = [("F1", monta_f1, le_f1, "contagem de linhas no cabeçalho"),
             ("F2", monta_f2, le_f2, "marcador `=` abrindo o b64, padding dropado"),
             ("F3", monta_f3, le_f3, "b64 primeiro, domínio no fim"),
             ("F4", monta_f4, le_f4, "tamanho em bytes no cabeçalho")]


def _wj(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def avalia(valores):
    """`{variante: (bytes, prefixo, rt)}` — cada uma pelo seu leitor independente."""
    r = {}
    for nome, montar, ler, _d in VARIANTES:
        w = montar(valores)
        if w is None:
            continue
        try:
            rt = ler(w) == valores
        except Exception:
            rt = False
        r[nome] = (len(w.encode()), prefixo_ate_1o_valor(w, nome), rt, w)
    return r


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    falhas = []
    out = ["# Domínio primeiro — o eixo de streaming (2026-07-27-2211)", "",
           "O lab `1647` escolheu **b64 primeiro** porque custa 0 B de declaração. Media o "
           "eixo errado sozinho: **com o domínio no fim, nenhum valor sai antes do payload "
           "inteiro chegar**. Aqui os dois eixos andam juntos.", "",
           "| | bytes | prefixo até o 1º valor |", "|---|---|---|",
           "| **F1** contagem de linhas | +1-2 B | cabeçalho + domínio + 4 |",
           "| **F2** marcador `=`, padding dropado | +1 B / −0-2 B | cabeçalho + domínio + 4 |",
           "| **F3** b64 primeiro | **+0 B** | **o wire inteiro** |",
           "| **F4** tamanho em bytes | +2-4 B | cabeçalho + domínio + 4 |", "",
           "## O `=` é deduzível — e por isso pode virar marcador de abertura", "",
           "O padding do base64 sai do número de bytes, que sai de `n` e `w` — ambos no "
           "cabeçalho. Dropar e recolocar reconstrói byte a byte.", "",
           "| n | w | b64 com `=` | sem `=` | economia |", "|---:|---:|---:|---:|---:|"]
    for n, w in ((100, 1), (200, 1), (200, 2), (200, 3), (93, 3), (2000, 5)):
        a, b = _b64_len_com_pad(n, w), _b64_len_sem_pad(n, w)
        out.append(f"| {n} | {w} | {a} | {b} | **{b - a:+}** |")
    out += ["", "Foi a sua observação: o `=` como **terminador** é dispensável, e liberá-lo "
            "para **abrir** o bloco resolve a delimitação sem gastar declaração.", ""]

    # ---------------------------------------------------------------- sintéticas
    out += ["## As quatro, medidas (n=200)", "",
            "`prefixo` = bytes que o leitor precisa bufferizar antes de emitir o **1º valor**.",
            "", "| coluna | k | F1 | F2 | F3 | F4 | prefixo F1/F2/F4 | prefixo F3 |",
            "|---|---:|---:|---:|---:|---:|---:|---:|"]
    rot = ["ativo", "inativo", "suspenso", "cancelado", "revisao", "arquivado", "pendente"]
    casos = {}
    for k in (2, 3, 4, 7):
        casos[f"str-k{k}"] = [rot[i % k] for i in range(200)]
        casos[f"str-k{k}-null"] = [None if i % 9 == 0 else rot[i % k] for i in range(200)]
    casos["num-k4"] = [f"{100 + i % 4}" for i in range(200)]          # seq-RLE colapsa o dom
    for nome, vals in casos.items():
        r = avalia(vals)
        for v, (_b, _p, rt, w) in r.items():
            if not rt:
                falhas.append(f"{nome}/{v}")
            (RAIZ / "outputs" / f"{nome}-{v}.tcfp").write_text(w, encoding="utf-8")
        _wj(RAIZ / "inputs" / f"{nome}-fonte.json", {"coluna": nome, "n": len(vals),
                                                     "amostra": vals[:6]})
        _wj(RAIZ / "intermediates" / f"{nome}-dataset-consumido.json", vals)
        _wj(RAIZ / "outputs" / f"{nome}-dataset.roundtrip.json", le_f1(r["F1"][3]))
        k = len(set(v for v in vals if v is not None)) + (1 if None in vals else 0)
        out.append(f"| `{nome}` | {k} | {r['F1'][0]} | {r['F2'][0]} | {r['F3'][0]} | "
                   f"{r['F4'][0]} | {r['F1'][1]} | **{r['F3'][1]}** |")
    out.append("")

    # ---------------------------------------------------------------- reais
    out += ["## Reais", "", "| coluna | n | k | F1 | F2 | F3 | F4 | prefixo F2 | prefixo F3 |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    reais = [("adult-sex", "adult-census/adult-sample.csv", "sex"),
             ("adult-workclass", "adult-census/adult-sample.csv", "workclass"),
             ("cnpj-situacao", "receita-cnpj/cnpj-2k.csv", "situacao"),
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
            vals = [row[col] for row in rd if row[col] != ""][:2000]
        r = avalia(vals)
        for v, (_b, _p, rt, w) in r.items():
            if not rt:
                falhas.append(f"{nome}/{v}")
            (RAIZ / "outputs" / f"{nome}-{v}.tcfp").write_text(w, encoding="utf-8")
        _wj(RAIZ / "outputs" / f"{nome}-dataset.roundtrip.json", le_f2(r["F2"][3]))
        out.append(f"| **`{nome}`** | {len(vals)} | {len(set(vals))} | {r['F1'][0]} | "
                   f"{r['F2'][0]} | {r['F3'][0]} | {r['F4'][0]} | {r['F2'][1]} | "
                   f"**{r['F3'][1]}** |")
    out.append("")

    # ---------------------------------------------------------------- a conclusão
    out += ["## O que os dois eixos dizem juntos", "",
            "Em bytes as quatro ficam **dentro de 3 B uma da outra** — ruído em qualquer "
            "coluna de tamanho real. Em prefixo a diferença é de **ordem de grandeza**: F3 "
            "precisa do wire inteiro, as outras precisam só do domínio.", "",
            "`cnpj-uf` (n=2000, k=28) é o caso que mostra: **F2 bufferiza ~100 B, F3 "
            "bufferiza ~1760 B** — 17× — para a mesma informação e 1 byte de diferença.", "",
            "Ou seja: **ter as duas é a resposta certa**, e a escolha não é de bytes, é de "
            "modo de transporte:", "",
            "| | quando |", "|---|---|",
            "| **domínio primeiro** (F1/F2/F4) | default — stream, pipe, resposta HTTP, "
            "qualquer consumo incremental |",
            "| **b64 primeiro** (F3) | lote fechado, arquivo em disco, quando 1-3 B importam "
            "e ninguém vai ler incrementalmente |", "",
            "Entre as três de domínio-primeiro, **F2 é a mais barata** (o `=` que abre o bloco "
            "se paga dropando o padding) e é a que você propôs. **F1 é a mais robusta**: a "
            "contagem de linhas não depende de nenhum char ser reservado.", "",
            "### O risco do F2, declarado", "",
            "O marcador `=` abre o bloco de bits. Se um **valor do domínio** começar com `=`, "
            "o leitor corta no lugar errado. Não é hipotético — `=` é char comum em dado "
            "(fórmula, base64 embutido, query string). F1 não tem esse risco.", ""]

    # o risco medido
    out += ["| domínio com valor começando em `=` | F1 | F2 |", "|---|:-:|:-:|"]
    veneno = ["=SOMA(A1)", "normal", "outro"] * 40
    r = avalia(veneno)
    out.append(f"| `['=SOMA(A1)','normal','outro']` | {'OK' if r['F1'][2] else '**FALHOU**'} | "
               f"{'OK' if r['F2'][2] else '**FALHOU**'} |")
    if not r["F1"][2]:
        falhas.append("veneno/F1")
    (RAIZ / "outputs" / "veneno-igual-F1.tcfp").write_text(r["F1"][3], encoding="utf-8")
    (RAIZ / "outputs" / "veneno-igual-F2.tcfp").write_text(r["F2"][3], encoding="utf-8")
    _wj(RAIZ / "intermediates" / "veneno-igual-dataset-consumido.json", veneno)
    out += ["", "Medido, não suposto. Se o `=` for o marcador, ele precisa ser escapado no "
            "domínio — e aí some a economia que o justificava.", ""]

    out += ["## Recomendação", "",
            "- **F1 como default**: domínio primeiro, contagem de linhas no cabeçalho. Custa "
            "1-2 B, streama, e não reserva char nenhum.",
            "- **F3 como modo extra**: b64 primeiro, para lote fechado. Ganha 1-3 B e é o que "
            "você chamou de \"formato de compressão extra\".",
            "- **F2 fica registrado**: a ideia do `=` é boa e a economia do padding é real, "
            "mas o marcador colide com dado. Vale se o `=` for escapado — o que consome de "
            "volta o que ele economiza.", "",
            f"RT pelos leitores independentes: **{'todos OK' if not falhas else falhas}**", ""]

    (RAIZ / "result.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0 if not falhas else 1


if __name__ == "__main__":
    sys.exit(main())
