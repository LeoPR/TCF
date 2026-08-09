"""TCF decoder — API publica unificada (ADR-0014).

Wrapper de alto nivel: TCF text -> lista de strings OU dict de colunas.

Dispatch automatico pelo shebang:
- `#TCF.7 M\\n` (vivo) ou `#TCF.6 M\\n` (LEGADO, leitura ate' o 1.0) -> multi-column,
  retorna `dict[str, list[str]]`
- caso contrario -> single-column, retorna `list[str]`

Uso minimo:

    from tcf import encode, decode

    # Single
    text = encode(["abc", "abcd"])
    values = decode(text)              # -> list[str]

    # Multi
    text = encode({"id": [...], "name": [...]})
    table = decode(text)               # -> dict[str, list[str]]

    # Identidade: decode(encode(x)) == x sempre, tanto pra list quanto dict

Internamente delega ao decoder de HCC com seq-RLE near-identical
(`HCCSeqRLE`, M10/ADR-0011) pra single-col e a `_decode_multi`
(ADR-0013) pra multi-col.

Backward compat:
- M9 puro (sem markers near-identical): lido sem mudanca (subset de M10)
- Outputs de versoes anteriores que nao tinham shebang multi: tratados
  como single-col (comportamento atual)

Detalhes:
- `docs/algorithms/HCC.md`, `docs/algorithms/output-convention.md`
  (convencao sem-brackets / LF-unico implementada aqui e em hcc_seqrle.py)
- `docs/adr/0011-pacote1-weld-canonical.md`
- `docs/adr/0013-multi-column-canonical-api.md`
- `docs/adr/0014-unified-api-side-outputs.md`

Invariante `decode(encode(x)) == x` guardado por `tests/test_core_rt.py`
(single) + `tests/test_multi_col_rt.py` (multi) +
`tests/test_real_world_snapshots.py` (real-world).
"""

from __future__ import annotations

import base64
import binascii as _binascii
from typing import TYPE_CHECKING

from tcf.composicional.hcc_seqrle import HCCSeqRLE

if TYPE_CHECKING:
    from tcf.natures.templated_checked import TemplatedCheckedSpec


# #TCF.8 = formato VIVO/DEFAULT (ADR-0032). O char logo apos '#TCF.8' discrimina:
# 'M'=multi (#TCF.8M, meta inline), ' '=single+spec (#TCF.8 [nome]:spec),
# ''=single version-stamp (#TCF.8, magic-number p/ file), 'H'=hierarquico RESERVADO
# (ADR-0031, codec no lab -> fail-loud). Legado #TCF.6/#TCF.7 CORTADO (git-as-compat).
_V8_MAGIC = "#TCF.8"  # base do #TCF.8; o disc (char no indice 6) decide


def _resolve_header_spec(nature_id: str, supplied, *, where: str):
    """Resolve um ID do header pelo registry core ou por spec declarado fora dele."""
    from tcf.natures import _resolve_nature_id

    spec = _resolve_nature_id(nature_id)
    if spec is not None:
        return spec
    if supplied is not None and getattr(supplied, "name", None) == nature_id:
        return supplied
    if supplied is not None:
        raise ValueError(
            f"nature-id {nature_id!r} no header {where} nao coincide com o spec "
            f"out-of-band {getattr(supplied, 'name', None)!r}"
        )
    raise ValueError(
        f"nature-id desconhecido no header {where}: {nature_id!r} — registry core "
        "fechado; forneca o spec correspondente out-of-band para decodificar"
    )


def decode(
    tcf_text: str,
    *,
    nature: "TemplatedCheckedSpec | None" = None,
    nature_per_col: "dict[str, TemplatedCheckedSpec] | None" = None,
    max_length: int | None = None,
) -> list[str] | dict[str, list[str]]:
    """Decode texto TCF. Roteia pela assinatura de formato (magic).

    Args:
        tcf_text: conteudo TCF (texto). Aceita (ADR-0032, #TCF.8 default):
            - Multi-col: `#TCF.8M<meta>\\n<bodies>` -> `dict[str, list[str]]`
            - Single + spec: `#TCF.8 [nome]:id\\n<body>` -> `list[str]`
            - Version-stamp: `#TCF.8\\n<body>` -> `list[str]`
            - Orfao: body puro (sem magic) -> `list[str]`
            Legado `#TCF.6/.7` e versoes desconhecidas `#TCF.<N>` -> ValueError
            (git-as-compat, ADR-0024).
        nature: spec usado no encode pra pre-tx (ADR-0015). Se fornecido,
            aplica decode_value reverse apos M10 decode.
        nature_per_col: dict pra reverse multi-col pre-tx.

    Returns:
        list[str] OU dict[str, list[str]] dependendo do formato.

    Raises:
        ValueError: multi-col malformado (sem magic, sem meta line).
    """
    if not isinstance(tcf_text, str):
        # BUG-10d (lote 3): fronteira clara em vez de AttributeError fundo.
        raise TypeError(
            f"decode espera str (conteudo TCF em texto); got {type(tcf_text).__name__}"
        )
    line1 = tcf_text.split("\n", 1)[0]
    # BUG-04 (T-QA-8 F0 lote 2): a VERSAO e' deduzivel do proprio magic —
    # '#TCF.' + run de digitos DECLARA a versao. Le o run COMPLETO (senao
    # '#TCF.85M' viraria .8 + disc '5'). Subversoes pre-1.0 sao controle de
    # dev (ADR-0024); compat real so' no 1.0 (visao owner 2026-07-10: um
    # '#TCF1M' final fecha tudo — sem 'if .7'/'if .6').
    _ver = ""
    if line1.startswith("#TCF."):
        for _ch in line1[5:]:
            if _ch in "0123456789":
                _ver += _ch
            else:
                break
    # Legado #TCF.6/#TCF.7 CORTADO (ADR-0032, 2026-07-09): nao decodavel no 0.8.
    # git-as-compat (ADR-0024) — recupere a era pra ler/comparar.
    if _ver in ("6", "7"):
        raise ValueError(
            f"formato legado {line1[:8]!r} nao suportado no 0.8 (ADR-0032: #TCF.6/.7 "
            f"cortados). git checkout <commit pre-0.8> pra ler, ou re-encode com o 0.8."
        )
    if _ver and _ver != "8":
        # Fail-loud claro (antes caia no decode orfao -> KeyError criptico do HCC).
        raise ValueError(
            f"blob #TCF.{_ver}: versao desconhecida deste decoder (formato atual = "
            f"#TCF.8, ADR-0032). Versoes de dev vivem no git (ADR-0024); "
            f"compatibilidade real so' a partir do 1.0."
        )
    # POLARIDADE (weld 2026-07-26): camada de BORDA, a PRIMEIRA coisa do decode. Desfaz o
    # delimitador e devolve o corpo CANONICO — dai' pra baixo todo o dispatch e o parser sao
    # os de sempre, e o seq-RLE (que localiza o digito incrementavel PELO ESCAPE) continua
    # vendo so' corpo canonico. Ver `composicional/polaridade.py`.
    if _ver == "8":
        _tag, _sufixo = _separa_sufixo_polaridade(line1[6:])
        if _sufixo:
            from tcf.composicional.polaridade import despolariza

            _corpo = tcf_text[len(line1) + 1 :]
            line1 = _V8_MAGIC + _tag
            tcf_text = line1 + "\n" + despolariza(_corpo, _sufixo)
    # Discriminador #TCF.8 (ADR-0029): char logo apos '#TCF.8'. 'M'=multi (#TCF.8M),
    # ' '=single+spec (#TCF.8 ...), ''=version-stamp (line1 == '#TCF.8').
    disc8 = line1[6:7] if _ver == "8" else None
    # HIER: #TCF.8H (disc 'H', ADR-0031) — codec hierarquico (weld T-CODE-TCF8H-WELD).
    # Camada L2 aditiva: dispatch O(1) pelo char; L1 (compressor de coluna) reusado.
    if disc8 == "H":
        from tcf.hierarchical import decode_hierarchical

        return decode_hierarchical(tcf_text)
    # TIPADO: #TCF.8<tag> (tag in {b,n,s}) — single-col TIPADO (weld #4). Pre-avaliador de
    # apelidos (camada implicita, owner 2026-07-24): expande o header tipado -> forma explicita
    # e delega o CORPO ao core (_decode_column), castando pro tipo. A variavel `modo` (o conceito
    # do '~') e' DEDUZIDA DA POSICAO (indice 7); NAO ha '~' no wire. #4a = modo CORE; denso bN = #4b.
    if disc8 in _TAGS_TIPO:
        return _decode_typed(tcf_text, disc8, max_length=max_length)
    # bN DE DOMINIO: #TCF.8B<w><n> (dominio primeiro) / #TCF.8C<w><n> (dominio por ultimo).
    # Densidade por CARDINALIDADE — ver composicional/dominio_bn.py e ADR-0036.
    if disc8 in _DISCS_BN:
        from tcf.composicional.dominio_bn import decode_bn

        return decode_bn(
            tcf_text, disc8, lambda b: _decode_column(b, max_length=max_length)
        )
    # FAIL-LOUD (ADR-0032 §6): discriminador reservado/desconhecido apos '#TCF.8' NAO
    # pode degradar pra decode orfao silencioso (corrompe).
    if disc8 is not None and disc8 not in ("M", " ", ""):
        raise ValueError(f"#TCF.8: discriminador {disc8!r} desconhecido — nao decodavel.")

    # MULTI: #TCF.8M (disc 'M', meta inline).
    if disc8 == "M":
        from tcf.multi import _decode_multi_impl

        result, header_ids = _decode_multi_impl(tcf_text)
        # Natures auto-descritas no header (#TCF.8M e' SELF-DESCRIBING): o header e'
        # AUTORITATIVO — resolve+aplica os :id. Pos-FLOOR (T-SPEC-DEEPDIVE §5.1), uma
        # coluna SEM :id significa DEFINITIVAMENTE valores ORIGINAIS (a nature perdeu
        # o min() ou nao foi passada). Logo o `nature_per_col` out-of-band do decode
        # NAO deve tocar colunas nao-marcadas — fazia isso e CORROMPIA silenciosamente
        # valores que casassem a forma base-94 (achado da verificacao adversarial do
        # FLOOR, 2026-07-12). Para IDs fora do registry core, o spec out-of-band so'
        # entra se o nome coincidir exatamente com o ID do header.
        header_resolved: set[str] = set()
        if header_ids:
            for name, nat_id in header_ids.items():
                supplied = nature_per_col.get(name) if nature_per_col else None
                spec = _resolve_header_spec(
                    nat_id, supplied, where=f"multi-col coluna {name!r}"
                )
                # Wrapper de modulo, nao o metodo: e' ele que trata o slot nulo do core
                # (`None` volta `None`). Ver `natures/templated_checked.py::decode_value`.
                from tcf.natures import decode_value as _nat_de

                result[name] = [_nat_de(spec, v) for v in result[name]]
                header_resolved.add(name)
        # Colunas sem :id continuam definitivamente originais; o parâmetro
        # out-of-band não pode inferir uma nature perdida pelo FLOOR.
        return result

    # SINGLE + SPEC: '#TCF.8 [nome]:spec' (disc espaco). Retorna LIST.
    if disc8 == " ":
        meta = line1[len(_V8_MAGIC) + 1 :]  # apos "#TCF.8 "
        body = tcf_text[len(line1) + 1 :]  # apos a 1a '\n'
        _name, _, nat_id = meta.partition(":")  # nome opcional, descartado
        values = _decode_column(body, max_length=max_length)
        spec = _resolve_header_spec(nat_id, nature, where="single-col")
        # Wrapper de modulo (trata `None` = slot nulo do core), nao o metodo cru.
        from tcf.natures import decode_value as _nat_de

        return [_nat_de(spec, v) for v in values]  # header vence

    # SINGLE version-stamp: line1 == '#TCF.8' (disc vazio). Carimbo de versao
    # (magic-number p/ file/libmagic, ADR-0029) — body single-col puro segue.
    # Out-of-band `nature=` NAO aplicado: pos-FLOOR (T-SPEC-DEEPDIVE §5.1) uma nature
    # que VENCE emite '#TCF.8 :id' (self-describing); stamp/orfao = valores ORIGINAIS
    # (a nature perdeu OU nao foi passada). Aplicar o spec aqui corromperia originais
    # que casassem a forma base-94 (mesma classe do achado multi-col; o param fica na
    # assinatura por compat, mas #TCF.8 e' self-describing e manda).
    if disc8 == "":
        body = tcf_text[len(line1) + 1 :]  # apos "#TCF.8\n"
        if body == "":
            # '#TCF.8\n' (corpo vazio) = [] — canonicidade do vazio (owner 2026-07-24,
            # simetrico ao encode). Distinto de '#TCF.8\n\n' (corpo '\n' -> ['']) e do
            # orfao. O version-stamp SEMPRE tem corpo nao-vazio, entao nao colide.
            return []
        return _decode_column(body, max_length=max_length)

    # ORFAO: single-col body puro (sem shebang) — camada 1 (ADR-0029).
    return _decode_column(tcf_text, max_length=max_length)


def _decode_column(tcf_text: str, max_length: int | None = None) -> "list[str | None]":
    """Decode body single-col. Cf. _encode_column no encoder.

    `None` no retorno so' aparece via `^0`/`0` (slot 0 pre-alocado = null). O encoder ATUAL
    nunca emite essas grafias — a rota flat exige `list[str]` e desvia coluna com `None` pro
    `.8H` —, entao na pratica o retorno segue `list[str]` ate' a rota flat abrir p/ `str|None`.

    FUNIL UNICO de coluna — single-col, `.8M`, `view` e hierarquico passam todos por aqui,
    entao o teto `max_length` (default em `syntax.MAX_LENGTH_PADRAO`) protege TODAS as rotas
    mesmo que so' o `decode` publico exponha o override.
    """
    syn = HCCSeqRLE()
    return syn.decode(tcf_text, max_length=max_length)


# --- SINGLE-COL TIPADO (weld #4) — pre-avaliador: header tipado -> forma explicita -> core ---
# Camada 2 (SIGNIFICADO): tag -> tipo, char de modo -> largura. O '~' NAO esta' aqui (nunca e' byte).
# Whitelist do DECODE = so' o que o encoder EMITE (simetria; verif. wf_85fcea32). Hoje: bool.
# 'n'/'s' ficam RESERVADOS no namespace (registry/notas) mas NAO decodaveis ainda -> caem no
# fail-loud 'discriminador desconhecido' em vez de aceitar wire que o encoder nunca produz.
def _separa_sufixo_polaridade(resto: str) -> "tuple[str, str]":
    """`'#TCF.8<resto>'` -> `(tag, sufixo_de_polaridade)`. `('', '')` quando nao ha' sufixo.

    O sufixo e' 1-2 chars IGUAIS de pontuacao no fim; a tag e' o prefixo alfanumerico. A
    separacao e' inequivoca por construcao: a FAIXA do delimitador exclui digito e letra, e
    nenhum discriminador de hoje (`M`, `H`, `b`, `n`, `s`, espaco, vazio) e' pontuacao.

    Conservador de proposito — so' separa quando o resto inteiro casa `[alnum]*[pont]{1,2}`.
    `'#TCF.8 nome:id'` tem espaco e `:`, nao casa, e segue pro caminho de spec intocado.
    """
    from tcf.composicional.polaridade import FAIXA

    faixa = frozenset(FAIXA)
    i = len(resto)
    while i > 0 and resto[i - 1] in faixa:
        i -= 1
    sufixo = resto[i:]
    if not sufixo or len(sufixo) > 2 or any(c != sufixo[0] for c in sufixo):
        return "", ""
    tag = resto[:i]
    if not tag.isalnum() and tag != "":
        return "", ""
    return tag, sufixo


#: Discriminadores do bN de dominio (ADR-0036). `B` = dominio primeiro (streaming);
#: `C` = dominio por ultimo (lote). Ver `composicional/dominio_bn.py`.
_DISCS_BN = frozenset({"B", "C"})

_TAGS_TIPO = frozenset({"b", "n", "s"})
_LARGURA_MODO = {"1": 1, "2": 2, "4": 4, "8": 8}   # modo denso bN (larguras); subtipos = preparado


def _cast_tipo(strs: "list[str | None]", tag: str) -> list:
    """Camada explicita->tipo: os literais do core viram o tipo TIPADO (a semantica nao some).

    `None` (slot 0 pre-alocado) ATRAVESSA qualquer tag: null nao pertence a um tipo, ele e'
    a ausencia do valor. Casta-se so' o que e' literal.

    Tag `b` — DUAS grafias, uma emitida: **slots** `"1"`/`"2"` (canonica, UNICA emitida desde
    o weld 2026-08-01, ADR-0038) e **nomes** `"false"`/`"true"` (decodavel-NAO-emitido:
    wires legados + futuro opt-in legivel; mesmo contrato do modo `C` da ADR-0036).
    O resto e' fail-loud. FONTE UNICA da tabela: `tcf/tipos_internos.py` (CAST_B).
    """
    if tag == "b":
        from tcf.tipos_internos import CAST_B
        for s in strs:
            if s is not None and s not in CAST_B:
                raise ValueError(f"#TCF.8b: valor fora do dominio bool (slots 1/2): {s!r}")
        return [None if s is None else CAST_B[s] for s in strs]
    if tag == "n":
        from math import isfinite

        out = []
        for s in strs:
            if s is None:
                out.append(None)
                continue
            try:
                v = int(s)
            except ValueError:
                try:
                    v = float(s)
                except ValueError:
                    raise ValueError(
                        f"#TCF.8n: valor fora do dominio numerico: {s!r}") from None
                if not isfinite(v):
                    # NaN/±Inf ficam FORA do JSON (RFC 8259) e o encoder nunca os emite —
                    # aceitar aqui seria assimetria (decode entendendo o que encode recusa).
                    raise ValueError(f"#TCF.8n: NaN/Infinity nao e' JSON (RFC 8259): {s!r}")
            # CANONICIDADE POR RE-EMISSAO (weld T-BN-TIPADO, 2026-08-07). O encoder grafa
            # com `str` (o `render` do `_tipo_single_col`); entao a grafia canonica de `v` e'
            # `str(v)`, e qualquer outra e' um wire que o encoder nunca produziria.
            #
            # Sem esta linha, CINCO familias de grafia colidiam no mesmo valor — medido:
            #   '01'->1  '1.50'->1.5  '+1'->1  '1e3'->1000.0  '1_0'->10   (PEP 515!)
            # E' a MESMA classe do bug de cabecalho que a auditoria de 2026-07-28 pegou no
            # bN, e o `test_grafia_nao_canonica_fail_loud` ja' travava o invariante para o
            # HEADER enquanto o VALOR ficava aberto. O invariante existia e nao era aplicado.
            #
            # Mora aqui, no `_cast_tipo`, porque este e' o ponto unico das DUAS rotas
            # numericas do SINGLE-COL TIPADO (corpo core `#TCF.8n` e denso bN `#TCF.8nB`).
            # Gate numa so' criaria a divergencia entre irmaos que ja' custou 4 bugs.
            #
            # ATENCAO — sao TRES rotas numericas no formato, nao duas (auditoria 2026-08-07;
            # a redacao anterior deste comentario dizia "as duas" e induzia o leitor a achar
            # que a familia estava fechada). A terceira e' o `#TCF.8H`, que tem cast proprio
            # em `hierarchical.py::_dec_scalar` (ramo `n`, via `json.loads`) e NAO passa por
            # aqui — e' por onde vai todo numero multi-coluna/aninhado. Ela aceita grafia
            # nao-canonica (`1e3`, `1.50`, `0e0`, `-0`) em silencio.
            # Nivel E5/E4 pela escala de verificacao (so' alcancavel por wire escrito a mao,
            # nunca por `encode`->`decode`), portanto REGISTRADO e nao corrigido aqui:
            # ver `notas/2026-08/2026-08-07-triagem-auditoria-nB-pela-escala.md` achado [1].
            if str(v) != s:
                raise ValueError(
                    f"#TCF.8n: grafia numerica nao-canonica {s!r} (canonica: {str(v)!r}) "
                    f"— duas grafias para o mesmo valor violariam a canonicidade do wire"
                )
            out.append(v)
        return out
    return list(strs)                              # 's' = string (identidade)


def _decode_typed(tcf_text: str, tag: str, max_length: int | None = None) -> list:
    """Decode do single-col tipado. A variavel `modo` (o '~' conceitual) e' deduzida da POSICAO.

    Contratos de retorno: modo core/denso -> lista do TIPO da tag (`b` -> bool/None);
    lazy `#TCF.8bB` (ADR-0039) -> lista mista [bool | None | str] (contrato UNIAO —
    ver `_decode_lazy_bool`)."""
    line1, _sep, body = tcf_text.partition("\n")
    resto = line1[7:]                              # apos '#TCF.8<tag>' (tag = 1 char, indice 6)
    # LAZY BOOL .8bB (ADR-0039): resto = 'B<w><n-hex>' — dominio de extras + bits.
    # Uniao bool+str(+null) com tipo preservado; decode DEDICADO (_decode_lazy_bool).
    # n/s com 'B' caem no fail-loud de header denso abaixo (lazy numerico = outro ticket).
    if resto[:1] == "B" and tag == "b":
        return _decode_lazy_bool(tcf_text, max_length=max_length)
    # DENSO bN TIPADO `#TCF.8nB<w><n>` (weld T-BN-TIPADO, 2026-08-07). A coluna numerica de
    # baixa cardinalidade nao tinha NENHUMA faceta de bits: `int 0/1` x200 gastava 608 B onde
    # 55 bastam. O bloqueio registrado na ADR-0036 era "exige tag DENTRO do cabecalho, que e'
    # grafia nova" — nao e': o `#TCF.8bB` (lazy bool, ADR-0039) ja' usa esta forma exata
    # (tag no indice 6, modo no 7, depois `<w><n>`). O que muda e' so' o CAST na volta.
    #
    # Reescreve o cabecalho pra forma explicita e DELEGA ao `decode_bn` — mesmo idioma que a
    # rota tipada ja' usa pro corpo core (expande o apelido, delega, casta). Delegar em vez de
    # duplicar o parser e' o que faz o `nB` herdar de graca TODAS as checagens do bN:
    # canonicidade do header, marcador obrigatorio, nada depois dos bits, todo slot
    # referenciado, e as tres validacoes do payload b64.
    if resto[:1] == "B" and tag == "n":
        from tcf.composicional.dominio_bn import decode_bn

        return _cast_tipo(
            decode_bn(_V8_MAGIC + tcf_text[7:], "B",
                      lambda b: _decode_column(b, max_length=max_length),
                      rotulo=f"{_V8_MAGIC}{tag}B"),
            tag,
        )
    # A VARIAVEL DE DECISAO: resto vazio -> modo CORE (implicito); senao -> modo DENSO bN.
    if resto == "":
        strs = _decode_column(body, max_length=max_length) if body else []
        return _cast_tipo(strs, tag)
    # MODO DENSO bN (weld #4b): resto = '<modo><n>'. modo = 1 char (largura); n = HEX (owner
    # 2026-07-24: len(hex(n))<=len(dec(n)) p/ todo n>=0, nunca pior, O(1)). Parse posicional: modo
    # sempre 1o char, entao hex nao colide com o namespace do <modo>.
    modo_c, nhex = resto[:1], resto[1:]
    n = None
    if modo_c in _LARGURA_MODO and nhex:
        try:
            n = int(nhex, 16)
        except ValueError:
            n = None
        # CANONICIDADE (evita '0a'/'a' colidirem no mesmo valor — mesma classe do weld #2/LF):
        # a grafia hex precisa ser a MINIMA (sem zero a esquerda, minusculo); re-formata e compara.
        if n is not None and f"{n:x}" != nhex:
            n = None
    if n is None:
        raise ValueError(f"#TCF.8{tag}: header de modo denso invalido: {resto!r} (esperado <modo><n-hex>)")
    return _decode_denso(body, tag, _LARGURA_MODO[modo_c], n)


def _decode_denso(b64: str, tag: str, w: int, n: int) -> list:
    """Modo denso: base64 -> bit-unpack a w bits -> indices -> tipo (dominio implicito).

    Dominio implicito CONGELADO: w=1 (b1) -> false=0/true=1; w=2 (b2 ternario, weld
    2026-07-31, ADR-0037) -> null=0/false=1/true=2, simbolo 3 = RESERVADO (fail-loud).
    FONTE UNICA das tabelas: `tcf/tipos_internos.py` (TABELA_B1/TABELA_B2).

    FAIL-LOUD por integridade (verif. adversarial wf_85fcea32, alinhado a ADR-0032 §6 e ao
    cross-check byte-exato do .8H): base64 ESTRITO + payload de tamanho EXATO. Wire adulterado
    (n != payload, char fora do alfabeto, padding lixo) para alto — nunca corrompe em silencio.
    """
    from tcf.bitpack import unpack_w
    if tag != "b":
        # n/s densos exigiriam dominio EMBUTIDO (nao implicito) — fora do escopo #4b (namespace reservado).
        raise ValueError(f"#TCF.8{tag}: modo denso so' implementado p/ bool; n/s exigem dominio embutido")
    if w not in (1, 2):                            # b1 = bool puro; b2 = ternario. Outra largura = invalido
        raise ValueError(f"#TCF.8b: largura denso invalida w={w} p/ bool (esperado 1 ou 2)")
    # FONTE UNICA (consolidacao 2026-08-07): este ramo fazia as checagens INLINE e serviu de
    # modelo pro `valida_payload_b64`. Deixar duplicado e' o que causou o problema original —
    # o denso evoluiu, o bN e o lazy nao, e a divergencia so' apareceu por auditoria. Agora as
    # tres rotas chamam a mesma funcao; quem melhorar a regra melhora as tres.
    # `padded=True`: o denso emite base64 COM `=` (as outras duas emitem sem).
    from tcf.composicional.dominio_bn import valida_payload_b64
    raw = valida_payload_b64(b64, n, w, "#TCF.8b", padded=True)
    idx = unpack_w(raw, w, n)
    # Dominio implicito CONGELADO — FONTE UNICA: `tcf/tipos_internos.py` (TABELA_B1/B2).
    from tcf.tipos_internos import TABELA_B1, TABELA_B2
    if w == 1:
        return [TABELA_B1[i] for i in idx]
    # b2 TERNARIO: indice fora da tabela (3 = RESERVADO) -> fail-loud (wire adulterado)
    if any(i >= len(TABELA_B2) for i in idx):
        raise ValueError("#TCF.8b: simbolo 3 fora do dominio ternario do denso b2 (wire adulterado)")
    return [TABELA_B2[i] for i in idx]


def _decode_lazy_bool(tcf_text: str, max_length: int | None = None) -> list:
    """Lazy bool `#TCF.8bB<w><n>` (ADR-0039): uniao bool+str(+null) com tipo preservado.

    Cabeca CONGELADA implicita null=0/false=1/true=2 (TABELA_B2 de `tcf/tipos_internos.py`)
    + extras str declarados no arquivo a partir do slot 3 — a mecanica do `decode_bn`
    (ADR-0036) com a cabeca bool implicita. Contrato UNIAO: devolve lista mista
    `[bool | None | str]`. NAO reusa `decode_bn` de proposito: ele mapearia indice->dominio
    declarado escondendo a distincao cabeca/extra — e um pos-mapeamento `"true"->True`
    fundiria o EXTRA `"true"` com o `True` da cabeca (a armadilha de tipos, lab 0322).

    FAIL-LOUD (espelho do `decode_bn` + o check da fiacao 2026-08-01-0322): header hex
    MINIMO canonico, marcador `=` ausente, conteudo apos o bloco de bits, dominio
    REDECLARANDO a cabeca (`0` cru le como None = slot 0 — a cabeca 0/1/2 e' implicita e
    NUNCA se declara), tabela maior que 2^w, indice fora da tabela, payload nao-base64.
    """
    from tcf.bitpack import unpack_w
    from tcf.composicional.dominio_bn import BS, MARCADOR, MAX_W, _le_grafia
    from tcf.tipos_internos import TABELA_B2

    line1, _sep, resto = tcf_text.partition("\n")
    campos = line1[8:]                               # apos '#TCF.8bB'
    if len(campos) < 2 or campos[0] not in "12345678":
        raise ValueError(
            f"#TCF.8bB: cabecalho nao-canonico: largura {campos[:1]!r} fora de 1..{MAX_W}"
        )
    w = int(campos[0])
    nhex = campos[1:]
    if any(c not in "0123456789abcdef" for c in nhex):
        raise ValueError(f"#TCF.8bB: contagem nao-hexadecimal-canonica: {nhex!r}")
    n = int(nhex, 16)
    if f"{n:x}" != nhex:                             # grafia MINIMA: sem zero a esquerda
        raise ValueError(f"#TCF.8bB: contagem nao-canonica: {nhex!r} (canonico: {n:x})")
    linhas = resto.split("\n")
    alvo = next((j for j, ln in enumerate(linhas) if ln.startswith(MARCADOR)), None)
    if alvo is None:
        raise ValueError(f"#TCF.8bB: wire sem o marcador {MARCADOR!r} — corpo nao-canonico")
    if any(ln for ln in linhas[alvo + 1:]):
        raise ValueError("#TCF.8bB: conteudo apos o bloco de bits — corpo nao-canonico")
    b64 = linhas[alvo][1:]
    bloco = "\n".join(ln[1:] if ln.startswith(BS + MARCADOR) else ln
                      for ln in linhas[:alvo])
    # `_decode_column` ja' devolve o `0` cru como None (slot 0) — None aqui = cabeca
    # redeclarada. Dominio de linha VAZIA e' VALIDO: e' o extra "" (string vazia);
    # `_decode_column("\n")` devolve [""] — espelho do bugfix `[:-1]` do dominio_bn.
    decod = _decode_column(bloco + "\n", max_length=max_length)
    if not decod:
        raise ValueError("#TCF.8bB: dominio lazy vazio — corpo nao-canonico")
    if any(s is None for s in decod):
        raise ValueError(
            "#TCF.8bB: dominio redeclara a cabeca congelada (slot 0 = null) — grafia "
            "nao-canonica; a cabeca 0/1/2 e' implicita e NUNCA se declara"
        )
    extras = [_le_grafia(s) for s in decod]
    tabela = list(TABELA_B2) + extras
    if len(tabela) > (1 << w):
        raise ValueError(f"#TCF.8bB: tabela lazy com {len(tabela)} valores nao cabe em {w} bits")
    # FONTE UNICA de validacao de payload (T-BN-B64-VALIDATE, lab 2026-08-06-2104): o
    # `validate=True` sozinho NAO pega extensao com bytes ZERO — `payload + "AAAA"` era
    # aceito CALADO aqui. Faltavam a re-codificacao (grafia canonica) e o tamanho exato,
    # que o `_decode_denso` ja' fazia. As tres sao independentes.
    from tcf.composicional.dominio_bn import valida_payload_b64
    raw = valida_payload_b64(b64, n, w, "#TCF.8bB")
    saida = []
    for i in unpack_w(raw, w, n):
        if i >= len(tabela):
            raise ValueError(
                f"#TCF.8bB: indice {i} fora da tabela lazy de {len(tabela)} valores "
                f"— corpo nao-canonico"
            )
        saida.append(tabela[i])
    return saida
