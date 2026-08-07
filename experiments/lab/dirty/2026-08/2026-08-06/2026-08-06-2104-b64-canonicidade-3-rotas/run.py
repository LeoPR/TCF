"""Lab 2026-08-06-2104 — canonicidade de payload b64 nas TRÊS rotas.

Refaz o `2026-08-06-2006` (T-BN-B64-VALIDATE) corrigindo uma classificação e convergindo
para uma proposta única.

    "acho que tomei algumas conclusões não muito boas e o lab ficou um pouco problemático
     (…) o objetivo é revisar a parte de B64, mas refaça o lab pra ficar consistente e os
     testes também."

## O que muda em relação ao lab anterior

1. **O lazy `bB` NÃO é padrão-ouro.** Ele valida mas não confere tamanho, e aceita payload
   estendido com **bytes zero** em silêncio. A sonda anterior não separou os dois.
   → a correção vai em **duas** rotas.
2. **`tamanho exato` não é variante opcional.** Medindo qual checagem pega o quê, nenhuma
   subsome a outra. As três juntas são o mínimo.
3. **O padding não é "decisão do owner".** Re-codificar-e-comparar é a MESMA técnica que o
   cabeçalho já usa (`f"{n:x}" != nhex`, ADR-0036) — a regra já existe, só não tinha sido
   aplicada ao payload.

VALIDAÇÃO: os wires adulterados são **materializados em `outputs/sondas/`** e relidos do
disco antes de cada decode. O `hoje` é o `decode` público REAL.

`src/tcf` intocado neste lab.
"""
import base64
import csv
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[4]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(RAIZ))

from proposta import por_que_cada_uma, valida_payload  # noqa: E402

from tcf import decode, encode  # noqa: E402

for d in ("inputs", "intermediates", "outputs", "outputs/sondas"):
    (RAIZ / d).mkdir(parents=True, exist_ok=True)


def _wj(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str) + "\n",
                 encoding="utf-8")


# ---------------------------------------------------------------- as rotas com payload b64
def gera(nome):
    if nome == "bn-B":
        return [f"v{i % 3}" for i in range(200)]
    if nome == "bn-C":
        return [f"v{i % 3}" for i in range(200)]        # mesmo dado; o modo C sai do candidato
    if nome == "denso-b1":
        return [bool(i % 2) for i in range(200)]
    if nome == "denso-b2":
        return [None if i % 3 == 0 else bool(i % 2) for i in range(200)]
    if nome == "lazy-bB":
        return [None if i % 7 == 0 else ([True, False][i % 2] if i % 3 else f"x{i % 4}")
                for i in range(200)]
    raise ValueError(nome)


def wire_de(nome, dados):
    """O wire válido da rota. `bn-C` não é emitido por default — vem do candidato."""
    if nome == "bn-C":
        from tcf.composicional.dominio_bn import candidatos
        from tcf.encoder import _encode_column
        return candidatos(dados, lambda vs: _encode_column(vs, header="val"), None)[1]
    return encode(dados)


def acha_payload(wire):
    """`(indice_da_linha, payload, prefixo)` — onde o b64 mora em cada grafia.

    Pelo MARCADOR, não pelo discriminador: o lazy `bB` usa a mesma grafia do bN modo `B`
    (domínio primeiro, `=` abre os bits), mas o índice 6 dele é `b`. Olhar o discriminador
    mandava o lazy pro ramo do denso e o `=` entrava no payload — o assert de
    byte-neutralidade pegou.
    """
    ls = wire.rstrip("\n").split("\n")
    for j, l in enumerate(ls):                          # `=` abre os bits (bN modo B, lazy bB)
        if l.startswith("="):
            return j, l[1:], "="
    if ls[0][6:7] == "C":                               # b64 logo apos o cabecalho
        return 1, ls[1], ""
    return len(ls) - 1, ls[-1], ""                      # denso: ultima linha


def monta(wire, i, prefixo, novo_payload):
    ls = wire.rstrip("\n").split("\n")
    ls[i] = prefixo + novo_payload
    return "\n".join(ls) + "\n"


# ---------------------------------------------------------------- as sondas
def _meio(p):
    return len(p) // 2


SONDAS = [
    ("s1-char-invalido", lambda p: p[:_meio(p)] + "!" + p[_meio(p):]),
    ("s2-espaco", lambda p: p[:_meio(p)] + " " + p[_meio(p):]),
    ("s3-quatro-invalidos", lambda p: p[:_meio(p)] + "!!!!" + p[_meio(p):]),
    ("s4-padding-extra", lambda p: p.rstrip("=") + "=="),
    ("s5-truncado-2", lambda p: p[:-2]),
    ("s6-truncado-4", lambda p: p[:-4]),
    # A SONDA QUE O LAB ANTERIOR NAO TINHA: extensao com bytes ZERO, base64 CANONICO.
    # Atravessa o `validate` E a checagem de bits-de-padding do `unpack_w`.
    ("s7-extensao-zero-AA", lambda p: p.rstrip("=") + "AA"),
    ("s8-extensao-zero-AAAA", lambda p: p.rstrip("=") + "AAAA"),
    ("s9-caixa-trocada", lambda p: p[:-1] + ("a" if p[-1].isupper() else "A")),
]


def classifica(fn, esperado):
    """`FAIL-LOUD TCF` / `BINASCII CRU` / `SILENCIOSO-IGUAL` / `SILENCIOSO-CORROMPIDO`."""
    try:
        obtido = fn()
    except ValueError as e:
        m = str(e)
        eh_tcf = "#TCF" in m or "bN" in m or "payload" in m or "dominio" in m
        return ("FAIL-LOUD TCF" if eh_tcf else "BINASCII CRU"), m[:70]
    except Exception as e:
        return "BINASCII CRU", f"{type(e).__name__}: {e}"[:70]
    if obtido == esperado:
        return "SILENCIOSO-IGUAL", ""
    return "SILENCIOSO-CORROMPIDO", f"{len(obtido)} valores"


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ROTAS = ["bn-B", "bn-C", "denso-b1", "denso-b2", "lazy-bB"]
    #: forma canônica do payload em cada rota (o denso emite COM padding).
    PADDED = {"denso-b1": True, "denso-b2": True}

    out = ["# Canonicidade de payload b64 — as três rotas (2026-08-06-2104)", "",
           "Refaz o lab `2026-08-06-2006` corrigindo **uma classificação** e convergindo para "
           "**uma** proposta.", "",
           "## Correção 1 — o lazy `bB` não é padrão-ouro", "",
           "O lab anterior deu a ele **48/48 fail-loud**. Ele valida, mas **não confere "
           "tamanho**, e aceita payload estendido com **bytes zero**:", ""]

    # ------------------------------------------------------------ prova da correção 1
    linhas_prova = []
    for rota in ROTAS:
        dados = gera(rota)
        w = wire_de(rota, dados)
        i, pay, pre = acha_payload(w)
        mut = monta(w, i, pre, pay.rstrip("=") + "AAAA")
        cls, msg = classifica(lambda: decode(mut), decode(w))
        linhas_prova.append((rota, w.split("\n")[0], cls, msg))
    out += ["| rota | cabeçalho | payload + `AAAA` (bytes zero) |", "|---|---|---|"]
    for rota, cab, cls, _m in linhas_prova:
        marca = "**" if cls.startswith("SILENCIOSO") else ""
        out.append(f"| `{rota}` | `{cab}` | {marca}{cls}{marca} |")
    out += ["", "A sonda do lab anterior não separava os dois porque a extensão que ela usava "
            "caía na checagem de bits-de-padding do `unpack_w` (que exige padding zerado). "
            "Estender com bytes que **são** zero atravessa essa checagem.", "",
            "**Consequência: a correção vai em duas rotas, não em uma.**", ""]

    # ------------------------------------------------------------ correção 2: nenhuma subsome
    out += ["## Correção 2 — `tamanho exato` não é variante opcional", "",
            "O lab anterior a chamou de \"recomendação\". Medindo **qual checagem pega o "
            "quê** (payload de 25 bytes, convenção sem padding):", "",
            "| adulteração | `validate` | re-codifica | tamanho |", "|---|:-:|:-:|:-:|"]
    raw_ref = bytes(range(25))
    base = base64.b64encode(raw_ref).decode().rstrip("=")
    n_ref, w_ref = 200, 1                                # 200*1/8 = 25 bytes
    provas = {
        "char inválido `!`": base[:5] + "!" + base[5:],
        "espaço": base[:5] + " " + base[5:],
        "padding `==` a mais": base + "==",
        "caixa trocada": base[:-1] + ("a" if base[-1].isupper() else "A"),
        "extensão zero `+AA`": base + "AA",
        "extensão zero `+AAAA`": base + "AAAA",
        "truncado −4": base[:-4],
    }
    for nome, b in provas.items():
        r = por_que_cada_uma(b, n_ref, w_ref)
        cel = {True: "passa", False: "**PEGA**", None: "—"}
        out.append(f"| {nome} | {cel[r['validate']]} | {cel[r['canonica']]} | "
                   f"{cel[r['tamanho']]} |")
    out += ["", "**Nenhuma subsome a outra.** A re-codificação não pega extensão com bytes "
            "zero; o tamanho não pega char inválido. As três juntas são o mínimo — e são "
            "exatamente o que o denso (`_decode_denso`) já faz.", "",
            "## Correção 3 — o padding não é decisão nova", "",
            "Re-codificar-e-comparar é a **mesma técnica** que o cabeçalho já usa para o hex "
            "(`f\"{n:x}\" != nhex`, ADR-0036). A regra de canonicidade já existe no formato; "
            "ela só não tinha sido aplicada ao payload. Cada rota declara a sua forma "
            "canônica (o denso emite **com** `=`; bN e lazy **sem**) e a checagem é sempre "
            "\"bate com a canônica desta rota\".", ""]

    # ------------------------------------------------------------ a matriz completa
    out += ["## A matriz — 9 sondas × 5 rotas, hoje × proposto", "",
            "Cada célula tem wire em `outputs/sondas/<rota>-<sonda>.tcf`, relido do disco "
            "antes do decode.", "",
            "| sonda | " + " | ".join(f"`{r}`" for r in ROTAS) + " |",
            "|---|" + "|".join([":-:"] * len(ROTAS)) + "|"]

    csv_linhas = [("rota", "sonda", "arquivo", "hoje", "proposto", "detalhe_hoje")]
    tot = {"hoje": {}, "prop": {}}
    for sonda_nome, mut_fn in SONDAS:
        cels = []
        for rota in ROTAS:
            dados = gera(rota)
            w = wire_de(rota, dados)
            i, pay, pre = acha_payload(w)
            esperado = decode(w)
            mut = monta(w, i, pre, mut_fn(pay))
            arq = RAIZ / "outputs" / "sondas" / f"{rota}-{sonda_nome}.tcf"
            arq.write_text(mut, encoding="utf-8")
            lido = arq.read_text(encoding="utf-8")       # RELE do disco

            c_hoje, m_hoje = classifica(lambda: decode(lido), esperado)
            # proposto: a validacao roda ANTES, sobre o payload do wire relido
            _i, p_mut, _pre = acha_payload(lido)
            n_, w_ = len(dados), int(lido[7:8]) if lido[6:7] in "BC" else None
            if w_ is None:                               # denso/lazy: largura no indice 7/8
                cab = lido.split("\n")[0]
                w_ = int(cab[8]) if cab[6:8] == "bB" else int(cab[7])
            try:
                valida_payload(p_mut, n_, w_, f"#TCF.8{lido[6:7]}",
                               padded=PADDED.get(rota, False))
                c_prop, m_prop = classifica(lambda: decode(lido), esperado)
            except ValueError as e:
                c_prop, m_prop = "FAIL-LOUD TCF", str(e)[:70]

            tot["hoje"][c_hoje] = tot["hoje"].get(c_hoje, 0) + 1
            tot["prop"][c_prop] = tot["prop"].get(c_prop, 0) + 1
            csv_linhas.append((rota, sonda_nome, arq.name, c_hoje, c_prop, m_hoje))
            sig = {"FAIL-LOUD TCF": "OK", "BINASCII CRU": "**cru**",
                   "SILENCIOSO-IGUAL": "**mudo**", "SILENCIOSO-CORROMPIDO": "**CORROMPE**"}
            cels.append(sig[c_hoje] if c_hoje == c_prop else f"{sig[c_hoje]}→OK")
        out.append(f"| `{sonda_nome}` | " + " | ".join(cels) + " |")

    with (RAIZ / "outputs" / "matriz-sondas.csv").open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(csv_linhas)

    n_cel = len(SONDAS) * len(ROTAS)
    out += ["", "`OK` = fail-loud TCF · `cru` = vaza `binascii` · `mudo` = aceita o wire "
            "adulterado calado · `→OK` = a proposta fecha.", "",
            "| | fail-loud TCF | binascii cru | silencioso | corrompe |",
            "|---|:-:|:-:|:-:|:-:|",
            f"| **hoje** | {tot['hoje'].get('FAIL-LOUD TCF', 0)} | "
            f"**{tot['hoje'].get('BINASCII CRU', 0)}** | "
            f"**{tot['hoje'].get('SILENCIOSO-IGUAL', 0)}** | "
            f"{tot['hoje'].get('SILENCIOSO-CORROMPIDO', 0)} |",
            f"| **proposto** | {tot['prop'].get('FAIL-LOUD TCF', 0)} | "
            f"{tot['prop'].get('BINASCII CRU', 0)} | "
            f"{tot['prop'].get('SILENCIOSO-IGUAL', 0)} | "
            f"{tot['prop'].get('SILENCIOSO-CORROMPIDO', 0)} |",
            f"", f"Total de células: **{n_cel}**. Matriz completa em "
            f"`outputs/matriz-sondas.csv`.", ""]

    # ------------------------------------------------------------ byte-neutralidade
    out += ["## Byte-neutralidade — a proposta só toca caminho de erro", "",
            "| rota | wire | bytes | RT byte-idêntico |", "|---|---|---:|:-:|"]
    ok_rt = True
    for rota in ROTAS:
        dados = gera(rota)
        w = wire_de(rota, dados)
        _wj(RAIZ / "inputs" / f"{rota}-fonte.json",
            {"rota": rota, "n": len(dados), "amostra": dados[:5]})
        _wj(RAIZ / "intermediates" / f"{rota}-dataset-consumido.json", dados)
        (RAIZ / "outputs" / f"{rota}-valido.tcf").write_text(w, encoding="utf-8")
        _wj(RAIZ / "outputs" / f"{rota}-dataset.roundtrip.json", decode(w))
        a = (RAIZ / "intermediates" / f"{rota}-dataset-consumido.json").read_bytes()
        b = (RAIZ / "outputs" / f"{rota}-dataset.roundtrip.json").read_bytes()
        # o wire valido passa pela proposta sem reclamar?
        i, pay, _pre = acha_payload(w)
        cab = w.split("\n")[0]
        w_ = int(cab[8]) if cab[6:8] == "bB" else int(cab[7])
        try:
            valida_payload(pay, len(dados), w_, "x", padded=PADDED.get(rota, False))
            passa = True
        except ValueError as e:
            passa = False
            out.append(f"| `{rota}` | — | — | **A PROPOSTA REJEITA O WIRE VALIDO: {e}** |")
        if passa:
            ok_rt &= a == b
            out.append(f"| `{rota}` | `{cab}` | {len(w.encode())} | "
                       f"{'OK' if a == b else '**DIFERE**'} |")
    out += ["", "Os wires válidos das 5 rotas **passam** pela proposta, e o roundtrip é "
            f"byte-idêntico ao consumido: **{'todos OK' if ok_rt else 'FALHA'}**. A mudança "
            "só toca caminho de erro — byte-neutra por construção.", ""]

    # ------------------------------------------------------------ o que sobra
    # ------------------------------------------------------------ o s9 e a fronteira real
    out += ["## O `s9` separa duas coisas que o lab anterior juntou", "",
            "Trocar a **caixa do último char** do payload dá resultados diferentes conforme "
            "o comprimento — e a diferença **não é acaso**:", "",
            "| rota | bits | último char tem bits mortos? | s9 |", "|---|---|:-:|---|"]
    for rota in ROTAS:
        dados = gera(rota)
        w = wire_de(rota, dados)
        cab = w.split("\n")[0]
        w_ = int(cab[8]) if cab[6:8] == "bB" else int(cab[7])
        nbytes = -(-len(dados) * w_ // 8)
        mortos = (nbytes % 3) != 0
        out.append(f"| `{rota}` | n={len(dados)}, w={w_} → {nbytes} B | "
                   f"{'**sim**' if mortos else 'não'} | "
                   f"{'a re-codificação **pega**' if mortos else 'nenhuma checagem pega'} |")
    out += ["", "Quando o payload **não** fecha em grupo de 3 bytes, o último char carrega "
            "bits que não significam nada — e trocá-lo produz uma grafia **não-canônica dos "
            "mesmos bytes**. Isso é sintaxe, e a re-codificação pega.", "",
            "Quando o payload fecha exato (o caso do `lazy-bB`: 200×3 bits = 75 B = 100 "
            "chars), **todos** os bits significam, e a troca é mudança de **conteúdo** — "
            "nenhuma validação sintática pode pegar.", "",
            "O lab anterior reportou **0 corrupção**; havia 3 células, das quais 2 são "
            "sintáticas (fechadas pela proposta) e 1 é de conteúdo (fora de escopo). A "
            "diferença entre elas é o que faltava.", "",
            "## O que a proposta NÃO resolve", "",
            "**Char válido trocado por outro char válido, em payload sem bits mortos** — é "
            "integridade de *conteúdo*, não de sintaxe. Nenhuma validação sintática pega; só "
            "checksum resolveria, e é outro ticket.", "",
            "## Consequência para o weld", "",
            "| onde | mudança |", "|---|---|",
            "| `dominio_bn.decode_bn` | as 3 checagens (hoje não tem nenhuma) |",
            "| `decoder._decode_lazy_bool` | acrescentar re-codificação + tamanho exato |",
            "| `decoder._decode_denso` | **nada** — já é o padrão |", "",
            "Os `outputs/sondas/*.tcf` viram casos de teste diretos.", ""]

    (RAIZ / "result.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0 if ok_rt else 1


if __name__ == "__main__":
    sys.exit(main())
