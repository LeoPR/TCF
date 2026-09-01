"""TCF encoder — API publica unificada (ADR-0014).

Pipeline canonical M10 (ADR-0011, T-CODE-PACOTE1-WELD-CANONICAL):

    values (por coluna)
      -> analyze_column (features pre-pass O(N))
      -> detect_cadence_from_features (regras 1+2, ADR-0008)
      -> detect_min_len_from_features (heur v3, ADR-0010)
      -> OBAT tokeniza (processar_with_hint se cadence, senao processar)
      -> HCCSeqRLE compacta body (com seq-RLE near-identical `*N+delta|`)
      -> texto TCF

API publica unificada (ADR-0014):

    from tcf import encode, SideOutputs

    text = encode(["a", "b", "c"])              # single -> body puro
    text = encode({"id": [...], "name": [...]}) # multi -> #TCF.8M + bodies (ADR-0032)

    # Captura opcional de side outputs (debug, stats, schema)
    side = SideOutputs()
    text = encode(data, side_outputs=side)
    print(side.hcc_trace)        # trace detector HCC
    print(side.column_features)  # features pre-pass
    # ... etc

Detalhes:
- `docs/algorithms/OBAT.md`, `docs/algorithms/HCC.md`
- `docs/adr/0011-pacote1-weld-canonical.md` — pipeline M10
- `docs/adr/0013-multi-column-canonical-api.md` — header multi-col
- `docs/adr/0014-unified-api-side-outputs.md` — unificacao + side outputs

Invariantes byte-canonical guardados por `tests/test_core_rt.py` +
`tests/test_regression_v1_baseline.py` (baselines D1-D9 / D17a — o teste mede,
nao copiar o numero aqui) e `tests/test_real_world_snapshots.py` (bytes reais;
GATE de qualquer mudanca em pre-pass/OBAT/HCC). decode(encode(x))==x: ver decoder.py.
"""

from __future__ import annotations

from collections import OrderedDict

from tcf.auto_cadence import detect_cadence_from_features
from tcf.auto_min_len import detect_min_len_from_features
from tcf.column_features import analyze_column
from tcf.composicional.hcc_seqrle import HCCSeqRLE
from tcf.composicional.syntax import M8AVirtualRefsSyntax
from tcf.core.online import processar
from tcf.obat_shape import processar_with_hint
from tcf.pipeline import DEFAULT_PIPELINE, PipelineConfig
from tcf.side_outputs import SideOutputs

def _nature_apply_stats(spec, statuses: list[str]) -> dict:
    """Telemetria (byte-neutra) do encode_value de uma nature: apply-rate por
    coluna. Conta quantos valores comprimiram ('compressible') vs cairam em
    fallback literal, com o breakdown por razao (taxonomia Kim 2003). NAO afeta
    os bytes — alimenta SideOutputs.nature_apply (efeito colateral zero-custo)."""
    from collections import Counter

    by_status = Counter(statuses)
    total = len(statuses)
    compressible = by_status.get("compressible", 0)
    return {
        "spec": getattr(spec, "name", repr(spec)),
        "total": total,
        "compressible": compressible,
        "apply_rate": (compressible / total) if total else 0.0,
        "by_status": dict(by_status),
    }


# (T-QA-8 lote 3) O antigo guard `_reject_linebreaks` foi absorvido: cada ramo
# valida \n/\r FUNDIDO na passada de stringificacao (_to_str) — ramo dict em
# `_encode_multi` (BUG-06), ramo list inline abaixo (BUG-10a). Valida-se o que
# VAI SER USADO (pos-transformacao), em 1 passada. Contrato lossless
# (T-CODE-RT-EDGES bug 2): LF delimita 1 valor por linha; \n embutido
# corromperia o round-trip EM SILENCIO — fail-loud na fronteira.


# --- DISPATCH type-coherent (Passo 2, API unica: encode/decode sao a porta do dev) ---
def _lista_flat(data) -> bool:
    """list single-col FLAT: nao-vazia e todos `str` OU `None`. Lista vazia/tipada/de-dict -> .8H.

    `None` entra no flat desde a pre-alocacao do slot 0: null e' mais um valor da
    coluna, referenciado como `0`. Antes, uma unica ocorrencia expulsava a coluna inteira pro
    envelope `.8H` — que compra generalidade (aninhamento, tipos mistos) que uma coluna de
    string com nulls nao usa. Ganho medido no lab 2026-07-24-2210.
    """
    return (isinstance(data, list) and bool(data)
            and all(x is None or isinstance(x, str) for x in data))


def _tipo_single_col(data):
    """`(tag, render)` se `data` e' uma coluna single-col TIPADA; senao `None`.

    FONTE UNICA da deteccao de tipo do single-col. Antes so' o bool tinha ramo;
    generalizado p/ que cada tipo novo seja uma LINHA aqui, nao um bloco novo no `encode`.

    - `None` NAO define o tipo: ele mora no slot 0 pre-alocado e convive com qualquer tag.
      Coluna so'-null nao e' tipada -> cai no flat de string (que ja' materializa o slot).
    - `bool` ANTES de int: em Python `bool <: int`, entao a ordem e' load-bearing.
    - float nao-finito (NaN/±Inf) NAO entra: fica fora do JSON (RFC 8259) e o `.8H` ja'
      fail-loud. Deixar entrar aqui aceitaria calado o que o formato recusa.
    - Uniao bool+str(+null) NAO e' tipo unico -> `None` aqui. Quem a captura e' a rota
      LAZY BOOL `#TCF.8bB` (ADR-0039), dispensada no `encode` antes do `.8H`.
    """
    if not isinstance(data, list) or not data:
        return None
    vals = [x for x in data if x is not None]
    if not vals:
        return None
    if all(type(x) is bool for x in vals):
        # RENDER EM SLOTS CONGELADOS (ADR-0038): o core grafava `true`/`false`
        # como NOMES; agora grafa o INDICE — FONTE UNICA da tabela: `tcf/tipos_internos.py`
        # (RENDER_B; mesma tabela do denso b2, ADR-0037). Nomes seguem DECODAVEIS
        # (decodavel-nao-emitido; precedente: modo `C` da ADR-0036).
        from tcf.tipos_internos import RENDER_B

        return "b", lambda v: RENDER_B[v]
    if all(type(x) is int or type(x) is float for x in vals):
        from math import isfinite

        if any(type(x) is float and not isfinite(x) for x in vals):
            return None                                  # NaN/±Inf -> .8H -> fail-loud
        return "n", str
    return None


def _registros_flat(data):
    """`list[dict]` RETANGULAR e PLANA -> as colunas dela; qualquer outra coisa -> `None`.

    A forma da entrada e' METADADO, nao rota (ADR-0049): `[{v: d}, {v: d}]` e `{v: [d, d]}`
    sao a mesma tabela e devem comprimir igual. Sem esta canonizacao a lista de dicionarios
    caia no `.8H`, que emite so' a rota `tcf`, sem o `min(tcf, raw, dict, split)` do `.8M`.
    Medido: ate' +430% na mesma coluna, so' por causa da grafia.

    Recusa (e deixa seguir pro `.8H`, que e' a rota certa pra elas) tudo que nao e' tabela:
    ragged, aninhado, array na celula, chave nao-str e lista vazia. A recusa e' uma passada
    so', e as varreduras que ela faz sao as mesmas que o encoder faria depois.

    Recusa TAMBEM quem tem `\\n` ou `\\r` em nome ou valor, e isso NAO e' detalhe: o `.8H`
    escapa folhas e nomes, o `.8M` os recusa (o wire e' LF-only e o LF separa o meta). Sem
    esta guarda o roteamento TIRARIA uma capacidade que a entrada ja' tinha, trocando um
    round-trip que funciona por um `ValueError`, que e' a pior classe de regressao.
    """
    if not (isinstance(data, list) and data):
        return None
    if not all(type(r) is dict for r in data):
        return None
    chaves = list(data[0])
    if not chaves or not all(isinstance(k, str) for k in chaves):
        return None
    if any("\n" in k or "\r" in k for k in chaves):
        return None                                      # nome com quebra -> .8H escapa
    # Mesmas chaves NA MESMA ORDEM: a ordem das colunas do wire e' a de entrada, e um
    # dicionario com as chaves trocadas de lugar descreveria outra tabela.
    if any(list(r) != chaves for r in data[1:]):
        return None
    for r in data:
        for v in r.values():
            if isinstance(v, (dict, list)):
                return None                              # aninhado -> .8H
            if isinstance(v, str) and ("\n" in v or "\r" in v):
                return None                              # folha com quebra -> .8H escapa
    return {k: [r[k] for r in data] for k in chaves}


def _tabela_flat(data) -> bool:
    """dict multi-col FLAT: nao-vazio, todos os valores sao list[str] de MESMO tamanho
    (tabela retangular). dict com valor escalar/aninhado, colunas tipadas ou ragged -> .8H.
    Precedencia flat (parecer 2340 §2): dict[str,list[str]] retangular preserva compat/bytes."""
    if not (isinstance(data, dict) and data):
        return False
    if not all(isinstance(k, str) for k in data):
        # chave nao-str -> .8H -> HierarchicalError tipado (D_json), por construcao;
        # antes caia num TypeError cru dentro do meta do .8M
        return False
    vals = list(data.values())
    if not all(isinstance(v, list) for v in vals):
        return False
    tamanhos = {len(v) for v in vals}
    if len(tamanhos) != 1:                               # ragged -> .8H
        return False
    # ZERO linhas fica no `.8M` (2026-08-26). Antes caia no `.8H` porque o corpo de uma
    # coluna vazia colidia com o de UMA linha vazia: os dois eram 0 byte, e nao havia de
    # onde deduzir a diferenca. O slot `@` (V2-B) desfaz a colisao sem tocar o formato,
    # porque o row-count dele sai de `len(stream) // width`, e nao de contar `\n`: stream
    # vazio e' zero, sem ambiguidade. Medido: `{"v": []}` cai de 18 B (.8H) pra 12 B, e
    # some a anomalia de tirar a ultima linha e o wire CRESCER. Ver
    # `experiments/lab/dirty/2026-08/2026-08-26/2026-08-26-0400-uma-coluna-e-o-vazio/`.
    # Coluna TIPADA (int/float/bool) e `None` NAO tiram mais a tabela do `.8M`: o tipo
    # viaja como tag de 1 byte no meta (`!8N=valor`), e o nulo pelo slot 0 do core. Antes
    # bastava um int pra tabela inteira cair no `.8H`, que nao roda o
    # `min(tcf,raw,dict,split)`: medido, +43,6% de bytes no adult-census. O `.8H` continua
    # dono do que E' aninhado: dict/list dentro da celula e ragged. O 0-linha
    # RETANGULAR saiu dessa lista em 2026-08-26 (ver o comentario acima).
    if not all(
        x is None or isinstance(x, (str, int, float, bool))
        for v in vals for x in v
    ):
        return False
    # HOMOGENEIDADE POR COLUNA, com o MESMO juiz do `.8H` (2026-08-27, onda 0).
    #
    # O `.8M` decidia o tipo da coluna pela PRIMEIRA celula e nunca conferia o resto. Numa
    # coluna mista isso nao dava erro: dava dado errado. Medido em 300 pares de tipos, 30
    # perdas CALADAS (`[1,""]` volta `[1,None]`, `["a",1]` volta `["a","1"]`, `[1,"1"]`
    # volta `[1,1]`) e 18 wires que o proprio `decode` nao le'. E a ORDEM das celulas
    # decidia qual dos dois danos acontecia.
    #
    # As outras duas familias ja' recusavam esse dado: o single-col por `_tipo_single_col`
    # (que tambem devolve None e deixa o `.8H` levantar) e o `.8H` por `_scalar_type`. A
    # correcao aqui e' so' PARAR DE REIVINDICAR a tabela: quem levanta continua sendo o
    # `.8H`, com a mesma mensagem que ele ja' dava, entao as tres portas passam a recusar o
    # mesmo conjunto pela mesma frase, por construcao e nao por coincidencia.
    #
    # `_scalar_type` tambem carrega o teste de finitude, o que fecha `NaN`/`Infinity`: eles
    # ficam fora do JSON (RFC 8259), o single e o `.8H` ja' recusavam, e o `.8M` gravava
    # `#TCF.8M!3N=c\nnan`, um wire morto.
    from tcf.hierarchical import HierarchicalError, _scalar_type
    for v in vals:
        try:
            _scalar_type([x for x in v if x is not None])
        except HierarchicalError:
            return False                                 # -> .8H -> fail-loud com a frase dele
    return True


# kwargs SO'-flat (default) -> em rota .8H, se != default = fail-loud (nunca ignorar calado,
# parecer 2340 §2.4). `side_outputs` e `nature_per_col` VALEM no .8H e nao entram aqui.
_KWARGS_FLAT_DEFAULT = {
    "parallel": False, "nature": None, "layers": None, "fallback": True,
    "min_header": True, "min_len": None, "sort_by": None, "name": None,
    "stamp": None, "drop_names": False,
}


def _rejeita_kwargs_flat_no_8h(**kw) -> None:
    ruins = [k for k, v in kw.items() if v != _KWARGS_FLAT_DEFAULT[k]]
    if ruins:
        # `nature` e' o canal INTERNO do schema escalar — pro usuario, a grafia e' schema=
        ruins = ["schema (forma escalar)" if k == "nature" else k for k in ruins]
        raise ValueError(
            f"kwargs {ruins} so' valem no flat de STRING (single/multi-col); nao se aplicam a "
            f"esta entrada (hierarquica .8H, tipada #TCF.8<tag> ou vazia). Use "
            f"schema={{path: spec}} p/ specs no .8H, ou reformate a entrada."
        )


def _encode_lazy_bool(data, side: SideOutputs | None = None) -> "str | None":
    """Candidato lazy bool `#TCF.8bB<w><n>` (ADR-0039) ou `None` quando nao se oferece.

    Uniao {bool, str, None} com >=1 bool E >=1 str: hoje essa coluna cai no `.8H` e
    FAIL-LOUD (uniao de tipos nao e' hierarquizavel) — o lazy e' o UNICO candidato que
    preserva o tipo, entao emite o wire direto, SEM min() (fiacao do lab
    2026-08-01-0322, sem bloqueadores).

    Cabeca CONGELADA implicita null=0/false=1/true=2 (TABELA_B2 de `tcf/tipos_internos.py`)
    + extras str declarados no arquivo a partir do slot 3, por 1a aparicao — a mecanica do
    `dominio_bn` (ADR-0036) com a cabeca bool implicita. Dominio comprimido pelo proprio
    core (mesma disciplina: `_grafa`, `[:-1]` da linha vazia final, escape `\\=` de linha
    comecando com `=`), b64 sem padding, n em hex minimo. Lab de origem:
    2026-08-01-0229-lazytype-bool-extras.

    NAO se oferece (devolve `None` -> cai no `.8H`, que fail-loud na uniao):
    - extra com LF embutido (achado da fiacao 0322: `_encode_column(['a\\nb'])` devolve
      CALADO — o fail-loud de LF mora no encode flat publico, nao no `_encode_column`;
      um extra com LF corromperia o parse do dominio. Check EXPLICITO aqui);
    - w > 8 (extras > 253) — teto do namespace bN (MAX_W do `dominio_bn`).
    """
    if not isinstance(data, list) or not data:
        return None
    tipos = {type(x) for x in data}
    if not tipos <= {bool, str, type(None)} or not {bool, str} <= tipos:
        return None
    extras: list[str] = []
    vistos: set[str] = set()
    for x in data:
        if type(x) is str and x not in vistos:
            vistos.add(x)
            extras.append(x)
    # QUEBRA DE LINHA no extra: o wire e' LF-only (AGENTS §wire, output-convention), e o
    # dominio do `bB` grava o extra LITERAL, uma linha por valor. O check era so' de LF, e
    # o CR passava: `encode([True, "a\rb"])` gravava o byte 0d cru no wire, com round-trip
    # exato mas fora da convencao canonica. As rotas irmas ja' recusavam CR (single e
    # multi) ou o escapavam (`.8H`); esta era a unica porta aberta.
    if any("\n" in e or "\r" in e for e in extras):
        return None
    import base64

    from tcf.bitpack import pack_w
    from tcf.composicional.dominio_bn import BS, MARCADOR, MAX_W, _grafa
    from tcf.multi.core import MAGIC_SINGLE_V3
    from tcf.tipos_internos import TABELA_B2

    w = (3 + len(extras) - 1).bit_length()           # ceil(log2(3 + k)), k >= 1 -> w >= 2
    if w > MAX_W:
        return None
    idx = {v: i for i, v in enumerate(TABELA_B2)}    # None:0, False:1, True:2
    ex_idx = {e: 3 + i for i, e in enumerate(extras)}
    # `type(x) is str` separa extra da cabeca — evita a colisao de dict "1" vs True.
    packed = pack_w([ex_idx[x] if type(x) is str else idx[x] for x in data], w)
    b64 = base64.b64encode(packed).decode("ascii").rstrip("=")
    _bl = _encode_column([_grafa(e) for e in extras], header="val", side=side)
    bloco = _bl[:-1] if _bl.endswith("\n") else _bl
    escapado = "\n".join(BS + ln if ln.startswith(MARCADOR) else ln
                         for ln in bloco.split("\n"))
    magic = MAGIC_SINGLE_V3.decode("utf-8")
    return f"{magic}bB{w}{len(data):x}\n{escapado}\n{MARCADOR}{b64}"


def encode(
    data,
    *,
    schema=None,
    side_outputs: SideOutputs | None = None,
    parallel: bool | int = False,
    layers: PipelineConfig | None = None,
    fallback: bool = True,
    min_header: bool = True,
    min_len: int | None = None,
    sort_by: str | None = None,
    name: str | None = None,
    stamp: bool | None = None,
    drop_names: bool = False,
) -> str:
    """Encode QUALQUER dataset (flat OU aninhado) em texto TCF — PORTA UNICA (Passo 2).

    Rota por TIPO de entrada, simetrico ao `decode` (que rota pelo magic). Contrato
    completo em `docs/reference/api.md`. Resumo:
      - `list[str]` (todos str, >=1)       -> single-col flat `#TCF.8` (header por DEFAULT)
      - `dict[str, list[str]]` retangular (inclusive 0 linhas) -> multi-col `#TCF.8M`
      - `list[bool|str|None]` misto (>=1 bool E >=1 str) -> lazy bool `#TCF.8bB` (ADR-0039)
      - list[dict] / objeto / escalar / `{}` / tipado / ragged
                                            -> hierarquico `#TCF.8H` (rota interna)
      - tipo nao-JSON (bytes/tuple/func) ou array de tipos mistos -> FAIL-LOUD

    Type-coherent: so' o flat PURO (todos str) fica flat; o resto vai pro `.8H`, que
    PRESERVA o tipo (`[1,2,3]` -> array int; `None` nao vira `""`). NAO existe
    `encode_hierarchical` publico — use so' `encode`/`decode`.

    kwargs SO'-flat (parallel/layers/fallback/min_header/min_len/sort_by/name/stamp/
    drop_names): passados com entrada `.8H` = fail-loud. `side_outputs` e `nature_per_col`
    valem no `.8H`; `nature` (spec unico) so' no single-col flat.

    Multi-col `#TCF.8M` (default, ADR-0032): por coluna min(TCF, raw, dict, split) +
    header minimo (meta inline, ultima sem size, sizes HEX). Single-col = version-stamp
    `#TCF.8` + body (header default 100%; ADR-0034 supersede o default do ADR-0029).

    Args:
        data: dataset — `list[str]` (single flat) · `dict[str, list[str]]` (multi flat) ·
            ou raiz aninhada/tipada/vazia (rota `.8H`). Ver a tabela de dispatch acima.
        schema: os SPECS da entrada, num parametro so' (decisao owner;
            substitui `nature=`/`nature_per_col=`). Formas:
            - `"cpf"` (str) — UM spec pelo NAME do registry (single-col); registry
              core: cpf, cnpj, ip, data-iso, int-pad (`tcf.SPEC_REGISTRY`).
            - objeto spec — idem, direto (specs de terceiros).
            - `{"col": "cpf", 3: "ip", "outra": SPEC_X}` — por coluna: chave str =
              NOME (inclusive `''` e `'0'`, ADR-0046), chave int = POSICAO na ordem
              das colunas; valor = str do registry, objeto spec ou None (sem spec).
              Posicao so' vale pra tabela `dict`; dataset `.8H` enderessa por PATH
              (str) e single-col usa a forma escalar.
            Fail-loud: name desconhecido, posicao fora do range, colisao
            posicao/nome e chave de tipo errado = erro na porta. O spec continua
            COMPETINDO no FLOOR (so' vence se encolher; colunas vencedoras ganham
            `:id` no header — self-describing, o decode nao precisa do schema).
        side_outputs: opcional. Se fornecido, captura logs/info interna
            (column_features, cadence_info, OBAT log, HCC trace/rede,
            seq_rle_runs, multi_info, per_col). Sem ele: descartado
            (comportamento pre-existente, overhead zero).
        parallel: paraleliza encode de colunas (multi-col so'). T-CODE-ENCODER-MANAGER Fase 1.
            - `False`/`0` (default): serial
            - `True`: ProcessPoolExecutor com `os.cpu_count()` workers
            - `int N >= 2`: N workers explicitos
            - `1`: SERIAL deduzido (1 worker ≡ serial byte-identico; sem spawn)
            - negativo/nao-int: erro na fronteira (T-QA-8 BUG-10c)
            - Para list (single-col): parametro ignorado (1 coluna)
        name: rotulo opcional do header single-col + spec (`#TCF.8 nome:id`).
            SO' com `schema` escalar (senao erro — seria ignorado calado; BUG-10e).
        stamp: (list) controla o header `#TCF.8\\n` do single-col. `None` (default)
            e `True` -> COM header, 100% dos casos (ADR-0034). `False` -> emite o
            CORPO CRU, sem header: pra transmissao ou container que ja' carrega o
            contrato (parquet), onde ele vive nas PONTAS e nao no arquivo.
            Ignorado pra dict — o `M` do multi JA' e' o stamp.

            DUAS RESSALVAS, porque `False` e' corpo-cru e nao "cabecalho minimo":
            (a) os mecanismos que se DECLARAM no cabecalho (polaridade, bN de
            dominio) ficam de fora da disputa, entao o wire pode sair MAIOR —
            medido: coluna de baixa cardinalidade, 102 B com header contra 611 B
            crua; (b) com `schema` vencedor o `:id` sai assim mesmo, porque e' o
            unico lugar onde viaja QUAL spec inverter — sem ele o decode
            devolveria o payload transformado.
            Separar o ESTATICO (que as duas pontas ja' sabem) do DINAMICO (que
            precisa ser declarado) e' o desenho do cabecalho minimo, e ele vive
            no objeto Schema: `tickets/T-API-SCHEMA-PRESCRITIVO.md`.
        drop_names: (multi-col) omite os nomes no meta (colunas ANONIMAS,
            ADR-0029); decode retorna nomes posicionais '0','1',... Nome de
            coluna '' NAO e' anonima: e' nome vazio, emitido como `\\z` e
            preservado no decode (ADR-0046). Com drop_names=True ele e'
            dropado como qualquer outro.
        fallback: (multi-col) por coluna escolhe min(tcf, raw, dict, split).
            **Default True**. False -> so' candidato tcf em toda coluna
            (comparacao/regressao; magic segue #TCF.8M — legado cortado,
            ADR-0032). Ignorado pra list.
        min_header: (multi-col) ultima coluna sem size (corpo ate' EOF,
            ADR-0023/O-FMT-15). **Default True**. False -> todas as colunas com
            size no meta (inspecao; meta segue INLINE no #TCF.8M). Ignorado
            pra list.
        min_len: override manual do min_len do OBAT (afixos com `length <
            min_len` viram literal). **Default None -> auto** (detect_min_len
            por coluna; comportamento inalterado). int >= 1 aplica o mesmo
            min_len a TODAS as colunas (tuning manual). Muda os bytes — so'
            quando passado explicitamente.
        sort_by: (multi-col, O-FMT-02) AUTORIZA reordenar as LINHAS pela coluna
            nomeada antes de encodar, agrupando valores iguais. **Order-free**:
            o decode devolve o mesmo MULTISET de linhas, e a ordem original NAO
            e' recuperavel, entao use so' quando a ordem nao importa.

            Desde 2026-09-01 (H-14-08) a ordenacao e' um CANDIDATO, nao uma
            ordem: o encoder emite os dois e fica com o MENOR, entao passar
            `sort_by` nunca faz o wire crescer. Isso importa porque ordenar
            agrupa os iguais da CHAVE e desarruma todas as outras colunas:
            medido, -43,0% quando as companheiras sao funcao da chave e +52,1%
            quando sao independentes dela. Consequencia: um wire pedido com
            `sort_by` pode voltar na ordem original, se ordenar nao tiver
            ajudado, e `view.group_ranges` (que exige contiguidade) pode recusa-lo
            e o `view.agg_by` cai no caminho order-free sozinho.

            A chave de ordenacao e' `str(valor)`, lexicografica: `'10'` vem antes
            de `'2'`, e um `None` compara como a string `'None'`. Nao ha' plano de
            mudar isso, porque a ordenacao aqui existe pra AGRUPAR iguais, e
            qualquer ordem total agrupa igualmente bem; a ordem em si deixou de
            ser promessa quando o contrato virou order-free.

            Default None -> sem reordenar (ordem preservada). Em lista de uma
            coluna e' RECUSADO (ate' 2026-09-01 era ignorado calado).

    Returns:
        Texto TCF (str, sempre UTF-8, LF only). **Output byte-identico
        ao modo serial** (parallel apenas reordena computacao, nao bytes).

    Raises:
        TypeError: data nao-list/dict; coluna str/bytes (envolva em [...]);
            layers nao-PipelineConfig; parallel de tipo invalido.
        ValueError: valor com `\\n`/`\\r` embutido (quebra o modelo de linha ->
            corromperia o RT); spec declarada em coluna de 0 linhas; (multi) table
            vazia, lengths
            divergentes, nome com `\\n`, colisao posicional de nome '';
            parallel negativo; name= sem nature; natures cruzados (BUG-10g).
            Nomes com `,`/`=`/`:`/`\\` sao ACEITOS (escapados no meta, M2).
    """
    # --- Fronteiras da API (T-QA-8 F0 lote 3, BUG-10): fail-loud ANTES do
    # pipeline — erro claro na porta, nao AttributeError/TypeError fundo. O
    # tratamento da' ISOLAMENTO (decisao owner): o codigo identifica
    # os casos e o comportamento pode mudar depois (T-API-BOUNDARY-CONTRACTS).
    if layers is not None and not isinstance(layers, PipelineConfig):
        raise TypeError(
            f"layers deve ser PipelineConfig (ou None); got {type(layers).__name__}"
        )
    if not isinstance(parallel, (bool, int)):
        raise TypeError(f"parallel deve ser bool ou int; got {type(parallel).__name__}")
    if not isinstance(parallel, bool) and parallel < 0:
        raise ValueError(
            f"parallel deve ser >= 0 (0/False=serial; 1=serial deduzido; "
            f"N>=2 = N workers); got {parallel}"
        )
    # `schema=` — o parametro UNICO de spec (owner; substituiu
    # `nature=`/`nature_per_col=`, corte seco pre-1.0 como o do legado .6/.7).
    # Normaliza AQUI, na porta, para os canais internos (`nature`/
    # `nature_per_col`) — o miolo das 4 rotas nao muda. Chave int = POSICAO,
    # resolvida contra a ordem das colunas; str = NOME (a coluna literalmente
    # chamada "0" e' a chave str "0" — sem ambiguidade; `''` e' nome, ADR-0046).
    # Byte-neutro por construcao: so' escolhe QUAL spec vai em QUAL coluna,
    # exatamente o que os canais internos ja' faziam.
    nature = None
    nature_per_col = None
    _alvo_e_tabela = False   # schema escalar apontado a uma tabela de 2+ colunas
    if schema is not None:
        from tcf.natures import resolve_schema

        _kind, _resolved = resolve_schema(schema, where="encode(schema=)")
        if _kind == "single":
            # A tabela ALVO da sobrecarga, seja qual for a grafia. Uma lista de registros
            # retangular e' tabela do mesmo jeito que o dict de colunas (ADR-0049), e antes
            # de 2026-09-01 ela caia no `else` abaixo e o spec era DESCARTADO CALADO: a
            # mesma chamada levantava como dict e passava em branco como registros.
            _tabela_alvo = data if isinstance(data, dict) else _registros_flat(data)
            if _tabela_alvo is not None and len(_tabela_alvo) == 1:
                # SOBRECARGA: alvo INEQUIVOCO — tabela de UMA
                # coluna aceita a forma escalar, sem cerimonia de dict. Com 2+
                # colunas o escalar segue erro ensinante (qual coluna? informacao
                # genuinamente necessaria).
                nature_per_col = {next(iter(_tabela_alvo)): _resolved}
            else:
                nature = _resolved
                _alvo_e_tabela = _tabela_alvo is not None
        elif isinstance(data, dict):
            _cols = list(data)
            _out: dict = {}
            for _k, _spec in _resolved.items():
                if isinstance(_k, int):
                    if not 0 <= _k < len(_cols):
                        raise ValueError(
                            f"encode(schema=): posicao {_k} fora do range — a "
                            f"tabela tem {len(_cols)} coluna(s) ({_cols})"
                        )
                    _k = _cols[_k]
                if _k in _out:
                    raise ValueError(
                        f"encode(schema=): coluna {_k!r} recebeu spec DUAS vezes "
                        f"(posicao e nome apontando pra mesma coluna?)"
                    )
                _out[_k] = _spec
            nature_per_col = _out
        else:
            if any(isinstance(_k, int) for _k in _resolved):
                raise ValueError(
                    "encode(schema=): chave int (posicao) so' vale pra tabela "
                    "dict — dataset .8H enderessa por PATH (str); single-col "
                    "usa schema='id' (escalar)"
                )
            nature_per_col = _resolved
    if nature is not None and _alvo_e_tabela:
        raise ValueError(
            "schema escalar ('id'/objeto) aplica a single-col (list) ou tabela "
            "de UMA coluna; com 2+ colunas use schema={coluna: spec}, porque qual "
            "coluna e' informacao necessaria (T-QA-8 BUG-10g). Vale igual para dict "
            "de colunas e para lista de registros: as duas sao a mesma tabela."
        )
    if (
        isinstance(data, list)
        and nature_per_col
        and not any(isinstance(x, (dict, list)) for x in data)
    ):
        # `nature_per_col` precisa de colunas COM NOME, e uma lista de ESCALARES nao tem
        # nenhuma — vale pra flat all-str (BUG-10g), pra TIPADA (`[1,2,3]`) e pra vazia.
        # `list[dict]` (dataset .8H) ACEITA `{path: spec}`: e' a rota de nature
        # hierarquica e ela aplica de verdade (medido 799 -> 52 B). `list[list]` cai no
        # .8H, que ja' explica melhor ("nao e' folha ESCALAR do dataset") — por isso o
        # `any(dict|list)` deixa os dois passarem.
        # ANTES o cheque era `_lista_flat(data)`, FALSO pra lista tipada -> o spec era
        # aceito e DESCARTADO CALADO.
        raise ValueError(
            "schema={coluna: spec} aplica a multi-col (dict) ou dataset (list[dict], .8H); "
            f"esta entrada e' uma lista de escalares (len={len(data)}) — pra single-col "
            "use schema='id' escalar (T-QA-8 BUG-10g / T-NATURE-IGNORADA-CALADA)"
        )
    if name is not None and (isinstance(data, dict) or nature is None):
        raise ValueError(
            "name= so' tem efeito em single-col COM schema escalar (rotulo do header "
            "'#TCF.8 nome:spec'); sem isso seria ignorado calado (T-QA-8 BUG-10e)"
        )
    if nature is not None or nature_per_col:
        # EMISSAO fail-loud do wire_id (ADR-0041): grafia + anti-mascarada,
        # validadas NA PORTA, antes de qualquer dispatch — a rota .8H envolve a
        # emissao interna num try/except que cai pro piso, e validar la' dentro
        # ENGOLIRIA o spec hostil em vez de recusar alto. Aqui cobre
        # single/multi/.8H de uma vez.
        from tcf.natures import _valida_emissao

        if nature is not None:
            _valida_emissao(nature, where="schema=")
        for _col, _sp in (nature_per_col or {}).items():
            if _sp is None:
                continue  # slot None = coluna sem nature (contrato pre-existente)
            _valida_emissao(_sp, where=f"nature_per_col[{_col!r}]")
    cfg = layers if layers is not None else DEFAULT_PIPELINE
    if min_len is not None and min_len < 1:
        raise ValueError(f"min_len deve ser >= 1 (ou None pra auto); got {min_len}")
    if _lista_flat(data):
        # SINGLE-COL FLAT (list, nao-vazia, TODOS str). Lista vazia (BUG-03 resolvido: `[]`
        # agora e' representavel via .8H `#D0`), lista tipada (`[1,2,3]` -> array .8H) e
        # list[dict] caem na ROTA .8H abaixo (dispatch type-coherent, Passo 2).
        # `_stringify_checked` valida \n/\r (BUG-06); a conversao e' no-op aqui (all-str).
        from tcf.multi.core import _stringify_checked, MAGIC_SINGLE_V3

        if sort_by is not None:
            # Ate' 2026-09-01 esta rota IGNORAVA o `sort_by`, calada, e o silencio estava
            # pinado em teste. As outras quatro rotas o recusam alto. O buraco existia
            # porque uma lista de uma coluna nao tem coluna NOMEADA pra ordenar, e ignorar
            # parecia inofensivo: nao e'. Quem passou o kwarg pediu uma coisa e recebeu
            # outra, sem sinal, que e' a classe de falha que este formato mais combate.
            raise ValueError(
                f"sort_by={sort_by!r} nao vale em lista de uma coluna: nao ha' coluna "
                f"nomeada pra ordenar. Ordene a lista voce mesmo (`sorted(...)`), ou passe "
                f"a tabela como dict de colunas se ela tiver mais de uma."
            )
        # O resto da lista, fechado no mesmo movimento (cauda do `.8`). Os quatro sao
        # declarados "(multi-col)" na propria docstring do `encode`, e medido: nao mexem
        # UM BYTE em nenhum de seis corpora nesta rota. Aceita-los calado era o ultimo
        # buraco da regra "nunca ignorar calado", e nem era decisao: a rota `.8H`, a
        # tipada e a vazia ja' os recusavam, com esta mesma mensagem.
        #
        # O `min_len` NAO entra aqui, e a distincao e' o ponto: ele nao se diz multi-col e
        # de fato FUNCIONA no single-col (medido, 46 B -> 23 B numa coluna de IDs e
        # 363 B -> 56 B em unicos longos). Recusa-lo seria tirar uma capacidade real.
        _so_multi = {"parallel": parallel, "fallback": fallback,
                     "min_header": min_header, "drop_names": drop_names}
        _passados = [k for k, v in _so_multi.items() if v != _KWARGS_FLAT_DEFAULT[k]]
        if _passados:
            # As grafias vem do registro da era (`tcf.wire`), nao de literal: a catraca
            # de `test_wire_eras.py` existe exatamente pra isso, e pegou esta mensagem.
            from tcf.wire import MAGIC_MULTI, MAGIC_RECORDS

            raise ValueError(
                f"kwargs {_passados} so' valem em tabela de VARIAS colunas "
                f"(`{MAGIC_MULTI}`/`{MAGIC_RECORDS}`): eles escolhem candidato POR "
                f"COLUNA, escrevem o meta por "
                f"coluna, omitem NOMES de coluna ou paralelizam ENTRE colunas, e uma "
                f"lista de uma coluna nao tem nada disso. Passe a tabela como dict de "
                f"colunas, ou tire o kwarg. O `min_len` vale aqui e continua valendo."
            )
        data = _stringify_checked(data)
        magic = MAGIC_SINGLE_V3.decode("utf-8")  # "#TCF.8"
        if nature is not None:
            # FLOOR single-col: a nature
            # COMPETE — encoda o original (órfão) e a nature-transformada
            # (`#TCF.8 [nome]:id` header), fica a MENOR (incluindo o custo do
            # header self-describing). So' vence se cobrir esse custo. Se perde ->
            # órfão/stamp, SEM marcador (o arquivo deixa de se auto-explicar; o
            # trade self-explain-vs-compete e a deducao de spec vao pro .9, §6).
            if name is not None and (":" in name or "\n" in name):
                raise ValueError(
                    f"name de single-col nao pode conter ':' nem '\\n' "
                    f"(reservado pro meta #TCF.8): {name!r}"
                )
            from tcf.natures.templated_checked import encode_value

            pairs = [encode_value(nature, v) for v in data]
            transformed = [p for p, _ in pairs]
            body_orig = _encode_column(data, header="val", cfg=cfg, min_len=min_len)
            body_nat = _encode_column(
                transformed, header="val", cfg=cfg, min_len=min_len
            )
            # `:id` = wire_id CURTO (plano do DADO, ADR-0041) — nunca o `name`.
            # O comprimento decide o FLOOR: com `:data-iso` (10 B) a nature
            # perdia em N>=11 diarias; com `:dt` vence (12 flips medidos).
            header_nat = f"{magic} {name or ''}:{nature.wire_id}\n"
            # FLOOR: compara os blobs completos; empate fica no baseline.
            # o baseline compete na MESMA grafia que sera' emitida (com header por default)
            # — inclusive POLARIZADA. Comparar contra a grafia antiga daria
            # vitoria a' nature em disputa que ela perde de fato.
            if stamp is False:
                baseline = body_orig
            else:
                from tcf.composicional.polaridade import polariza

                _suf_b, _body_b = polariza(body_orig)
                baseline = f"{magic}{_suf_b}\n{_body_b}"
                # O BASELINE TEM DE SER O QUE O ENCODER EMITIRIA DE FATO (weld
                # T-DATA-LAZY-ISO, 2026-08-08). Ate' aqui o FLOOR da nature comparava so'
                # contra o corpo do CORE — mas o bN de dominio (ADR-0036) tambem e'
                # candidato na rota flat, e ele costuma vencer justo nas colunas de baixa
                # cardinalidade que atraem nature. Medido antes desta linha: coluna de 2
                # CPFs repetidos saia com 61 B sem `nature=` (rota bN) e 198 B com — a
                # nature "vencia" um baseline que o encoder nao emitiria.
                #
                # E' a MESMA classe do que era o `T-BN-TIPADO`: o candidato existe e a rota
                # nao o consultava. Comparar contra o baseline errado nao e' so' perder
                # bytes — e' o FLOOR deixando de ser nunca-pior, que e' a invariante que
                # sustenta todo mecanismo novo do projeto.
                from tcf.composicional.dominio_bn import candidatos as _bn_cands

                for _c in _bn_cands(
                    data, lambda vs: _encode_column(vs, header="val", cfg=cfg), None
                )[:1]:                                   # so' o modo `B`, como na rota flat
                    if len(_c.encode("utf-8")) < len(baseline.encode("utf-8")):
                        baseline = _c
            candidate = header_nat + body_nat
            win = len(candidate.encode("utf-8")) < len(baseline.encode("utf-8"))
            if side_outputs is not None:
                stats = _nature_apply_stats(nature, [s for _, s in pairs])
                stats["used"] = win
                side_outputs.nature_apply = {"val": stats}
                _encode_column(
                    transformed if win else data,
                    header="val",
                    side=side_outputs,
                    cfg=cfg,
                    min_len=min_len,
                )
            if win:
                return header_nat + body_nat
            body = body_orig  # nature perdeu -> órfão/stamp abaixo
        else:
            body = _encode_column(
                data, header="val", side=side_outputs, cfg=cfg, min_len=min_len
            )
        if stamp is False:
            # ESCAPE EXPLICITO: single-col orfao, sem `#TCF.8`. So' por
            # pedido — casos de transmissao e de embutir em container que ja' carrega o
            # contrato (parquet), onde o header nao paga. O contrato passa a viver nas
            # pontas: quem produz e quem consome combinam fora do arquivo.
            return body
        # DEFAULT = COM cabecalho, 100% dos casos. O `#TCF.8\n` infla o
        # single-col em 7 B, e isso e' INEVITAVEL — o arquivo se auto-explica em vez de
        # depender de quem o produziu. Supersede o default do ADR-0029 (ver ADR-0034).
        #
        # POLARIDADE: camada de BORDA, a ultima coisa do encode. Troca
        # `1 escape por LITERAL` por `1 byte por TRANSICAO`, com FLOOR nunca-pior que ja'
        # inclui o custo do proprio sufixo. Sufixo vazio = a grafia de hoje, byte a byte.
        # So' aqui e no tipado: orfao (`stamp=False`) nao tem cabecalho onde declarar, e
        # `.8M`/`.8H`/spec ficam de fora deste weld.
        from tcf.composicional.polaridade import polariza

        sufixo, body = polariza(body)
        # bN DE DOMINIO (ADR-0036): mais candidatos do MESMO min(). Coluna
        # de cardinalidade baixa gasta ~3 B/linha em `^N`; com `k` distintos bastam
        # ceil(log2(k)) BITS. Nunca-pior: o FLOOR so' troca se encolher.
        from tcf.composicional.dominio_bn import candidatos as _bn_cands

        # So' o modo `B` (dominio primeiro) concorre por DEFAULT. O `C` (dominio por ultimo)
        # e' ~1 B menor e por isso venceria SEMPRE num min() cego — mas ele NAO STREAMA: o
        # leitor precisa do payload inteiro antes de emitir o 1o valor (17x mais buffer numa
        # coluna de 2000 linhas, lab 2026-07-27-2211). Trocar streaming por 1 byte, calado,
        # seria a decisao errada tomada pelo criterio errado. O `C` fica DECODAVEL (wire
        # produzido por outra ponta le' normalmente) e o opt-in de emissao e' T-BN-LOTE.
        _bn = _bn_cands(data, lambda vs: _encode_column(vs, header="val", cfg=cfg), None)
        _cands = [magic + sufixo + "\n" + body] + _bn[:1]
        return min(_cands, key=lambda w: len(w.encode("utf-8")))
    if isinstance(data, list) and not data:
        # [] FLAT (canonicidade do vazio): a forma flat passa a
        # expressar a lista vazia como '#TCF.8\n' (7 B), em vez de fugir pro .8H '#D0'
        # (11 B). Simetrico ao decode (disc '' + corpo vazio -> []). Colunas vazias
        # ANINHADAS nao passam aqui (o .8H usa `if cols[key] else ''`, hierarchical.py:499),
        # entao a mudanca e' isolada ao top-level. kwargs so'-flat rejeitados (mesmo contrato
        # do .8H). Re-pina test_core_rt/test_f0/test_hierarchical (wire re-pinavel, ADR-0024).
        from tcf.multi.core import MAGIC_SINGLE_V3

        _rejeita_kwargs_flat_no_8h(
            parallel=parallel, nature=nature, layers=layers, fallback=fallback,
            min_header=min_header, min_len=min_len, sort_by=sort_by, name=name,
            stamp=stamp, drop_names=drop_names,
        )
        return MAGIC_SINGLE_V3.decode("utf-8") + "\n"
    _tipado = _tipo_single_col(data)
    if _tipado is not None:
        # SINGLE-COL TIPADO (weld #4a/#4b 2026-07-24 p/ bool; GENERALIZADO 2026-07-25 p/ numero
        # e p/ conviver com null). Antes ia tudo pro .8H — um envelope de estrutura aninhada
        # (`#V`/count/`[]`) gasto so' pra PRESERVAR o tipo de uma coluna plana. Agora o tipo e'
        # 1 char de TAG no indice 6, e o corpo e' o core de sempre.
        #
        # Candidatos de MODO competindo no FLOOR (a variavel `modo`; o '~' e' conceitual, NAO
        # vai no wire):
        #   A core   '#TCF.8<tag>\n<core>'    -> reusa _encode_column (seq-RLE/aliases de graca).
        #                                      Para a tag b o corpo e' grafado em SLOTS
        #                                      (null=0/false=1/true=2, ADR-0038) — mesma
        #                                      tabela do denso b2.
        #   B denso  '#TCF.8b1<n>\n<b64>'     -> bit-pack 1 bit/elem; bool SEM null
        #      denso  '#TCF.8b2<n>\n<b64>'     -> bit-pack 2 bits/elem; bool COM null (ternario)
        # O denso e' bool-only por construcao: o dominio e' IMPLICITO e congelado
        # (b1: false=0/true=1; b2: null=0/false=1/true=2, 3 reservado). Weld b2:
        # lab 2026-07-31-2350-denso-b2-ternario, ADR-0037.
        # min() nunca-pior ENTRE os candidatos (materializa e emite o menor). Refino do
        # preditor (sem materializar os dois) -> .9 (T-TYPED-SINGLECOL-MODE-HEURISTIC).
        from tcf.multi.core import MAGIC_SINGLE_V3

        tag, render = _tipado
        # PORTA TIPADA ABERTA A SPEC E A `min_len`.
        #
        # Antes, `nature=` e `min_len=` eram recusados aqui — a rota tipada nao aceitava
        # NENHUM dos dois mecanismos que o inteiro precisa, e `"entra int, spec int, devolve
        # int"` nao era expressavel em rota alguma. Medido no lab de conformidade: o int ja'
        # percorre o MESMO caminho que bool/float/str em todos os regimes (muda a tag, nao o
        # mecanismo) — faltava so' a porta.
        #
        # O spec entra DEPOIS do `render` (a grafia decimal e' o que ele transforma) e
        # compete no MESMO `min()` — como o bool ja' faz com o denso. Nao e' rota nova.
        _rejeita_kwargs_flat_no_8h(
            parallel=parallel, layers=layers, fallback=fallback,
            min_header=min_header, sort_by=sort_by, name=name,
            stamp=stamp, drop_names=drop_names,
        )
        if nature is not None:
            from tcf.natures import _valida_emissao

            _valida_emissao(nature, where="schema=")
        magic = MAGIC_SINGLE_V3.decode("utf-8")
        tem_nulo = any(x is None for x in data)
        corpo_core = _encode_column(
            [None if x is None else render(x) for x in data],
            header="val", side=side_outputs, cfg=cfg, min_len=min_len,
        )
        # POLARIDADE: mais um candidato do MESMO min(), nao um caminho
        # a parte. O sufixo e' pontuacao e a tag e' letra/digito, entao `#TCF.8n!` se le
        # sem ambiguidade — e nenhum discriminador de hoje (`M`/`H`/`b`/`n`/`s`/espaco) e'
        # pontuacao. Sufixo vazio -> este candidato E' o core, e o min() nao muda nada.
        from tcf.composicional.polaridade import polariza

        _suf, _corpo_pol = polariza(corpo_core)
        candidatos = [f"{magic}{tag}\n{corpo_core}"]
        if _suf:
            candidatos.append(f"{magic}{tag}{_suf}\n{_corpo_pol}")

        # bN DE DOMINIO TIPADO — so' p/ NUMERO.
        #
        # A objecao antiga ("o wire `#TCF.8B…` devolve STRING e a rota tipada tem de
        # preservar o tipo") continua valendo, e e' exatamente por isso que a tag vai DENTRO
        # do cabecalho: `#TCF.8nB<w><n>`. Isso NAO e' grafia nova — o `#TCF.8bB` (lazy bool,
        # ADR-0039) ja' usa esta forma exata desde 2026-08-01. O corpo e' o mesmo
        # `candidatos()` do bN de sempre; o decode reescreve o cabecalho e delega.
        #
        # So' o modo `B` concorre, pela MESMA razao da rota flat: o `C` e' ~1 B menor e
        # venceria sempre num min() cego, mas nao streama (dominio depois do payload —
        # medido: 100% do fio antes do 1o valor, contra 2,1-7,0% do `B`).
        #
        # `bool` NAO entra: o denso b1/b2 tem dominio IMPLICITO e vence por construcao
        # (medido: 47 B contra 57 B sem null; 79 B contra 92 B com null). `s` tambem nao —
        # a rota flat ja' consulta o bN pra string.
        if tag == "n":
            from tcf.composicional.dominio_bn import candidatos as _bn_cands

            _grafias = [None if x is None else render(x) for x in data]
            for _c in _bn_cands(
                _grafias, lambda vs: _encode_column(vs, header="val", cfg=cfg), None
            )[:1]:
                # A tag entra no indice 6, empurrando o disc pro 7 — o mesmo slot posicional
                # de `b1`/`b2`/`bB` (ADR-0029). Custo: 1 byte.
                candidatos.append(_c[:6] + tag + _c[6:])

        if tag == "b":
            import base64

            from tcf.bitpack import pack_w

            if tem_nulo:
                # DENSO b2 TERNARIO (ADR-0037): dominio implicito CONGELADO
                # null=0, false=1, true=2 (3 = reservado, fail-loud no decode). Medido:
                # 546 B (core) -> 79 B p/ n=200, vence ate' n=3.
                idx = [0 if x is None else (2 if x else 1) for x in data]
                b64 = base64.b64encode(pack_w(idx, 2)).decode("ascii")
                candidatos.append(f"{magic}b2{len(data):x}\n{b64}")
            else:
                idx = [1 if x else 0 for x in data]            # dominio implicito FIXO (canonico)
                b64 = base64.b64encode(pack_w(idx, 1)).decode("ascii")
                # `n` em HEX: len(hex(n)) <= len(dec(n)) p/ TODO n >= 0 -- propriedade matematica,
                # nunca pior, O(1). Parse e' POSICIONAL (modo = 1o char), entao hex nao colide
                # com o namespace do <modo>.
                candidatos.append(f"{magic}b1{len(data):x}\n{b64}")

        # SPEC NA ROTA TIPADA (weld EXP-018): mais um candidato do MESMO min(), aplicado
        # sobre a grafia que o `render` produz. O header leva a tag E o `:id`
        # (`#TCF.8n [nome]:ipad`) — o slot do indice 7 comporta os dois, verificado.
        # Vem por ULTIMO na lista para so' vencer com margem estrita (mesma ordem
        # load-bearing do periodico no ADR-0040).
        if nature is not None:
            from tcf.natures.templated_checked import encode_value as _nat_enc

            _grafado = [None if x is None else render(x) for x in data]
            _pares = [(None, "empty_value") if g is None else _nat_enc(nature, g)
                      for g in _grafado]
            _corpo_nat = _encode_column(
                [p for p, _ in _pares], header="val", cfg=cfg, min_len=min_len,
            )
            candidatos.append(f"{magic}{tag} {name or ''}:{nature.wire_id}\n{_corpo_nat}")
            if side_outputs is not None:
                _st = _nature_apply_stats(nature, [s for _, s in _pares])
                _st["used"] = None            # preenchido apos o min(), abaixo
                side_outputs.nature_apply = {"val": _st}

        # FLOOR: a variavel `modo` = argmin. Empate fica no 1o (core, mais inspecionavel).
        _venc = min(candidatos, key=lambda w: len(w.encode("utf-8")))
        if nature is not None and side_outputs is not None:
            side_outputs.nature_apply["val"]["used"] = _venc is candidatos[-1]
        return _venc
    # FORMA REGISTROS -> `#TCF.8R` (ADR-0049). A grafia da entrada e' METADADO, nao rota:
    # canoniza `list[dict]` retangular nas colunas dela e segue pela rota `.8M`, trocando
    # so' o discriminador na saida. Custa ZERO byte (o `R` ocupa o slot do `M`) e nao pode
    # piorar, porque `corpo(.8M) = min(tcf, raw, dict, split) <= corpo(.8H) = tcf`.
    _colunas_de_registros = _registros_flat(data)
    if _colunas_de_registros is not None:
        if sort_by is not None:
            # NAO liberado junto com a solda, e de proposito. O `sort_by` e' order-free:
            # ele devolveria a lista do usuario REORDENADA. Em colunas isso ja' e' o
            # contrato; numa lista de registros a ordem e' a unidade que o chamador ve', e
            # trocar um erro alto por um reordenamento calado e' exatamente o silencio que
            # este formato recusa. Se for liberado um dia, e' com aviso proprio.
            raise ValueError(
                "sort_by nao vale em lista de registros: ele e' order-free e devolveria a "
                "lista REORDENADA, silenciosamente. Passe a tabela como dict de colunas "
                "(`{col: [...]}`), onde a troca de ordem e' o contrato declarado, ou "
                "ordene a lista voce mesmo antes de encodar."
            )
        data = _colunas_de_registros
    if _tabela_flat(data):
        from tcf.multi import _encode_multi

        _dados_ordenados = None
        if sort_by is not None:
            # O-FMT-02: reordena linhas pela coluna-chave (order-free). E' so'
            # um pre-encode transform; output e' TCF normal, decode retorna a
            # ordem ordenada (ordem original NAO recuperavel).
            if sort_by not in data:
                raise ValueError(
                    f"sort_by: coluna '{sort_by}' inexistente; colunas: {list(data)}"
                )
            # Havia aqui um `raise` para colunas de tamanhos diferentes, e ele era CODIGO
            # MORTO: este bloco so' roda dentro de `_tabela_flat(data)`, que ja' recusa
            # tabela ragged antes (`len(tamanhos) != 1 -> False`, acima). Um dict ragged
            # nunca chegava nesta linha: ele cai na rota `.8H`, que rejeita o kwarg com a
            # mensagem generica de kwargs so'-flat. Removido em 2026-09-01.
            key_col = data[sort_by]
            order = sorted(range(len(key_col)), key=lambda i: str(key_col[i]))
            # FLOOR do sort (H-14-08, 2026-09-01): a ordenacao vira CANDIDATO em vez de
            # ordem. O contrato do `sort_by` JA' e' order-free, entao passa-lo AUTORIZA o
            # encoder a reordenar; nada o obriga a reordenar quando isso PIORA. E piora com
            # frequencia: a permutacao da chave agrupa os iguais dela e desarruma todas as
            # outras colunas, medido em +52,1% numa tabela de 6 colunas independentes (e em
            # -43,0% quando elas sao funcao da chave, que e' o outro extremo). Aqui os dois
            # sao encodados e sai o menor, do mesmo jeito que o `.8M` ja' faz por coluna.
            _dados_ordenados = {c: [v[i] for i in order] for c, v in data.items()}
        # FLOOR: a nature NAO e' mais
        # pre-transformacao FORCADA — os SPECS descem pro _encode_multi, que a faz
        # COMPETIR no min() por coluna (encoda original vs nature-transformada, fica
        # a menor). So' as colunas onde a nature vence ganham ':id'. Safe-by-
        # construction: nunca pior que o baseline (resolve a regressao F4).
        if nature_per_col:
            # Coluna que NAO existe na tabela era filtrada CALADA aqui (`if name in data`)
            # — o usuario pedia spec e nao recebia, sem aviso. O `.8H` JA' falhava alto em
            # path inexistente ("nao e' folha ESCALAR do dataset"); isto alinha o `.8M`.
            #
            _desconhecidas = [c for c in nature_per_col if c not in data]
            if _desconhecidas:
                raise ValueError(
                    f"schema: coluna(s) {_desconhecidas} nao existe(m) na tabela "
                    f"(colunas: {list(data)}) — o spec seria descartado calado "
                    f"(T-NATURE-IGNORADA-CALADA)"
                )
        # `{col: None}` = coluna SEM nature continua valido (contrato pre-existente).
        nature_specs = (
            {name: spec for name, spec in nature_per_col.items() if spec is not None}
            if nature_per_col
            else None
        )
        def _emite(_tab):
            return _encode_multi(
                _tab,
                side_outputs=side_outputs,
                parallel=parallel,
                cfg=cfg,
                fallback=fallback,
                min_header=min_header,
                min_len=min_len,
                nature_specs=nature_specs,
                drop_names=drop_names,
            )

        _wire = _emite(data)
        if _dados_ordenados is not None:
            _ord = _emite(_dados_ordenados)
            if len(_ord.encode("utf-8")) < len(_wire.encode("utf-8")):
                _wire = _ord
        if _colunas_de_registros is not None:
            # A troca do discriminador (ADR-0049). O corpo e o meta sao os do `.8M`; o `R`
            # so' registra a forma de origem, e por ocupar o mesmo slot nao soma byte.
            from tcf.wire import DISC_RECORDS, MAGIC_BASE, MAGIC_MULTI

            assert _wire.startswith(MAGIC_MULTI), (
                f"rota de registros nao emitiu multi: {_wire[:12]!r}"
            )
            return MAGIC_BASE + DISC_RECORDS + _wire[len(MAGIC_MULTI):]
        return _wire
    # ROTA LAZY BOOL .8bB (ADR-0039): uniao bool+str(+null) — hoje cai no `.8H` e
    # fail-loud; o lazy e' o unico candidato que preserva o tipo. kwargs so'-flat
    # rejeitados ANTES de emitir (mesmo contrato do tipado/.8H); se o lazy NAO se
    # oferece (LF em extra / w>8), cai no `.8H` abaixo, que fail-loud na uniao.
    _lazy = _encode_lazy_bool(data, side=side_outputs)
    if _lazy is not None:
        _rejeita_kwargs_flat_no_8h(
            parallel=parallel, nature=nature, layers=layers, fallback=fallback,
            min_header=min_header, min_len=min_len, sort_by=sort_by, name=name,
            stamp=stamp, drop_names=drop_names,
        )
        # A coluna tem tipos MISTURADOS, e isso e' anomalia de origem, nao capacidade
        # pedida: o TCF preserva os dois tipos aqui (rota lazy, ADR-0039) mas as outras
        # duas familias RECUSAM a mesma coluna, entao o mesmo dado passa ou nao passa
        # conforme a forma de entrada. Avisar e' o que o formato deve ao chamador; quem
        # quer o silencio higieniza na fonte, que e' onde o problema nasce.
        import warnings
        # O `None` e' membro legitimo da uniao e NAO e' booleano: soma-lo aos bools
        # mentia na contagem e, pior, fazia dois perfis diferentes gerarem o MESMO
        # texto, que o `__warningregistry__` do Python deduplica por (mensagem, local).
        # A segunda coluna mista ficava CALADA.
        _n_bool = sum(1 for x in data if type(x) is bool)
        _n_str = sum(1 for x in data if type(x) is str)
        _n_nulo = sum(1 for x in data if x is None)
        _nulos = f", {_n_nulo} nulo(s)" if _n_nulo else ""
        warnings.warn(
            f"coluna de tipos MISTOS (bool e str): {_n_bool} booleano(s) e "
            f"{_n_str} string(s){_nulos} na mesma coluna. O round-trip e' exato pela "
            f"rota lazy `#TCF.8bB` (single-col), mas a MESMA coluna e' recusada como "
            f"`dict` (`#TCF.8M`) e como dataset (`#TCF.8H`). Separe por tipo na origem, "
            f"ou converta a coluna toda para string.",
            UserWarning, stacklevel=2)
        return _lazy
    # ROTA HIERARQUICA .8H (dispatch type-coherent, Passo 2, API unica): tudo que NAO e'
    # flat puro — lista vazia/tipada/list[dict], dict objeto/ragged/tipado, escalar solto,
    # `{}`. Simetrico ao decode (que rota pelo magic `#TCF.8H`). kwargs so'-flat = fail-loud.
    _rejeita_kwargs_flat_no_8h(
        parallel=parallel, nature=nature, layers=layers, fallback=fallback,
        min_header=min_header, min_len=min_len, sort_by=sort_by, name=name,
        stamp=stamp, drop_names=drop_names,
    )
    from tcf.hierarchical import _encode_hierarchical

    return _encode_hierarchical(data, nature_per_col=nature_per_col, side_outputs=side_outputs)


def _encode_column(
    values: list[str],
    *,
    header: str = "val",
    side: SideOutputs | None = None,
    cfg: PipelineConfig = DEFAULT_PIPELINE,
    min_len: int | None = None,
) -> str:
    """Pipeline canonical M10 por coluna. Capta side outputs se fornecido.

    Esta eh a "encode unit" (cf. plano v0.4 D13 EncodeManager). O
    dispatcher `encode()` chama esta funcao 1+ vezes (1 pra list, N
    pra dict).

    `cfg` controla quais camadas aplicar (T-CODE-LAYERED-PIPELINE Fase 1).
    Default = M10 canonical (todas camadas on).

    `min_len` (Segment 2): override manual do min_len do OBAT. None (default)
    -> auto (detect_min_len, ou 3 se pre_pass off). Comportamento inalterado
    no default.
    """
    # `unicas` = literais DESCOBERTOS (slots altos da tabela). `None` NAO entra: ele mora no
    # slot 0, PRE-ALOCADO pelo formato (ver syntax._SLOTS_RESERVADOS). Por isso os eids de
    # dado seguem comecando em 1 e o wire de coluna sem null e' byte-identico.
    seen: OrderedDict[str, bool] = OrderedDict()
    tem_nulo = False
    for s in values:
        if s is None:
            tem_nulo = True
        else:
            seen[s] = True
    unicas = list(seen.keys())

    # CAMADA 1 — Pre-pass (toggleable). Roda sobre os LITERAIS: null nao tem forma textual,
    # entao nao participa de cadencia/min_len (e nao pode virar '' calado). Sem null, a lista
    # e' a mesma referencia de antes -> zero custo e zero risco de mudanca de bytes.
    valores_lit = [s for s in values if s is not None] if tem_nulo else values
    features = analyze_column(valores_lit)  # sempre computa (barato, util pra side)
    if cfg.pre_pass:
        cadence_detected, cadence_info = detect_cadence_from_features(features, unicas)
        auto_min_len = detect_min_len_from_features(features)
    else:
        cadence_detected = False
        cadence_info = {"rule_hit": None, "reason": "pre_pass disabled by cfg"}
        auto_min_len = 3  # default M9
    # Override explicito (Segment 2): min_len manual sobrepoe o auto/default.
    min_len = min_len if min_len is not None else auto_min_len

    # CAMADA 2 — OBAT (shape-preserve toggleable se cadence detected)
    if cadence_detected and cfg.obat_shape_preserve:
        tokens, obat_log = processar_with_hint(
            unicas, min_len=min_len, prefer_shape_consistency=True
        )
        used_hint = True
    else:
        tokens, obat_log = processar(unicas, min_len=min_len)
        used_hint = False

    # CAMADA 3 — HCC (seq-RLE toggleable; sem seq-RLE = M9 puro)
    if cfg.hcc_seq_rle:
        syn = HCCSeqRLE()
    else:
        syn = M8AVirtualRefsSyntax()
    # Telemetria OPT-IN: sem `side_outputs=` o trace/rede nem e'
    # construido. Antes rodava sempre e era descartado logo abaixo — 4-17% do
    # encode (17,1% numa cadeia true/false). Zero efeito no wire.
    syn.coletar_trace = side is not None
    body = syn.encode(values, unicas, tokens, header)

    if side is not None:
        side.column_features = features
        side.cadence_detected = cadence_detected
        side.cadence_info = cadence_info
        side.min_len = min_len
        side.obat_log = obat_log
        side.obat_used_hint = used_hint
        side.hcc_trace = syn.get_trace()
        side.hcc_rede = syn.get_rede()
        # seq_rle_runs so' existe em HCCSeqRLE; M8AVirtualRefsSyntax nao tem
        side.seq_rle_runs = syn.get_seq_info() if hasattr(syn, "get_seq_info") else []
        side.body_bytes = len(body.encode("utf-8"))

    return body
