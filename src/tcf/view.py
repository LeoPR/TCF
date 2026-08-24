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


_PY_DO_TIPO = {"n": (int, float), "b": (bool,), "s": (str,)}
_NOME_DO_TIPO = {"n": "int/float", "b": "bool", "s": "str"}


def _valida_where_value(value, pred, stype: str = "s") -> None:
    """O valor comparado tem de ser do tipo DA COLUNA, que o header declara.

    Numa coluna `n`, `where(col, 120)` é a forma natural e `where(col, "120")`
    nunca casaria: os valores voltam `int`. Numa coluna de texto vale o inverso.
    Nos dois casos o erro é alto: comparar tipo trocado respondia 0 linhas
    CALADO, que parece filtro vazio e é bug do chamador (lab 2026-08-23-1410 G6).
    `None` casa nulo em qualquer coluna; com `pred=`, `value` é ignorado.
    """
    if pred is not None or value is None:
        return
    aceitos = _PY_DO_TIPO.get(stype, (str,))
    # bool é subclasse de int: numa coluna `n`, `True` não é 1.
    if isinstance(value, aceitos) and not (stype == "n" and isinstance(value, bool)):
        return
    sugestao = {"n": "where(col, 120)", "b": "where(col, True)",
                "s": f"where(col, {str(value)!r})"}[stype]
    raise TypeError(
        f"view.where: esta coluna é {_NOME_DO_TIPO.get(stype, 'str')} e o valor é "
        f"{type(value).__name__} ({value!r}), então a comparação nunca casaria. "
        f"Compare com o tipo da coluna, ex. {sugestao}"
    )


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
            # `count`, `sum` e `where` valem igual. Aqui não há laziness a preservar,
            # o blob INTEIRO é a coluna, então o decode oficial é a fonte: ele já
            # trata as sub-formas (bool denso em bits, float, spec no header) que
            # reimplementar aqui só faria divergir. Nome da coluna: `0`, como qualquer
            # anônima (ADR-0029).
            from tcf.decoder import decode as _decode_blob
            nome = "0"
            self._mode[nome] = "tcf"
            self._body[nome] = raw[nl1 + 1:]
            self._order.append(nome)
            self._cache[nome] = _decode_blob(blob)
            self.touched.append(nome)
            primeiro = next((v for v in self._cache[nome] if v is not None), None)
            self._stype[nome] = {bool: "b", int: "n", float: "n"}.get(
                type(primeiro), "s")
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
            stype = self._stype.get(name)
            if stype and stype != "s":
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
    def _dict_parts(self, name: str):
        """Parseia um corpo V2-B (`@`): (unicas, width, stream). Decodifica só a
        tabelinha de únicos (K valores), nunca as N linhas. A3-O2: cacheado por
        coluna — ops dict repetidas (group_count + where) não re-decodam a tabela."""
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
        if name not in self.touched:
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
        """Linhas SEM decodificar valores: dict (tamanho do stream) / raw
        (nº de '\\n'). None se o modo exige decode (tcf/split)."""
        mode = self._mode[name]
        if mode == "dict":
            _, width, stream = self._dict_parts(name)
            return len(stream) // width
        if mode == "raw":
            if name not in self.touched:
                self.touched.append(name)
            return self._body[name].count(b"\n") + 1
        return None

    @property
    def nrows(self) -> int:
        """Número de linhas, pelo CAMINHO mais curto (A3-O1):
        1) raw → conta `\\n` (ZERO decode); 2) dict → 1 decode da tabela;
        3) fallback → decodifica a coluna tcf/split mais barata."""
        for name in self._order:                 # O1: raw primeiro (custo zero)
            if self._mode[name] == "raw":
                if name not in self.touched:
                    self.touched.append(name)
                return self._body[name].count(b"\n") + 1
        for name in self._order:                 # senão dict (1 decode de tabela)
            sc = self._structural_count(name)
            if sc is not None:
                return sc
        cheapest = min(self._body, key=lambda n: len(self._body[n]))
        return len(self._col(cheapest))

    def group_count(self, col: str) -> dict[str, int]:
        """Contagem por grupo (`{valor: n}`) SEM expandir a coluna, quando ela é
        dicionário (`@`): tallia o stream de índices + decodifica só os únicos.
        Demais modos: fallback (decode + Counter). É a 'agregação sem expandir'."""
        col = self._resolve_col(col)
        if self._mode[col] == "dict":
            unicas, width, stream = self._dict_parts(col)
            tally = Counter()
            for off in range(0, len(stream), width):
                tally[unicas[_idx_at(stream, off, width)]] += 1
            return dict(tally)
        return dict(Counter(self._col(col)))

    def group_sum(self, por: str, col: str) -> dict:
        """Soma `col` agrupando por `por`: o `GROUP BY x SUM(y)` do TCF.

        Materializa as DUAS colunas e nada mais, então numa tabela larga a conta sai
        sem tocar o resto do blob. Vazio e nulo ficam de fora da soma, como em
        `sum()`; um grupo em que todos os valores são nulos soma `0.0`, porque o
        grupo existe (diferente de não existir).

        Diferente de `agg_by`, que é mais barato mas exige a tabela já ordenada pela
        chave (`encode(..., sort_by=)`): aqui a ordem não importa.
        """
        por, col = self._resolve_col(por), self._resolve_col(col)
        chaves, valores = self._col(por), self._col(col)
        if len(chaves) != len(valores):
            raise ValueError(
                f"colunas com n_rows divergentes: {por!r}={len(chaves)} vs "
                f"{col!r}={len(valores)}")
        out: dict = {}
        for chave, v in zip(chaves, valores):
            acc = out.setdefault(chave, 0.0)
            if v == "" or v is None:
                continue
            out[chave] = acc + float(v)
        return out

    # ---- L4: filtro assistido por índice de dicionário (sem decodar tudo) ----
    def _dict_target_ids(self, col: str, value, pred):
        """Para uma coluna `@`: (width, stream, set de ids dos únicos que casam).
        Avalia value/pred sobre os K únicos (não sobre as N linhas)."""
        unicas, width, stream = self._dict_parts(col)
        if pred is not None:
            ids = {i for i, u in enumerate(unicas) if pred(u)}
        else:
            ids = {i for i, u in enumerate(unicas) if u == value}
        return width, stream, ids

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
        _valida_where_value(value, pred, self._stype.get(col, "s"))
        if self._mode[col] == "dict":           # L4: varre o stream, sem decodar os N valores
            width, stream, ids = self._dict_target_ids(col, value, pred)
            idx = [i for i, off in enumerate(range(0, len(stream), width))
                   if _idx_at(stream, off, width) in ids]
            return Filtered(self, idx)
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

    def select(self, cols: list[str] | None = None) -> list[dict]:
        return self._p.select(cols, self.indices)

    def where(self, col: str, value=None, *, pred=None) -> "Filtered":
        """Encadeia filtro (AND): restringe os índices atuais."""
        p = self._p
        col = p._resolve_col(col)
        _valida_where_value(value, pred, p._stype.get(col, "s"))
        if p._mode[col] == "dict":              # L4: lê só as posições já filtradas no stream
            width, stream, ids = p._dict_target_ids(col, value, pred)
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
