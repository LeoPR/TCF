"""tcf.view — view lazy/consultável sobre um blob TCF: descomprime só o suficiente pra responder.

Camada READ-ONLY do TCF (parte do pacote desde A4; lê SÓ `#TCF.8M` — legado
`#TCF.6/.7` cortado, ADR-0032; NÃO muda encode/decode/formato). Meta inline +
natures (revertidas LAZY ao materializar a coluna) + colunas anônimas (nome =
ordem). Parse do meta = fonte única `_parse_meta` (paridade com o decode por
construção). Caminho canônico: `from tcf import view`. O shim em
`scripts/tcf_lazy/` re-exporta daqui pra compat com código/labs antigos.
PoC de origem: `experiments/lab/dirty/old/welded/2026-06-16-lazy-query/`.

Princípio (a "venda" do TCF): a estrutura do formato já diz, no header, o nome / modo /
tamanho de cada coluna. Dá pra FATIAR o corpo por coluna sem decodificar nada, e só
descomprimir a(s) coluna(s) — e, no filtro, só as linhas — que a pergunta precisa.
`count` / `sum` / `min` / `max` / `avg` + `where`, materializando uma fração do blob.

**Alinhamento de linha**: o formato é row-aligned por POSIÇÃO — a i-ésima posição de
cada coluna é a linha `i`. `where()` devolve os índices das linhas que casaram; agregação
e `select()` em QUALQUER outra coluna usam os MESMOS índices. É assim que "a linha de uma
coluna é a mesma linha na outra".

FUNCIONAL primeiro. Otimizações (saltos dedutivos, agregar runs `*N|` sem expandir, índice
de dicionário, dicas no header) são hooks documentados pra depois — ver NOTAS no fim.
"""
from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable

from tcf.multi import (
    MAGIC_MULTI_V3,
    _decode_v2b, _decode_struct_split, _v2b_width, _V2B_BASE,
    _decode_raw_body, _parse_meta,
)
from tcf.multi.core import _nomes_resolvidos
from tcf.decoder import _decode_column

MAGIC_HIER = b"#TCF.8H"      # tabela retangular tambem chega por aqui


def _idx_at(stream: bytes, off: int, width: int) -> int:
    """Decoda UM índice base-94 do stream V2-B na posição de byte `off`."""
    k = 0
    for ch in stream[off:off + width]:
        k = k * _V2B_BASE + (ch - 0x21)
    return k


# ---- COUNT sem materializar valor ------------------------------------------------
# Contar linhas nunca precisa dos valores, só da estrutura, e a estrutura já diz.
# São três leituras, escolhidas pelo modo da coluna:
#
#   DECLARADO  as rotas densas (`b`/`B`/`C`, com ou sem tag de tipo) escrevem `n` no
#              cabeçalho, em hex. Lê o cabeçalho e para, sem abrir o corpo.
#   SOMADO     o corpo core traz contadores (`*N|`, `*N+d|`, `*N~d|`) que declaram
#              quantas linhas cada um vale. Percorre as linhas somando.
#   SEPARADOR  o corpo raw é uma linha por valor: conta os `\n`. É o caso particular
#              do SOMADO em que nenhuma linha tem contador.
#
# Nenhuma das três constrói um objeto de valor. Escolher a leitura errada não levanta,
# devolve um número errado, então cada uma é conferida contra `decode()` em
# `tests/test_tcf_lazy.py::TestCountSemMaterializar` (341 combinações de tipo,
# cardinalidade, tamanho e forma no lab de origem).
# Levantamento: experiments/lab/dirty/2026-08/2026-08-24/2026-08-24-0600-count-minimo/
_RE_BN_CAB = re.compile(rb"^#TCF\.8[nbs]?[BCb][1-8][0-9a-f]+$")


def _n_declarado(cabecalho: bytes):
    """O `n` escrito no cabeçalho das rotas densas, ou None se a rota não declara.

    A grafia é canônica por imposição do próprio decodificador (`dominio_bn.py`
    levanta se `f"{n:x}" != nhex`: hex minúsculo, sem zero à esquerda, sem `0x`,
    sem sinal), então ler daqui não cria uma segunda interpretação do wire.
    """
    if not _RE_BN_CAB.match(cabecalho):
        return None
    # depois de `#TCF.8`: um char opcional de tipo, a letra de rota, a largura, o n
    resto = cabecalho[len(b"#TCF.8"):]
    if resto[:1] in (b"n", b"b", b"s") and len(resto) > 1 and resto[1:2] in b"BCb":
        resto = resto[1:]
    return int(resto[2:], 16)


def _n_somado(corpo: bytes) -> int:
    """Soma os contadores declarados de um corpo core.

    Cada linha ou abre com um contador (`*N|`, valendo N linhas) ou é uma linha
    solta (valendo 1). O aninhamento `*N+d|*M|` vale N*M.

    Quem lê o contador é `_contador_declarado`, de `composicional/hcc_seqrle.py`, e
    é de propósito: a primeira versão daqui usava um regex próprio,
    `^\\*(\\d+)([+~]\\d+)?\\|`, que **não casa o multi-delta** `*29+0,1|` emitido em
    qualquer coluna de data ou datetime. O efeito era mudo e grave: numa coluna de
    1000 datas ISO o `view` respondia 63, e como `select` itera `range(self.nrows)`,
    a tabela voltava truncada sem erro nenhum. Duas grafias do mesmo marcador, dois
    leitores, e o mais novo estava errado. Fonte única resolve a classe inteira.
    """
    from tcf.composicional.hcc_seqrle import _contador_declarado

    # Tira UM `\n` final, o terminador do wire, e não todos: `rstrip` comeria também
    # uma última linha legitimamente vazia. Em `b"a\n\n"` (os valores `"a"` e `""`)
    # o `rstrip` deixava `b"a"` e a contagem saía 1 em vez de 2.
    if corpo.endswith(b"\n"):
        corpo = corpo[:-1]
    if not corpo:
        return 0
    total = 0
    for bruta in corpo.split(b"\n"):
        linha = bruta.decode("utf-8", "surrogateescape")
        n = _contador_declarado(linha)
        if not n:
            total += 1
            continue
        # aninhado `*N+d|*M|`: o segundo contador multiplica o primeiro
        resto = linha[linha.find("|") + 1:]
        m = _contador_declarado(resto)
        total += n * m if m else n
    return total


_PY_DO_TIPO = {"n": (int, float), "b": (bool,), "s": (str,)}
_NOME_DO_TIPO = {"n": "int/float", "b": "bool", "s": "str"}


def _coage_where_value(value, pred, stype: str = "s", strict: bool = False):
    """Ajusta o valor do filtro ao tipo DA COLUNA. Devolve (valor, aviso|None).

    O arquivo é sempre texto: o tipo é uma leitura que o header declara, então
    comparar `where(col, "true")` numa coluna booleana é uma intenção clara, não
    um erro. No modo **soft** (o default) o valor é convertido e um aviso registra
    o que foi feito; no **strict** (`view(...).strict()`) vira erro, para quem quer
    o código rígido. É a mesma escolha que Polars e DuckDB fazem por padrão, com o
    strict virado do avesso: aqui a conveniência é o default e o rigor é opt-in.

    O cast é do lado BARATO: converte o UM valor do filtro, nunca as N linhas da
    coluna. Se o tipo já bate, não há cast nenhum.

    `None` casa nulo em qualquer coluna; com `pred=`, `value` é ignorado.
    """
    if pred is not None or value is None:
        return value, None
    aceitos = _PY_DO_TIPO.get(stype, (str,))
    # bool é subclasse de int: numa coluna `n`, `True` não é 1.
    if isinstance(value, aceitos) and not (stype == "n" and isinstance(value, bool)):
        return value, None                       # tipo bate: zero cast

    de, para = type(value).__name__, _NOME_DO_TIPO.get(stype, "str")
    convertido, ok = _converte(value, stype)
    if not ok:
        raise TypeError(
            f"view.where: esta coluna é {para} e o valor é {de} ({value!r}), que não "
            f"tem leitura possível nesse tipo."
        )
    if strict:
        raise TypeError(
            f"view.where: esta coluna é {para} e o valor é {de} ({value!r}). "
            f"A view está em modo STRICT, então a conversão não é automática: "
            f"passe {convertido!r}, ou use a view sem `.strict()`."
        )
    return convertido, (
        f"coluna {para}: o valor {value!r} ({de}) foi lido como {convertido!r}"
    )


def _converte(value, stype: str):
    """(valor_no_tipo_da_coluna, deu_certo). Nunca levanta."""
    try:
        if stype == "b":
            if isinstance(value, str):
                s = value.strip().lower()
                # a mesma grafia que o TCF emite, mais as formas que qualquer um
                # escreveria. Fora dessa lista NAO se adivinha: string nao-vazia
                # virar True por truthiness e' a armadilha classica do pandas.
                if s in ("true", "1", "t", "yes", "sim"):
                    return True, True
                if s in ("false", "0", "f", "no", "nao", "não"):
                    return False, True
                return None, False
            if isinstance(value, int):
                return bool(value), True
            return None, False
        if stype == "n":
            if isinstance(value, bool):
                return None, False               # `True` nao e' 1 numa coluna n
            return (float(value) if "." in str(value) or "e" in str(value).lower()
                    else int(value)), True
        # coluna de TEXTO: a grafia e' a que o encode usaria (`_to_str`)
        from tcf.multi.core import _to_str
        return _to_str(value), True
    except (TypeError, ValueError):
        return None, False


class LazyTCF:
    """View lazy sobre um blob TCF multi-coluna. Nada é descomprimido no __init__."""

    def __init__(self, blob: str):
        self._mode: dict[str, str] = {}        # name -> 'raw'|'dict'|'split'|'tcf'
        self._nature: dict[str, str] = {}      # name -> nature-id (#TCF.8 :spec)
        self._body: dict[str, bytes] = {}      # name -> bytes (NÃO decodificado)
        self._cache: dict[str, list[str]] = {}  # name -> valores (sob demanda)
        self._dict_cache: dict[str, tuple] = {}  # A3-O2: (unicas,width,stream) parseado do @dict
        self._order: list[str] = []
        self._stype: dict[str, str] = {}       # name -> 's'|'n'|'b' (tipo do dado; `.8H`)
        self._emask: dict[str, bytes] = {}     # name -> mascara de nulo (`.8H`), sob demanda
        self._strict = False                   # modo duro: cast tem de ser explicito
        self.coercoes: list[str] = []          # telemetria: o que foi convertido, e como
        self.touched: list[str] = []           # colunas que foram descomprimidas
        self._parse(blob)

    # ---- parse do header (barato; sem decodificar corpos) ----
    def _parse(self, blob: str) -> None:
        raw = blob.encode("utf-8")
        nl1 = raw.find(b"\n")
        if nl1 == -1:
            raise ValueError("blob inválido: sem shebang")
        line1 = raw[:nl1]
        # `#TCF.8H` que É TABELA RETANGULAR: uma coluna tipada (int/bool/float) ou um
        # `None` tiram o dict do `.8M`, e sem este ramo o view recusava a tabela inteira.
        # O tipo primitivo do dado já é um spec, só que implícito: ele viaja no header
        # (`valor#:3[]:14n`) do mesmo jeito que o `:id` de nature. Aqui o view lê o que
        # já está declarado. Aninhado, ragged e opcional seguem fora: ali não há tabela.
        if line1.startswith(MAGIC_HIER):
            self._parse_hier(raw, line1, nl1)
            return
        # SINGLE-COL: `#TCF.8` (texto), `#TCF.8n` (número), `#TCF.8b` (bool). É uma
        # tabela de uma coluna só, e o view não tinha razão pra recusá-la: `count`,
        # `sum` e `where` valem igual. O nome da coluna é `0`, como em qualquer
        # coluna anônima (ADR-0029).
        if line1.startswith(b"#TCF.8") and not line1.startswith(MAGIC_MULTI_V3):
            # SINGLE-COL: `#TCF.8` (texto), `#TCF.8n`, `#TCF.8b`, `#TCF.8 nome:spec`.
            # Uma coluna só também é tabela, e o view não tinha razão pra recusá-la:
            # `count`, `sum` e `where` valem igual. O decode oficial é a fonte dos
            # VALORES, porque ele já trata as sub-formas (bool denso em bits, float,
            # spec no header) que reimplementar aqui só faria divergir. Nome da
            # coluna: `0`, como qualquer anônima (ADR-0029).
            #
            # O que este ramo NÃO faz mais é chamar esse decode na ABERTURA. Havia
            # aqui um comentário afirmando que "não há laziness a preservar, o blob
            # INTEIRO é a coluna", e a premissa é falsa: o blob ser a coluna não
            # obriga a lê-lo antes de perguntarem. Quem só queria `columns`, `nrows`
            # ou o tipo pagava o decode completo (medido: 100% do wire em 9 regimes,
            # lab 2026-08-24-0400). O corpo agora espera o 1º pedido de VALOR.
            nome = "0"
            self._mode[nome] = "blob"    # o wire inteiro é a coluna; `_col` resolve
            self._blob_single = blob
            self._body[nome] = raw[nl1 + 1:]
            self._order.append(nome)
            # O tipo está DECLARADO no char de índice 6 (`n` número, `b` bool, ausente
            # texto), a mesma tag de 1 byte do `.8M`. Deduzi-lo do primeiro valor JÁ
            # DECODIFICADO custava o blob inteiro para saber algo que estava escrito.
            disc = line1[6:7]
            self._stype[nome] = {b"n": "n", b"b": "b"}.get(disc, "s")
            return
        # #TCF.8M = UNICO multi-col vivo (ADR-0032). Legado #TCF.6/#TCF.7 cortado —
        # fail-loud. Meta INLINE na linha do shebang.
        if not line1.startswith(MAGIC_MULTI_V3):
            raise ValueError(
                f"não é #TCF.8M multi-col (legado #TCF.6/#TCF.7 cortado, ADR-0032; "
                f"git checkout <pre-0.8> pra ler): {line1[:16]!r}")
        meta = line1[len(MAGIC_MULTI_V3):].decode("utf-8")   # inline
        cursor = nl1 + 1
        # BUG-08 fold (lote 3, paridade com _decode_multi_impl): meta vazio SEM
        # body e' nao-emitivel -> fail-loud (meta vazio COM body e' legitimo).
        if not meta and cursor >= len(raw):
            raise ValueError(
                "blob corrompido: meta vazio sem body ('#TCF.8M\\n' nao-emitivel "
                "— 0 linhas nao e' representavel; T-QA-8 BUG-08)"
            )

        # Parse delegado a `_parse_meta` (tcf.multi.core) — FONTE UNICA core+view:
        # paridade view/decode por CONSTRUCAO (BUG-02, T-QA-8 F0 2026-07-10).
        # Aqui so' resolve anonimas -> nome posicional e fatia os bodies.
        # Anonima -> posicional (ADR-0029) + guard de colisao: FONTE UNICA com o decode
        # (`_nomes_resolvidos`), mesma razao do `_parse_meta`. Sem ele a view era PIOR
        # que o decode aqui — reportava as N colunas do header e servia os MESMOS bytes
        # nas chaves colididas (T-META-COLISAO-NOME-POSICIONAL).
        _pares = _parse_meta(meta)
        _nomes = _nomes_resolvidos(_pares)
        for i, (size, name, mode, nat_id, tipo) in enumerate(_pares):
            name = _nomes[i]
            body = raw[cursor:] if size is None else raw[cursor:cursor + size]
            # BUG-05 (paridade estrutural com o decode): size do header vs bytes
            # disponiveis. O cross-check de n_rows do decode NAO roda aqui —
            # exigiria materializar todas as colunas, quebrando a laziness
            # (divergencia DELIBERADA e documentada; decode() completo valida).
            if size is not None and len(body) != size:
                raise ValueError(
                    f"body truncado: coluna {name!r} declara {size}B no header, "
                    f"restam {len(body)}B no blob (T-QA-8 BUG-05)"
                )
            self._mode[name] = mode
            self._body[name] = body
            self._order.append(name)
            if nat_id is not None:
                self._nature[name] = nat_id
            if tipo is not None:
                self._stype[name] = tipo
            cursor += len(body)
        if cursor != len(raw):
            raise ValueError(
                f"bytes excedentes: {len(raw) - cursor}B apos a ultima coluna "
                f"(header declara menos que o blob contem; T-QA-8 BUG-05)"
            )

    # ---- `.8H` que é tabela retangular: mesmas estruturas, outra gramática ----
    def _parse_hier(self, raw: bytes, line1: bytes, nl1: int) -> None:
        """Preenche `_mode`/`_body`/`_order`/`_nature`/`_stype` a partir do `.8H`.

        Depois daqui o resto da classe não sabe (nem precisa saber) de qual rota o blob
        veio: `where`, `sum`, `select` e `group_count` funcionam sem uma linha a mais.

        O corpo de cada coluna no `.8H` é o core puro, então o modo é sempre `tcf`: a
        competição `min(tcf, raw, dict, split)` do `.8M` não roda nesta rota. É por isso
        que `group_count` cai em fallback aqui, e o blob é maior.
        """
        from tcf.hierarchical import MAGIC as _MAGIC_H
        from tcf.hierarchical import _parse_meta as _parse_meta_h

        resto = line1[len(_MAGIC_H.encode()):].decode("utf-8")
        if resto.startswith("#O"):          # encode(dict): campo = array de escalares
            forma, meta = "objeto", resto[2:]
        elif resto.startswith("#"):         # #D/#E/#V: escalar solto, vazio, array cru
            raise ValueError(
                f"`view()` precisa de uma TABELA: este `.8H` tem raiz {resto[:2]!r}, "
                f"que não é tabela. Use `decode()`.")
        else:                                # encode(list[dict]): dataset de registros
            forma, meta = "dataset", resto

        schema, ordem, naturezas = _parse_meta_h(meta)
        esperado = "arr_scalars" if forma == "objeto" else "scalar"
        for kind, nome, mascarado, _kids, elem_null, stype in schema:
            # `mascarado` é campo OPCIONAL (existe em uns registros e não em outros):
            # isso é ragged, não tabela. `elem_null` é outra coisa: a coluna existe em
            # todas as linhas e algumas valem `None`. Aí ainda é tabela, e o nulo vem
            # numa coluna de máscara ao lado dos dados densos.
            if kind != esperado or mascarado:
                motivo = "opcional (ragged)" if mascarado else "aninhada"
                raise ValueError(
                    f"`view()` precisa de uma tabela retangular: a coluna {nome!r} é "
                    f"{motivo}. Use `decode()` para este blob.")
            self._stype[nome] = stype

        cursor = nl1 + 1
        for caminho, kind, size in ordem:
            nome = caminho[0]
            corpo = raw[cursor:] if size is None else raw[cursor:cursor + size]
            if size is not None and len(corpo) != size:
                raise ValueError(
                    f"body truncado: coluna {nome!r} declara {size}B no header, "
                    f"restam {len(corpo)}B no blob")
            if kind == "emask":            # onde estão os nulos desta coluna
                self._emask[nome] = corpo
            elif kind != "count":          # `count` é o comprimento do array, não dado
                self._mode[nome] = "tcf"
                self._body[nome] = corpo
                self._order.append(nome)
                if nome in naturezas:
                    self._nature[nome] = naturezas[nome]
            cursor += len(corpo)
        if cursor != len(raw):
            raise ValueError(
                f"bytes excedentes: {len(raw) - cursor}B após a última coluna")

    def strict(self) -> "LazyTCF":
        """Liga o modo DURO: o valor do filtro tem de vir no tipo da coluna.

        O default é soft, porque o arquivo é texto e a intenção de
        `where(col, "true")` numa coluna booleana é clara. Em código que se quer
        rígido (revisão, CI, conformidade), `.strict()` transforma a conversão
        automática em erro, com a mensagem dizendo o valor que ele esperava.

        Devolve a própria view, então encadeia: `view(blob).strict().where(...)`.
        """
        self._strict = True
        return self

    def _coage(self, col: str, value, pred):
        """Ajusta o valor ao tipo da coluna e registra a conversão, se houve."""
        import warnings
        value, aviso = _coage_where_value(
            value, pred, self._stype.get(col, "s"), self._strict)
        if aviso:
            self.coercoes.append(f"{col}: {aviso}")
            warnings.warn(f"view.where em {aviso}", stacklevel=3)
        return value

    # ---- introspecção barata (só header) ----
    @property
    def columns(self) -> list[str]:
        return list(self._order)

    def _resolve_col(self, col) -> str:
        """int = POSICAO, str = NOME — a MESMA regra e faixa do `schema=`
        (ADR-0047; espelha encoder.py: 0 <= pos < n, sem negativo; bool excluido
        como em natures.resolve_schema). A view e' a terceira porta publica que
        recebe coluna — as tres falam a mesma lingua. Desambiguacao identica ao
        schema=: coluna CHAMADA '2' e' achada por str '2' (nome); int 2 e' a
        posicao 2."""
        if isinstance(col, bool) or not isinstance(col, (int, str)):
            raise TypeError(
                f"view: coluna deve ser str (nome) ou int (posicao); "
                f"got {type(col).__name__} ({col!r})"
            )
        if isinstance(col, int):
            if not 0 <= col < len(self._order):
                raise ValueError(
                    f"view: posicao {col} fora do range — o blob tem "
                    f"{len(self._order)} coluna(s) ({self._order})"
                )
            return self._order[col]
        return col

    def column_bytes(self, name: str) -> int:
        """Tamanho do corpo (comprimido) da coluna, sem decodificar."""
        return len(self._body[self._resolve_col(name)])

    @property
    def total_bytes(self) -> int:
        return sum(len(b) for b in self._body.values())

    @property
    def materialized_bytes(self) -> int:
        """Bytes do blob já descomprimidos (soma dos corpos tocados)."""
        return sum(len(self._body[n]) for n in self.touched)

    # ---- reversao de nature: FONTE UNICA dos dois caminhos ----
    def _reverte_nature(self, name: str, vals: list) -> list:
        """Reverte a nature de `vals` se a coluna declara `:id` no header.

        FONTE UNICA de proposito. O bug que motivou esta funcao: a
        reversao existia SO' em `_col`, e o caminho L4 (`_dict_parts` -> where /
        group_count) comparava contra o PAYLOAD cru. Medido: numa coluna
        `#TCF.8M@1c7=dt:data-iso,@v`, `where('dt','2025-01-01')` devolvia **0** onde a
        verdade era **8**, e `group_count` devolvia chaves ordinais ('739252') — errado
        e SEM erro, a pior classe pela regra do projeto. Dois caminhos, um so' revertia;
        juntar num ponto e' o que impede a divergencia de voltar.

        Usa o WRAPPER DE MODULO, nao o metodo do spec: e' ele que trata o slot nulo do
        core (`None` volta `None`). Mesma escolha do `decoder.py` — o `_col` usava o
        metodo cru e quebraria em coluna com null.
        """
        nat_id = self._nature.get(name)
        if nat_id is None:
            return vals
        from tcf.natures import _resolve_nature_id
        from tcf.natures import decode_value as _nat_de
        spec = _resolve_nature_id(nat_id)
        if spec is None:
            # BUG-13b (lote 4, paridade com decode): id desconhecido =
            # ERRO na materializacao (dado cru calado corrompe).
            raise ValueError(
                f"nature-id desconhecido no header: {nat_id!r} (coluna "
                f"{name!r}) — registry core fechado; ADR-0024"
            )
        return [_nat_de(spec, v) for v in vals]

    # ---- decode de UMA coluna, sob demanda (cache + tracking) ----
    def _col(self, name: str) -> list[str]:
        name = self._resolve_col(name)
        if name not in self._mode:
            raise KeyError(f"coluna inexistente: {name!r} (tem: {self._order})")
        if name not in self._cache:
            mode, body = self._mode[name], self._body[name]
            if mode == "raw":
                # fonte única com o decode (dedup C0 D3 — paridade por construção)
                vals = _decode_raw_body(body)
            elif mode == "dict":
                vals = _decode_v2b(body)
            elif mode == "split":
                vals = _decode_struct_split(body)
            elif mode == "blob":
                # single-col: o wire inteiro é a coluna, e o decode oficial resolve
                # as sub-formas. É AQUI que ele roda, no 1º pedido de valor, não na
                # abertura da view.
                from tcf.decoder import decode as _decode_blob
                vals = _decode_blob(self._blob_single)
            else:
                vals = _decode_column(body.decode("utf-8"))
            # Nulo (`.8H`): os valores vem DENSOS e a posicao do `None` mora numa
            # coluna de mascara ao lado. Reidrata antes de tudo, senao a nature e o
            # tipo cairiam no valor errado e o alinhamento de linha quebraria.
            if name in self._emask:
                marcas = _decode_column(self._emask[name].decode("utf-8"))
                densos = iter(vals)
                vals = [next(densos) if m == "." else None for m in marcas]
            # Nature self-describing (#TCF.8, ADR-0027): reverte LAZY — so' ao
            # materializar a coluna consultada, preservando a laziness (colunas nao
            # tocadas nem decodam o body). Fonte unica com o caminho L4: `_reverte_nature`.
            vals = self._reverte_nature(name, vals)
            # Tipo primitivo (`.8H`): a mesma reversao lazy, um nivel abaixo. O header
            # declarou `n`/`b`, entao a coluna volta int/float/bool, nao a grafia. Fonte
            # unica com o decode: `_dec_scalar`.
            # O modo `blob` fica de fora: ali quem produziu os valores foi o
            # `decode()` oficial do single-col, que JÁ devolve no tipo declarado.
            # Castar de novo aplicaria `_dec_scalar` sobre um `int`, que levanta.
            stype = self._stype.get(name)
            if stype and stype != "s" and mode != "blob":
                from tcf.hierarchical import _dec_scalar
                vals = [None if v is None else _dec_scalar(v, stype) for v in vals]
            # BUG-13d (lote 4): cross-check de n_rows INCREMENTAL — compara com
            # qualquer coluna JA' materializada (ints, custo zero, laziness
            # intacta). Fecha o buraco da view em blob EOF-truncado sem exigir
            # decode completo (o cross-check global fica no decode()).
            if self._cache:
                other = next(iter(self._cache))
                if len(vals) != len(self._cache[other]):
                    raise ValueError(
                        f"colunas com n_rows divergentes: {name!r}={len(vals)} "
                        f"vs {other!r}={len(self._cache[other])} — blob "
                        f"corrompido/truncado (T-QA-8 BUG-13d)"
                    )
            self._cache[name] = vals
            if name not in self.touched:   # A2: evita dupla contagem (coluna ja' tocada via _dict_parts)
                self.touched.append(name)
        return self._cache[name]

    # ---- L3: estrutura (dict/raw) — contar/agrupar SEM expandir as N linhas ----
    def _dict_parts(self, name: str, marcar: bool = True):
        """Parseia um corpo V2-B (`@`): (unicas, width, stream). Decodifica só a
        tabelinha de únicos (K valores), nunca as N linhas. A3-O2: cacheado por
        coluna — ops dict repetidas (group_count + where) não re-decodam a tabela.

        `marcar=False` para quem só quer a FORMA (o tamanho do stream e a largura),
        não os valores: `touched` alimenta `materialized_bytes`, que soma o corpo
        INTEIRO da coluna, então marcar por causa de uma tabelinha de K faria um
        `count()` reportar 94,1% de materialização tendo construído 2 valores.
        Nenhum dos dois números é exato (o certo seriam os bytes da tabelinha), e o
        ajuste fino de `materialized_bytes` fica para a revisão do `.9`.
        """
        cached = self._dict_cache.get(name)
        if cached is not None:
            return cached
        body = self._body[name]
        nl = body.find(b"\n")
        ntable = int(body[:nl])
        start = nl + 1
        unicas = _decode_column(body[start:start + ntable].decode("utf-8"))
        # A tabelinha guarda o PAYLOAD; quem consulta (where L4, group_count) compara
        # contra o VALOR. Reverter aqui — nos K unicos, nao nas N linhas — mantem a
        # laziness intacta e fecha a divergencia com `_col` (fonte unica).
        unicas = self._reverte_nature(name, unicas)
        if marcar and name not in self.touched:
            self.touched.append(name)
        stream = body[start + ntable:]
        width = _v2b_width(len(unicas))
        if len(stream) % width != 0:
            # BUG-13e (paridade estrutural com _decode_v2b): stream desalinhado.
            raise ValueError(
                f"slot V2-B corrompido: stream de {len(stream)}B nao e' "
                f"multiplo da largura {width} (coluna {name!r}; T-QA-8 BUG-13e)"
            )
        parts = (unicas, width, stream)
        self._dict_cache[name] = parts
        return parts

    def _structural_count(self, name: str):
        """Linhas SEM materializar valor nenhum. None se a estrutura não disser.

        Uma leitura por modo, da mais barata para a menos:

        - `blob` (single-col): o `n` DECLARADO no cabeçalho das rotas densas; se a
          rota não declara, os contadores SOMADOS do corpo.
        - `raw`: uma linha por valor, conta os `\\n`.
        - `dict`: `len(stream) // width`. A largura depende de K, e K sai da
          tabelinha, que custa O(K) e não O(N). Deduzir K contando `\\n` na tabela
          seria mais barato e **erra**: a tabelinha termina em `\\n` e o corpo raw
          não, então K sai maior em um. No cruzamento K=94 a largura pula de 1 para
          2 e a contagem sai pela metade, com resto zero, ou seja, um guard de
          divisibilidade não pega. Medido no lab 2026-08-24-0600.
        - `tcf` (core no `.8M`): os contadores somados.
        - `split`: a estrutura não diz; devolve None e o chamador decide.
        """
        mode = self._mode[name]
        if mode == "blob":
            cabecalho = self._blob_single.split("\n", 1)[0].encode("utf-8")
            n = _n_declarado(cabecalho)
            return n if n is not None else _n_somado(self._body[name])
        if mode == "raw":
            # Sem marcar `touched`: contar `\n` não constrói valor, e `touched`
            # alimenta `materialized_bytes`. Marcar aqui fazia um `count()` puro
            # reportar 94,1% de materialização com o cache vazio, ou seja, o
            # relatório que existe pra medir a laziness mentia sobre ela.
            return self._body[name].count(b"\n") + 1
        if mode == "dict":
            _, width, stream = self._dict_parts(name, marcar=False)
            return len(stream) // width
        if mode == "tcf":
            return _n_somado(self._body[name])
        return None

    @property
    def nrows(self) -> int:
        """Número de linhas, pelo caminho mais curto que a estrutura oferecer.

        Todas as colunas têm o mesmo número de linhas, então basta UMA, e a ordem de
        preferência é por custo: o cabeçalho que já declara, depois o `raw` que só
        conta separadores, depois o `dict` que lê uma tabelinha de K, depois os
        contadores do core. Só o `split` não diz nada, e aí decodifica a coluna mais
        barata, que era o comportamento antigo para todos os modos.
        """
        for modo in ("blob", "raw", "dict", "tcf"):
            for name in self._order:
                if self._mode[name] != modo:
                    continue
                sc = self._structural_count(name)
                if sc is not None:
                    return sc
        cheapest = min(self._body, key=lambda n: len(self._body[n]))
        return len(self._col(cheapest))

    def group_count(self, col, idx=None) -> dict:
        """Contagem por grupo (`{valor: n}`).

        Numa coluna dicionário (`@`) sem filtro, o caminho é estrutural: tallia o
        stream de índices e decodifica só os K únicos, sem expandir as N linhas. Nos
        demais modos, e sempre que há filtro ou mais de uma coluna de agrupamento,
        cai no fallback de materializar e contar.

        `col` aceita uma coluna ou uma lista; com lista a chave é a tupla dos valores.
        """
        if isinstance(col, (list, tuple)) or idx is not None:
            return dict(Counter(self._chaves_de_grupo(col, idx)))
        col = self._resolve_col(col)
        if self._mode[col] == "dict":
            unicas, width, stream = self._dict_parts(col)
            # `_dict_parts` já reverte a NATURE; o TIPO é o que faltava. Sem ele o
            # grupo vinha com a grafia crua (`'true'` em vez de `True`) e a chave do
            # resultado não batia com a que o `select` devolve.
            stype = self._stype.get(col)
            if stype and stype != "s":
                from tcf.hierarchical import _dec_scalar
                unicas = [None if u is None or u == "" else _dec_scalar(u, stype)
                          for u in unicas]
            tally = Counter()
            for off in range(0, len(stream), width):
                tally[unicas[_idx_at(stream, off, width)]] += 1
            return dict(tally)
        return dict(Counter(self._col(col)))

    def _chaves_de_grupo(self, por, idx=None):
        """A chave de cada linha, para `por` simples ou lista de colunas.

        Com uma coluna a chave é o valor; com várias é a tupla dos valores, que é o
        `GROUP BY a, b` do SQL. Uma coluna só continua devolvendo o valor cru, e não
        uma tupla de um elemento, porque a chave é o que o usuário vê no resultado.
        """
        if isinstance(por, (list, tuple)):
            cols = [self._resolve_col(c) for c in por]
            if not cols:
                raise ValueError("group by sem coluna: passe ao menos uma")
            colunas = [self._col(c) for c in cols]
            n = len(colunas[0])
            for c, vals in zip(cols, colunas):
                if len(vals) != n:
                    raise ValueError(
                        f"colunas com n_rows divergentes: {cols[0]!r}={n} vs "
                        f"{c!r}={len(vals)}")
            linhas = range(n) if idx is None else idx
            return [tuple(vals[i] for vals in colunas) for i in linhas]
        col = self._resolve_col(por)
        vals = self._col(col)
        return vals if idx is None else [vals[i] for i in idx]

    def _group_agg(self, por, col, op: str, idx=None) -> dict:
        """Motor único de `group_sum/min/max/avg`: um laço, uma regra de nulo.

        O contrato de valor é o mesmo dos agregadores simples: vazio e nulo ficam de
        fora da conta, e não-numérico levanta. A diferença está no grupo sem nenhum
        valor aproveitável: para `sum` ele vale `0.0`, porque o grupo existe mesmo que
        a soma seja vazia; para `min`/`max`/`avg` não há resposta, e o grupo sai como
        `None` em vez de sumir. Sumir esconderia que a chave estava lá.
        """
        chaves = self._chaves_de_grupo(por, idx)
        cnome = self._resolve_col(col)
        valores = self._col(cnome)
        if idx is not None:
            valores = [valores[i] for i in idx]
        if len(chaves) != len(valores):
            raise ValueError(
                f"colunas com n_rows divergentes: chave={len(chaves)} vs "
                f"{cnome!r}={len(valores)}")

        acumulado: dict = {}
        for chave, v in zip(chaves, valores):
            baldes = acumulado.setdefault(chave, [])
            if v == "" or v is None:
                continue
            baldes.append(float(v))   # ValueError em não-numérico, como em `sum()`

        out: dict = {}
        for chave, nums in acumulado.items():
            if op == "sum":
                out[chave] = sum(nums) if nums else 0.0
            elif not nums:
                out[chave] = None
            elif op == "min":
                out[chave] = min(nums)
            elif op == "max":
                out[chave] = max(nums)
            elif op == "avg":
                out[chave] = sum(nums) / len(nums)
            else:
                raise ValueError(
                    f"operação de grupo desconhecida: {op!r} "
                    f"(use sum, min, max ou avg)")
        return out

    def group_sum(self, por, col: str, idx=None) -> dict:
        """Soma `col` agrupando por `por`: o `GROUP BY x SUM(y)` do TCF.

        Materializa as colunas envolvidas e nada mais, então numa tabela larga a conta
        sai sem tocar o resto do blob. Vazio e nulo ficam de fora da soma, como em
        `sum()`; um grupo em que todos os valores são nulos soma `0.0`, porque o grupo
        existe (diferente de não existir).

        `por` aceita uma coluna ou uma lista, e com lista a chave é a tupla dos
        valores, que é o `GROUP BY a, b`.

        Diferente de `agg_by`, que é mais barato mas exige a tabela já ordenada pela
        chave (`encode(..., sort_by=)`): aqui a ordem não importa.
        """
        return self._group_agg(por, col, "sum", idx)

    def group_min(self, por, col: str, idx=None) -> dict:
        """Menor valor de `col` por grupo. Grupo sem valor aproveitável sai `None`."""
        return self._group_agg(por, col, "min", idx)

    def group_max(self, por, col: str, idx=None) -> dict:
        """Maior valor de `col` por grupo. Grupo sem valor aproveitável sai `None`."""
        return self._group_agg(por, col, "max", idx)

    def group_avg(self, por, col: str, idx=None) -> dict:
        """Média de `col` por grupo. Grupo sem valor aproveitável sai `None`."""
        return self._group_agg(por, col, "avg", idx)

    # ---- L4: filtro assistido por índice de dicionário (sem decodar tudo) ----
    def _dict_target_ids(self, col: str, value, pred):
        """Para uma coluna `@`: (width, stream, set de ids dos únicos que casam).

        Avalia value/pred sobre os K únicos, não sobre as N linhas: é o caminho
        rápido do filtro. Os únicos saem do dicionário em TEXTO, então o tipo e a
        nature precisam ser revertidos aqui também, senão a comparação é feita
        contra a grafia crua: `where("ativo", True)` respondia **zero** numa coluna
        booleana em modo `@`, porque comparava `True` com `"true"`. O caminho lento
        (`_col`) já revertia, então os dois discordavam conforme o modo da coluna.
        """
        unicas, width, stream = self._dict_parts(col)
        stype = self._stype.get(col)
        if stype and stype != "s":
            from tcf.hierarchical import _dec_scalar
            unicas = [None if u is None or u == "" else _dec_scalar(u, stype)
                      for u in unicas]
        if pred is not None:
            ids = {i for i, u in enumerate(unicas) if pred(u)}
        else:
            ids = {i for i, u in enumerate(unicas) if u == value}
        return width, stream, ids, len(unicas)

    @staticmethod
    def _idx_do_dict(width: int, stream: bytes, ids: set, k: int) -> list:
        """Índices das linhas que casaram, num corpo `@`.

        A tabela de únicos é a lista FECHADA dos valores que a coluna contém, então
        ela responde os dois extremos antes de o stream ser tocado:

        - **nenhum** único casou: nenhuma linha pode casar, porque toda linha aponta
          para algum único. A resposta é `[]` sem ler um byte do stream.
        - **todos** os únicos casaram: toda linha casa, e a resposta é
          `range(n_linhas)`, com `n_linhas = len(stream) // width`.

        Antes os dois extremos varriam o stream inteiro decodificando índice por
        índice para chegar na mesma resposta: numa coluna de 2000 linhas, filtrar por
        um valor inexistente visitava 2000 posições para devolver lista vazia.

        No caso do meio a varredura continua, porque aí a resposta depende mesmo de
        quais linhas apontam para quê.
        """
        if not ids:
            return []
        if len(ids) == k:
            return list(range(len(stream) // width))
        return [i for i, off in enumerate(range(0, len(stream), width))
                if _idx_at(stream, off, width) in ids]

    # ---- numérico (contrato: ignora vazios; erra em não-numérico) ----
    def _floats(self, col: str, idx: list[int] | None) -> list[float]:
        vals = self._col(col)
        rng = idx if idx is not None else range(len(vals))
        out = []
        for i in rng:
            s = vals[i]
            # vazio e NULO não entram na conta: `None` é ausência de valor, não zero.
            # É a mesma escolha de qualquer agregador de coluna (SQL, pandas), e sem
            # ela um único nulo derrubava a soma da coluna inteira com TypeError.
            if s == "" or s is None:
                continue
            out.append(float(s))   # ValueError em não-numérico = intencional
        return out

    # ---- agregadores ----
    def count(self, idx: list[int] | None = None) -> int:
        return len(idx) if idx is not None else self.nrows

    def sum(self, col: str, idx: list[int] | None = None) -> float:
        return sum(self._floats(col, idx))

    def min(self, col: str, idx: list[int] | None = None) -> float:
        f = self._floats(col, idx)
        if not f:
            raise ValueError(f"sem valores numéricos em {col!r}")
        return min(f)

    def max(self, col: str, idx: list[int] | None = None) -> float:
        f = self._floats(col, idx)
        if not f:
            raise ValueError(f"sem valores numéricos em {col!r}")
        return max(f)

    def avg(self, col: str, idx: list[int] | None = None) -> float:
        f = self._floats(col, idx)
        if not f:
            raise ValueError(f"sem valores numéricos em {col!r}")
        return sum(f) / len(f)

    # ---- L5: layout p/ baixa latência — grupos contíguos (requer sort_by) ----
    def group_ranges(self, key: str) -> dict[str, tuple[int, int]]:
        """`{valor: (início, fim)}` por grupo CONTÍGUO. Pensado pra um blob já
        ordenado por `key` (`encode(table, sort_by=key)`), onde os grupos ficam
        adjacentes (a chave vira runs `*N|`). Erra se a coluna não está agrupada."""
        vals = self._col(key)
        ranges: dict[str, tuple[int, int]] = {}
        i, n = 0, len(vals)
        while i < n:
            v = vals[i]
            j = i + 1
            while j < n and vals[j] == v:
                j += 1
            if v in ranges:
                raise ValueError(
                    f"coluna {key!r} não está agrupada (valor {v!r} reaparece); "
                    f"use encode(table, sort_by={key!r}) pro layout L5"
                )
            ranges[v] = (i, j)
            i = j
        return ranges

    def agg_by(self, key: str, col: str | None = None, op: str = "count") -> dict:
        """Group-by sobre o layout ordenado: `{valor_da_chave: agregado}`.
        `op='count'` (default) usa só os intervalos; `sum/min/max/avg` agregam `col`
        em cada intervalo (a coluna é decodificada UMA vez; cada grupo = um slice).
        É o 'qtd por usuário': `agg_by('usuario', 'qtd', 'sum')`."""
        ranges = self.group_ranges(key)
        if op == "count":
            return {v: e - s for v, (s, e) in ranges.items()}
        fn = {"sum": self.sum, "min": self.min, "max": self.max, "avg": self.avg}[op]
        return {v: fn(col, range(s, e)) for v, (s, e) in ranges.items()}

    # ---- filtro: descomprime SÓ a coluna do filtro, devolve view restrita ----
    def where(self, col: str, value=None, *, pred: Callable[[str], bool] | None = None) -> "Filtered":
        col = self._resolve_col(col)
        value = self._coage(col, value, pred)
        if self._mode[col] == "dict":           # L4: varre o stream, sem decodar os N valores
            width, stream, ids, k = self._dict_target_ids(col, value, pred)
            return Filtered(self, self._idx_do_dict(width, stream, ids, k))
        vals = self._col(col)
        if pred is not None:
            idx = [i for i, v in enumerate(vals) if pred(v)]
        else:
            idx = [i for i, v in enumerate(vals) if v == value]
        return Filtered(self, idx)

    # ---- linhas alinhadas (decodifica só as colunas pedidas) ----
    def select(self, cols: list[str] | None = None, idx: list[int] | None = None) -> list[dict]:
        # `is not None`, nao truthiness: `select(0)` (posicao 0) era engolido pelo
        # `or` e devolvia TODAS as colunas, calado (lab 2026-08-23-1410). Escalar
        # (str|int) e' sobrecarga de 1 coluna, como no schema=; int resolve pra
        # NOME via _resolve_col, e as chaves do dict de saida sao sempre nomes.
        if cols is None:
            cols = list(self._order)
        elif isinstance(cols, (str, int)):
            cols = [cols]
        cols = [self._resolve_col(c) for c in cols]
        decoded = {c: self._col(c) for c in cols}
        rng = idx if idx is not None else range(self.nrows)
        return [{c: decoded[c][i] for c in cols} for i in rng]

    # ---- relatório da seletividade (memória/latência) ----
    def report(self) -> dict:
        mat = self.materialized_bytes
        tot = self.total_bytes
        return {
            "total_bytes": tot,
            "materialized_bytes": mat,
            "pct": round(100 * mat / tot, 1) if tot else 0.0,
            "touched": list(self.touched),
            "n_cols": len(self._order),
        }


class Filtered:
    """Resultado de `where()`: agrega/seleciona só nas linhas que casaram (alinhadas)."""

    def __init__(self, parent: LazyTCF, idx: list[int]):
        self._p = parent
        self.indices = idx

    def count(self) -> int:
        return len(self.indices)

    def sum(self, col: str) -> float:
        return self._p.sum(col, self.indices)

    def min(self, col: str) -> float:
        return self._p.min(col, self.indices)

    def max(self, col: str) -> float:
        return self._p.max(col, self.indices)

    def avg(self, col: str) -> float:
        return self._p.avg(col, self.indices)

    # ---- agrupamento sobre as linhas filtradas: o `WHERE ... GROUP BY` ----
    # Sem isto, filtrar e agrupar era a única combinação básica de SQL que a view não
    # fazia: `where(...)` devolvia um `Filtered` que só sabia agregar o conjunto todo.
    # Cada um repassa os índices já filtrados, então a conta roda nas linhas que
    # casaram e a chave continua sendo a mesma que o `group_*` da view devolve.

    def group_count(self, col) -> dict:
        return self._p.group_count(col, self.indices)

    def group_sum(self, por, col: str) -> dict:
        return self._p.group_sum(por, col, self.indices)

    def group_min(self, por, col: str) -> dict:
        return self._p.group_min(por, col, self.indices)

    def group_max(self, por, col: str) -> dict:
        return self._p.group_max(por, col, self.indices)

    def group_avg(self, por, col: str) -> dict:
        return self._p.group_avg(por, col, self.indices)

    def select(self, cols: list[str] | None = None) -> list[dict]:
        return self._p.select(cols, self.indices)

    def where(self, col: str, value=None, *, pred=None) -> "Filtered":
        """Encadeia filtro (AND): restringe os índices atuais."""
        p = self._p
        col = p._resolve_col(col)
        value = p._coage(col, value, pred)
        if p._mode[col] == "dict":              # L4: lê só as posições já filtradas no stream
            width, stream, ids, k = p._dict_target_ids(col, value, pred)
            # Os mesmos dois extremos do `where` de entrada, agora sobre os índices já
            # filtrados: nenhum único casou, nada sobrevive ao AND; todos casaram, o
            # filtro não restringe nada e os índices atuais passam inteiros.
            if not ids:
                return Filtered(p, [])
            if len(ids) == k:
                return Filtered(p, list(self.indices))
            idx = [i for i in self.indices if _idx_at(stream, i * width, width) in ids]
            return Filtered(p, idx)
        vals = p._col(col)
        if pred is not None:
            idx = [i for i in self.indices if pred(vals[i])]
        else:
            idx = [i for i in self.indices if vals[i] == value]
        return Filtered(p, idx)


def view(blob: str) -> LazyTCF:
    """Conecta a um blob TCF multi-coluna sem descomprimir. Ver LazyTCF."""
    return LazyTCF(blob)


# ===========================================================================
# NOTAS — otimizações:
#   L3 (FEITO, via dict/raw) — `nrows`/`group_count` contam/agrupam SEM expandir as
#       N linhas: dicionário (`@`) = tamanho do stream + tally; raw = nº de '\n'.
#       ACHADO (verificado): agregar os runs `*N|` direto no modo-tcf
#       NÃO é barato/separável — OBAT+HCC entrelaçam o valor com refs de outras
#       linhas (invariante de contagem falhou em colunas tipo-ID; 0 colunas tcf
#       "clean-numeric"). O ganho estrutural limpo vive no dict/raw. Por isso L3
#       usa o dicionário, não o parse de `*N|` do tcf. tcf/split caem em fallback.
#   L4 (FEITO) — `where` sobre coluna `@` varre só o stream de índices (compara id,
#       sem decodar os N valores); value/pred avaliados sobre os K únicos. Encadeado
#       (AND) lê só as posições já filtradas. Non-dict: fallback (decode + filtro).
#   L5 (FEITO) — layout p/ baixa latência: `encode(table, sort_by=key)` agrupa as linhas
#       (a chave vira runs `*N|` contíguos) → `group_ranges(key)` dá `{valor:(início,fim)}`
#       e `agg_by(key, col, op)` faz group-by por SLICE (cada grupo = um intervalo). É o
#       "qtd por usuário". sort_by é order-free; mantém/melhora a compressão da transmissão.
#   +   saltos dedutivos / inferência pela estrutura; em último caso, dicas no header.
# Acoplamento: reusa decoders internos de tcf.multi/tcf.decoder (_decode_column/
#   _decode_v2b/_decode_struct_split). É a camada que LÊ o formato; se os internos
#   mudarem, ela acompanha. NÃO muda encode/decode/formato (read-only por design).
# ===========================================================================
