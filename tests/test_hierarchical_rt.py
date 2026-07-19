"""RT do codec hierárquico #TCF.8H (weld T-CODE-TCF8H-WELD, ADR-0031).

Gate de CAPACIDADE: decode(encode_hierarchical(x)) == x nos clássicos de transmissão
(cadastro, pedido, telemetria) e nas bordas da classe coberta. O compressor de coluna
(L1) é reusado; este módulo (L2/L3) é aditivo — o flat fica byte-idêntico (guardado
pelos test_core_rt / test_regression_v1_baseline / test_real_world_snapshots).
"""
import pytest

from tcf import decode, encode, encode_hierarchical
from tcf.hierarchical import HierarchicalError


CLASSICOS = {
    "cadastro-multi-lista": [
        {"nome": "Ana Souza", "cpf": "111.111.111-11",
         "endereco": {"rua": "Rua A, 100", "cidade": "Sao Paulo",
                      "geo": {"lat": "-23.55", "lon": "-46.63"}},
         "telefones": ["+55 11 99999-0001", "+55 11 3333-0001"],
         "emails": ["ana@acme.com.br", "ana@gmail.com"]},
        {"nome": "Bruno Lima", "cpf": "222.222.222-22",
         "endereco": {"rua": "Av. B, 1500", "cidade": "Sao Paulo",
                      "geo": {"lat": "-23.56", "lon": "-46.65"}},
         "telefones": ["+55 11 99999-0002"],
         "emails": []},
    ],
    "pedido-aninhado": [
        {"cliente": "Ana", "pedidos": [
            {"data": "2026-01", "itens": [{"produto": "Teclado", "qtd": "1"},
                                          {"produto": "Mouse", "qtd": "2"}]},
            {"data": "2026-02", "itens": [{"produto": "Monitor", "qtd": "1"}]}]},
        {"cliente": "Bruno", "pedidos": []},
    ],
    "telemetria": [
        {"device": "estufa-01",
         "sensores": {"temp": {"un": "C"}, "umid": {"un": "%"}},
         "leituras": [{"ts": "06:00", "temp": "21.4", "umid": "63.0"},
                      {"ts": "06:15", "temp": "21.6", "umid": "63.4"}]},
    ],
    "ambiguidade-mesma-chave": [
        {"cli": "Ana", "pedidos": [
            {"data": "X", "itens": [{"p": "a"}]},
            {"data": "X", "itens": [{"p": "b"}]}]}],  # count resolve (nao funde)
    "array-escalar-duplicatas": [{"nome": "Ana", "tags": ["x", "x", "y"]}],
    "array-vazio-unico": [{"nome": "Ana", "telefones": []}],
    "array-vazio-primeiro": [{"n": "Ana", "tel": []},
                             {"n": "Bob", "tel": ["t1", "t2"]}],
}


@pytest.mark.parametrize("name", list(CLASSICOS))
def test_roundtrip_classicos(name):
    doc = CLASSICOS[name]
    blob = encode_hierarchical(doc)
    assert blob.startswith("#TCF.8H")           # sem-espaco (ADR-0031)
    assert decode(blob) == doc                  # decode() auto-roteia pelo magic


def test_flat_intacto():
    # weld aditivo: single-col e multi-col inalterados
    assert decode(encode(["abc", "abcd", "abcde"])) == ["abc", "abcd", "abcde"]
    assert decode(encode({"id": ["1", "2"], "n": ["a", "b"]})) == {"id": ["1", "2"], "n": ["a", "b"]}


def test_ragged_agora_rt():
    # P1 (2026-07-15): chave OPCIONAL agora faz RT (era fail-loud). Mudança de CONTRATO.
    docs = [{"a": "1", "b": "2"}, {"a": "3"}]
    blob = encode_hierarchical(docs)
    assert "?" in blob.split("\n", 1)[0]                  # 'b' é opcional no header
    assert decode(blob) == docs


# --- P1 presença/ragged: RT dos clássicos + bordas (estudo lab 2026-07-15-0125) ---
P1_RAGGED = {
    "cadastro-campos-opcionais": [
        {"nome": "Ana", "cpf": "1", "email": "a@x", "tel": "9", "end": {"rua": "R1", "comp": "ap"}},
        {"nome": "Bruno", "cpf": "2", "tel": "8", "end": {"rua": "R2"}},
        {"nome": "Carla", "cpf": "3", "email": "c@x", "end": {"rua": "R3"}},
    ],
    "telemetria-erro-raro": [
        {"ts": "06:00", "temp": "21"},
        {"ts": "06:15", "temp": "22", "erro": "instavel"},
        {"ts": "06:30", "temp": "23"},
    ],
    "pedido-cupom-e-itens-opcionais": [
        {"cli": "Ana", "cupom": "P10", "itens": [{"p": "T", "q": "1", "obs": "x"}, {"p": "M", "q": "2"}]},
        {"cli": "Bruno", "itens": [{"p": "Mon", "q": "1"}]},
        {"cli": "Carla", "itens": []},                   # vazio ≠ ausente
        {"cli": "Daniel", "cupom": "FG"},                # itens AUSENTE
    ],
    "opcional-em-elemento-de-array": [
        {"g": [{"v": "1", "op": "a"}, {"v": "2"}]},
        {"g": []},
        {"g": [{"v": "3"}, {"v": "4", "op": "b"}]},
    ],
    "objeto-opcional-com-filho-opcional": [
        {"a": "1", "cfg": {"tema": "dark", "fonte": "14"}},
        {"a": "2"},
        {"a": "3", "cfg": {"tema": "light"}},
    ],
    "string-vazia-vs-ausente": [{"x": "1", "op": ""}, {"x": "2"}],  # ''≠ausente
    "presente-em-so-um": [{"x": "1"}, {"x": "2"}, {"x": "3", "raro": "s"}, {"x": "4"}],
    "ordem-de-chave-heterogenea": [{"a": "1", "b": "2"}, {"b": "3", "a": "4"}],
}


@pytest.mark.parametrize("name", list(P1_RAGGED))
def test_p1_ragged_rt(name):
    docs = P1_RAGGED[name]
    assert decode(encode_hierarchical(docs)) == docs


def test_p1_compat_uniforme_byte_identico():
    # dado SEM raggedness → wire idêntico ao que seria sem P1 (sem '?'); '?' só onde há opcional
    uni = [{"n": "Ana", "t": ["a", "b"], "e": {"r": "R1"}}, {"n": "Bob", "t": [], "e": {"r": "R2"}}]
    blob = encode_hierarchical(uni)
    assert "?" not in blob.split("\n", 1)[0]              # nenhum campo opcional
    assert decode(blob) == uni


# --- P3a: null em CAMPO agora faz RT (mudança de contrato 2026-07-15; máscara '0'=None) ---
P3A_NULL = {
    "null-escalar": [{"x": "a"}, {"x": None}, {"x": "b"}],
    "null-objeto": [{"cfg": {"t": "dark", "f": "14"}}, {"cfg": None}, {"cfg": {"t": "light"}}],
    "null-array (≠[] ≠presente)": [{"itens": ["a", "b"]}, {"itens": None}, {"itens": []}],
    "all-null": [{"x": None}, {"x": None}],
    "null+ausente (ausente≠null)": [{"a": "1", "b": "2"}, {"a": "3", "b": None}, {"a": "4"}],
    "4-vias null/'null'/''/ausente": [{"x": None}, {"x": "null"}, {"x": ""}, {"y": "so-y"}],
    "null aninhado em objeto": [{"o": {"a": "1", "b": None}}, {"o": {"a": "2", "b": "x"}}],
}


@pytest.mark.parametrize("name", list(P3A_NULL))
def test_p3a_null_campo_rt(name):
    docs = P3A_NULL[name]
    assert decode(encode_hierarchical(docs)) == docs


def test_p3a_quatro_vias_distintas():
    # null(None) ≠ "null"(str) ≠ ""(str) ≠ ausente — a assinatura do P3a
    docs = [{"x": None}, {"x": "null"}, {"x": ""}, {"y": "outra"}]
    back = decode(encode_hierarchical(docs))
    assert back == docs
    assert back[0]["x"] is None and back[1]["x"] == "null" and back[2]["x"] == ""
    assert "x" not in back[3]                            # ausente ≠ null


def test_p3a_mask_reservado_agora_null():
    # o slot '0' da máscara (reservado no P1) agora materializa None (era fail-loud)
    from tcf.encoder import encode as _enc_col
    mask_body = _enc_col([".", "0"])
    scalar_body = _enc_col(["A"])
    blob = f"#TCF.8Hx?:{len(mask_body.encode())}\n{mask_body}{scalar_body}"
    assert decode(blob) == [{"x": "A"}, {"x": None}]


# --- P3b: null em ELEMENTO de array agora faz RT (element-mask; 2026-07-15) ---
P3B_NULL = {
    "null-no-meio": [{"tags": ["a", None, "b"]}],
    "null-inicio-fim": [{"xs": [None, "m", None]}],
    "array-todo-null": [{"xs": [None, None]}],
    "vazio≠[null]≠[v]": [{"xs": []}, {"xs": [None]}, {"xs": ["v"]}],
    "elemento-objeto-null": [{"itens": [{"p": "T", "q": "1"}, None, {"p": "M", "q": "2"}]}],
    "4-vias-no-elemento": [{"xs": [None, "", "null", "v"]}],
    "duas-listas-so-uma-null": [{"tel": ["1", None], "email": ["a@x", "b@x"]}],
    "aninhado-array-obj-array": [{"ped": [{"itens": ["x", None]}, {"itens": [None]}]}],
    "campo-opcional+elemento-null (compose)": [{"a": "1", "xs": ["v", None]}, {"a": "2"}, {"a": "3", "xs": None}],
    "campo-null+array-elem-null (compose)": [{"xs": ["a", None]}, {"xs": None}, {"ys": "outro"}],
}


@pytest.mark.parametrize("name", list(P3B_NULL))
def test_p3b_null_elemento_rt(name):
    docs = P3B_NULL[name]
    assert decode(encode_hierarchical(docs)) == docs


def test_p3b_vazio_null_valor_distintos():
    docs = [{"xs": []}, {"xs": [None]}, {"xs": ["v"]}]
    back = decode(encode_hierarchical(docs))
    assert back == docs
    assert back[0]["xs"] == [] and back[1]["xs"] == [None] and back[2]["xs"] == ["v"]


def test_p3b_emask_invalida_fail_loud():
    from tcf.encoder import encode as _enc_col
    # element-mask com char inválido → fail-loud (corrupção, nunca silenciosa)
    docs = [{"xs": ["a", None]}]                             # produz emask '.0'
    blob = encode_hierarchical(docs)
    # corromper: substituir a coluna emask por um char inválido é frágil; garante via encode
    bad_em = _enc_col([".", "Z"])                            # emask inválida
    cnt = _enc_col(["2"]); val = _enc_col(["a"])
    b = f"#TCF.8Hxs#:{len(cnt.encode())}?:{len(bad_em.encode())}[]\n{cnt}{bad_em}{val}"
    with pytest.raises(HierarchicalError, match="element-mask inválida|corrompida"):
        decode(b)


# --- fail-loud declarado (auditoria 2026-07-15): NUNCA str()-engolir fora da classe ---
def test_p3b_tipo_misto_em_elemento_fail_loud():
    with pytest.raises(HierarchicalError, match="mistos"):
        encode_hierarchical([{"xs": ["a", {"b": "1"}]}])    # escalar + objeto no mesmo array


# --- F1 (auditoria P3b): objeto vazio {} mascarado como ÚLTIMA folha (data-loss pré-existente) ---
@pytest.mark.parametrize("docs", [
    [{"a": "1"}, {"a": "2", "b": {}}],                      # opcional → {} vazio, última folha
    [{"a": {}}, {"a": None}],                               # null-P3a → {} vazio
    [{"f0": {}}, {}],                                       # dois registros, um {} opcional
    [{"x": "1"}, {"x": "2", "f0": {}}],
])
def test_f1_objeto_vazio_mascarado_ultima_folha_rt(docs):
    # controle nunca omite size → encode/decode simétricos (antes: encode aceitava, decode rejeitava)
    assert decode(encode_hierarchical(docs)) == docs


def test_f2_emask_body_corrompido_fail_loud_tipado():
    # gatilho: body HOSTIL cru `5..` (range com fim vazio) — estoura o decoder do L1.
    # (era o par ETC&TAL/ETC&TAL... emitido pelo ENCODER, que deixou de estourar com o
    # fix do BUG-SEQRLE — a emissão agora separa; o DECODER continua rejeitando blob cru.)
    from tcf.encoder import encode as _enc_col
    cnt = _enc_col(["2"])
    crash = "5..\n"
    val = _enc_col(["a", "b"])
    blob = f"#TCF.8Hxs#:{len(cnt.encode())}?:{len(crash.encode())}[]\n{cnt}{crash}{val}"
    with pytest.raises(HierarchicalError, match="coluna de controle emask corrompida"):
        decode(blob)


def test_p1_tipos_estruturais_mistos_fail_loud():
    # scalar-depois-dict / list-depois-str: eram str()-engolidos (corrupção silenciosa)
    with pytest.raises(HierarchicalError, match="mistos|divergente"):
        encode_hierarchical([{"x": "s"}, {"x": {"a": "1"}}])
    with pytest.raises(HierarchicalError, match="mistos|divergente"):
        encode_hierarchical([{"x": ["a"]}, {"x": "bc"}])


def test_p1_array_de_objetos_vazios_fail_loud():
    # [{}] colidia com arr_scalars no wire (corrupção silenciosa pré-existente do weld)
    with pytest.raises(HierarchicalError, match="sem chaves|objetos"):
        encode_hierarchical([{"g": [{}]}, {"g": [{}]}])


def test_p1_registros_sem_campos_agora_fazem_rt():
    """PROMOVIDO 2026-07-17 (P4b): [{}]×N e [] viraram `#D<N>` (contagem explícita — funil J1)."""
    for docs in ([{}], [], [{}, {}], [{}] * 7):
        back = decode(encode_hierarchical(docs))
        assert back == docs and type(back) is type(docs)
    assert encode_hierarchical([]) == "#TCF.8H#D0\n"       # pino do wire (re-pinável, ADR-0024)
    assert encode_hierarchical([{}, {}]) == "#TCF.8H#D2\n"
    a = decode(encode_hierarchical([{}, {}]))
    a[0]["k"] = 1                                          # N dicts DISTINTOS (não o mesmo objeto)
    assert a[1] == {}


def test_p1_raiz_objeto_unico_agora_faz_rt():
    """PROMOVIDO 2026-07-17 (P4b): objeto único na raiz = `#O<meta>` (desembrulhado no decode)."""
    for raiz in ({"a": "1"}, {"device": "s1", "v": [1.5, 2.5], "ok": True}, {"a": {"b": None}}):
        back = decode(encode_hierarchical(raiz))
        assert back == raiz and type(back) is dict
    assert encode_hierarchical({"a": "1"}).startswith("#TCF.8H#O")


def test_p3a_mask_invalido_fail_loud():
    from tcf.encoder import encode as _enc_col
    # máscara com char inválido (nem '.'/'-'/'0') = fail-loud (corrupção, nunca silenciosa)
    scalar_body = _enc_col(["A"])
    bad = _enc_col([".", "Z"])
    blob = f"#TCF.8Hx?:{len(bad.encode())}\n{bad}{scalar_body}"
    with pytest.raises(HierarchicalError, match="máscara inválida|corrompida"):
        decode(blob)


def test_p1_size_none_no_meio_fail_loud():
    # size omitido fora da última coluna lia bytes repetidos (corrupção pré-existente)
    with pytest.raises(HierarchicalError, match="size ausente"):
        decode("#TCF.8Ha,b\nva\nvb")


def test_p1_size_negativo_e_frame_inconsistente_fail_loud():
    with pytest.raises(HierarchicalError, match="negativo"):
        decode("#TCF.8Hx:-4\nvvvv")


def test_raiz_lista_de_valores_agora_faz_rt():
    """PROMOVIDO 2026-07-17 (P4b): lista de VALORES na raiz = `#V` (envelope; nunca escapa)."""
    for raiz in (["nao", "e", "objeto"], [1, 2, 3], [1, None, 2], [[1], [2, 3]]):
        back = decode(encode_hierarchical(raiz))
        assert back == raiz
    with pytest.raises(HierarchicalError, match="MISTA|P5"):
        encode_hierarchical([1, {"a": 2}])                 # misto continua P5 fail-loud


# --- P4b (2026-07-17): raiz generalizada — adversarial e canonicidade -------------------

def test_p4b_adversarial_fail_loud():
    for blob, motivo in [("#TCF.8H#D\n", "contagem ausente"), ("#TCF.8H#Dxx\n", "contagem lixo"),
                         ("#TCF.8H#D-1\n", "negativo"), ("#TCF.8H#D٣\n", "unicode digit"),
                         ("#TCF.8H#D2\nlixo\n", "corpo apendado"), ("#TCF.8H#E lixo", "bytes após #E"),
                         ("#TCF.8H#X\n", "kind desconhecido"), ("#TCF.8H#\n", "kind vazio")]:
        with pytest.raises(HierarchicalError):
            decode(blob), motivo


def test_p4b_O_e_V_nao_canonicos_fail_loud():
    from tcf.hierarchical import _encode_dataset
    w2 = _encode_dataset([{"a": "1"}, {"a": "2"}]).replace("#TCF.8H", "#TCF.8H#O", 1)
    with pytest.raises(HierarchicalError, match="objeto único"):
        decode(w2)                                          # #O com 2 registros
    wv = _encode_dataset([{"": "x", "b": "y"}]).replace("#TCF.8H", "#TCF.8H#V", 1)
    with pytest.raises(HierarchicalError, match="envelope"):
        decode(wv)                                          # #V com 2 campos


def test_p4b_dataset_com_campo_vazio_nao_vira_envelope():
    """[{"": "x"}] é DATASET legítimo de J0 (campo de nome vazio) — segue sem `#`."""
    ds = [{"": "x"}]
    w = encode_hierarchical(ds)
    assert not w.startswith("#TCF.8H#")
    assert decode(w) == ds


# --- E3 (2026-07-17): canal SideOutputs no .8H — aditivo, bytes idênticos ----------------

def test_e3_side_outputs_bytes_identicos_e_populado():
    from tcf.hierarchical import encode_hierarchical_so
    from tcf.side_outputs import SideOutputs
    docs = [{"id": 1, "nome": "Ana", "tags": ["x", None]}, {"id": 2, "nome": "Bob", "tags": []}]
    so = SideOutputs()
    assert encode_hierarchical_so(docs, so) == encode_hierarchical(docs)   # zero mudança de wire
    assert so.hier_info["root_kind"] == "dataset"
    assert so.hier_info["n_records"] == 2
    assert so.hier_info["cols"] == {"controle": 2, "dado": 3}              # count+emask · id/nome/leaf
    assert set(so.per_col) == {"id:scalar", "nome:scalar", "tags:count", "tags:emask",
                               "tags:arr_scalars"}
    assert so.per_col["tags:count"].body_bytes is not None                 # L1 child populado


def test_e3_root_kind_por_forma():
    from tcf.hierarchical import encode_hierarchical_so
    from tcf.side_outputs import SideOutputs
    for raiz, kind in [({"a": 1}, "O"), (42, "V"), ("", "V"), (None, "V"),
                       ({}, "E"), ([], "D"), ([{}, {}], "D"), ([1, 2], "V")]:
        so = SideOutputs()
        encode_hierarchical_so(raiz, so)
        assert so.hier_info["root_kind"] == kind, (raiz, so.hier_info)


def test_malformed_blob_fail_loud():
    with pytest.raises(HierarchicalError):
        decode("#TCF.8Hnome#:X[]\nbody")   # count size invalido


# --- nomes ADVERSARIAIS (auditoria 2026-07-15): chars da gramática do meta em NOMES ---
# Antes do escaping (portado do .8M): ','/'{' corrompiam CALADO, '['/']'/'}' TRAVAVAM o
# parse, ':'/'#' falhavam tarde, espaço inicial era comido. Agora: RT byte-exato.
ADVERSARIAL_NAMES = [
    "a:b", "c,d", "ef#", "g[h", "i{j", "a]b", "a}b",     # chars estruturais do meta
    "Order Date", " x", "x ",                            # espaços (inicial/interno/final)
    "k\\l", "a\\,b", "fim\\",                            # backslash literal + combinações
    "tudo,:#[]{}\\ junto",
]


@pytest.mark.parametrize("nome", ADVERSARIAL_NAMES)
def test_nome_adversarial_escalar_rt(nome):
    docs = [{nome: "1", "outro": "2"}, {nome: "3", "outro": "4"}]
    assert decode(encode_hierarchical(docs)) == docs


def test_nome_adversarial_em_toda_posicao_da_arvore():
    # nome com meta-chars em OBJETO, ARRAY-de-objetos e ARRAY-escalar (interações
    # escaping × colchetes estruturais × omit-closes)
    docs = [{"p,e{d": [{"it[em]": "1", "en{d": {"r,ua": "A"}}],
             "tag#s": ["x", "y"], "no}me": "Ana"}]
    assert decode(encode_hierarchical(docs)) == docs


def test_nome_escapado_no_fim_nao_quebra_omit_closes():
    # último campo DFS com nome terminando em ']'/'}': o omit-closes não pode comer
    # o closer ESCAPADO (só os estruturais)
    docs = [{"a": [{"ultimo]": "1"}]}, {"a": []}]
    assert decode(encode_hierarchical(docs)) == docs
    docs2 = [{"b": {"fecha}": "2"}}]
    assert decode(encode_hierarchical(docs2)) == docs2


# --- escape D_json (weld 2026-07-17): 3 lacunas viraram CAPACIDADE ---------------------
# Antes: `test_nome_vazio_fail_loud` / `test_nome_com_newline_fail_loud` pinavam a RECUSA.
# `{"": v}` e `{"a\nb": v}` são JSON válido (D_json) e o caminho json faz RT -> o TCF tinha de
# fazer (critério J-RT-TX => T-RT). Agora fazem. Os pinos abaixo cobrem o que SUBSTITUIU a recusa.

def test_nome_vazio_agora_faz_rt():
    """`{"": v}` é JSON válido — vira `\\z` no meta (marcador inemitível por dado)."""
    docs = [{"": "v"}]
    blob = encode_hierarchical(docs)
    assert "\\z" in blob.split("\n")[0], "nome vazio deve virar o marcador \\z no meta"
    assert decode(blob) == docs


def test_nome_vazio_LITERAL_no_meta_continua_corrupcao():
    """O SENTINELA sobrevive: TOKEN CRU vazio no header = corrupção (o `\\z` não é vazio).

    Mecânica (medida): o parser come runs de ' ,' — então `,,` NÃO produz token vazio.
    O token vazio real é um separador estrutural logo no início do campo (ex.: `:`).
    """
    with pytest.raises(HierarchicalError, match="vazio"):
        decode("#TCF.8H:2\nxy\n")                  # nome ausente antes do ':' = token vazio


def test_nome_z_real_nao_colide_com_marcador_de_vazio():
    """Injetividade: o nome `z` sai como `z`; o nome `\\z` sai com o `\\` dobrado."""
    for docs in ([{"z": "v"}], [{"\\z": "v"}], [{"": "a", "z": "b", "\\z": "c"}]):
        assert decode(encode_hierarchical(docs)) == docs


def test_nome_com_newline_agora_faz_rt():
    """`{"a\\nb": v}` é JSON válido — LF no nome vira `\\n` (meta continua 1 linha)."""
    docs = [{"a\nb": "v"}]
    blob = encode_hierarchical(docs)
    assert len(blob.split("\n")[0]) > 0 and "\\n" in blob.split("\n")[0]
    assert decode(blob) == docs


def test_lf_em_valor_agora_faz_rt_sem_tocar_o_L1():
    """A lacuna mais comum da vida real (string multilinha). O L1 nunca vê o LF."""
    docs = [{"a": "linha1\nlinha2", "b": "x"}]
    assert decode(encode_hierarchical(docs)) == docs


def test_escape_de_folha_e_injetivo():
    """`\\` e LF compõem sem ambiguidade (o `\\` é sempre dobrado primeiro)."""
    for docs in ([{"a": "\\"}], [{"a": "\\n"}], [{"a": "\n"}], [{"a": "\\\n"}],
                 [{"a": "a\\\\nb"}], [{"a": "C:\\temp\\x"}], [{"a": "\\123"}]):
        assert decode(encode_hierarchical(docs)) == docs


def test_folha_com_escape_invalido_fail_loud():
    """Blob estrangeiro: escape que o encoder NUNCA emite = corrupção tipada, nunca calada.

    Camadas (medido): o L1 tem escape PRÓPRIO e já consome `\\X` -> `X` (leniência dele,
    pré-existente). Para o nosso `_unesc_leaf` VER um `\\q`, o wire precisa trazer `\\\\q`.
    """
    blob = encode_hierarchical([{"a": "x"}])
    hostil = blob.replace("\nx\n", "\n\\\\q\n")          # wire `\\q` -> L1 entrega `\q` a nós
    with pytest.raises(HierarchicalError, match="escape invalido|dangling"):
        decode(hostil)


def test_folha_escape_dangling_fail_loud():
    """`\\` sozinho no fim da folha (inemitível: o encoder sempre dobra)."""
    blob = encode_hierarchical([{"a": "x"}])
    hostil = blob.replace("\nx\n", "\n\\\\\\\\\\\\\n")   # wire `\\\\\\` -> L1 entrega `\\\` (ímpar)
    with pytest.raises(HierarchicalError, match="dangling|escape invalido"):
        decode(hostil)


def test_chave_nao_str_erro_TIPADO_que_ensina():
    """Fora de D_json (o json coage e perde: 'loads(dumps(x)) != x'). Era TypeError CRU."""
    for k in (1, True, 3.5):
        with pytest.raises(HierarchicalError, match="deve ser str|D_json"):
            encode_hierarchical([{k: "v"}])


# --- auditoria do escape (2026-07-17): CR é D_json + cap de profundidade TOTAL ----------

def test_cr_em_valor_e_nome_faz_rt():
    """CR (`\\r`) é D_json (json.loads('"x\\ru"') é válido). A auditoria pegou: o alfabeto
    do escape não cobria CR (ValueError CRU do L1) e havia assimetria nome/valor."""
    for docs in ([{"a": "x\ry"}], [{"a": "\r"}], [{"a": "linha1\r\nlinha2"}],
                 [{"a\rb": "v"}], [{"a": ["x\ry", None, "z"]}],
                 [{"a": "\r\\n\r"}], [{"": "\r", "b\rc": "\n"}]):
        assert decode(encode_hierarchical(docs)) == docs


def test_profundidade_objeto_puro_fail_loud_tipado():
    """Auditoria: objeto puro não tinha cap NENHUM — RecursionError cru a ~497 níveis."""
    d = "x"
    for _ in range(600):
        d = {"a": d}
    with pytest.raises(HierarchicalError, match="excede o limite"):
        encode_hierarchical([d])


def test_profundidade_alternancia_evadia_o_cap():
    """Auditoria: array→objeto→array… evadia o cap por-array (o contador zerava);
    RecursionError cru a ~331 níveis com o limite de 128 NUNCA disparando."""
    d = "x"
    for _ in range(400):
        d = [{"k": d}]
    with pytest.raises(HierarchicalError, match="excede o limite"):
        encode_hierarchical([{"a": d}])


def test_profundidade_sana_continua_rt():
    """O cap TOTAL (128) não pode rejeitar profundidade legítima da classe coberta."""
    d = 7
    for i in range(40):                       # 80 níveis estruturais alternados — bem abaixo do cap
        d = [{"k": d}] if i % 2 else {"a": d}
    docs = [{"raiz": d}]
    assert decode(encode_hierarchical(docs)) == docs


def test_profundidade_parse_header_hostil_tipado():
    """O cap TOTAL vale também no PARSE: header hostil de objetos puros não estoura pilha."""
    meta = "a{" * 300 + "x" + "}" * 300
    with pytest.raises(HierarchicalError, match="excede o limite"):
        decode("#TCF.8H" + meta + "\n" + "v\n")


def test_valor_bracket_isolado_single_col_faz_rt():
    """PROMOVIDO 2026-07-17 (fix do par R0, aprovado pelo owner): era o BLOQUEADOR formal de
    J0 (corrupção silenciosa no domínio aceito — régua do funil, condição 4). Com o skip
    back-compat removido do L1 (BUG-BRACKET), o registro `]` sobrevive. J0 pleno."""
    docs = [{"a": "x"}, {"a": "]"}, {"a": "y"}]
    assert decode(encode_hierarchical(docs)) == docs
    docs2 = [{"a": "["}, {"a": "]"}, {"a": "[]"}]
    assert decode(encode_hierarchical(docs2)) == docs2
    docs3 = [{"a": "ETC & TAL"}, {"a": "ETC & TAL..."}]      # o outro R0, no .8H
    assert decode(encode_hierarchical(docs3)) == docs3


def test_escape_invalido_no_blob_fail_loud():
    # escape fora da whitelist = marcador de corrupção (unescape ESTRITO, como no .8M)
    with pytest.raises(HierarchicalError, match="nao-estrutural|dangling"):
        decode("#TCF.8H\\qx\ncorpo")


# --- property-test seedado: fuzz da classe coberta (promovido do lab 2026-07-14-2120) ---
# Guarda permanente: milhares de documentos aleatorios DENTRO da classe coberta devem
# fazer RT byte-exato. Seed fixa -> deterministico, sem flakiness. N modesto p/ a suite;
# o lab roda 8000 (fuzz.py).
def _gen_scalar(rng):
    r = rng.random()
    if r < 0.25:
        return str(rng.randint(0, 999999))
    if r < 0.45:
        return rng.choice(["ativo", "inativo", "SP", "RJ", "MG"])
    if r < 0.60:
        return rng.choice(["a,b", "x|y", "l\\m", "p:q", "c#d"])   # separadores -> escaping
    return "".join(rng.choice("abcdefghij .-_0123456789") for _ in range(rng.randint(1, 20)))


def _gen_schema(rng, depth):
    schema = {}
    for i in range(rng.randint(1, 4)):
        # ~25% dos nomes carregam chars adversariais do meta (auditoria 2026-07-15)
        nome = f"f{i}"
        if rng.random() < 0.25:
            nome += rng.choice([",a", ":b", "#c", "[d", "]e", "{f", "}g", " h", "\\i"])
        r = rng.random()
        if depth > 0 and r < 0.22:
            schema[nome] = ("obj", _gen_schema(rng, depth - 1))
        elif depth > 0 and r < 0.44:
            schema[nome] = ("arr_obj", _gen_schema(rng, depth - 1))
        elif r < 0.60:
            schema[nome] = ("arr_sca", None)
        else:
            schema[nome] = ("scalar", None)
    return schema


def _gen_record(rng, schema):
    rec = {}
    for name, (kind, sub) in schema.items():
        if kind == "scalar":
            rec[name] = _gen_scalar(rng)
        elif kind == "obj":
            rec[name] = _gen_record(rng, sub)
        elif kind == "arr_obj":
            rec[name] = [_gen_record(rng, sub) for _ in range(rng.choice([0, 1, 1, 2, 3]))]
        elif kind == "arr_sca":
            rec[name] = [_gen_scalar(rng) for _ in range(rng.choice([0, 1, 1, 2, 4]))]
    return rec


def test_fuzz_classe_coberta_seedado():
    import random
    rng = random.Random(20260714)   # seed fixa (reproduzivel)
    for _ in range(1200):
        schema = _gen_schema(rng, depth=rng.randint(0, 3))
        recs = [_gen_record(rng, schema) for _ in range(rng.randint(1, 8))]
        assert decode(encode_hierarchical(recs)) == recs


# --- P2: tipos escalares (number/bool) — tag por-coluna, 2026-07-16 ---
P2_TIPOS = {
    "int": [{"idade": 30}, {"idade": 40}],
    "float": [{"nota": 9.5}, {"nota": 10.0}],
    "int+float misto (JSON number)": [{"q": 1}, {"q": 1.5}, {"q": 2}],
    "bool": [{"ativo": True}, {"ativo": False}],
    "big-int": [{"x": 10 ** 30}],
    "negativo + zero": [{"a": -5, "b": 0}, {"a": 7, "b": -3}],
    "todos-os-tipos": [{"nome": "Ana", "idade": 30, "ativo": True, "nota": 9.5}],
    "array-de-number": [{"xs": [1, 2, 3]}, {"xs": [4]}],
    "array-de-bool": [{"flags": [True, False]}],
    "int-ULTIMA-folha (tag+size)": [{"nome": "Ana", "idade": 30}],
    "number-nullable (P2+P3a)": [{"x": 30}, {"x": None}, {"x": 40}],
    "array-number-null-elem (P2+P3b)": [{"xs": [1, None, 3]}],
    "bool-nullable + array-bool": [{"a": True, "fs": [False, True]}, {"a": None, "fs": []}],
}


@pytest.mark.parametrize("name", list(P2_TIPOS))
def test_p2_tipos_rt(name):
    docs = P2_TIPOS[name]
    assert decode(encode_hierarchical(docs)) == docs


def test_p2_disambiguacao_string_vs_tipo():
    # a assinatura do P2: string "30" ≠ int 30; string "true" ≠ bool True
    assert decode(encode_hierarchical([{"a": "30"}, {"a": "40"}])) == [{"a": "30"}, {"a": "40"}]
    assert decode(encode_hierarchical([{"a": "true"}])) == [{"a": "true"}]
    assert decode(encode_hierarchical([{"a": 30}])) == [{"a": 30}]         # int, não "30"
    assert decode(encode_hierarchical([{"a": True}])) == [{"a": True}]     # bool, não "true"


def test_p2_byte_compat_all_string():
    # dado all-string → NENHUM tag no header (byte-idêntico ao pré-P2)
    uni = [{"n": "Ana", "t": ["a", "b"]}, {"n": "Bob", "t": []}]
    meta = encode_hierarchical(uni).split("\n", 1)[0]
    assert meta == "#TCF.8Hn:8,t#:8["                                     # sem 'n'/'b' de tag
    assert decode(encode_hierarchical(uni)) == uni


def test_p2_nan_inf_fail_loud():
    for bad in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(HierarchicalError, match="NaN|Infinity"):
            encode_hierarchical([{"x": bad}])


def test_p2_tipo_misto_str_num_fail_loud():
    with pytest.raises(HierarchicalError, match="MISTOS|mistos"):
        encode_hierarchical([{"x": 30}, {"x": "texto"}])                  # int + str = P5 union
    with pytest.raises(HierarchicalError, match="MISTOS|mistos"):
        encode_hierarchical([{"xs": [1, "a"]}])                           # number + string no array


def test_p5_union_fronteira_ratificada_mensagem_ensina():
    """P5/union RATIFICADO fora do `.8` (2026-07-17). A mensagem de fail-loud ENSINA as duas
    saídas: separar por tipo OU converter a coluna toda p/ string (o fallback que o owner apontou).
    Cobre os 3 lugares: escalar-em-array, escalar-entre-registros, estrutural."""
    casos = [
        [{"v": [1, "a"]}],            # escalar misto em array
        [{"x": 1}, {"x": "a"}],       # escalar misto entre registros
        [{"v": [1, {"a": 2}]}],       # estrutural: scalar + object
        [{"x": 5}, {"x": [1, 2]}],    # estrutural: scalar + array entre registros
    ]
    for docs in casos:
        with pytest.raises(HierarchicalError, match="union") as ei:
            encode_hierarchical(docs)
        msg = str(ei.value)
        assert "string" in msg, f"mensagem deve ensinar o fallback-pra-string: {msg!r}"


def test_p5_workaround_string_realmente_funciona():
    """O que a mensagem promete: converter a coluna union toda p/ string FAZ RT (é o fallback)."""
    # union: [1, "a"] -> se o produtor stringifica tudo, vira dado válido de D_json
    docs_str = [{"v": ["1", "a"]}]                    # o mesmo array, agora homogêneo-string
    assert decode(encode_hierarchical(docs_str)) == docs_str
    docs_str2 = [{"x": "1"}, {"x": "a"}]              # campo homogêneo-string entre registros
    assert decode(encode_hierarchical(docs_str2)) == docs_str2


# --- P2 decode fail-loud (auditoria wf_10194874-083): dado tipado corrompido nunca calado/cru ---
def test_p2_bool_corrompido_fail_loud():
    from tcf.encoder import encode as _enc_col
    # bool body != 'true'/'false' → HierarchicalError (era: qualquer != 'true' → False SILENCIOSO)
    for bad in ["tru", "True", "1", "", "falseX"]:
        b = _enc_col([bad])
        blob = f"#TCF.8Hx:{len(b.encode())}b\n{b}"
        with pytest.raises(HierarchicalError, match="bool inválido"):
            decode(blob)
    # true/false válidos seguem RT
    assert decode(encode_hierarchical([{"x": True}, {"x": False}])) == [{"x": True}, {"x": False}]


def test_p2_number_corrompido_fail_loud_tipado():
    from tcf.encoder import encode as _enc_col
    for bad in ["abc", "01", "+5", "0x10"]:
        b = _enc_col([bad])
        blob = f"#TCF.8Hx:{len(b.encode())}n\n{b}"
        with pytest.raises(HierarchicalError, match="number inválido"):     # não JSONDecodeError cru
            decode(blob)


def test_p2_number_nan_inf_no_decode_fail_loud():
    from tcf.encoder import encode as _enc_col
    for bad in ["Infinity", "-Infinity", "NaN", "1e999"]:
        b = _enc_col([bad])
        blob = f"#TCF.8Hx:{len(b.encode())}n\n{b}"
        with pytest.raises(HierarchicalError, match="NaN|Infinity"):         # decode∘encode fechado
            decode(blob)


def test_p2_tag_desconhecida_fail_loud():
    # revisão owner 2026-07-16: 'x:<size>x' reinterpretava o 'x' como campo -> [] CALADO
    from tcf.encoder import encode as _enc_col
    b = _enc_col(["abc"])
    for meta in [f"x:{len(b.encode())}x", f"a:{len(b.encode())}z", f"n:{len(b.encode())}q"]:
        with pytest.raises(HierarchicalError, match="tag de tipo desconhecida"):
            decode(f"#TCF.8H{meta}\n{b}")
    # delimitador/tag válido/campo-nomeado-n seguem OK
    assert decode(encode_hierarchical([{"n": "v", "x": 30}])) == [{"n": "v", "x": 30}]


# --- P4a: array-em-array via COUNT RECURSIVO (2026-07-16; estudo lab 2026-07-16-0213) ---
P4A_NESTED = {
    "basico [[1,2],[3]]": [{"m": [[1, 2], [3]]}],
    "matriz retangular": [{"g": [[1, 2, 3], [4, 5, 6]]}],
    "profundidade 3": [{"cubo": [[[1, 2]], [[3], [4, 5]]]}],
    "inners vazios": [{"m": [[], [1], []]}],
    "[]≠[[]]≠[[1]]": [{"m": []}, {"m": [[]]}, {"m": [[1]]}],
    "arrays de arrays de OBJETOS": [{"t": [[{"n": "Ana"}, {"n": "Bob"}], [{"n": "C"}]]}],
    "null ENTRE arrays (P3b∘P4a externo)": [{"m": [[1], None, [2]]}],
    "null no inner (P3b interno)": [{"m": [[1, None, 2], [3]]}],
    "compose total P2+P3b+P4a": [{"m": [[1, None, 2], None, [3]], "r": "x", "ok": True}],
    "strings aninhadas": [{"tags": [["a", "b"], ["c"]]}],
    "bool em matriz": [{"bits": [[True, False], [False]]}],
    "campo no meio + externo vazio": [{"id": 1, "m": [[1], [2, 3]], "nome": "x"},
                                      {"id": 2, "m": [], "nome": "y"}],
    "array-em-array OPCIONAL (P1)": [{"a": "1", "m": [[1]]}, {"a": "2"}],
    "array-em-array NULL de campo (P3a)": [{"m": [[1]]}, {"m": None}],
}


@pytest.mark.parametrize("name", list(P4A_NESTED))
def test_p4a_array_em_array_rt(name):
    docs = P4A_NESTED[name]
    assert decode(encode_hierarchical(docs)) == docs


def test_p4a_fuzz_profundidade_seedado():
    import random
    rng = random.Random(20260716)

    def gen_arr(depth, st):
        k = rng.randint(0, 3)
        if depth == 0:
            base = {"n": lambda: rng.randint(0, 99), "b": lambda: rng.random() < 0.5,
                    "s": lambda: rng.choice(["a", "b,c", "x"])}[st]
            return [None if rng.random() < 0.2 else base() for _ in range(k)]
        return [None if rng.random() < 0.15 else gen_arr(depth - 1, st) for _ in range(k)]

    for _ in range(400):
        depth = rng.randint(1, 4)
        st = rng.choice(["n", "b", "s"])
        docs = [{"id": i, "m": gen_arr(depth, st)} for i in range(rng.randint(1, 4))]
        assert decode(encode_hierarchical(docs)) == docs


def test_p4a_tipo_misto_entre_niveis_fail_loud():
    # array com elemento array E elemento escalar no MESMO nível = P5 union
    with pytest.raises(HierarchicalError, match="mistos"):
        encode_hierarchical([{"m": [[1], 2]}])


# --- Hardening da auditoria P4a (wf_5fa61459-a9e): blob adulterado fail-loud, nunca calado/cru ---
def test_p4a_meta_truncado_tag_parcial_fail_loud():
    # cortar 1 byte do meta (some a tag, sobra o size) → size-explícito-na-última-string = não-canônico
    blob = encode_hierarchical([{"m": [[1, 2], [3]]}])
    m, c = blob.split("\n", 1)
    with pytest.raises(HierarchicalError, match="não-canônico|size explícito"):
        decode(m[:-1] + "\n" + c)


def test_p4a_profundidade_cap_fail_loud():
    # header hostil profundo → fail-loud tipado (era RecursionError cru); encode idem
    with pytest.raises(HierarchicalError, match="excede o limite"):
        decode("#TCF.8Hm" + "#:0[" * 1000 + "\n")
    v = [1]
    for _ in range(200):
        v = [v]
    with pytest.raises(HierarchicalError, match="excede o limite"):
        encode_hierarchical([{"m": v}])


def test_p4a_bracket_deletado_fail_loud():
    # ']' deletado no meio do meta (nível interno) não passa calado
    blob = encode_hierarchical([{"m": [[1]], "y": "z"}])
    m, c = blob.split("\n", 1)
    assert "]" in m
    m2 = m.replace("],", ",", 1)                        # deleta o ']' interno
    with pytest.raises(HierarchicalError):
        decode(m2 + "\n" + c)


def test_nome_duplicado_fail_loud():
    from tcf.encoder import encode as _enc_col
    cnt = _enc_col(["1"])
    with pytest.raises(HierarchicalError, match="duplicado"):
        decode(f"#TCF.8Ha:{len(cnt.encode())},a\n{cnt}{cnt}")


def test_corpo_perdido_e_bytes_apendados_fail_loud():
    with pytest.raises(HierarchicalError, match="frame vazio"):
        decode("#TCF.8Hx\n")                            # corpo inteiro perdido
    blob = encode_hierarchical([{"x": 30}])             # typed → all-sized
    with pytest.raises(HierarchicalError, match="não referenciados"):
        decode(blob + "LIXO")                           # bytes apendados


def test_coluna_de_dado_corrompida_fail_loud_tipado():
    # size mentiroso caindo em coluna de DADO re-tipa (era exceção crua do L1).
    # gatilho: body hostil cru `5..` (o antigo, via encoder, deixou de estourar — fix SEQRLE).
    from tcf.encoder import encode as _enc_col
    crash = "5..\n"
    blob = f"#TCF.8Hx:{len(crash.encode())},y\n{crash}" + _enc_col(["v", "w"])
    with pytest.raises(HierarchicalError, match="corrompida"):
        decode(blob)
