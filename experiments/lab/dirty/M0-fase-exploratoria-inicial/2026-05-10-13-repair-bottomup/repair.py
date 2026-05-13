"""Re-Pair simplificado: a cada iteracao escolhe a substring de maior
'gain liquido' que aparece em multiplas strings, cria um simbolo e
substitui em todas. Continua ate ganho marginal.

Re-Pair classico (Larsson & Moffat 2000) trabalha com pares de
adjacentes em nivel de byte. Esta versao trabalha com substrings
arbitrarias dentro dos literais — equivalente mas mais grosseira,
adequada para inspecao visual.

Cada string vira list[Token], onde Token = Literal(str) | Ref(int).
Iteracao para quando o melhor candidato tem ganho liquido baixo
(heuristica abaixo).
"""

from dataclasses import dataclass


@dataclass
class Literal:
    text: str

    def __repr__(self) -> str:
        return f'L({self.text!r})'


@dataclass
class Ref:
    sym_id: int

    def __repr__(self) -> str:
        return f'R{self.sym_id}'


Token = Literal | Ref


def _contar_substrings(strings_tok: list[list[Token]],
                       min_len: int) -> dict[str, int]:
    """Conta em quantas strings distintas cada substring aparece
    (dentro dos literais).
    """
    cont: dict[str, int] = {}
    for tokens in strings_tok:
        substrs_da_string: set[str] = set()
        for tok in tokens:
            if isinstance(tok, Literal):
                v = tok.text
                for i in range(len(v)):
                    for j in range(i + min_len, len(v) + 1):
                        substrs_da_string.add(v[i:j])
        for sub in substrs_da_string:
            cont[sub] = cont.get(sub, 0) + 1
    return cont


def _substituir(strings_tok: list[list[Token]], padrao: str,
                sym_id: int) -> list[list[Token]]:
    novas: list[list[Token]] = []
    for tokens in strings_tok:
        novos: list[Token] = []
        for tok in tokens:
            if isinstance(tok, Literal):
                parts = tok.text.split(padrao)
                for k, p in enumerate(parts):
                    if p:
                        novos.append(Literal(p))
                    if k < len(parts) - 1:
                        novos.append(Ref(sym_id))
            else:
                novos.append(tok)
        novas.append(novos)
    return novas


def _ganho_liquido(padrao: str, count: int, ref_chars: int = 3,
                   decl_overhead: int = 7) -> int:
    """Heuristica simples:
      - cada ocorrencia troca 'padrao' por uma ref de ref_chars
      - 1 decl extra custa decl_overhead + len(padrao)
    """
    L = len(padrao)
    return count * (L - ref_chars) - (decl_overhead + L)


def repair(strings_unicas: list[str], min_len: int = 3,
           min_count: int = 2,
           ganho_min: int = 1) -> tuple[dict[int, str], list[list[Token]], str]:
    """Retorna (simbolos_id_to_text, strings_em_tokens, log_textual)."""
    log: list[str] = []
    strings_tok: list[list[Token]] = [[Literal(s)] for s in strings_unicas]
    simbolos: dict[int, str] = {}
    proximo_id = 1
    iter_n = 0

    log.append("Strings iniciais:")
    for i, s in enumerate(strings_unicas):
        log.append(f"  s{i+1}: {s!r}")
    log.append("")

    while True:
        iter_n += 1
        log.append(f"===== Iteracao {iter_n} =====")
        cont = _contar_substrings(strings_tok, min_len)
        cont = {sub: c for sub, c in cont.items() if c >= min_count}

        if not cont:
            log.append("  sem substrings com count >= min_count. STOP.")
            break

        # ordena por gain liquido desc; tie por len desc, count desc, lex
        candidatos = sorted(
            cont.items(),
            key=lambda x: (-_ganho_liquido(x[0], x[1]),
                           -len(x[0]), -x[1], x[0]),
        )
        log.append(f"  top 12 candidatos (por ganho liquido):")
        log.append(f"    {'gain':>5} {'len':>3} {'count':>5}  substring")
        for sub, c in candidatos[:12]:
            log.append(f"    {_ganho_liquido(sub, c):>5} "
                       f"{len(sub):>3} {c:>5}  {sub!r}")

        padrao, count = candidatos[0]
        gain = _ganho_liquido(padrao, count)
        if gain < ganho_min:
            log.append(f"  melhor candidato gain={gain} < min={ganho_min}. STOP.")
            break

        sym_id = proximo_id
        proximo_id += 1
        simbolos[sym_id] = padrao
        log.append(f"  ESCOLHIDO: {padrao!r} (gain={gain}) -> S{sym_id}")
        strings_tok = _substituir(strings_tok, padrao, sym_id)

        log.append("  strings apos substituicao:")
        for i, tokens in enumerate(strings_tok):
            tok_str = " + ".join(repr(t) for t in tokens)
            log.append(f"    s{i+1}: [{tok_str}]")
        log.append("")

    return simbolos, strings_tok, "\n".join(log)


def reconstroi(tokens: list[Token], simbolos: dict[int, str]) -> str:
    parts: list[str] = []
    for tok in tokens:
        if isinstance(tok, Literal):
            parts.append(tok.text)
        else:
            parts.append(simbolos[tok.sym_id])
    return "".join(parts)
