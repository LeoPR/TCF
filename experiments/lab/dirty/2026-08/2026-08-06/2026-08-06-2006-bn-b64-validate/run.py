"""T-BN-B64-VALIDATE — bateria de sondas de corrupção b64 × rotas com payload bit-packed.

RECONSTRUÍDO 2026-08-06 após reprovação do owner ("fictício, sem contraprova em arquivo"):
toda a evidência é MATERIALIZADA — nada vive só em memória:

    inputs/<nome>-fonte.json                    gerador/parâmetros declarados por coluna
    intermediates/<nome>-dataset-consumido.json o dado que o run efetivamente CONSOME
                                                (relido do disco, não gerado e descartado)
    outputs/<nome>-valido.tcf                   wire válido de referência (byte-inspecionável)
    outputs/<nome>-dataset.roundtrip.json       decode do wire válido — BYTE-IDÊNTICO ao
                                                consumido (assert de bytes abaixo)
    outputs/sondas/<nome>-<sonda>.tcf           CADA wire adulterado da bateria — a matriz
                                                se deriva relendo esses arquivos do disco
    outputs/matriz-sondas.csv                   sonda × rota × atual × proposto × +tam-exato
    outputs/caso-silencioso.txt                 as células silenciosas, com antes/depois

Medição (inalterada vs a 1ª versão do lab — só a evidência mudou de forma):
`decode_bn` (modos B/C) decoda b64 SEM `validate=True` — vaza `binascii.Error` cru e
aceita wire adulterado calado. Denso b1/b2 e lazy bB (`validate=True` + wrap TCF) são o
padrão-ouro. Proposta: `decode_bn_fixed.py` (módulo do lab, inspecionável).

`src/tcf` INTOCADO.
"""
import binascii
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).parent
sys.path.insert(0, str(RAIZ.parents[6] / "src"))
sys.path.insert(0, str(RAIZ))

from tcf import encode, decode  # noqa: E402
from tcf.composicional.dominio_bn import _b64_len, candidatos  # noqa: E402
from tcf.decoder import _decode_column  # noqa: E402
from tcf.encoder import _encode_column  # noqa: E402

from decode_bn_fixed import decode_bn_fixed  # noqa: E402

INP, INT, OUT = RAIZ / "inputs", RAIZ / "intermediates", RAIZ / "outputs"
SONDAS_DIR = OUT / "sondas"


def _wj(path, obj):
    """JSON canônico do lab — consumido e roundtrip passam pelo MESMO writer (diffável)."""
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- colunas (declaração)
# Cada coluna: gerador determinístico declarado (vai pro `-fonte.json`), a rota que o
# wire cobre, o LAYOUT do payload no wire (como localizar o b64) e o disc do decode_bn.
COLUNAS = {
    "bn-B": {
        "gerador": "['0','1']*100 — alternado, 2 distintos (cardinalidade mínima do bN)",
        "valores": ["0", "1"] * 100,
        "desc": "bN flat modo B (dominio primeiro, streaming), payload 34 chars ≡ 2 (mod 4)",
        "layout": "marcador", "disc": "B",
    },
    "bn-C": {
        "gerador": "['x','y']*100 — alternado, 2 distintos",
        "valores": ["x", "y"] * 100,
        "desc": "bN modo C (dominio por ultimo, lote; decodavel-nao-emitido, ADR-0036)",
        "layout": "lote", "disc": "C",
    },
    "denso-b1": {
        "gerador": "[True, False]*100 — bool puro alternado",
        "valores": [True, False] * 100,
        "desc": "denso b1 (bool puro, 1 bit) — padrão-ouro (validate=True)",
        "layout": "corpo", "disc": None,
    },
    "denso-b2": {
        "gerador": "[True, None, False]*60 — ternário com null",
        "valores": [True, None, False] * 60,
        "desc": "denso b2 (ternário, 2 bits) — padrão-ouro (validate=True)",
        "layout": "corpo", "disc": None,
    },
    "lazy-bB": {
        "gerador": "[True, 'other', None, False]*50 — união bool+str+null",
        "valores": [True, "other", None, False] * 50,
        "desc": "lazy bB (ADR-0039) — padrão-ouro (validate=True)",
        "layout": "marcador", "disc": None,
    },
    "ref-silencioso": {
        "gerador": "['0','1']*96 — alternado; n=192 -> payload 32 chars ≡ 0 (mod 4)",
        "valores": ["0", "1"] * 96,
        "desc": "bN modo B de REFERÊNCIA do caso silencioso (controle de tamanho do b64)",
        "layout": "marcador", "disc": "B",
    },
}


def _wire_valido(nome, spec, valores):
    if spec["disc"] == "C":
        wires = candidatos(valores, lambda vs: _encode_column(vs, header="val"), None)
        wire = wires[1]
        assert wire.startswith("#TCF.8C"), wire[:20]
        return wire
    wire = encode(valores)
    if spec["disc"] == "B":
        assert wire.startswith("#TCF.8B"), (nome, wire[:20])
    return wire


# ------------------------------------------------- localização do payload em cada wire
def extrai_payload(layout, wire):
    """(payload, rebuild) — rebuild(novo_payload) devolve o wire com o payload trocado."""
    if layout == "marcador":                       # bN modo B e lazy bB: linha '=<b64>'
        linhas = wire.split("\n")
        i = next(j for j, ln in enumerate(linhas) if ln.startswith("="))
        return linhas[i][1:], lambda p: "\n".join(linhas[:i] + ["=" + p] + linhas[i + 1:])
    if layout == "lote":                           # bN modo C: prefixo do corpo, tam. fixo
        cab, _, resto = wire.partition("\n")
        w, n = int(cab[7]), int(cab[8:], 16)
        nb = _b64_len(n, w)
        return resto[:nb], lambda p: cab + "\n" + p + resto[nb:]
    cab, _, corpo = wire.partition("\n")           # denso b1/b2: o corpo inteiro é o b64
    return corpo, lambda p: cab + "\n" + p


# ---------------------------------------------------------------- sondas de mutação
def _meio(p):
    return len(p) // 2


SONDAS = [
    ("s01-dollar-inicio",           lambda p: "$" + p[1:],     "1 char inválido `$` no início"),
    ("s02-exclamacao-meio",         lambda p: p[:_meio(p)] + "!" + p[_meio(p) + 1:],
     "1 char inválido `!` no meio"),
    ("s03-espaco-fim",              lambda p: p[:-1] + " ",    "1 char inválido espaço no fim"),
    ("s04-insere-4x-exclamacao-meio", lambda p: p[:_meio(p)] + "!!!!" + p[_meio(p):],
     "4 chars inválidos INSERIDOS — a contagem restante segue múltiplo de 4"),
    ("s05-igual-no-meio",           lambda p: p[:_meio(p)] + "=" + p[_meio(p) + 1:],
     "`=` (padding) no meio do payload"),
    ("s06-padding-extra-fim",       lambda p: p + "==",        "padding `==` a mais no fim"),
    ("s07-payload-curto",           lambda p: p[:-2],          "payload cortado (2 chars a menos)"),
    ("s08-payload-longo",           lambda p: p + "AA",        "payload estendido (2 chars VÁLIDOS a mais)"),
]


# ---------------------------------------------------------------- classificação
def classifica(fn_decode, esperado):
    """Roda o decode do wire-sonda e classifica. Devolve (classe, detalhe, saida|None)."""
    try:
        out = fn_decode()
    except binascii.Error as e:                    # ANTES de ValueError (é subclasse)
        return "BINASCII CRU", f"{type(e).__name__}: {e}", None
    except ValueError as e:
        return "FAIL-LOUD TCF", str(e).split("\n")[0][:100], None
    except Exception as e:                         # noqa: BLE001 — classificar, nunca esconder
        return f"OUTRO-{type(e).__name__}", str(e)[:100], None
    tipos_ok = len(out) == len(esperado) and all(type(a) is type(b) for a, b in zip(out, esperado))
    if out == esperado and tipos_ok:
        return "SILENCIOSO-IGUAL", "", out
    diffs = sum(1 for a, b in zip(out, esperado) if a != b or type(a) is not type(b))
    det = (f"len {len(esperado)}->{len(out)}, {diffs} valores divergentes; "
           f"orig[:8]={esperado[:8]!r} sonda[:8]={out[:8]!r}")
    return "SILENCIOSO-CORROMPIDO", det, out


# ---------------------------------------------------------------- main
def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    SONDAS_DIR.mkdir(parents=True, exist_ok=True)
    for velho in SONDAS_DIR.glob("*.tcf"):         # rerodar não deixa evidência velha
        velho.unlink()

    # ---- ESTÁGIO 1: fontes declaradas (inputs/) + dado materializado (intermediates/)
    for nome, spec in COLUNAS.items():
        _wj(INP / f"{nome}-fonte.json", {
            "coluna": nome,
            "rota": spec["desc"],
            "gerador": spec["gerador"],
            "n": len(spec["valores"]),
            "distintos": sorted({v for v in spec["valores"] if v is not None}, key=repr),
            "amostra": spec["valores"][:8],
            "seed": None,                          # determinístico, sem aleatoriedade
        })
        _wj(INT / f"{nome}-dataset-consumido.json", spec["valores"])

    # ---- ESTÁGIO 2: wires válidos + roundtrip como ARQUIVO (assert de bytes)
    # O dado consumido é RELIDO do intermediates/ — não o objeto em memória do estágio 1.
    dados, wires = {}, {}
    linhas_rt = []
    for nome, spec in COLUNAS.items():
        consumido = INT / f"{nome}-dataset-consumido.json"
        vals = json.loads(consumido.read_text(encoding="utf-8"))
        dados[nome] = vals
        wire = _wire_valido(nome, spec, vals)
        wires[nome] = wire
        (OUT / f"{nome}-valido.tcf").write_text(wire, encoding="utf-8", newline="")
        rt_path = OUT / f"{nome}-dataset.roundtrip.json"
        _wj(rt_path, decode(wire))
        # ROUNDTRIP É ARQUIVO: byte-idêntico ao consumido (o leitor pode dar diff)
        assert rt_path.read_bytes() == consumido.read_bytes(), nome
        # o proposto é byte-neutro por construção: mesmos valores nos wires VÁLIDOS
        if spec["disc"]:
            assert decode_bn_fixed(wire, spec["disc"], _decode_column) == vals, nome
            assert decode_bn_fixed(wire, spec["disc"], _decode_column, True) == vals, nome
        linhas_rt.append(f"{nome:15} {len(wire):4} B  roundtrip byte-idêntico  ({spec['desc']})")
    (OUT / "rt-validos.txt").write_text("\n".join(linhas_rt) + "\n", encoding="utf-8")

    # ---- ESTÁGIO 3: sondas materializadas — cada wire adulterado vira ARQUIVO .tcf
    for nome, spec in COLUNAS.items():
        wire = (OUT / f"{nome}-valido.tcf").read_text(encoding="utf-8")
        payload, rebuild = extrai_payload(spec["layout"], wire)
        for sonda_id, muta, _desc_s in SONDAS:
            (SONDAS_DIR / f"{nome}-{sonda_id}.tcf").write_text(
                rebuild(muta(payload)), encoding="utf-8", newline="")

    # ---- ESTÁGIO 4: a matriz se DERIVA dos arquivos de sonda no disco
    linhas_csv = ["sonda,rota,arquivo_sonda,comportamento_atual,detalhe_atual,"
                  "comportamento_proposto,detalhe_proposto,"
                  "comportamento_proposto_tam_exato,detalhe_proposto_tam_exato"]
    casos_silenciosos = []
    for sonda_id, _muta, _desc_s in SONDAS:
        for nome, spec in COLUNAS.items():
            vals = dados[nome]
            arq = SONDAS_DIR / f"{nome}-{sonda_id}.tcf"
            wire_sonda = arq.read_text(encoding="utf-8")

            def _atual(w=wire_sonda):
                return decode(w)

            def _proposto(w=wire_sonda, s=spec):
                if s["disc"]:
                    return decode_bn_fixed(w, s["disc"], _decode_column)
                return decode(w)                   # denso/lazy já são o padrão-ouro

            def _proposto_te(w=wire_sonda, s=spec):
                if s["disc"]:
                    return decode_bn_fixed(w, s["disc"], _decode_column, True)
                return decode(w)

            cl_a, det_a, out_a = classifica(_atual, vals)
            cl_p, det_p, _o_p = classifica(_proposto, vals)
            cl_t, det_t, _o_t = classifica(_proposto_te, vals)
            linhas_csv.append(",".join([
                sonda_id, nome, arq.name, cl_a, f'"{det_a}"',
                cl_p, f'"{det_p}"', cl_t, f'"{det_t}"',
            ]))
            if cl_a.startswith("SILENCIOSO"):
                payload = extrai_payload(spec["layout"], wires[nome])[0]
                payload_s = extrai_payload(spec["layout"], wire_sonda)[0]
                casos_silenciosos.append(
                    f"=== {sonda_id} × rota {nome} (arquivo: sondas/{arq.name}): "
                    f"ATUAL = {cl_a} -> PROPOSTO = {cl_p} -> PROPOSTO+TAMANHO-EXATO = {cl_t}\n"
                    f"payload original : {payload!r}\n"
                    f"payload sonda    : {payload_s!r}\n"
                    f"detalhe atual    : {det_a or '(valores idênticos ao original)'}\n"
                    f"valores orig[:12] : {vals[:12]!r}\n"
                    f"valores sonda[:12]: {(out_a or [])[:12]!r}\n"
                )
    (OUT / "matriz-sondas.csv").write_text("\n".join(linhas_csv) + "\n", encoding="utf-8")
    (OUT / "caso-silencioso.txt").write_text(
        "\n".join(casos_silenciosos) if casos_silenciosos
        else "(nenhum caso silencioso encontrado — hipótese NÃO confirmada)\n",
        encoding="utf-8")

    from collections import Counter
    cnt_a = Counter(l.split(",")[3] for l in linhas_csv[1:])
    cnt_p = Counter(l.split(",")[5] for l in linhas_csv[1:])
    cnt_t = Counter(l.split(",")[7] for l in linhas_csv[1:])
    print("ATUAL               :", dict(cnt_a))
    print("PROPOSTO            :", dict(cnt_p))
    print("PROPOSTO+TAM-EXATO  :", dict(cnt_t))
    print(f"roundtrips byte-idênticos: {len(COLUNAS)} colunas OK")
    print(f"sondas materializadas: {len(list(SONDAS_DIR.glob('*.tcf')))} arquivos em outputs/sondas/")
    print(f"casos silenciosos: {len(casos_silenciosos)} -> outputs/caso-silencioso.txt")


if __name__ == "__main__":
    main()
