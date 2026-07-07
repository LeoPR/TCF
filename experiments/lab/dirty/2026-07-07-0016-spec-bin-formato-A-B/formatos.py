"""formatos — Formato A vs B do corpo spec_bin, e a reutilização do stream de refs do HCC (owner).

Descoberta (grounding): o HCC já representa um binário como RLE de LITERAIS+REFERÊNCIAS:
  ['male'*3,'female'*2,'male'*2,'female'*3] -> '*3|male\\n*2|fe1\\n*2|^1\\n*3|^2\\n'
  → male=^1=bit0, female(=fe1)=^2=bit1; a corrente de refs JÁ É o bit-stream (em RLE). Os "nós já têm
  nomes e índices naturais" (owner). Pra ordenado, HCC já faz (textual). O pack (A/B) é o passo pós-HCC
  (V2-L) pro caso espalhado.

Formato B: os 2 literais DECLARADOS no topo (ordem previamente determinada 0/1), depois bits empacotados.
Formato A: literais na 1ª ocorrência (escape), bits empacotados ao redor; o 2º valor é declarado no 1º
  escape de byte MESMO que ainda não tenha ocorrido — casa com o layout nativo do HCC (reuso). Não toca src/tcf.
"""
from __future__ import annotations


def _pack(bits: str):
    pad = (-len(bits)) % 8
    padded = bits + "0" * pad
    data = bytes(int(padded[i:i + 8], 2) for i in range(0, len(padded), 8))
    return data, len(bits)


def _unpack(data: bytes, n: int) -> str:
    return "".join(f"{b:08b}" for b in data)[:n]


def _domain(values):
    dom = list(dict.fromkeys(values))                 # ordem de 1ª aparição
    return dom


def encode_B(values):
    dom = _domain(values)
    assert len(dom) == 2, "spec_bin: domínio != 2"
    idx = {dom[0]: "0", dom[1]: "1"}
    data, n = _pack("".join(idx[v] for v in values))
    return {"fmt": "B", "dom": dom, "data": data, "n": n}


def encode_A(values):
    # A e B decodificam igual (precisam dos 2 literais + bits); diferem no LAYOUT serializado.
    enc = encode_B(values)
    enc["fmt"] = "A"
    # posição da 1ª ocorrência do 2º valor (onde ele "apareceria"); no layout A ele é declarado no 1º byte.
    dom = enc["dom"]
    enc["second_first_seen"] = next((i for i, v in enumerate(values) if v == dom[1]), None)
    return enc


def decode(enc):
    dom = enc["dom"]
    bits = _unpack(enc["data"], enc["n"])
    return [dom[int(b)] for b in bits]


def serialize(enc, col="col") -> str:
    """blob textual mostrando o LAYOUT (bytes em hex — metadado de máquina). Mesmos bytes em A e B."""
    dom = enc["dom"]
    hexb = enc["data"].hex()
    if enc["fmt"] == "B":
        # 2 literais no topo, depois os bytes
        return f"#TCF.8 {col}:spec_bin:B\n{dom[0]}\n{dom[1]}\n@bytes:{hexb}\n"
    # Formato A: literal0, 1º byte, literal1 (declarado aqui mesmo sem ter ocorrido), resto dos bytes
    first, rest = hexb[:2], hexb[2:]
    return (f"#TCF.8 {col}:spec_bin:A\n{dom[0]}\n@byte:{first}\n{dom[1]}\n"
            + (f"@bytes:{rest}\n" if rest else ""))


def body_bytes(enc) -> int:
    """tamanho do corpo: 2 literais (afixo-comprimíveis) + bytes empacotados (ceil(N/8))."""
    dom = enc["dom"]
    return len(dom[0]) + len(dom[1]) + len(enc["data"])
