"""tcf.natures — pre-tx por natureza (CAMADA 0 do funil).

Welded canonical 2026-05-24 via ADR-0015 (T-CODE-NATURES-WELD).

Cobre categoria "Templated + Checked + Unique-Discrete":
- SPEC_CPF (NNN.NNN.NNN-DD, mod-11)
- SPEC_CNPJ — **UM SO'**, alfanumerico por padrao (AA.AAA.AAA/AAAA-DD, corpo
  `[0-9A-Z]`, DV decimal; IN RFB no 2.229/2024, vigente desde jul/2026; ADR-0044).
  Nao ha' spec numerico separado: o numerico e' um CASO do alfanumerico — corpo
  100% decimal grava em 7 chars (payload BYTE-IDENTICO ao wire `:cnpj` historico),
  corpo com letra em 10; o decode discrimina pelo COMPRIMENTO. O caso compacto e'
  LOAD-BEARING, nao otimizacao: sem ele um `:cnpj` alfanumerico nao leria o wire
  de 7 chars ja' emitido. O DV e' o MESMO mod-11 com os MESMOS pesos — muda so' a
  conversao char->valor (`ASCII - 48`), e por isso o numerico gera DV identico nas
  duas regras.

Cobre categoria "TCU-Delta" (weld 2026-08-08):
- SPEC_DATA_ISO (YYYY-MM-DD -> ordinal decimal; alvo = o `*N+M|` do seq-RLE)

Outras categorias (TCU-NoCheckVarLength, TCU-Delta, Lossy, Composite)
nao welded — registradas em
`experiments/lab/dirty/notas/naturezas-templated-2026-05-24.md`.

Filosofia:
- Opt-in per-value: cada valor decide se vale comprimir; fallback literal
- TCF nao valida semantica (nao checa "este CPF existe")
- Decoder precisa do mesmo spec usado no encode (out-of-band). O "header carry
  spec id" (self-describing) foi desenhado como H-NAT-MARK-01 e PARADO em (A) —
  ADR-0027 `proposed` (nao implementar agora; rota zero-core via registry gadget)
- RT byte-canonical preservado em todos casos

API publica:

    from tcf.natures import SPEC_CPF, SPEC_CNPJ, encode_value, decode_value

    # Single value
    encoded, status = encode_value(SPEC_CPF, "123.456.789-09")
    original = decode_value(SPEC_CPF, encoded)

    # Em coluna (via tcf.encode com nature param). O header e' SELF-DESCRIBING
    # (#TCF.8 :cpf, ADR-0027): o decode resolve sozinho pelo registry — passar
    # nature= no decode e' redundante (header vence; sem dupla aplicacao).
    from tcf import encode, decode
    text = encode(cpfs_list, schema=SPEC_CPF)
    cpfs_back = decode(text)

Identificacao em DOIS planos (ADR-0041): `spec.name` legivel e' o plano do
CODIGO (API/telemetria/erros — nunca viaja); `spec.wire_id` curto e' o plano do
DADO (o `:id` do header; `dt` p/ data-iso, demais = name). Grafia
`^[a-z][a-z0-9]{0,7}$`, fail-loud no registro e na emissao.
"""

from tcf.natures.templated_checked import (
    TemplatedCheckedSpec,
    SPEC_CPF,
    SPEC_CNPJ,
    ALFABETO_CNPJ,
    BASE94,
    MARKER_LITERAL,
    encode_value,
    decode_value,
    classify_value,
)
from tcf.natures.templated_padded import (
    TemplatedPaddedSpec,
    SPEC_IP,
)

# --- Self-describing nature (ADR-0027, #TCF.8): resolucao CORE-ONLY ---
# Vocabulario FECHADO, em DOIS planos (ADR-0041): `name` legivel e' o plano do
# CODIGO (API/telemetria/erros — NUNCA viaja); `wire_id` curto e' o plano do
# DADO (o `:id` do header). O decode resolve pelo dict FIXO keyed por wire_id —
# ZERO eval, zero codigo vindo do header.
from tcf.natures.data_iso import DataIsoSpec, SPEC_DATA_ISO  # noqa: E402
from tcf.natures.int_pad import IntPadSpec, int_pad_para  # noqa: E402

#: Instancia do registry para `ipad` (weld EXP-018). A `largura` NAO participa do decode —
#: `decode_value` faz `str(int(payload))` e a largura e' o comprimento das linhas do corpo,
#: deduzivel. Ela so' governa o ENCODE, e quem encoda usa `int_pad_para(vals)`, que a
#: dimensiona pela coluna. Esta instancia existe para o `:ipad` do header RESOLVER.
SPEC_INT_PAD = IntPadSpec(largura=38)

import re as _re  # noqa: E402

#: ADR-0041 decisao 2 (owner 2026-08-13): minuscula inicial, alfanumerico, 1-8.
#: O requisito DURO e' so' excluir `,`/`:`/controle (corrompem o meta); o resto
#: e' convencao — previsibilidade, familia por prefixo (`dt*`, `x*` terceiros),
#: imunidade a separador futuro. O ganho de bytes vem do LIMITE, nao do charset.
_WIRE_ID_RE = _re.compile(r"[a-z][a-z0-9]{0,7}")


def _valida_wire_id(spec, *, where: str = "nature=") -> None:
    """Fail-loud da grafia do wire_id (ADR-0041). Chamado no REGISTRO (abaixo) e
    na EMISSAO (porta do `tcf.encode`) — nunca no decode: a valvula de leitura de
    wire historico (`dataclasses.replace(SPEC, wire_id=<id antigo>)`) depende de
    construir spec fora da regra."""
    wid = getattr(spec, "wire_id", None)
    if not isinstance(wid, str) or not _WIRE_ID_RE.fullmatch(wid):
        nome = getattr(spec, "name", repr(spec))
        # Spec escrito ANTES do ADR-0041 nao tem o campo — a mensagem tem de dizer
        # o que fazer, nao so' que esta' errado (a grafia nem e' o problema dele).
        falta = (
            f" — spec sem o campo `wire_id` (escrito antes do ADR-0041?): "
            f"declare o id curto que vai viajar no header, ex: wire_id={nome[:8]!r}"
            if not hasattr(spec, "wire_id")
            else ""
        )
        raise ValueError(
            f"wire_id invalido em {where}: {wid!r} (spec {nome!r}) — regra "
            f"ADR-0041: ^[a-z][a-z0-9]{{0,7}}$ (minuscula inicial, alfanumerico, "
            f"1-8 chars){falta}"
        )


def _valida_emissao(spec, *, where: str = "nature=") -> None:
    """Porta de EMISSAO (chamada em `tcf.encode`): grafia + anti-MASCARADA.

    A mascarada e' consequencia nova dos dois planos: `replace(SPEC_CPF,
    name="custom-cpf")` HERDA `wire_id="cpf"` — emitiria `:cpf`, o decode
    resolveria o spec CORE, e uma transformacao derivada divergente corromperia
    CALADO (pre-ADR-0041 o id era o name, entao esse buraco nao existia).

    O check e' por NAME, de proposito: wire_id do registry exige name IGUAL ao
    do dono. Mesmo name = a fronteira de confianca PRE-weld (um spec chamado
    'cpf' ja' resolvia pro core no decode, registry-first — ex.: clone compilado
    de .dsl pelo gadget, que nao passa em igualdade de dataclass porque regex/
    callables comparam por identidade). Este weld fecha so' o buraco NOVO
    (identidade declarada divergente + wire_id herdado), sem estreitar nem
    alargar a fronteira antiga."""
    _valida_wire_id(spec, where=where)
    dono = _WIRE_REGISTRY.get(spec.wire_id)
    if dono is not None and getattr(spec, "name", None) != dono.name:
        raise ValueError(
            f"wire_id {spec.wire_id!r} em {where} pertence ao spec core "
            f"{dono.name!r} e o spec fornecido se declara "
            f"{getattr(spec, 'name', spec)!r} — mascarada corromperia o decode "
            f"calado (ADR-0041); derive com wire_id proprio (ex: prefixo 'x' "
            f"p/ terceiros)"
        )


SPEC_REGISTRY: dict = {}   # name -> spec     (plano do CODIGO: lookup da API)
_WIRE_REGISTRY: dict = {}  # wire_id -> spec  (plano do DADO: resolucao do header)


def _register(spec) -> None:
    """Registro fail-loud (ADR-0041): recusa grafia invalida E colisao, nos DOIS
    planos, ANTES de inserir em qualquer um (falha nao deixa estado parcial)."""
    _valida_wire_id(spec, where="registro")
    if spec.name in SPEC_REGISTRY:
        raise ValueError(f"nature name {spec.name!r} ja' registrado")
    if spec.wire_id in _WIRE_REGISTRY:
        raise ValueError(
            f"wire_id {spec.wire_id!r} ja' registrado "
            f"(por {_WIRE_REGISTRY[spec.wire_id].name!r}) — colisao com {spec.name!r}"
        )
    SPEC_REGISTRY[spec.name] = spec
    _WIRE_REGISTRY[spec.wire_id] = spec


for _spec in (SPEC_CPF, SPEC_CNPJ, SPEC_IP, SPEC_DATA_ISO, SPEC_INT_PAD):
    _register(_spec)
del _spec


def _resolve_nature_id(nature_id: str):
    """Resolve a STRING de um nature-id (o `:id` do header #TCF.8) -> spec, ou
    None se desconhecido. Compara contra o WIRE_ID vigente, ESTRITO (ADR-0041
    decisao 3): id historico (`data-iso`) NAO resolve — wire antigo le-se
    out-of-band, coerente com ADR-0024 (o passado se le pelo git). A funcao
    permanece total; o decoder publico converte `None` em ValueError fail-loud.
    NAO reusar `scripts/natures_compiler/registry.py:get()` aqui (esse faz
    raise, e e' keyed por NAME — plano do codigo, nao do dado)."""
    return _WIRE_REGISTRY.get(nature_id)


# ---------------------------------------------------------------------------
# `schema=` — o parametro UNICO de spec da API publica (decisao owner 2026-08-22)
# ---------------------------------------------------------------------------

def _resolve_schema_valor(v, *, where: str):
    """Um VALOR do schema -> spec. String resolve por NAME no SPEC_REGISTRY (o
    plano da API, ADR-0041 — nunca o wire_id: dois nomes pra mesma coisa e'
    convite a deriva). Objeto spec (duck: tem `wire_id`) passa direto — e' a
    porta dos specs de terceiros. `None` = coluna sem spec (contrato
    pre-existente do `{col: None}`)."""
    if v is None:
        return None
    if isinstance(v, str):
        spec = SPEC_REGISTRY.get(v)
        if spec is None:
            raise ValueError(
                f"{where}: spec {v!r} desconhecido — registry core: "
                f"{sorted(SPEC_REGISTRY)}. Spec de terceiro entra como OBJETO, "
                f"nao como string."
            )
        return spec
    if hasattr(v, "wire_id"):
        return v
    if hasattr(v, "encode_value") or hasattr(v, "name"):
        # PARECE spec mas nao tem `wire_id` (escrito antes do ADR-0041?) — a
        # recusa ensinante e' a de sempre, fonte unica:
        _valida_wire_id(v, where=where)
    raise TypeError(
        f"{where}: valor de spec deve ser str (name do registry), objeto spec "
        f"ou None; got {type(v).__name__}"
    )


def resolve_schema(schema, *, where: str):
    """Normaliza o `schema=` publico -> ('single', spec) | ('per_col', dict).

    Formas aceitas (fail-loud em tudo que nao for uma delas):
      - str            -> UM spec pelo name do registry (single-col)
      - objeto spec    -> UM spec direto (single-col; terceiros)
      - dict           -> {coluna: spec}; chave str = NOME (inclusive '' e '0',
                          ADR-0046), chave int = POSICAO (resolvida na porta,
                          onde a ordem das colunas existe); valor = str/spec/None
    A resolucao POSICAO->NOME nao acontece aqui: ela precisa do dado (encode)
    ou do meta (decode), entao vive em cada porta."""
    if isinstance(schema, str) or hasattr(schema, "wire_id") or (
        hasattr(schema, "encode_value") or hasattr(schema, "name")
    ):
        # a 3a clausula: objeto que PARECE spec sem `wire_id` — deixa o
        # _resolve_schema_valor recusar ENSINANDO (ADR-0041), nao com o
        # TypeError generico de forma.
        return "single", _resolve_schema_valor(schema, where=where)
    if isinstance(schema, dict):
        out = {}
        for k, v in schema.items():
            if isinstance(k, bool) or not isinstance(k, (int, str)):
                raise TypeError(
                    f"{where}: chave de coluna deve ser str (nome) ou int "
                    f"(posicao); got {type(k).__name__} ({k!r})"
                )
            out[k] = _resolve_schema_valor(v, where=where)
        return "per_col", out
    raise TypeError(
        f"{where}: schema deve ser str (name do registry), objeto spec ou "
        f"dict {{coluna: spec}}; got {type(schema).__name__}"
    )


__all__ = [
    # Templated + Checked (CPF, CNPJ)
    "TemplatedCheckedSpec",
    "SPEC_CPF",
    "SPEC_CNPJ",
    "ALFABETO_CNPJ",
    # Templated + Padded (IP)
    "TemplatedPaddedSpec",
    "SPEC_IP",
    # Data ISO (T-DATA-LAZY-ISO)
    "DataIsoSpec",
    "SPEC_DATA_ISO",
    # Inteiro zero-padded (EXP-018)
    "IntPadSpec",
    "SPEC_INT_PAD",
    "int_pad_para",
    # Compartilhados
    "BASE94",
    "MARKER_LITERAL",
    "encode_value",
    "decode_value",
    "classify_value",
    # `schema=` (parametro unico de spec da API)
    "SPEC_REGISTRY",
    "resolve_schema",
]
