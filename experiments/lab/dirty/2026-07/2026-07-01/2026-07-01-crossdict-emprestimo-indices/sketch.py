"""DESENHO RUDIMENTAR — cross-dict por EMPRESTIMO DE INDICES (H-REF-02 re-derivado).

NAO mede compressao real. Demonstra a ESTRUTURA das variantes que o owner propos, e prova
RT (reconstrucao). Owner corrige as variacoes. Exemplo: par same-domain from/to com um valor
que so' aparece em 'to' (pra mostrar o indice MOVEL).
"""

FROM = ["A", "B", "A", "C", "B"]
TO   = ["B", "C", "B", "A", "D"]     # D so' existe em 'to' -> indice movel (minted em B)

SEP = "-" * 70


def build_shared_incremental(cols):
    """O dict GLOBAL INCREMENTAL: varre as colunas na ordem, atribui id first-seen.
    O espaco de indices cresce (movel) conforme novos valores aparecem.
    Retorna (id_of, table, minted_em) — minted_em = em qual coluna o valor nasceu."""
    id_of, table, minted = {}, [], []
    for cname, vals in cols.items():
        for v in vals:
            if v not in id_of:
                id_of[v] = len(table)
                table.append(v)
                minted.append(cname)     # rastreia onde o indice "nasceu"
    return id_of, table, minted


def encode(cols, id_of):
    return {n: [id_of[v] for v in vals] for n, vals in cols.items()}


def decode(streams, table):
    return {n: [table[i] for i in ids] for n, ids in streams.items()}


cols = {"from": FROM, "to": TO}
id_of, table, minted = build_shared_incremental(cols)
streams = encode(cols, id_of)
back = decode(streams, table)

print("ENTRADA (par same-domain):")
print(f"  from = {FROM}")
print(f"  to   = {TO}   (D so' em 'to')\n")

print(SEP)
print("O DICT GLOBAL INCREMENTAL (o mesmo objeto, 3 framings):")
print(SEP)
print(f"  tabela (first-seen, ordem das colunas): {list(enumerate(table))}")
print(f"  minted em (indice NASCEU na coluna):    {list(zip(range(len(table)), minted))}")
print("  -> indice 3 (D) e' MOVEL: nasceu em 'to' (o espaco cresceu 3->4)\n")

print("FRAMING (2) 1a-COLUNA-COMO-DICT / (4) 'header ou 1a coluna e' quase o mesmo':")
print("  'from' estabelece {A:0, B:1, C:2}. 'to' EMPRESTA esses e ESTENDE com D:3.")
print("  decode: le 'from' (vira o dict) -> 'to' indexa nele + extensao {D}.\n")

print("FRAMING (5)/(6) INDICES DO OBAT VIRAM DICT / EMPRESTIMO:")
print("  o ^N do OBAT (first-seen) JA' e' esse id. Basta torna-lo GLOBAL (continuo entre colunas):")
for n, ids in streams.items():
    obat_view = []
    seen = set()
    for v, i in zip(cols[n], ids):
        obat_view.append(f"{v}=id{i}" if v not in seen else f"^{i}")
        seen.add(v)
    print(f"    {n:5}: {obat_view}")
print()

print(SEP)
print("STREAMS (indices por coluna) + RT")
print(SEP)
for n, ids in streams.items():
    print(f"  {n:5}: {ids}")
print(f"\n  RT: {back == cols}  ({'ok' if back == cols else 'FALHA'})\n")

print(SEP)
print("DE ONDE VEM O CUSTO (a dobradica, ilustrativa) — e o ANGULO MOVEL")
print(SEP)
K = len(table)
print(f"  |uniao| = K_G = {K}. Referenciar 1 de {K} valores custa ~log(K) por celula.")
print("  B2-naive: largura FIXA w(K_G) em TODA celula -> se K_G cruza 94/8836, +1 char/linha em tudo.")
print("  MOVEL/variavel: ids cedo/frequentes = estreitos; raros/tardios = largos.")
print("  -> so' os valores tardios (ex: D=id3) pagariam largura extra, NAO toda a coluna.")
print("     (esse e' o unico caminho que escapa do bucket-crossing; risco: some sob brotli.)")
