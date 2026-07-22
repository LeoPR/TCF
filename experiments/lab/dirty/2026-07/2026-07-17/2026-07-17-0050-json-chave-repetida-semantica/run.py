"""ESTUDO — o que SIGNIFICA chave repetida em JSON e como o modelo dict+array resolve.

Pergunta do owner: "o json colidiria chaves? se não, então temos uma inferência de como
reconstruir". Este lab MEDE (não opina): (1) o que o json CONSTRÓI ao importar texto com
chave repetida (simples + 2 níveis + difíceis); (2) o que o export de tipos Python permite
(e onde ele COLIDE); (3) as representações em dict+array que fazem round-trip de
multi-valor; (4) as bordas do .8H (API, wire estrangeiro, chave não-str, NFC/NFD).
Zero mudança em src/tcf. Evidência: outputs/*.txt (medições) + inputs/*.json (textos).
"""
from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3] / "src"))
sys.stdout.reconfigure(encoding="utf-8")

from tcf import decode, encode_hierarchical  # noqa: E402
from tcf.hierarchical import HierarchicalError  # noqa: E402

# textos ESTRANGEIROS (válidos como texto ECMA-404; nosso contrato os rejeita — objeto do estudo)
CASOS_TEXTO = {
    "01-raso": '{"a":1,"a":2}',
    "02-raso-intercalado": '{"a":1,"b":9,"a":2}',
    "03-nivel2-objeto": '{"o":{"a":1,"a":2}}',
    "04-nivel2-array-de-objetos": '[{"a":1,"a":2},{"a":3}]',
    "05-tipos-diferentes": '{"a":1,"a":[1,2]}',
    "06-mesmo-valor": '{"a":1,"a":1}',
    "07-tripla": '{"a":1,"a":2,"a":3}',
    "08-dup-nos-2-niveis": '{"a":1,"a":{"b":2,"b":3}}',
    "09-alvo-da-ambiguidade": '{"a":[1,2]}',
}


def main():
    for d in ("inputs", "intermediates", "outputs"):
        (HERE / d).mkdir(exist_ok=True)
    for nome, txt in CASOS_TEXTO.items():
        (HERE / "inputs" / f"{nome}.json").write_bytes(txt.encode("utf-8"))

    out = ["ESTUDO chave repetida — medições (json import/export, modelo dict+array, bordas .8H).", ""]

    # ---------- (1) IMPORT: o que o json CONSTRÓI ----------
    out.append("(1) IMPORT — json.loads em texto com chave repetida (o que ele constrói):")
    for nome, txt in CASOS_TEXTO.items():
        built = json.loads(txt)
        pares = json.loads(txt, object_pairs_hook=lambda ps: ps)
        out.append(f"  {nome:<28} {txt:<28} -> {json.dumps(built, ensure_ascii=False)}")
        if json.dumps(built, ensure_ascii=False, separators=(',', ':')) != txt.replace(" ", ""):
            out.append(f"      pares reais (pairs_hook, LOSSLESS): {pares}")
    out.append("  REGRA MEDIDA: last-wins CALADO em todo nível; posição = 1ª aparição, valor = última.")
    out.append("  ÚNICA observação sem perda: object_pairs_hook (lista de pares) — fora do modelo dict.")

    # ---------- (2) POLÍTICAS de import + a colisão do collect ----------
    out.append("")
    out.append("(2) POLÍTICAS de import possíveis (medidas) e onde cada uma perde/colide:")
    txt = CASOS_TEXTO["01-raso"]

    def p_fail(ps):
        ks = [k for k, _ in ps]
        if len(ks) != len(set(ks)):
            raise ValueError(f"chave duplicada: {sorted(set(k for k in ks if ks.count(k) > 1))}")
        return dict(ps)

    def p_first(ps):
        d = {}
        for k, v in ps:
            d.setdefault(k, v)
        return d

    def p_collect(ps):
        d = {}
        for k, v in ps:
            d.setdefault(k, []).append(v)
        return {k: (v[0] if len(v) == 1 else v) for k, v in d.items()}

    out.append(f"  P1 last-wins (DEFAULT py/js): {json.loads(txt)}  <- perda CALADA")
    out.append(f"  P2 first-wins:                {json.loads(txt, object_pairs_hook=p_first)}  <- perda CALADA")
    collected = json.loads(txt, object_pairs_hook=p_collect)
    alvo = json.loads(CASOS_TEXTO["09-alvo-da-ambiguidade"])
    out.append(f"  P3 collect->array:            {collected}")
    out.append(f"     COLISÃO PROVADA: collect('{txt}') == loads('{CASOS_TEXTO['09-alvo-da-ambiguidade']}')"
               f" -> {collected == alvo}  <- indistinguível do array LEGÍTIMO")
    out.append(f"  P4 lista-de-pares (lossless): {json.loads(txt, object_pairs_hook=lambda ps: ps)}"
               f"  <- preserva TUDO, mas SAI do modelo dict")
    try:
        json.loads(txt, object_pairs_hook=p_fail)
    except ValueError as e:
        out.append(f"  P0 fail-loud (S0 do owner):   ValueError: {e}  <- não decide pelo usuário")

    # ---------- (3) EXPORT: o dict COLIDE? (a inferência do owner) ----------
    out.append("")
    out.append("(3) EXPORT — 'o json colidiria chaves?' (a inferência de reconstrução):")
    out.append(f"  dict literal {{'a':1,'a':2}} -> {dict([('a', 1), ('a', 2)])}  <- o MODELO colapsa ANTES de serializar")
    out.append(f"  dict {{True:'x', 1:'y'}}     -> {({True: 'x', 1: 'y'})}  <- True==1: colapsa NO MODELO (hash igual)")
    d = {1: "x", "1": "y"}
    s = json.dumps(d)
    rt = json.loads(s)
    out.append(f"  *** O FURO: dumps({{1:'x','1':'y'}}) = '{s}'  <- json.dumps EMITE DUPLICATA (coerção int->str)")
    out.append(f"      loads de volta = {rt}  <- PERDA CALADA no round-trip")
    out.append(f"  dumps({{None:'x'}}) = '{json.dumps({None: 'x'})}'  <- None->'null' pode colidir com chave 'null' literal")
    out.append(f"  dumps(nan) = '{json.dumps(float('nan'))}'  <- INVÁLIDO por RFC 8259 (allow_nan=True é o DEFAULT!)")
    out.append(f"  dumps((1,2)) -> loads -> {json.loads(json.dumps((1, 2)))}  <- tuple vira list (tipo não volta)")
    for bad, nome in [({1, 2}, "set"), (b"x", "bytes")]:
        try:
            json.dumps(bad)
        except TypeError:
            out.append(f"  dumps({nome}) -> TypeError (export fail-loud)")
    out.append("  CONCLUSÃO MEDIDA: com chaves STRING o modelo NUNCA colide (a duplicata é inexpressível);")
    out.append("  o ÚNICO furo é chave NÃO-string (coerção int/None->str pode emitir duplicata/colidir).")

    # ---------- (4) REPRESENTAÇÕES multi-valor que fazem round-trip ----------
    out.append("")
    out.append("(4) REPRESENTAÇÕES de multi-valor no modelo dict+array (todas RT-medidas):")
    reps = [
        ("R1 array-valued", {"a": [1, 2]}, "canônica (HTTP APIs, xmltodict); NÃO distingue 'lista' de 'repetida' — escolha do PRODUTOR"),
        ("R2 lista-de-pares", [["a", 1], ["a", 2]], "preserva ordem+multiplicidade+duplicata; MUDA o modelo (não é objeto)"),
        ("R3 sufixo-renomeio", {"a": 1, "a__2": 2}, "colide com chave literal 'a__2' — exigiria escape (regressão ao problema)"),
        ("R4 envelope-marcador", {"a": {"__dup__": [1, 2]}}, "colide com chave literal '__dup__' — idem"),
    ]
    for nome, obj, aval in reps:
        rt_ok = json.loads(json.dumps(obj)) == obj
        out.append(f"  {nome:<22} {json.dumps(obj, ensure_ascii=False):<28} RT={rt_ok}  | {aval}")

    # ---------- (5) BORDAS do .8H ----------
    out.append("")
    out.append("(5) BORDAS do .8H (medidas):")
    out.append(f"  API: duplicata INEXPRESSÍVEL (o dict colapsa antes do encode) — TCF nunca a vê.")
    for blob in ["#TCF.8Ha,a\nx\ny\n"]:
        try:
            decode(blob)
        except HierarchicalError as e:
            out.append(f"  WIRE estrangeiro c/ coluna duplicada -> HierarchicalError: {e}  (hardening P4a)")
    for probe, rotulo in [([{1: "x"}], "chave int"), ([{True: "x"}], "chave bool"), ([{None: "x"}], "chave None")]:
        try:
            encode_hierarchical(probe)
            out.append(f"  {rotulo}: ACEITO?!")
        except HierarchicalError as e:
            out.append(f"  {rotulo}: HierarchicalError: {str(e)[:58]}  <- tipado, msg ENGANOSA p/ None")
        except TypeError as e:
            out.append(f"  {rotulo}: TypeError CRU: {str(e)[:58]}  <- rejeita (BEM), erro NÃO-tipado (registrar)")
    k1 = "café"
    k2 = unicodedata.normalize("NFD", k1)
    probe = [{k1: "a", k2: "b"}]
    ok = decode(encode_hierarchical(probe)) == probe
    out.append(f"  NFC vs NFD ('café' composto x decomposto): chaves DISTINTAS, .8H RT={ok} (sem normalização — igual ao json)")

    (HERE / "outputs" / "00-resultado.txt").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
    print("\n".join(out))


if __name__ == "__main__":
    main()
