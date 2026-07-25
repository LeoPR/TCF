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
from typing import TYPE_CHECKING

from tcf.auto_cadence import detect_cadence_from_features
from tcf.auto_min_len import detect_min_len_from_features
from tcf.column_features import analyze_column
from tcf.composicional.hcc_seqrle import HCCSeqRLE
from tcf.composicional.syntax import M8AVirtualRefsSyntax
from tcf.core.online import processar
from tcf.obat_shape import processar_with_hint
from tcf.pipeline import DEFAULT_PIPELINE, PipelineConfig
from tcf.side_outputs import SideOutputs

if TYPE_CHECKING:
    from tcf.natures.templated_checked import TemplatedCheckedSpec


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

    `None` entra no flat desde a pre-alocacao do slot 0 (2026-07-25): null e' mais um valor da
    coluna, referenciado como `0`. Antes, uma unica ocorrencia expulsava a coluna inteira pro
    envelope `.8H` — que compra generalidade (aninhamento, tipos mistos) que uma coluna de
    string com nulls nao usa. Ganho medido no lab 2026-07-24-2210.
    """
    return (isinstance(data, list) and bool(data)
            and all(x is None or isinstance(x, str) for x in data))


def _tabela_flat(data) -> bool:
    """dict multi-col FLAT: nao-vazio, todos os valores sao list[str] de MESMO tamanho
    (tabela retangular). dict com valor escalar/aninhado, colunas tipadas ou ragged -> .8H.
    Precedencia flat (parecer 2340 §2): dict[str,list[str]] retangular preserva compat/bytes."""
    if not (isinstance(data, dict) and data):
        return False
    vals = list(data.values())
    if not all(isinstance(v, list) for v in vals):
        return False
    tamanhos = {len(v) for v in vals}
    if len(tamanhos) != 1 or 0 in tamanhos:              # ragged OU 0-linhas -> .8H
        return False                                     # (0-linha: `{"a":[]}` = objeto c/ array vazio)
    return all(isinstance(x, str) for v in vals for x in v)


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
        raise ValueError(
            f"kwargs {ruins} so' valem no flat de STRING (single/multi-col); nao se aplicam a "
            f"esta entrada (hierarquica .8H, tipada #TCF.8<tag> ou vazia). Use nature_per_col= "
            f"p/ specs no .8H, ou reformate a entrada."
        )


def encode(
    data,
    *,
    side_outputs: SideOutputs | None = None,
    parallel: bool | int = False,
    nature: "TemplatedCheckedSpec | None" = None,
    nature_per_col: "dict[str, TemplatedCheckedSpec] | None" = None,
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
      - `dict[str, list[str]]` retangular >=1 linha -> multi-col `#TCF.8M`
      - list[dict] / objeto / escalar / `[]` / `{}` / tipado / ragged / 0-linha
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
        nature: pre-tx por natureza (ADR-0015; list apenas — pra dict use
            nature_per_col, erro cruzado BUG-10g). Emite header self-describing
            `#TCF.8 [nome]:id` — o decode resolve SOZINHO pelo registry
            (cpf/cnpj/ip); spec out-of-band so' pra ids fora do registry.
        nature_per_col: dict col_name -> spec (dict input apenas). Sufixo `:id`
            por coluna no meta (ADR-0027, self-describing).
        name: rotulo opcional do header single-col + nature (`#TCF.8 nome:id`).
            SO' com nature (senao erro — seria ignorado calado; BUG-10e).
        stamp: (list) controla o header `#TCF.8\\n` do single-col. `None` (default) e
            `True` -> COM header, 100% dos casos (ADR-0034). `False` -> ESCAPE explicito
            (orfao, sem header): so' pra transmissao ou container que ja' carrega o
            contrato (parquet) — ai o contrato vive nas PONTAS, nao no arquivo.
            Ignorado pra dict — o `M` do multi JA' e' o stamp.
        drop_names: (multi-col) omite os nomes no meta (colunas ANONIMAS,
            ADR-0029); decode retorna nomes posicionais '0','1',... Nome de
            coluna '' equivale a anonima so' naquela coluna (warning).
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
        sort_by: (multi-col, O-FMT-02) reordena as LINHAS pela coluna nomeada
            antes de encodar, agrupando valores similares -> mais compressao
            (5-15% em dados com chave low-card). **Order-free**: o decode
            retorna a ordem ORDENADA, NAO a original (a ordem original NAO e'
            recuperavel — use so' quando a ordem nao importa). Default None ->
            sem reordenar (ordem preservada). Ignorado pra list.

    Returns:
        Texto TCF (str, sempre UTF-8, LF only). **Output byte-identico
        ao modo serial** (parallel apenas reordena computacao, nao bytes).

    Raises:
        TypeError: data nao-list/dict; coluna str/bytes (envolva em [...]);
            layers nao-PipelineConfig; parallel de tipo invalido.
        ValueError: valor com `\\n`/`\\r` embutido (quebra o modelo de linha ->
            corromperia o RT); 0 linhas (BUG-03); (multi) table vazia, lengths
            divergentes, nome com `\\n`, colisao posicional de nome '';
            parallel negativo; name= sem nature; natures cruzados (BUG-10g).
            Nomes com `,`/`=`/`:`/`\\` sao ACEITOS (escapados no meta, M2).
    """
    # --- Fronteiras da API (T-QA-8 F0 lote 3, BUG-10): fail-loud ANTES do
    # pipeline — erro claro na porta, nao AttributeError/TypeError fundo. O
    # tratamento da' ISOLAMENTO (decisao owner 2026-07-10): o codigo identifica
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
    if isinstance(data, dict) and nature is not None:
        raise ValueError(
            "nature= aplica a single-col (list); pra dict use "
            "nature_per_col={col: spec} (T-QA-8 BUG-10g)"
        )
    if _lista_flat(data) and nature_per_col:
        # so' a list FLAT single-col (all-str) rejeita nature_per_col (usa nature=). list[dict]
        # (dataset .8H) ACEITA nature_per_col={path: spec} — e' a rota de nature hierarquica.
        raise ValueError(
            "nature_per_col= aplica a multi-col (dict) ou dataset (.8H); pra single-col (list[str]) "
            "use nature= (T-QA-8 BUG-10g)"
        )
    if name is not None and (isinstance(data, dict) or nature is None):
        raise ValueError(
            "name= so' tem efeito em single-col COM nature= (rotulo do header "
            "'#TCF.8 nome:spec'); sem isso seria ignorado calado (T-QA-8 BUG-10e)"
        )
    cfg = layers if layers is not None else DEFAULT_PIPELINE
    if min_len is not None and min_len < 1:
        raise ValueError(f"min_len deve ser >= 1 (ou None pra auto); got {min_len}")
    if _lista_flat(data):
        # SINGLE-COL FLAT (list, nao-vazia, TODOS str). Lista vazia (BUG-03 resolvido: `[]`
        # agora e' representavel via .8H `#D0`), lista tipada (`[1,2,3]` -> array .8H) e
        # list[dict] caem na ROTA .8H abaixo (dispatch type-coherent, Passo 2).
        # `_stringify_checked` valida \n/\r (BUG-06); a conversao e' no-op aqui (all-str).
        from tcf.multi.core import _stringify_checked, MAGIC_SINGLE_V3

        data = _stringify_checked(data)
        magic = MAGIC_SINGLE_V3.decode("utf-8")  # "#TCF.8"
        if nature is not None:
            # FLOOR single-col (T-SPEC-DEEPDIVE §5.1, owner 2026-07-12): a nature
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
            header_nat = f"{magic} {name or ''}:{nature.name}\n"
            # FLOOR: compara os blobs completos; empate fica no baseline.
            # o baseline compete na MESMA grafia que sera' emitida (com header por default)
            baseline = body_orig if stamp is False else f"{magic}\n{body_orig}"
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
            # ESCAPE EXPLICITO (owner 2026-07-24): single-col orfao, sem `#TCF.8`. So' por
            # pedido — casos de transmissao e de embutir em container que ja' carrega o
            # contrato (parquet), onde o header nao paga. O contrato passa a viver nas
            # pontas: quem produz e quem consome combinam fora do arquivo.
            return body
        # DEFAULT = COM cabecalho, 100% dos casos (owner 2026-07-24). O `#TCF.8\n` infla o
        # single-col em 7 B, e isso e' INEVITAVEL — o arquivo se auto-explica em vez de
        # depender de quem o produziu. Supersede o default do ADR-0029 (ver ADR-0034).
        return magic + "\n" + body
    if isinstance(data, list) and not data:
        # [] FLAT (owner 2026-07-24, canonicidade do vazio): a forma flat passa a
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
    if isinstance(data, list) and data and all(isinstance(x, bool) for x in data):
        # SINGLE-COL TIPADO bool (weld #4a/#4b, owner 2026-07-24): antes ia pro .8H (envelope
        # #V/count/[] so' pra PRESERVAR o tipo); agora o tipo vira 1 char de TAG. DOIS algoritmos de
        # corpo competem no FLOOR (a variavel `modo`, o '~' conceitual; SEM '~' no wire):
        #   A core   '#TCF.8b\n<core>'      -> reusa _encode_column (seq-RLE/aliases de graca)
        #   B denso  '#TCF.8b1<n>\n<b64>'   -> bit-pack 1 bit/elem (false=0,true=1) -> base64
        # min() nunca-pior ENTRE os 2 candidatos tipados (materializa os dois, emite o menor); nao e'
        # garantia formal vs o .8H antigo, mas empiricamente 0 regressao (verif. wf_85fcea32, 300+ listas
        # + testes: typed sempre <= .8H). `bool` antes de int (bool <: int em Python).
        # Refino da heuristica (preditor, sem materializar os 2) -> .9 (T-TYPED-SINGLECOL-MODE-HEURISTIC).
        from tcf.multi.core import MAGIC_SINGLE_V3

        _rejeita_kwargs_flat_no_8h(
            parallel=parallel, nature=nature, layers=layers, fallback=fallback,
            min_header=min_header, min_len=min_len, sort_by=sort_by, name=name,
            stamp=stamp, drop_names=drop_names,
        )
        magic = MAGIC_SINGLE_V3.decode("utf-8")
        corpo_core = _encode_column(
            ["true" if x else "false" for x in data],
            header="val", side=side_outputs, cfg=cfg, min_len=min_len,
        )
        wire_core = f"{magic}b\n{corpo_core}"
        import base64

        from tcf.bitpack import pack_w

        idx = [1 if x else 0 for x in data]                # dominio implicito FIXO (canonico)
        b64 = base64.b64encode(pack_w(idx, 1)).decode("ascii")
        # `n` em HEX (owner 2026-07-24): len(hex(n)) <= len(dec(n)) p/ TODO n >= 0 (base 16 > base 10)
        # -- propriedade matematica, nunca pior, O(1) (sem FLOOR extra pra decidir a base). Parse e'
        # posicional (modo = 1o char, sempre), entao hex nao colide com o namespace do <modo>.
        wire_denso = f"{magic}b1{len(data):x}\n{b64}"      # modo '1' = largura 1 bit; n em hex

        # FLOOR: a variavel `modo` = argmin. Empate fica no core (mais legivel/inspecionavel).
        return wire_core if len(wire_core.encode("utf-8")) <= len(wire_denso.encode("utf-8")) else wire_denso
    if _tabela_flat(data):
        from tcf.multi import _encode_multi

        if sort_by is not None:
            # O-FMT-02: reordena linhas pela coluna-chave (order-free). E' so'
            # um pre-encode transform; output e' TCF normal, decode retorna a
            # ordem ordenada (ordem original NAO recuperavel).
            if sort_by not in data:
                raise ValueError(
                    f"sort_by: coluna '{sort_by}' inexistente; colunas: {list(data)}"
                )
            if len({len(v) for v in data.values()}) > 1:
                raise ValueError(
                    "sort_by requer colunas de mesmo tamanho: "
                    f"{ {c: len(v) for c, v in data.items()} }"
                )
            key_col = data[sort_by]
            order = sorted(range(len(key_col)), key=lambda i: str(key_col[i]))
            data = {c: [v[i] for i in order] for c, v in data.items()}
        # FLOOR (T-SPEC-DEEPDIVE §5.1, owner 2026-07-12): a nature NAO e' mais
        # pre-transformacao FORCADA — os SPECS descem pro _encode_multi, que a faz
        # COMPETIR no min() por coluna (encoda original vs nature-transformada, fica
        # a menor). So' as colunas onde a nature vence ganham ':id'. Safe-by-
        # construction: nunca pior que o baseline (resolve a regressao F4).
        nature_specs = (
            {
                name: spec
                for name, spec in nature_per_col.items()
                if name in data and spec is not None
            }
            if nature_per_col
            else None
        )
        return _encode_multi(
            data,
            side_outputs=side_outputs,
            parallel=parallel,
            cfg=cfg,
            fallback=fallback,
            min_header=min_header,
            min_len=min_len,
            nature_specs=nature_specs,
            drop_names=drop_names,
        )
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
