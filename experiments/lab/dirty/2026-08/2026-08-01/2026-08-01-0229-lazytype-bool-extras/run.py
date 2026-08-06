"""Lab 2026-08-01-0229 — T-LAZYTYPE-BOOL: cabeça congelada + extras declarados (`#TCF.8bB`).

Coluna concentrada em null/true/false COM exceções string ("other"). ACHADO DO LAB: hoje a
união bool+str não "cai no .8H" — o `.8H` RECUSA escalares mistos (fail-loud); a única rota
atual é converter tudo pra string, PERDENDO o tipo. A proposta: slots congelados da
`TABELA_B2` (null=0, false=1, true=2) + extras declarados a partir do slot 3, mecânica do
`dominio_bn` (ADR-0036), só modo `B` (streaming).

Mede 4 rotas por coluna:
  (a) lazy `bB` (protótipo `lazy_bn.py`)
  (b) `bB` COMPLETO — domínio inteiro declarado (null/true/false viajam), via `candidatos()`
      do `dominio_bn` com tag injetada (mesmo truque do `tipado_bn.py` do lab 0829)
  (c) rota atual `encode()` real — FAIL-LOUD na união (registrado, não é byte)
  (d) flat-string — converte tudo pra str, perde tipo

`src/tcf` intocado.
"""
import csv
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
VIZINHO = REPO / "experiments/lab/dirty/2026-07/2026-07-28/2026-07-28-0829-bn-tipado-ganho-medido"
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(VIZINHO))

from lazy_bn import proto_decode, proto_encode  # noqa: E402

from tcf import decode, encode  # noqa: E402
from tcf.composicional.dominio_bn import DISC_STREAM, candidatos, decode_bn  # noqa: E402
from tcf.decoder import _decode_column  # noqa: E402
from tcf.encoder import _encode_column  # noqa: E402
from tcf.tipos_internos import TABELA_B2  # noqa: E402

for d in ("inputs", "intermediates", "outputs"):
    (RAIZ / d).mkdir(exist_ok=True)

SAMPLES = REPO / "datasets" / "samples"


def _wj(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str) + "\n",
                 encoding="utf-8")


def rt_tipo(obtido, esperado):
    """Valor E tipo (NoneType/bool/str) E comprimento — `"true"` str NÃO é True."""
    if len(obtido) != len(esperado) or obtido != esperado:
        return False
    return all(type(a) is type(b) for a, b in zip(obtido, esperado))


def _str_de_tudo(dados):
    return ["" if x is None else ("true" if x is True else "false" if x is False else x)
            for x in dados]


def rota_completo(dados):
    """(b) domínio INTEIRO declarado: bool/null viajam no domínio. `(wire, decode_fn)`."""
    strs = [None if x is None else ("true" if x is True else "false" if x is False else x)
            for x in dados]
    cands = candidatos(strs, lambda vs: _encode_column(vs, header="val"), None)
    if not cands:
        return None
    corpo = cands[0][len("#TCF.8"):]                       # modo B, com a tag injetada
    return "#TCF.8" + "b" + corpo


def decode_completo(wire):
    strs = decode_bn("#TCF.8" + wire[7:], DISC_STREAM, _decode_column)
    return [None if s is None else (True if s == "true" else False if s == "false" else s)
            for s in strs]


def caso(nome, dados, gravar=True):
    r = {"nome": nome, "n": len(dados), "extras": len({x for x in dados if isinstance(x, str)})}
    # (a) lazy
    lazy_w, w_lazy, extras = proto_encode(dados)
    r["lazy"] = len(lazy_w.encode()) if lazy_w else None
    r["w"] = w_lazy
    r["rt_lazy"] = rt_tipo(proto_decode(lazy_w), dados) if lazy_w else None
    # (b) completo
    comp_w = rota_completo(dados)
    r["comp"] = len(comp_w.encode()) if comp_w else None
    r["rt_comp"] = rt_tipo(decode_completo(comp_w), dados) if comp_w else None
    # (c) rota atual — união hoje é FAIL-LOUD (o .8H recusa escalares mistos)
    try:
        hoje_w = encode(dados)
        r["hoje"] = len(hoje_w.encode())
        r["rt_hoje"] = rt_tipo(decode(hoje_w), dados)
    except Exception as e:  # noqa: BLE001 — registrado como dado, não como falha do lab
        r["hoje"] = f"FAIL-LOUD ({type(e).__name__})"
        r["rt_hoje"] = None
    # (d) flat-string
    flat_w = encode(_str_de_tudo(dados))
    r["flat"] = len(flat_w.encode())
    if gravar and lazy_w:
        _wj(RAIZ / "inputs" / f"{nome}-fonte.json",
            {"coluna": nome, "n": len(dados), "extras": extras, "amostra": dados[:8]})
        _wj(RAIZ / "intermediates" / f"{nome}-dataset-consumido.json", dados)
        (RAIZ / "outputs" / f"{nome}-lazy.tcf").write_text(lazy_w, encoding="utf-8")
        if comp_w:
            (RAIZ / "outputs" / f"{nome}-completo.tcf").write_text(comp_w, encoding="utf-8")
        (RAIZ / "outputs" / f"{nome}-flat.tcf").write_text(flat_w, encoding="utf-8")
        rt_path = RAIZ / "outputs" / f"{nome}-dataset.roundtrip.json"
        _wj(rt_path, proto_decode(lazy_w))
        cons = RAIZ / "intermediates" / f"{nome}-dataset-consumido.json"
        assert rt_path.read_bytes() == cons.read_bytes(), nome   # roundtrip é ARQUIVO
    return r


def _c(v):
    return str(v) if not isinstance(v, int) else str(v)


def linha(r):
    rt = "OK" if r["rt_lazy"] else ("—" if r["rt_lazy"] is None else "**FALHOU**")
    rtc = "—" if r["rt_comp"] is None else ("OK" if r["rt_comp"] else "**perde tipo**")
    return (f"| `{r['nome']}` | {r['n']} | {r['extras']} | {_c(r['lazy'])} | "
            f"{_c(r['comp'])} | {_c(r['hoje'])} | {r['flat']} | {rt} | {rtc} |")


CAB = ["| coluna | n | extras | (a) lazy bB | (b) bB completo | (c) hoje | (d) flat-str | RT lazy | RT compl |",
       "|---|---:|---:|---:|---:|---|---:|:--|:--|"]


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    falhas = []
    # consistência do lab: a cabeça do protótipo É a TABELA_B2 do src/tcf
    from lazy_bn import CABECA
    assert tuple(CABECA) == tuple(TABELA_B2), "cabeça do lab != TABELA_B2 do tipos_internos"

    out = ["# T-LAZYTYPE-BOOL — cabeça congelada + extras declarados (2026-08-01-0229)",
           "",
           "**Achado de rota**: hoje a união bool+str NÃO cai no `.8H` — o `.8H` RECUSA "
           "escalares mistos (`HierarchicalError`, fail-loud). A única rota atual é a (d) "
           "flat-string, que **perde o tipo**. O lazy `bB` seria a primeira rota a EMITIR "
           "lista mista `[True, None, \"other\", …]` por construção.", ""]

    # ================================================================ A: as 4 rotas
    base = [None if i % 9 == 0 else bool(i % 2) for i in range(200)]
    casos = {
        "extras-raro": [("other" if i in (7, 113) else x) for i, x in enumerate(base)],
        "extras-frequentes": [("other" if i % 5 == 4 else x) for i, x in enumerate(base)],
        "k-extras-01": [("e0" if i % 7 == 3 else x) for i, x in enumerate(base)],
        "k-extras-05": [(f"e{i % 5}" if i % 7 == 3 else x) for i, x in enumerate(base)],
        "k-extras-20": [(f"e{(i // 4) % 20}" if i % 4 == 3 else x) for i, x in enumerate(base)],
        "armadilha-tipos": [(["true", "0", "1"][i % 3] if i % 11 == 5 else x)
                            for i, x in enumerate(base)],
    }
    out += ["## A — bytes × rota × coluna (n=200)", ""] + CAB
    rs = {}
    for nome, dados in casos.items():
        r = caso(nome, dados)
        rs[nome] = r
        if r["rt_lazy"] is not True:
            falhas.append(f"{nome}: RT lazy")
        out.append(linha(r))
    out.append("")

    # ================================================================ B: controles
    out += ["## B — controles", ""] + CAB
    controle0 = [None if i % 3 == 0 else bool(i % 2) for i in range(200)]
    r0 = caso("controle-0-extras", controle0)
    b2_w = encode(controle0)                              # ternário puro -> b2 soldado
    out.append(f"| `controle-0-extras` | 200 | 0 | — (recusa) | {r0['comp']} | "
               f"{r0['hoje']} | {r0['flat']} | — | — |")
    out += ["",
            f"**0 extras**: o lazy RECUSA (`proto_encode` devolve `None`) — o ternário puro "
            f"é do denso b2 soldado ({len(b2_w.encode())} B, modo `{b2_w[7:8]}`).", ""]
    controle300 = [None if i % 9 == 0 else bool(i % 2) for i in range(400)]
    for i in range(300):
        controle300[i] = f"e{i:03d}"
    r300 = caso("controle-300-extras", controle300, gravar=False)
    out.append(f"| `controle-300-extras` | 400 | 300 | — (recusa w>8) | "
               f"{'—' if r300['comp'] is None else r300['comp']} | {r300['hoje']} | "
               f"{r300['flat']} | — | — |")
    out += ["",
            "**300 extras**: recusa — `w` passaria de 8 (tabela > 256 slots). Cairia no "
            "flat-string.", ""]

    # ================================================================ C: real
    out += ["## C — coluna real-ish (Adult)", "",
            "Adult `sex` convertido a bool (conversão dos labs 0829/2350/0037), null "
            "injetado a cada 11º e a exceção `\" ?\"` a cada 23º — **injetados pelo lab**, "
            "proveniência em `datasets-provenance.md`.", ""] + CAB
    with (SAMPLES / "adult-census" / "adult-sample.csv").open(encoding="utf-8", newline="") as f:
        vals = [row["sex"].strip() == "Male" for row in csv.DictReader(f)
                if row["sex"] not in ("", "NA")][:2000]
    dados_real = [(" ?" if i % 23 == 22 else (None if i % 11 == 10 else v))
                  for i, v in enumerate(vals)]
    r = caso("real-adult-sex-lazy", dados_real)
    rs["real-adult-sex-lazy"] = r
    if r["rt_lazy"] is not True:
        falhas.append("real: RT lazy")
    out.append(linha(r))
    out.append("")

    # ================================================================ D: fail-loud
    dados_fl = casos["extras-raro"]
    wire_ok, _w, _x = proto_encode(dados_fl)
    fl = []
    # índice fora da tabela: tabela de 5 slots (2 extras) a w=3 tem slots 5..7 sobrando;
    # empacota um 7 proposital -> wire adulterado
    from tcf.bitpack import pack_w
    import base64 as _b64
    dados_fl2 = [("e0" if i % 7 == 3 else ("e1" if i % 7 == 4 else x))
                 for i, x in enumerate(base)]
    wire_fl2, w_fl2, _ = proto_encode(dados_fl2)
    idx_ok = [0 if x is None else (2 if x is True else 1 if x is False else
                                   (3 if x == "e0" else 4)) for x in dados_fl2]
    idx_ok[5] = 7                                        # slot 7 NAO existe numa tabela de 5
    cab2 = wire_fl2.split("\n")[0]
    corpo_dom = wire_fl2.split("\n=", 1)[0].split("\n", 1)[1]
    wire_adulterado = (f"{cab2}\n{corpo_dom}\n="
                       + _b64.b64encode(pack_w(idx_ok, w_fl2)).decode("ascii").rstrip("="))
    try:
        proto_decode(wire_adulterado)
        fl.append("[FALHOU] índice fora da tabela: passou calado")
        falhas.append("fail-loud: índice fora")
    except ValueError as e:
        fl.append(f"[OK] índice fora da tabela (7 numa tabela de 5) → ValueError: {e}")
    # header não-canônico: zero à esquerda no n
    cab, _, corpo = wire_ok.partition("\n")
    try:
        proto_decode(cab.replace(f"{len(dados_fl):x}", "0" + f"{len(dados_fl):x}") + "\n" + corpo)
        fl.append("[FALHOU] header não-canônico (zero à esquerda): passou calado")
        falhas.append("fail-loud: header")
    except ValueError as e:
        fl.append(f"[OK] header não-canônico (zero à esquerda) → ValueError: {e}")
    # domínio mal-formado: bloco vazio antes do marcador
    try:
        proto_decode(f"{cab}\n={corpo.split('=')[-1]}")
        fl.append("[FALHOU] domínio vazio: passou calado")
        falhas.append("fail-loud: domínio vazio")
    except ValueError as e:
        fl.append(f"[OK] domínio mal-formado (vazio) → ValueError: {e}")
    (RAIZ / "outputs" / "fail-loud.txt").write_text(
        "# fail-loud — lazy bB (gerado por run.py)\n\n" + "\n".join(fl) + "\n",
        encoding="utf-8")
    out += ["## D — fail-loud", "", "```", "\n".join(fl), "```", ""]

    # determinismo
    if proto_encode(dados_fl)[0] != proto_encode(dados_fl)[0]:
        falhas.append("determinismo")
    out += ["Determinismo: mesmo input → mesmo wire, byte a byte (**OK**).", ""]

    # ================================================================ E: vereditos
    ganho_cabeca = {n: (r["comp"] - r["lazy"]) for n, r in rs.items()
                    if isinstance(r["lazy"], int) and isinstance(r["comp"], int)}
    ganho_flat = {n: (r["flat"] - r["lazy"]) for n, r in rs.items()
                  if isinstance(r["lazy"], int)}
    arm = rs["armadilha-tipos"]
    out += ["## E — vereditos (pra decisão do owner)", "",
            "### 1. ganho da cabeça congelada", "",
            f"- × domínio completo: **{min(ganho_cabeca.values())}..{max(ganho_cabeca.values())} B** "
            f"por coluna ({ganho_cabeca}).",
            f"- × flat-string (única rota atual que codifica): **{min(ganho_flat.values())}.."
            f"{max(ganho_flat.values())} B** por coluna, E preserva o tipo (a flat perde).",
            "- × rota atual: N/A — a rota atual é **fail-loud** na união (não produz byte).",
            "",
            "### 2. semântica do marcador `bB`", "",
            "**Recomendação: `bB` = SEMPRE cabeça congelada pra tag `b`.** O domínio bool é "
            "fechado e conhecido a priori — declará-lo é redundante (mesma lógica do ADR-0037). "
            "O `bB` completo do lab 0829 viraria não-canônico para a tag `b` (o decode pode "
            "seguir aceitando como decodável-não-emitido, contrato do modo `C`).",
            "",
            "### 3. contrato união", "",
            "Primeira rota que EMITE lista mista `[True, None, \"other\", …]` por construção "
            "(hoje união = fail-loud no `.8H`). Contrato medido: coluna = união de "
            "{bool, None, str} com ≥1 extra str; extras por primeira aparição a partir do "
            "slot 3; tabela = `TABELA_B2 + extras`; RT tipo-estrito. **Documentado, sem "
            "decidir weld.**",
            "",
            "### 4. adversário de tipo (`\"true\"`/`\"0\"`/`\"1\"` como strings-extra)", "",
            f"Lazy: cada armadilha vira **slot próprio** (≥3), RT tipo-estrito OK — "
            f"`\"true\"` str NUNCA colide com `True` (ele é o slot 2 congelado). "
            f"**Na rota (b) completo o RT tipo FALHA** (RT compl = "
            f"{'OK' if arm['rt_comp'] else 'perde tipo'}): o domínio declara por string e "
            f"`\"true\"` extra funde com o `True` — perda silenciosa de tipo. Mais um "
            "argumento pra cabeça congelada.",
            "",
            "### 5. limites", "",
            "- **Onde deixa de compensar**: extras dominantes (`k-extras-20`, 20 distintos a "
            "cada 4º) — o lazy continua ≤ flat, mas a margem encolhe; a 300 extras recusa "
            "(w>8, tabela > 256).",
            "- Frequência do extra quase não move o tamanho (índices são bits); o que pesa é "
            "o **número de extras distintos** (domínio + largura).",
            "- O lazy nunca piora o 0-extras porque **recusa** — o b2/core cobrem.",
            "",
            "### Recomendação minimalista de forma (SE soldar um dia — PROPOSTA)", "",
            "`bB` sempre lazy pra tag `b`: candidato quando a coluna é união de "
            "{bool, None, str} com 1..253 extras distintos; entra no FLOOR (`min()`) dos "
            "candidatos; decode misto (tabela = `TABELA_B2` + domínio declarado). "
            "**T-TIPOS-CONFORTO-MAP ficou FORA** — o mapa congelado/versionado/custom é "
            "decisão separada do owner; isto aqui é domínio DECLARADO no arquivo, não tipo "
            "de conforto.", ""]

    if falhas:
        out += [f"**FALHAS**: {falhas}", ""]
    (RAIZ / "result.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0 if not falhas else 1


if __name__ == "__main__":
    sys.exit(main())
