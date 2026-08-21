"""TemplatedCheckedSpec — categoria "Templated + Checked + Unique-Discrete".

Welded canonical 2026-05-24 via ADR-0015.
Origem: experiments/lab/dirty/old/welded/2026-05-24-cpf-templated-checked/07-generalizar-CNPJ/

Categoria abstrata: identificadores unicos com:
1. Layout fixo (template regex)
2. Digito verificador derivavel (check_fn)
3. Sem ordem entre instancias (Unique-Discrete)

Mesma maquina parametrica serve CPF, CNPJ, e potencialmente IBAN/Luhn
(nao welded — registrar SPEC novo quando dataset real existir).

Filosofia opt-in per-value (sub-exp 05):
- compressible -> base-94 encoded (5-7 chars)
- format_padded / check_invalid / format_mismatch / etc. -> literal fallback
- Marker prefix `_` distingue literal vs compressed
- RT byte-canonical preservado SEMPRE

Implementa Protocol NatureSpec (encode_value / decode_value /
classify_value como methods). Encoder/decoder polimorfico, zero
`isinstance` check.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable


# === Alfabeto base-94 safe pra TCF textual ===
# Exclui: \n \r \t (control), space, , ~ * \ # = [ ] < > " ' ` _ (TCF reserved + marker)
_RESERVED = set('\n\r\t ,~*\\#=[]<>"\'`_')
BASE94 = ''.join(chr(c) for c in range(33, 127) if chr(c) not in _RESERVED)
assert len(BASE94) >= 50, f"base alphabet only {len(BASE94)} chars"

MARKER_LITERAL = '_'


@dataclass(frozen=True)
class TemplatedCheckedSpec:
    """Spec parametrico pra encoder generico Templated+Checked+Unique.

    Attributes:
        name: identificador ("cpf" / "cnpj" / etc.)
        regex: padrao re.compile pra validar formato
        body_length: numero digitos no corpo (sem check)
        check_length: numero digitos check
        check_fn: dado lista[int] body, retorna lista[int] checks
        formatter: dado lista[int] (body+check), retorna string formatada
        encoded_length: chars pra encodar len(alfabeto)^body_length em BASE94
        alfabeto: simbolos aceitos no CORPO, na ORDEM que define a base (o indice
            de cada simbolo E' o digito da conversao). Default `'0123456789'` =
            base 10, o comportamento historico. `SPEC_CNPJ_ALFA` usa os 36
            simbolos `0-9A-Z` (IN RFB 2.229/2024). DOIS mapeamentos convivem e
            NAO se confundem (weld H-15-01):
              - alfabeto -> indice 0..N-1 = base da GRAVACAO;
              - `_valor()` (ASCII-48) = valor que o `check_fn` consome, a LEI.
            Os digitos precisam estar no alfabeto quando `check_length > 0` — os
            digitos verificadores sao sempre decimais.
        wire_id: id CURTO que viaja no header (`:id`). Plano do DADO — o `name`
            e' o plano do CODIGO (API/telemetria/erros) e NUNCA viaja (ADR-0041).
            Vazio -> assume o `name`. A grafia (`^[a-z][a-z0-9]{0,7}$`) NAO e'
            validada aqui de proposito: a valvula de leitura de wire historico
            (`dataclasses.replace(SPEC, wire_id=<id antigo>)`) precisa construir
            specs fora da regra. Fail-loud fica no REGISTRO e na EMISSAO.
    """
    name: str
    regex: re.Pattern
    body_length: int
    check_length: int
    check_fn: Callable[[list[int]], list[int]]
    formatter: Callable[[list[int]], str]
    encoded_length: int
    wire_id: str = ""
    alfabeto: str = "0123456789"

    def __post_init__(self):
        if not self.wire_id:
            object.__setattr__(self, "wire_id", self.name)
        # CONTRATO do alfabeto (weld H-15-01). Fail-loud aqui e' barato e evita a
        # classe de bug que so' aparece no valor que estoura a capacidade.
        if len(set(self.alfabeto)) != len(self.alfabeto):
            raise ValueError(f"alfabeto com simbolo repetido em {self.name!r}")
        if self.check_length and not set("0123456789") <= set(self.alfabeto):
            raise ValueError(
                f"alfabeto de {self.name!r} nao contem os digitos decimais — os "
                f"digitos verificadores sao sempre decimais e precisam sobreviver "
                f"ao filtro de simbolos"
            )
        if len(self.alfabeto) ** self.body_length > len(BASE94) ** self.encoded_length:
            raise ValueError(
                f"encoded_length={self.encoded_length} insuficiente em {self.name!r}: "
                f"{len(self.alfabeto)}^{self.body_length} nao cabe em "
                f"{len(BASE94)}^{self.encoded_length}"
            )

    # === Mapeamentos: sao DOIS, e nao se confundem ===

    def _valor(self, c: str) -> int:
        """Char -> valor que o `check_fn` consome. E' a LEI, nao a gravacao.

        `ord(c) - 48` e' UNIVERSAL: para digito devolve o proprio digito (ASCII
        '0' = 48) e para letra devolve a regra da IN RFB 2.229/2024 ('A' = 17).
        E' exatamente por isso que o CNPJ numerico gera o MESMO DV sob a regra
        nova — a retrocompatibilidade e' estrutural, nao coincidencia.
        """
        return ord(c) - 48

    def _simbolos(self, v: str) -> str:
        """Os chars de `v` que pertencem ao corpo+check (descarta a mascara)."""
        return "".join(c for c in v if c in self.alfabeto)

    # === Protocol NatureSpec methods ===

    def classify_value(self, v: str) -> str:
        """Classifica valor: 'compressible' ou razao Kim 2003 taxonomy."""
        if not v:
            return 'empty_value'
        expected_total = self.body_length + self.check_length
        if len(v) == expected_total and all(c in self.alfabeto for c in v):
            return 'format_unmasked'
        if not self.regex.match(v):
            return 'format_mismatch' if len(v) > 5 else 'length_wrong'
        simbolos = self._simbolos(v)
        if len(simbolos) != expected_total:
            return 'length_wrong'
        body = [self._valor(c) for c in simbolos[:self.body_length]]
        actual_check = [self._valor(c) for c in simbolos[self.body_length:]]
        expected_check = self.check_fn(body)
        if expected_check != actual_check:
            return 'check_invalid'
        return 'compressible'

    def encode_value(self, v: str) -> tuple[str, str]:
        """Encode generico. Retorna (payload, status)."""
        status = self.classify_value(v)
        if status != 'compressible':
            return MARKER_LITERAL + v, status
        simbolos = self._simbolos(v)
        # o corpo em base-len(alfabeto). Com o alfabeto default isto E' `int(str)`
        # em base 10 — mesma conta, mesmo inteiro, mesmos bytes.
        base = len(self.alfabeto)
        n = 0
        for c in simbolos[:self.body_length]:
            n = n * base + self.alfabeto.index(c)
        chars = []
        for _ in range(self.encoded_length):
            chars.append(BASE94[n % len(BASE94)])
            n //= len(BASE94)
        return ''.join(reversed(chars)), status

    def decode_value(self, payload: str) -> str:
        """Decode generico — reverte encode_value."""
        if payload.startswith(MARKER_LITERAL):
            return payload[1:]
        if len(payload) == self.encoded_length and all(c in BASE94 for c in payload):
            n = 0
            for c in payload:
                n = n * len(BASE94) + BASE94.index(c)
            # Expansao SEM truncar + pad a esquerda: com o alfabeto default isto e'
            # EXATAMENTE `str(n).zfill(body_length)`, inclusive quando o payload
            # adulterado estoura a capacidade do corpo (n >= base^body_length) e a
            # string sai mais longa. Trocar por `n % base**body` mudaria o
            # comportamento nesse caso de borda — o que aqui nao se faz calado.
            base = len(self.alfabeto)
            idx = []
            while n:
                idx.append(n % base)
                n //= base
            body_str = ''.join(
                self.alfabeto[i] for i in reversed(idx)
            ).rjust(self.body_length, self.alfabeto[0])
            valores = [self._valor(c) for c in body_str]
            valores.extend(self.check_fn(valores))
            return self.formatter(valores)
        return payload


# === Standalone functions (backward compat wrappers — delegam pra methods) ===

#: O SLOT NULO E' DO CORE, NAO DO SPEC (fix 2026-08-08, weld T-DATA-LAZY-ISO).
#:
#: `None` e' valor legitimo de coluna single-col flat (`_lista_flat` aceita `str` OU `None`) e
#: o core ja' o materializa no slot 0. Mas as quatro natures classificavam `None` como
#: `empty_value` e caiam em `MARKER_LITERAL + v` — concatenar str com None. Resultado medido
#: ANTES deste fix, nas QUATRO (cpf, cnpj, ip, data-iso):
#:
#:     encode(['000.000.000-00', None, ...], nature=SPEC_CPF)
#:     TypeError: can only concatenate str (not "NoneType") to str
#:
#: `TypeError` cru vazando pela API publica, com dado perfeitamente normal — e o MESMO dado
#: sem `nature=` encoda sem reclamar. E' alcancavel por `encode->decode`, entao e' da classe
#: que a escala de verificacao chama de E1/E2, a que corrompe de verdade.
#:
#: O conserto mora AQUI, no wrapper de modulo, por dois motivos: e' o ponto unico por onde o
#: encoder aplica qualquer nature (`encoder.py`: `pairs = [encode_value(nature, v) ...]`), e
#: e' tambem a API publica (`from tcf.natures import encode_value`). Consertar nos 4 specs
#: seria a divergencia-entre-irmaos que ja' custou caro no bN.
_STATUS_NULO = "null_slot"


def classify_value(spec, v):
    """Compat wrapper — delega a spec.classify_value(v). `None` = slot do core."""
    if v is None:
        return _STATUS_NULO
    return spec.classify_value(v)


def encode_value(spec, v):
    """Compat wrapper — delega a spec.encode_value(v).

    `None` PASSA DIRETO, sem marcador: quem o materializa e' o core, no slot 0. Marcar seria
    inventar uma segunda grafia pro mesmo nada — e a inversa teria de desfazer exatamente
    isso, que e' a assimetria de escape que este projeto ja' viu cinco vezes.
    """
    if v is None:
        return None, _STATUS_NULO
    return spec.encode_value(v)


def decode_value(spec, payload):
    """Compat wrapper — delega a spec.decode_value(payload). `None` volta `None`."""
    if payload is None:
        return None
    return spec.decode_value(payload)


# ===========================================================================
# SPEC_CPF (Brazilian individual taxpayer ID)
# ===========================================================================

_CPF_RE = re.compile(r'^(\d{3})\.(\d{3})\.(\d{3})-(\d{2})$')


def _cpf_check_fn(body: list[int]) -> list[int]:
    """Mod-11 CPF: 2 check digits."""
    s1 = sum(d * w for d, w in zip(body, range(10, 1, -1)))
    d1 = (s1 * 10) % 11
    if d1 == 10:
        d1 = 0
    s2 = sum(d * w for d, w in zip(body + [d1], range(11, 1, -1)))
    d2 = (s2 * 10) % 11
    if d2 == 10:
        d2 = 0
    return [d1, d2]


def _cpf_formatter(digits: list[int]) -> str:
    s = ''.join(str(d) for d in digits)
    return f"{s[:3]}.{s[3:6]}.{s[6:9]}-{s[9:]}"


SPEC_CPF = TemplatedCheckedSpec(
    name="cpf",
    regex=_CPF_RE,
    body_length=9,
    check_length=2,
    check_fn=_cpf_check_fn,
    formatter=_cpf_formatter,
    encoded_length=5,  # 80^5 = 3.3*10^9 > 10^9 ✓
)


# ===========================================================================
# SPEC_CNPJ (Brazilian company taxpayer ID)
# ===========================================================================

_CNPJ_RE = re.compile(r'^(\d{2})\.(\d{3})\.(\d{3})/(\d{4})-(\d{2})$')

_W1_CNPJ = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
_W2_CNPJ = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]


def _cnpj_check_fn(body: list[int]) -> list[int]:
    """Mod-11 CNPJ: 2 check digits (pesos diferentes de CPF)."""
    s1 = sum(d * w for d, w in zip(body, _W1_CNPJ))
    rem1 = s1 % 11
    d1 = 0 if rem1 < 2 else 11 - rem1
    s2 = sum(d * w for d, w in zip(body + [d1], _W2_CNPJ))
    rem2 = s2 % 11
    d2 = 0 if rem2 < 2 else 11 - rem2
    return [d1, d2]


def _cnpj_formatter(digits: list[int]) -> str:
    s = ''.join(str(d) for d in digits)
    return f"{s[:2]}.{s[2:5]}.{s[5:8]}/{s[8:12]}-{s[12:]}"


SPEC_CNPJ = TemplatedCheckedSpec(
    name="cnpj",
    regex=_CNPJ_RE,
    body_length=12,
    check_length=2,
    check_fn=_cnpj_check_fn,
    formatter=_cnpj_formatter,
    encoded_length=7,  # 80^7 = 2.1*10^13 > 10^12 ✓
)


# ===========================================================================
# SPEC_CNPJ_ALFA (CNPJ alfanumerico — IN RFB no 2.229/2024, vigente jul/2026)
# ===========================================================================
#
# As 12 primeiras posicoes passam a aceitar `[0-9A-Z]`; os 2 DV seguem DECIMAIS.
# O DV e' o MESMO mod-11, com OS MESMOS PESOS — muda so' a conversao de char pra
# valor, que a IN define como `ASCII(c) - 48` e que `_valor()` ja' implementa.
# Verificado contra o exemplo publicado `12.ABC.345/01DE-35` (DV 35).
#
# POR QUE DOIS SPECS, e nao um so' alfanumerico (medido, lab 2026-08-21-0030):
#   - `cnpj`  corpo em base 10 -> 7 chars
#   - `cnpja` corpo em base 36 -> 10 chars   (36^12 = 4,74e18 <= 80^10 = 1,07e19)
# Usar `cnpja` numa coluna 100% numerica custa +38,1%. Como os CNPJ numericos
# CONTINUAM validos e sendo emitidos (a IN nao os altera), taxar o legado pra
# acomodar o novo seria a troca errada. `SPEC_CNPJ` fica BYTE-INTOCADO.
#
# POR QUE base 36 e nao 43 (ASCII-48 como base): o mapeamento legal tem um GAP
# (10..16 = `:;<=>?@`, que nao sao simbolos validos). Usa-lo como base gastaria
# 43^12 = 4,00e19 > 80^10 -> 11 chars em vez de 10. A LEI governa o DV; a
# GRAVACAO usa o alfabeto denso. Sao dois mapeamentos, e ficam separados.

_CNPJ_ALFA_RE = re.compile(
    r'^([0-9A-Z]{2})\.([0-9A-Z]{3})\.([0-9A-Z]{3})/([0-9A-Z]{4})-(\d{2})$'
)

#: Ordem = a base. Digitos primeiro, de modo que um corpo 100% numerico tenha os
#: MESMOS indices que teria em base 10 (o valor do inteiro muda, a leitura nao).
ALFABETO_CNPJ_ALFA = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _cnpj_alfa_formatter(valores: list[int]) -> str:
    """valores (ASCII-48 no corpo, decimais no check) -> string mascarada.

    A inversa de `_valor` e' `chr(v + 48)`: 0->'0' ... 9->'9', 17->'A' ... 42->'Z'.
    Os 2 ultimos sao digitos verificadores e saem como decimal.
    """
    s = ''.join(chr(v + 48) for v in valores[:12]) + \
        ''.join(str(d) for d in valores[12:])
    return f"{s[:2]}.{s[2:5]}.{s[5:8]}/{s[8:12]}-{s[12:]}"


SPEC_CNPJ_ALFA = TemplatedCheckedSpec(
    name="cnpj-alfa",
    regex=_CNPJ_ALFA_RE,
    body_length=12,
    check_length=2,
    check_fn=_cnpj_check_fn,          # OS MESMOS pesos do numerico. E' a mesma lei.
    formatter=_cnpj_alfa_formatter,
    encoded_length=10,                # 36^12 = 4.7*10^18 < 80^10 = 1.1*10^19 ✓
    wire_id="cnpja",                  # ADR-0041: id curto, plano do DADO
    alfabeto=ALFABETO_CNPJ_ALFA,
)


def cnpj_spec_para(vals) -> TemplatedCheckedSpec:
    """Escolhe entre `SPEC_CNPJ` e `SPEC_CNPJ_ALFA` para uma coluna (weld H-15-02).

    NAO e' "tem letra -> alfa". Essa regra foi MEDIDA e esta' ERRADA: numa coluna
    real de 2.000 CNPJ ela erra em 8 dos 12 pontos da varredura, porque o spec
    numerico (7 chars) segue ganhando mesmo pagando literal pelos poucos
    alfanumericos, ate' ~1/4 da coluna. A virada tem forma fechada — igualando
    `(n-k)*E1 + k*(1+L)` a `n*E2` da' `k/n = (E2-E1)/(1+L-E1)` = 3/12 = 1/4 — e
    foi confirmada em k=500 de n=2.000.

    Aqui a escolha e' por SOMA DE PAYLOAD: classifica cada valor sob os dois
    specs e soma o que cada um emitiria (compressivel -> `encoded_length`; senao
    literal -> `1 + len(v)`). UMA passada, sem encodar a coluna duas vezes.

    Empate escolhe `SPEC_CNPJ`: ele e' o byte-compat com todo wire `:cnpj` ja'
    emitido, e desempatar pro novo re-pinaria baseline sem ganho.

    RESIDUO MEDIDO (nao e' exato, e o quanto nao e' esta' aqui). Contra a verdade
    (encodar com os dois e comparar), em 3 sementes x 17 fracoes x n=2.000 de CNPJ
    real: **41/51 corretos**. Os 10 erros sao SISTEMATICOS, nao ruido — todos na
    faixa **22-25% de alfanumericos** e todos na mesma direcao (escolhe `cnpj`
    quando `cnpja` ja' ganhou), porque a soma de payload nao ve' o que o core faz
    a jusante com literais no meio de payloads densos. Custo do pior erro medido:
    **3,15%**; fora da faixa, 0. Quem precisar de exatidao paga dois encodes:

        cand = [encode(col, nature=s) for s in (SPEC_CNPJ, SPEC_CNPJ_ALFA)]
        texto = min(cand, key=lambda t: len(t.encode()))

    O chamador continua no controle — `encode(col, nature=<spec>)` NUNCA e'
    sobrescrito calado. Uso normal:

        from tcf.natures import cnpj_spec_para
        texto = encode(coluna, nature=cnpj_spec_para(coluna))
    """
    custo_num = custo_alfa = 0
    for v in vals:
        if v is None:                              # slot do core, nao do spec
            continue
        s = str(v)
        literal = 1 + len(s)
        custo_num += (SPEC_CNPJ.encoded_length
                      if SPEC_CNPJ.classify_value(s) == 'compressible' else literal)
        custo_alfa += (SPEC_CNPJ_ALFA.encoded_length
                       if SPEC_CNPJ_ALFA.classify_value(s) == 'compressible' else literal)
    return SPEC_CNPJ if custo_num <= custo_alfa else SPEC_CNPJ_ALFA
