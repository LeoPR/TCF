"""O código do weld, escrito como ele entraria em `src/tcf/composicional/hcc_seqrle.py`.

**NÃO ESTÁ SOLDADO.** `src/tcf` exige aprovação explícita do owner. Este arquivo existe
para o owner revisar o diff exato antes de dar (ou não) o OK — e para que, com o OK, o
weld seja transcrição, não redação.

Decisões de colocação (ADR-0040, medidas):

  1. `expande_periodico` entra em `expand_seq_marker` — NÃO num passe separado de decode.
     Motivo medido: o laço de `HCCSeqRLE.decode` pré-checa o teto ANTES de materializar
     (`_contador_declarado`, que já lê `*N~…|` certo). Bomba `*2000000~1,2|` com
     `max_length=10`: passe separado rejeita em 2,473 s (depois de materializar 2 M
     strings); dentro do `expand_seq_marker`, em 0,0000 s.

  2. Duas guardas obrigatórias no detector/FLOOR (sem elas o mecanismo REGRIDE):
     padrão uniforme rejeitado, e FLOOR contra o corpo JÁ COMPACTADO.

  3. Empate preserva a preferência de hoje (compactado > cru), porque `min()` devolve o
     PRIMEIRO mínimo e isso é load-bearing pra byte-canonicidade.

Os quatro pontos de integração estão marcados com `# <<< WELD` abaixo.
"""
from __future__ import annotations

# ────────────────────────────── 1. detector (novo) ──────────────────────────────
# Vizinho de `detect_seq_runs`. Não substitui: o uniforme continua sendo dele.

MAX_PERIODO = 24   # cobre mensal (12) e quinzenal-ano (24). Sem caso medido acima disso.


def deltas_da_coluna(body_lines, _compare):
    """O array que os DOIS detectores consomem.

    <<< WELD: hoje `detect_seq_runs` chama `compare_for_seq` por conta própria. O weld
    deve computar este array UMA vez e passar aos dois — medido: recomputá-lo custa
    6,8 ms num corpo de 1200 linhas, ~27% do encode inteiro, jogado fora.
    """
    out = []
    for a, b in zip(body_lines, body_lines[1:]):
        v = _compare(a, b)
        out.append(v[0] if v is not None and len(v) == 1 else None)
    return out


def detect_periodic_runs(body_lines, deltas, _marcador_len):
    """Runs `(start, count, padrao)` onde o delta entre linhas CICLA com período p >= 2.

    O(n · MAX_PERIODO). Escopo do 1º weld: pares de UM run de escape-digit (multi-run é
    do ADR-0016).

    A forma INGÊNUA desta função é O(n²) e foi medida: n=2400 levava **13,8 s** contra
    47 ms do encode. Duas armadilhas, ambas por índice em vez de por cadeia:
      1. reachar o fim da cadeia a cada `i`;
      2. fatiar `deltas[i:j]` a cada `i`.
    E uma terceira, achada só instrumentando POR DENTRO da camada (a medição isolada
    mentia porque reconstruía o corpo sem o hint de cadência):
      3. o guard de padrão uniforme rodava por (posição × período) — 1199 posições × 23
         períodos = ~27 600 fatias e `set()` para concluir "é uniforme, pule".
    O pré-cálculo `mudanca[]` abaixo mata a (3) em O(n).
    """
    n, m = len(body_lines), len(deltas)

    # mudanca[k] = distancia de k ate' o proximo delta DIFERENTE. Qualquer periodo
    # p <= mudanca[k] tem padrao uniforme por construcao -> nem precisa ser testado.
    mudanca = [0] * m
    for k in range(m - 1, -1, -1):
        mudanca[k] = 1 if (k == m - 1 or deltas[k] != deltas[k + 1]) else mudanca[k + 1] + 1

    runs, i = [], 0
    while i < n - 1:
        if deltas[i] is None:
            i += 1
            continue
        fim = i                                   # fronteira da cadeia: UMA vez
        while fim < n - 1 and deltas[fim] is not None:
            fim += 1
        pos = i
        while pos < fim:
            melhor = None                         # (economia, count, padrao)
            for p in range(max(2, mudanca[pos] + 1), min(MAX_PERIODO, fim - pos) + 1):
                pad = deltas[pos:pos + p]         # fatia LIMITADA por MAX_PERIODO
                # GUARDA 1 — padrao uniforme ([1,1]) e' `*N+d|` disfarcado, e mais caro.
                # Sem isto o diario regredia 32 -> 34 B (medido). Com o `mudanca[]`
                # acima, esta linha quase nunca dispara — mas fica, porque e' o
                # invariante, nao a otimizacao.
                if len(set(pad)) == 1:
                    continue
                L = p
                while pos + L < fim and deltas[pos + L] == pad[L % p]:
                    L += 1
                # DOIS ciclos completos: com um so', o marcador vira LISTA literal de
                # deltas — que e' o transform de coluna em gramatica, e perde dele
                # (1825 B contra 644 B no espalhado). ADR-0040 §alternativa rejeitada.
                if L < 2 * p:
                    continue
                count = L + 1
                custo = _marcador_len(count, pad, body_lines[pos]) + 1
                economia = sum(len(body_lines[pos + k]) + 1 for k in range(count)) - custo
                if economia > 0 and (melhor is None or economia > melhor[0]):
                    melhor = (economia, count, pad)
            if melhor is None:
                pos += 1
            else:
                runs.append((pos, melhor[1], melhor[2]))
                pos += melhor[1]
        i = max(fim, i + 1)
    return runs


# ─────────────────────── 2. emissão do marcador (novo) ───────────────────────

def marcador_periodico(count, padrao, template):
    """`*N~d1,…,dp|template`. O caractere `~` é reversível (ADR-0040): marcador é
    abstrato por dentro, o char é só a saída."""
    return f"*{count}~{','.join(str(d) for d in padrao)}|{template}"


# ─────────── 3. <<< WELD em `compact_body`: periódico primeiro, resto igual ───────────
#
# `compact_body` de hoje faz `runs = detect_seq_runs(...)` e monta a saída. A versão nova
# roda o periódico ANTES (é o mais específico) e delega os trechos não cobertos ao
# `compact_body` de hoje, sem duplicar o caminho do uniforme.

def compact_body_com_periodico(body_lines, deltas, _compact_body_hoje):
    runs = detect_periodic_runs(body_lines, deltas, _len_marcador)
    if not runs:
        # SAIDA CURTA: sem run periodico a decisao e' EXATAMENTE a de hoje. Nao
        # recompactar e nao adicionar candidato ao min() — o caminho comum tem de
        # custar o minimo possivel.
        return _compact_body_hoje(body_lines)          # caminho de hoje, byte a byte

    saida, pendente, i, ri = [], [], 0, 0

    def _drena():
        if pendente:
            saida.extend(_compact_body_hoje(pendente)[0])
            pendente.clear()

    while i < len(body_lines):
        if ri < len(runs) and runs[ri][0] == i:
            _drena()
            _, count, pad = runs[ri]
            saida.append(marcador_periodico(count, pad, body_lines[i]))
            i += count
            ri += 1
        else:
            pendente.append(body_lines[i])
            i += 1
    _drena()
    return saida, []                                    # info do seq_info: ver nota abaixo


# ────────── 4. <<< WELD em `HCCSeqRLE.encode`: o FLOOR ganha um terceiro candidato ──────────
#
# HOJE (hcc_seqrle.py:311-329):
#     compacted, info = compact_body(body_lines)
#     compactado = "\n".join(compacted) + "\n"
#     return compactado if len(compactado.encode()) <= len(body_text.encode()) else body_text
#
# DEPOIS — a ORDEM é load-bearing: `min()` devolve o PRIMEIRO mínimo, então `hoje` vem
# antes de `cru` para preservar a preferência atual em empates (byte-canonicidade), e
# `periodico` vem por último para só vencer com margem estrita.
#
#     hoje      = "\n".join(compact_body(body_lines)[0]) + "\n"
#     periodico = "\n".join(compact_body_com_periodico(body_lines, compact_body)[0]) + "\n"
#     return min(hoje, body_text, periodico, key=lambda s: len(s.encode("utf-8")))
#
# GUARDA 2 — o candidato periódico compete contra o corpo JÁ COMPACTADO, não contra o cru.
# Comparando com o cru ele "vencia" e piorava 4 de 8 casos (ruído alta-card 203 -> 253 B),
# porque ganhava do cru e perdia do uniforme. Mesma classe do fix de baseline do FLOOR da
# nature (2026-08-08) e do `T-BN-TIPADO` — a TERCEIRA vez.
#
# CUSTO DE CPU (medido, rodadas intercaladas, mediana de 7 — o caso que importa é o
# diário uniforme, onde o periódico NUNCA ganha e tudo que gasta é overhead):
#
#     versão do detector            n=600    n=1200   n=2400
#     ingênua (O(n²))                756 ms   3 269 ms  13 838 ms
#     + fronteira de cadeia 1x        27        60        127
#     + saída curta                   25        52        101
#     + salto de padrão uniforme      18        35         71      <- o que vai no weld
#     encode SEM a camada             10,5      25,5       52
#                                   +71%      +38%       +35%
#
# Desses ~35%, a maior parte é o array de deltas — que o `deltas_da_coluna` acima manda
# COMPARTILHAR com o detector uniforme. Isolado: 6,8 ms de deltas contra 1,6 ms de lógica
# de período num corpo de 1200 linhas. Compartilhar é parte do weld, não otimização
# posterior. Vizinho direto do `T-GATES-ANTES` e do `T-SEQRLE-INCREMENTAL`.


# ────────── 5. <<< WELD em `expand_seq_marker`: o espelho, no lugar que preserva o teto ──────────
#
# `expand_seq_marker` ganha o ramo do `~` NO TOPO. O laço de `decode` fica INTOCADO — e é
# justamente isso que mantém a pré-checagem do teto valendo pro marcador novo (medido:
# 0,0000 s contra 2,473 s se a expansão virasse passe separado).

def expand_periodic_marker(linha, _shift):
    """`*N~d1,…,dp|template` -> N linhas. `None` se não é marcador periódico CANÔNICO."""
    if not linha.startswith("*"):
        return None
    bar = linha.find("|")
    if bar == -1:
        return None
    head = linha[1:bar]
    til = head.find("~")
    if til <= 0 or not head[:til].isdigit():
        return None
    try:
        padrao = [int(x) for x in head[til + 1:].split(",")]
    except ValueError:
        return None                    # cai no ramo de hoje -> erro canônico do core
    count, template = int(head[:til]), linha[bar + 1:]
    if not _grafia_emissivel(padrao, count):
        return None                    # <<< GUARDA #5 — ver abaixo
    out, curr = [template], template
    for k in range(1, count):
        curr = _shift(curr, padrao[(k - 1) % len(padrao)])
        out.append(curr)
    return out


# ────────── 6. <<< WELD — canonicidade da grafia (achado #5 da caçada) ──────────
#
# Sem isto o marcador é NÃO-INJETIVO: `*3~1,4,9|` decodifica idêntico a `*3~1,4|` porque
# o `9` nunca é lido. Infinitas grafias válidas pro mesmo dado — o oposto do byte-canonical
# que o projeto usa como gate. Medido pelos caçadores em 6 formas distintas.

def _periodo_minimo(seq):
    """Menor `q` com `seq[k] == seq[k % q]` para todo k — o pad canônico de `seq`."""
    n = len(seq)
    for q in range(1, n + 1):
        if all(seq[k] == seq[k % q] for k in range(n)):
            return q
    return n


def _pad_canonico(pad, count):
    """INJETIVIDADE: `count` linhas consomem `count-1` deltas, e o decode lê
    `seq = [pad[k % len(pad)] …]`. A grafia canônica é a de PERÍODO MÍNIMO de `seq`.

        *5~1,4,9|    seq=[1,4,1,4] -> mín 2, pad 3  cauda MORTA        recusa
        *5~1,4,1,4|  idem          -> mín 2, pad 4  repetição          recusa
        *5~1,4,1|    idem          -> mín 2, pad 3  extensão parcial   recusa
        *600~1,1|    seq=[1,1,…]   -> mín 1         uniforme (`*N+d|`) recusa
        *5~1,4|      seq=[1,4,1,4] -> mín 2 == len  CANÔNICA           aceita

    `mínimo == 1` cobre a guarda 1 (pad uniforme) de graça.
    """
    if not pad or count < 2 or len(pad) > count - 1:
        return False
    seq = [pad[k % len(pad)] for k in range(count - 1)]
    q = _periodo_minimo(seq)
    return q == len(pad) and q >= 2


def _grafia_emissivel(pad, count):
    """RE-EMISSÃO: canônica **e** produzível pelo encoder. O detector exige 2 ciclos
    completos (`L >= 2p` ⇒ `count-1 >= 2p`); sem esta linha, `*4~1,3|` — que nenhum
    encoder TCF produz — decodificaria calado.

    Precedente direto: o `DataIsoSpec` recusa `20191204` porque `fromisoformat` aceita
    mais do que `isoformat` emite (`d.isoformat() != v`). Mesma assimetria, mesma cura.
    """
    return _pad_canonico(pad, count) and count - 1 >= 2 * len(pad)


# ────────── 7. <<< WELD — telemetria por candidato VENCEDOR (achado #4) ──────────
#
# O protótipo zerava `_seq_info` e nunca reatribuía: `seq_rle_runs` caía de 1 -> 0 mesmo
# com o corpo emitido BYTE-IDÊNTICO ao do core e cheio de `*N+d|`. Não é lacuna do
# mecanismo novo — é REGRESSÃO de um canal público com consumidores reais
# (`encoder.py:726` -> `schema.py:192` -> `scripts/schema_gadget/sideouts_quality.py`, e
# os próprios labs). Nenhum teste pegava: `test_side_outputs.py:58` só afirma `isinstance`.
#
# Duas armadilhas no conserto, as DUAS obrigatórias:
#   (a) o info tem de ser o do candidato VENCEDOR — vazio quando o cru vence;
#   (b) `compact_body(pendente)` devolve `start_line`/`end_line` relativos ao PEDAÇO;
#       sem reancorar no corpo inteiro, troca-se um silêncio por uma MENTIRA.
#
#     def _info_periodico(pos, count, pad, economia, template):
#         return {"start_line": pos + 1, "end_line": pos + count, "count": count,
#                 "deltas": list(pad), "uniform_delta": None, "periodo": len(pad),
#                 "template": template, "savings": economia}
#
#     # no encode, depois do min():
#     corpo, self._seq_info = min(candidatos, key=lambda t: len(t[0].encode("utf-8")))
#
# `uniform_delta=None` + `periodo` distinguem o run periódico do uniforme sem quebrar
# quem já lê o dicionário de hoje.


# ────────────────────────────────── notas do weld ──────────────────────────────────
#
# `_contador_declarado`: NÃO MUDA. Já lê `*2000000~1,2|` como 2000000 (para no primeiro
#   não-dígito). Verificado.
#
# Implementação de referência COMPLETA e rodando: `detector_v5.py` (mesmo diretório).
# Verificação dos 5 achados + gates: `v5_verificacao.py` — **8/8**.
#
# Testes que acompanham o weld:
#   - os 8 controles do `design_probe.py` (3 que usam + 4 byte-idênticos + 1 não-data)
#   - as 9 grafias não-canônicas de `v5_verificacao.py` (6 não-injetivas + 3 não-emissíveis)
#   - adversariais: valores que imitam o marcador
#   - bomba de memória com `max_length` (o caso que decidiu a colocação)
#   - telemetria: marcador no corpo ⇒ `seq_rle_runs` não-vazio; wire idêntico ⇒ runs iguais
#   - os dois gates byte-canonical + suíte inteira (1199)

def _len_marcador(count, padrao, template):
    return len(marcador_periodico(count, padrao, template))
