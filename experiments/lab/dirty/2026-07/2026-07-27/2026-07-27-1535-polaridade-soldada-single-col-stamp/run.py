"""Lab 2026-07-27-1535 — a polaridade SOLDADA, rota single-col stamp.

    "se puder seguir a lógica dos labs bem acabados e demonstrar isso, pode testar o
     single-col stamp por enquanto."

Diferença deste lab para os quatro que o precederam (`1853`/`1913`/`1954`/`2126`): lá o
mecanismo vivia no lab e os artefatos eram `.tcfp` — *propostas*, que o núcleo não lia. Aqui
o mecanismo está em `src/tcf` (ADR-0035), e **os artefatos são `.tcf` de verdade**: o
`decode` público os lê.

O "antes" é reconstruível byte a byte sem checkout: a grafia anterior era exatamente
`'#TCF.8\\n' + _encode_column(dados)` — o corpo canônico não mudou, só a camada de borda foi
acrescentada. Então a comparação antes/depois é exata, não estimada.

Mede:
  A. antes × depois em 30 colunas (sintéticas + reais), com RT estrito no `decode` REAL
  B. onde a regra RECUSA e por quê — o FLOOR nunca-pior
  C. os 3 gates byte-canônicos (D1-D9, D17a, real-world)
  D. os casos que a auditoria adversarial do lab `2126` reproduziu, agora como regressão
"""
import csv
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
sys.path.insert(0, str(REPO / "src"))

from tcf import decode, encode  # noqa: E402
from tcf.composicional.polaridade import FAIXA, polariza  # noqa: E402
from tcf.encoder import _encode_column  # noqa: E402

for d in ("inputs", "intermediates", "outputs"):
    (RAIZ / d).mkdir(exist_ok=True)

SAMPLES = REPO / "datasets" / "samples"
MAGIC = "#TCF.8"


def _lcg(seed=7):
    x = seed
    while True:
        x = (1103515245 * x + 12345) % (2 ** 31)
        yield x


def sinteticas(n=200):
    g = _lcg()
    L = lambda m: next(g) % m                                       # noqa: E731
    A = lambda: chr(65 + next(g) % 26)                              # noqa: E731
    a = lambda: chr(97 + next(g) % 26)                              # noqa: E731
    H = lambda k: "".join("0123456789abcdef"[next(g) % 16] for _ in range(k))  # noqa: E731
    return {
        # --- formatadas: o regime onde a polaridade ganha
        "cpf-mascara": [f"{i % 1000:03d}.{i * 7 % 1000:03d}.{i * 13 % 1000:03d}-{i % 100:02d}"
                        for i in range(n)],
        "cnpj-mascara": [f"{L(100):02d}.{L(1000):03d}.{L(1000):03d}/0001-{L(100):02d}"
                         for _ in range(n)],
        "cartao": ["-".join(f"{L(10000):04d}" for _ in range(4)) for _ in range(n)],
        "cep": [f"{L(99999):05d}-{L(999):03d}" for _ in range(n)],
        "telefone": [f"({L(90) + 10}) 9{L(10000):04d}-{L(10000):04d}" for _ in range(n)],
        "ip": [".".join(str(L(256)) for _ in range(4)) for _ in range(n)],
        "mac": [":".join(H(2) for _ in range(6)) for _ in range(n)],
        "uuid": [f"{H(8)}-{H(4)}-{H(4)}-{H(4)}-{H(12)}" for _ in range(n)],
        "data-iso": [f"20{L(30) + 10}-{L(12) + 1:02d}-{L(28) + 1:02d}" for _ in range(n)],
        "data-br": [f"{L(28) + 1:02d}/{L(12) + 1:02d}/20{L(30) + 10}" for _ in range(n)],
        "timestamp": [f"20{L(30) + 10}-{L(12) + 1:02d}-{L(28) + 1:02d}T{L(24):02d}:"
                      f"{L(60):02d}:{L(60):02d}Z" for _ in range(n)],
        "moeda": [f"R$ {L(10000)},{L(100):02d}" for _ in range(n)],
        "coord": [f"-{L(90):02d}.{L(10 ** 6):06d}" for _ in range(n)],
        "isbn": [f"978-{L(10)}-{L(10000):04d}-{L(10000):04d}-{L(10)}" for _ in range(n)],
        "placa": [f"{A()}{A()}{A()}{L(10)}{A()}{L(100):02d}" for _ in range(n)],
        "sku": [f"{A()}{A()}-{L(100000):05d}" for _ in range(n)],
        # --- regimes onde ela deve RECUSAR
        "texto": [f"palavra{a()}" for _ in range(n)],
        "frase": [" ".join(f"{a()}{a()}{a()}{a()}" for _ in range(6)) for _ in range(n)],
        "nomes": [f"{A()}{a()}{a()}{a()} {A()}{a()}{a()}{a()}{a()}" for _ in range(n)],
        "email": [f"user{L(10000)}@d{L(9)}.com" for _ in range(n)],
        "binario-01": [str(L(2)) for _ in range(n)],
        "sem-digito": ["".join(a() for _ in range(8)) for _ in range(n)],
        # --- bordas
        "uma-linha": ["12345"],
        "vazia": [],
        "so-vazio": [""],
    }


REAIS = [("retail-stockcode", "online-retail/stockcode-2k.csv", "StockCode"),
         ("retail-description", "online-retail/description-2k.csv", "Description"),
         ("lineitem-comment", "tpch-sf001/lcomment-2k.csv", "l_comment"),
         ("cnpj-doc", "receita-cnpj/cnpj-2k.csv", "cnpj"),
         ("cnpj-data-inicio", "receita-cnpj/cnpj-2k.csv", "data_inicio"),
         ("pessoas-cpf", "br-identidades/pessoas-sample.csv", "cpf"),
         ("ibge-municipio", "ibge-municipios/ibge-municipios-sample.csv", "municipio"),
         ("tpch-phone", "tpch-sf001/customer-sample.csv", "c_phone")]


def le_real(rel, coluna, n=200):
    p = SAMPLES / rel
    if not p.exists():
        return None
    with p.open(encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        if coluna not in (r.fieldnames or []):
            raise KeyError(f"coluna {coluna!r} nao existe em {rel} (tem: {r.fieldnames})")
        vals = []
        for row in r:
            if row[coluna] == "":
                continue                        # a rota flat exige list[str]; vazio distorce
            vals.append(row[coluna])
            if len(vals) >= n:
                break
    return vals or None


def _wj(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def caso(nome, dados, real=False):
    # ANTES: a grafia anterior ao weld, reconstruida byte a byte (o corpo canonico nao mudou)
    corpo = _encode_column(dados) if dados else ""
    antes = MAGIC + "\n" + corpo
    depois = encode(dados)
    obtido = decode(depois)

    sufixo = depois.split("\n")[0][len(MAGIC):]
    escapes = sum(1 for i, c in enumerate(corpo)
                  if c == chr(92) and i + 1 < len(corpo) and corpo[i + 1].isdigit())
    _suf_calc, _ = polariza(corpo) if corpo else ("", "")

    _wj(RAIZ / "inputs" / f"{nome}-fonte.json",
        {"coluna": nome, "n": len(dados), "real": real, "amostra": dados[:4]})
    _wj(RAIZ / "intermediates" / f"{nome}-dataset-consumido.json", dados)
    (RAIZ / "outputs" / f"{nome}-antes.tcf").write_text(antes, encoding="utf-8")
    (RAIZ / "outputs" / f"{nome}-depois.tcf").write_text(depois, encoding="utf-8")
    _wj(RAIZ / "outputs" / f"{nome}-dataset.roundtrip.json", obtido)

    return {"nome": nome, "n": len(dados), "real": real,
            "antes": len(antes.encode()), "depois": len(depois.encode()),
            "escapes": escapes, "sufixo": sufixo,
            "rt": len(obtido) == len(dados) and obtido == dados
                 and all(type(x) is type(y) for x, y in zip(obtido, dados))}


def tabela(titulo, itens, out):
    out += [f"### {titulo}", "",
            "| coluna | n | antes | depois | Δ | escapes | sufixo | RT |",
            "|---|---:|---:|---:|---:|---:|:-:|:-:|"]
    for r in itens:
        d = r["depois"] - r["antes"]
        out.append(f"| `{r['nome']}` | {r['n']} | {r['antes']} | {r['depois']} | "
                   f"{'**' + format(d, '+') + '**' if d else '0'} | {r['escapes']} | "
                   f"`{r['sufixo'] or '—'}` | {'OK' if r['rt'] else '**FALHOU**'} |")
    out.append("")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    res_s = [caso(k, v) for k, v in sinteticas().items()]
    res_r = []
    for nome, rel, col in REAIS:
        v = le_real(rel, col)
        if v:
            res_r.append(caso(nome, v, real=True))
    todas = res_s + res_r

    ativa = [r for r in todas if r["sufixo"]]
    recusa = [r for r in todas if not r["sufixo"]]
    falhas = [r["nome"] for r in todas if not r["rt"]]
    pior = max((r["depois"] - r["antes"] for r in todas), default=0)

    out = ["# A polaridade SOLDADA — single-col stamp (2026-07-27-1535)", "",
           "Os quatro labs anteriores (`1853`/`1913`/`1954`/`2126`) propunham; o mecanismo "
           "vivia no lab e os artefatos eram `.tcfp`, que o núcleo não lia. **Aqui ele está "
           "em `src/tcf`** (ADR-0035) e os artefatos em `outputs/` são `.tcf` de verdade — "
           "lidos pelo `decode` público.", "",
           "O *antes* é reconstruível byte a byte sem checkout: a grafia anterior era "
           f"exatamente `'{MAGIC}\\n' + _encode_column(dados)`, porque o corpo canônico não "
           "mudou — só ganhou uma camada de borda. A comparação é **exata**, não estimada.",
           "", "## A — antes × depois", ""]
    tabela("Sintéticas", res_s, out)
    tabela("Reais (fixtures do repo)", res_r, out)

    ganho = sum(r["depois"] - r["antes"] for r in todas)
    out += ["## B — o FLOOR", "",
            f"- colunas medidas: **{len(todas)}** ({len(res_s)} sintéticas + {len(res_r)} reais)",
            f"- a polaridade **ativa** em **{len(ativa)}**, **recusa** em **{len(recusa)}**",
            f"- **pior caso: {pior:+} B** — nenhuma coluna sai maior. O FLOOR inclui o custo "
            "do próprio sufixo, e o empate fica com a grafia de hoje.",
            f"- ganho somado: **{ganho} B**",
            f"- RT estrito (valor **e** tipo, com guarda de comprimento) pelo `decode` REAL: "
            f"**{len(todas) - len(falhas)}/{len(todas)}**"
            + (f" — falha em {falhas}" if falhas else ""), "",
            "As que recusam, e o motivo — sempre o mesmo, contado:", "",
            "| coluna | escapes | por quê |", "|---|---:|---|"]
    for r in recusa:
        motivo = ("coluna sem corrida de dígito literal" if r["escapes"] == 0
                  else f"{r['escapes']} escapes não pagam as transições + o sufixo")
        out.append(f"| `{r['nome']}` | {r['escapes']} | {motivo} |")
    out.append("")

    # ---------------------------------------------------------------- C: os gates
    out += ["## C — os três gates byte-canônicos", ""]
    sys.path.insert(0, str(REPO / "tests"))
    import test_real_world_snapshots as RW  # noqa: E402
    import test_regression_v1_baseline as RG  # noqa: E402

    d19 = 0
    linhas_d19 = []
    for k, esp in RG.D1_D9_BYTES_FROZEN.items():
        v = RG._load_single_col(k)
        b = len(encode(v).encode())
        d19 += b
        linhas_d19.append((k, esp, b, decode(encode(v)) == v))
    cols = RG._load_multi_col("D17a-multi-column-mixed")
    d17 = len(encode(cols).encode())
    rw = 0
    linhas_rw = []
    for k, (esp, rel) in RW.REAL_WORLD_BYTES_FROZEN.items():
        v = RW._load_single_col(rel)
        b = len(encode(v).encode())
        rw += b
        linhas_rw.append((k, esp, b, decode(encode(v)) == v))

    out += ["| gate | pinado | medido | bate? |", "|---|---:|---:|:-:|",
            f"| **D1-D9** (9 single-col) | {RG.D1_D9_TOTAL} | {d19} | "
            f"{'OK' if d19 == RG.D1_D9_TOTAL else '**NAO**'} |",
            f"| **D17a** (multi-col `.8M`) | {RG.D17A_INVARIANT} | {d17} | "
            f"{'OK' if d17 == RG.D17A_INVARIANT else '**NAO**'} |",
            f"| **real-world** (3 × 2k) | {RW.REAL_WORLD_TOTAL} | {rw} | "
            f"{'OK' if rw == RW.REAL_WORLD_TOTAL else '**NAO**'} |", "",
            "Detalhe do D1-D9 — quais datasets a polaridade tocou:", "",
            "| dataset | pinado | medido | RT |", "|---|---:|---:|:-:|"]
    for k, esp, b, rt in linhas_d19:
        out.append(f"| {k} | {esp} | {b} | {'OK' if rt else '**FALHOU**'} |")
    out += ["", "`D17a` **não mudou**: o `.8M` está fora do escopo do weld. Confirma que a "
            "solda ficou onde foi declarada.", ""]

    # ---------------------------------------------------------------- D: regressão da auditoria
    out += ["## D — os casos da auditoria adversarial, agora como regressão", "",
            "A auditoria do lab `2126` reproduziu dois defeitos de eleição do char. A `FAIXA` "
            "passou a excluir por **classe** (só pontuação). Os dois casos, re-rodados contra "
            "o código soldado:", "",
            "| caso | o que quebrava | agora |", "|---|---|---|"]
    d_digito = ['!"#$%&\'()+-/.11.22.33', '!"#$%&\'()+-/.22.33.44']
    seed = "".join(c for c in [chr(x) for x in range(0x21, 0x7F)]
                   if c < "b" and c not in set("*~^,|" + chr(92)))
    d_letra = [seed] + [f"{i * 7 + 100000000}" for i in range(30)]
    for nome, dd, quebra in [("dígito eleito", d_digito, "`0` eleito funde com a corrida"),
                             ("letra eleita", d_letra, "`b` eleito vira `#TCF.8b` de bool")]:
        w = encode(dd)
        h = w.split("\n")[0]
        ok = decode(w) == dd
        char = h[len(MAGIC):][:1]
        out.append(f"| {nome} | {quebra} | `{h}` — char `{char}` "
                   f"({'pontuação' if char and not char.isalnum() else '**ALNUM!**'}), "
                   f"RT {'OK' if ok else '**FALHOU**'} |")
        (RAIZ / "outputs" / f"adversarial-{nome.split()[0]}.tcf").write_text(w, encoding="utf-8")
    out += ["", f"`FAIXA` = `{''.join(FAIXA)}` ({len(FAIXA)} chars). Nem dígito, nem letra, "
            "nem gramática.", ""]

    ok_gates = d19 == RG.D1_D9_TOTAL and d17 == RG.D17A_INVARIANT and rw == RW.REAL_WORLD_TOTAL
    (RAIZ / "result.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0 if (not falhas and pior <= 0 and ok_gates) else 1


if __name__ == "__main__":
    sys.exit(main())
