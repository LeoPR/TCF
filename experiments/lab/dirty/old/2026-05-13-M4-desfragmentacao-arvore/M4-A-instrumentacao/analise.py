"""M4.A — Instrumentacao da arvore (sem mexer no alg16).

Carrega cada dataset, roda alg16, simula serializacao M1.E, e mede:

1. Substrings compartilhadas (candidatos a no intermediario)
   - Por (eid_origem, P|S, length) com R >= 2 descendentes
   - Texto, R, Lr (chars M1.E), ganho potencial absoluto vs encadeado
2. Frags alocados vs realmente usados
   - Total de idx alocados
   - Idx referenciados em 2+ lugares vs idx usados 1x (candidatos a inline)
3. Distribuicao de idx (1 char [1-9], 2 chars [10-99], 3 chars [100+])
   - Quantos bytes gastos em refs por categoria
4. Limite teorico se alocacao fosse densa (idx baixos pros mais usados)
5. Limite teorico se idx-por-demanda (frags 1x viram inline)

Saida: 1 relatorio markdown por dataset em `relatorios/`.

NAO emite TCF. NAO altera alg16. Apenas medicao.
"""

import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

THIS = Path(__file__).parent
MACRO = THIS.parent
sys.path.insert(0, str(MACRO))

from online import processar, reconstroi, TokLit, TokRefPref, TokRefSuf


DATASETS = [
    "D1-emails-simples",
    "D2-emails-quote-id",
    "D3-stress-substring",
    "D4-caos-mix",
]


def coletar_quebras_e_frags(unicas, tokens_por_string):
    """Mesma logica de M1.E."""
    quebras = {eid: set() for eid in range(1, len(unicas) + 1)}
    for tokens in tokens_por_string:
        for tok in tokens:
            if isinstance(tok, TokRefPref):
                quebras[tok.string_id].add(tok.length)
            elif isinstance(tok, TokRefSuf):
                s_ref = unicas[tok.string_id - 1]
                quebras[tok.string_id].add(len(s_ref) - tok.length)
    for eid in range(len(unicas), 0, -1):
        toks = tokens_por_string[eid - 1]
        pos = 0
        for tok in toks:
            if isinstance(tok, TokLit):
                pos += len(tok.text)
            elif isinstance(tok, TokRefPref):
                cov = tok.length
                for q in list(quebras[eid]):
                    if pos < q < pos + cov:
                        quebras[tok.string_id].add(q - pos)
                pos += cov
            else:
                cov = tok.length
                rs = len(unicas[tok.string_id - 1]) - cov
                for q in list(quebras[eid]):
                    if pos < q < pos + cov:
                        quebras[tok.string_id].add((q - pos) + rs)
                pos += cov
    return quebras


def emit_refs_range(refs):
    """M1.E range serialization."""
    if not refs:
        return ""
    runs = []
    cur = [refs[0]]
    for r in refs[1:]:
        if r == cur[-1] + 1:
            cur.append(r)
        else:
            runs.append(cur)
            cur = [r]
    runs.append(cur)
    partes = []
    for run in runs:
        if len(run) >= 3:
            partes.append(f"{run[0]}..{run[-1]}")
        else:
            partes.extend(str(r) for r in run)
    return ",".join(partes)


def custo_idx(idx):
    """Bytes para serializar idx."""
    return len(str(idx))


def simular_alocacao(unicas, tokens_por_string, quebras):
    """Reproduz alocacao M1.E e coleta info de uso por frag."""
    frags_por_no = {}
    proximo_idx = 1
    # idx_usos[idx] = lista de eids que referenciam (cada vez que aparece)
    # eid_origem do frag = quem o criou (literal)
    idx_origem = {}  # idx -> eid_origem
    idx_texto = {}  # idx -> texto
    idx_usos = defaultdict(list)  # idx -> [(eid_user, posicao), ...]

    # cada eid pode ter elementos lit ou sub
    # sub_chave (eid_orig, tipo, length) -> lista de (eid_user, refs_idx)
    sub_chave_usos = defaultdict(list)

    for eid in range(1, len(unicas) + 1):
        s = unicas[eid - 1]
        toks = tokens_por_string[eid - 1]
        qa = quebras[eid]
        frags_por_no[eid] = []
        pos = 0
        for tok in toks:
            if isinstance(tok, TokLit):
                sl, el = pos, pos + len(tok.text)
                qs = sorted(q for q in qa if sl < q < el)
                pts = [sl] + qs + [el]
                for i in range(len(pts) - 1):
                    a, b = pts[i], pts[i + 1]
                    idx = proximo_idx
                    proximo_idx += 1
                    frags_por_no[eid].append((a, b, idx))
                    idx_origem[idx] = eid
                    idx_texto[idx] = s[a:b]
                pos = el
            elif isinstance(tok, TokRefPref):
                herdados = [(a, b, idx)
                             for (a, b, idx) in frags_por_no[tok.string_id]
                             if a < tok.length and b <= tok.length]
                refs_idx = [idx for (a, b, idx) in herdados]
                for (a, b, idx) in herdados:
                    frags_por_no[eid].append((pos + a, pos + b, idx))
                    idx_usos[idx].append(eid)
                key = (tok.string_id, 'P', tok.length)
                sub_chave_usos[key].append((eid, refs_idx))
                pos += tok.length
            else:
                s_ref = unicas[tok.string_id - 1]
                rs = len(s_ref) - tok.length
                herdados = [(a, b, idx)
                             for (a, b, idx) in frags_por_no[tok.string_id]
                             if a >= rs and b > rs]
                refs_idx = [idx for (a, b, idx) in herdados]
                for (a, b, idx) in herdados:
                    frags_por_no[eid].append(
                        (pos + (a - rs), pos + (b - rs), idx))
                    idx_usos[idx].append(eid)
                key = (tok.string_id, 'S', tok.length)
                sub_chave_usos[key].append((eid, refs_idx))
                pos += tok.length

    return {
        'frags_por_no': frags_por_no,
        'proximo_idx': proximo_idx,
        'idx_origem': idx_origem,
        'idx_texto': idx_texto,
        'idx_usos': idx_usos,
        'sub_chave_usos': sub_chave_usos,
    }


def metrica_substrings_compartilhadas(unicas, sub_chave_usos):
    """Identifica (eid_origem, P|S, length) usados por R>=2 descendentes."""
    candidatos = []
    for key, usos in sub_chave_usos.items():
        R = len(usos)
        if R < 2:
            continue
        eid_orig, tipo, length = key
        s_orig = unicas[eid_orig - 1]
        if tipo == 'P':
            texto = s_orig[:length]
        else:
            texto = s_orig[-length:]
        # Lr usando refs do primeiro uso (igual entre usos)
        refs_idx = usos[0][1]
        Lr = len(emit_refs_range(refs_idx))
        # ganho teorico se alias fosse idx 1-digit:
        # economia/uso = Lr - 1 (alias 1 char)
        # custo_decl = 0 (idx implicito, sem preambulo)
        ganho_implicito = R * (Lr - 1)
        # com declaracao explicita:
        # decl = `&N=texto\n` = 4 + len(texto) (alias absoluto)
        # economia/uso = Lr - 2 (alias 2 chars `&N`)
        ganho_explicito = R * (Lr - 2) - (4 + len(texto))
        candidatos.append({
            'key': key,
            'texto': texto,
            'Lt': len(texto),
            'R': R,
            'Lr': Lr,
            'ganho_implicito': ganho_implicito,
            'ganho_explicito': ganho_explicito,
        })
    return sorted(candidatos, key=lambda c: -c['ganho_implicito'])


def metrica_idx_uso(idx_usos, idx_texto, proximo_idx):
    """Quantos idx alocados, quantos referenciados em 2+ vs 1x."""
    total_alocados = proximo_idx - 1
    usados_2_mais = 0
    usados_1x = 0
    nao_referenciados = 0
    inline_potencial_bytes = 0  # se frags 1x virassem inline
    for idx in range(1, proximo_idx):
        usos = idx_usos.get(idx, [])
        if len(usos) == 0:
            nao_referenciados += 1
        elif len(usos) == 1:
            usados_1x += 1
            # se inline: economiza `idx` chars e ganha `len(texto)` chars
            # net inline = -custo_idx(idx) + len(texto)? Depende.
            # Atualmente: idx usado 1x custa custo_idx(idx) bytes na ref
            # Texto inline custaria len(texto) bytes
            # Inline ganha se len(texto) < custo_idx(idx)
            t = idx_texto.get(idx, '')
            if len(t) < custo_idx(idx):
                inline_potencial_bytes += custo_idx(idx) - len(t)
        else:
            usados_2_mais += 1
    return {
        'total_alocados': total_alocados,
        'usados_2_mais': usados_2_mais,
        'usados_1x': usados_1x,
        'nao_referenciados': nao_referenciados,
        'inline_potencial_bytes': inline_potencial_bytes,
    }


def metrica_distribuicao_idx(idx_usos, proximo_idx):
    """Distribuicao dos idx por categoria + bytes gastos em refs."""
    cat_1d = 0  # idx 1-9
    cat_2d = 0  # 10-99
    cat_3d = 0  # 100+
    bytes_total_refs = 0  # soma de bytes ao referenciar (sem ranges/agrupamento)
    bytes_total_refs_pesado = 0  # idem ponderado por uso
    for idx in range(1, proximo_idx):
        n_usos = len(idx_usos.get(idx, []))
        c = custo_idx(idx)
        if c == 1:
            cat_1d += 1
        elif c == 2:
            cat_2d += 1
        else:
            cat_3d += 1
        bytes_total_refs += c
        bytes_total_refs_pesado += c * n_usos
    return {
        'cat_1d': cat_1d,
        'cat_2d': cat_2d,
        'cat_3d': cat_3d,
        'bytes_total_idx_unicos': bytes_total_refs,
        'bytes_total_refs_pesado': bytes_total_refs_pesado,
    }


def metrica_realocacao_densa(idx_usos, proximo_idx):
    """Se idx fossem realocados densos (1-9 pros mais usados, depois
    10-99, etc), quantos bytes economiza?"""
    # ordena idx por uso decrescente
    idxs_por_uso = sorted(
        range(1, proximo_idx),
        key=lambda i: -len(idx_usos.get(i, [])))
    bytes_atual = sum(custo_idx(i) * len(idx_usos.get(i, []))
                      for i in range(1, proximo_idx))
    bytes_realocado = 0
    novo_idx = 1
    for old_idx in idxs_por_uso:
        usos = len(idx_usos.get(old_idx, []))
        bytes_realocado += custo_idx(novo_idx) * usos
        novo_idx += 1
    return {
        'bytes_atual': bytes_atual,
        'bytes_realocado': bytes_realocado,
        'economia': bytes_atual - bytes_realocado,
    }


def gerar_relatorio(ds, unicas, tokens, info, candidatos, m_uso,
                      m_distr, m_realoc):
    md = []
    md.append(f"# M4.A — Instrumentacao da arvore: {ds}")
    md.append("")
    md.append(f"Strings unicas: {len(unicas)}")
    md.append(f"Tokens emitidos por alg16: {sum(len(t) for t in tokens)}")
    md.append("")
    md.append("## 1. Frags alocados")
    md.append("")
    md.append(f"- Total alocados: {info['proximo_idx'] - 1}")
    md.append(f"- Usados em 2+ eids: **{m_uso['usados_2_mais']}**")
    md.append(f"- Usados 1x apenas: **{m_uso['usados_1x']}** (candidatos a inline)")
    md.append(f"- Nao-referenciados: {m_uso['nao_referenciados']} "
              f"(criados pelo no fonte mas nunca usados)")
    md.append(f"- Inline potencial (frags 1x onde texto < idx): "
              f"**{m_uso['inline_potencial_bytes']} bytes**")
    md.append("")
    md.append("## 2. Distribuicao de idx por categoria")
    md.append("")
    md.append(f"- Idx 1-9 (1 char): {m_distr['cat_1d']}")
    md.append(f"- Idx 10-99 (2 chars): {m_distr['cat_2d']}")
    md.append(f"- Idx 100+ (3 chars): {m_distr['cat_3d']}")
    md.append(f"- Bytes em refs (ponderado por uso): "
              f"**{m_distr['bytes_total_refs_pesado']}**")
    md.append("")
    md.append("## 3. Realocacao densa (idx baixos pros mais usados)")
    md.append("")
    md.append(f"- Bytes atual: {m_realoc['bytes_atual']}")
    md.append(f"- Bytes apos realocacao: {m_realoc['bytes_realocado']}")
    md.append(f"- **Economia teorica: {m_realoc['economia']} bytes**")
    md.append("")
    md.append("## 4. Substrings compartilhadas (candidatos a no intermediario)")
    md.append("")
    if not candidatos:
        md.append("Nenhuma substring com R>=2 detectada.")
    else:
        md.append(f"{len(candidatos)} candidato(s) com R>=2:")
        md.append("")
        md.append("| key (eid, tipo, len) | R | Lt | Lr | ganho implicito | ganho explicito | texto |")
        md.append("|---|---:|---:|---:|---:|---:|---|")
        for c in candidatos:
            key = c['key']
            texto_esc = c['texto'].replace('|', '\\|').replace('\n', '\\n')
            if len(texto_esc) > 30:
                texto_esc = texto_esc[:27] + '...'
            md.append(f"| ({key[0]},{key[1]},{key[2]}) | {c['R']} | {c['Lt']} | "
                      f"{c['Lr']} | {c['ganho_implicito']:+d} | "
                      f"{c['ganho_explicito']:+d} | `{texto_esc}` |")
    md.append("")
    md.append("## 5. Resumo dos limites teoricos")
    md.append("")
    soma_implicito = sum(c['ganho_implicito']
                          for c in candidatos if c['ganho_implicito'] > 0)
    soma_explicito = sum(c['ganho_explicito']
                          for c in candidatos if c['ganho_explicito'] > 0)
    md.append(f"- **Inline frags 1x** (s/ tocar arvore): "
              f"{m_uso['inline_potencial_bytes']} bytes")
    md.append(f"- **Realocacao densa** (s/ tocar arvore): "
              f"{m_realoc['economia']} bytes")
    md.append(f"- **No intermediario com idx implicito** (modifica arvore): "
              f"{soma_implicito} bytes")
    md.append(f"- **No intermediario com decl explicita** (M3-style): "
              f"{soma_explicito} bytes")
    md.append("")
    md.append("Notas:")
    md.append("- Ganhos *implicitos* somam ocorrencias mas ignoram conflitos "
              "(varios candidatos podem competir).")
    md.append("- Ganhos *explicitos* descontam custo de declaracao (M3-style).")
    md.append("- *Inline* e *realocacao densa* sao ortogonais; podem somar.")
    md.append("- *No intermediario* modifica a arvore (M4.C).")
    return "\n".join(md)


def main():
    DATA = MACRO / "data"
    OUT = THIS / "relatorios"
    OUT.mkdir(exist_ok=True)

    print("=== M4.A — Instrumentacao da arvore ===")
    print(f"Datasets: {DATASETS}")
    print()

    resumo_global = []
    for ds in DATASETS:
        path = DATA / f"{ds}.csv"
        with path.open(encoding="utf-8") as f:
            r = csv.reader(f)
            next(r)
            linhas = [row[0] for row in r if row]
        # unicas preservando ordem
        unicas = []
        seen = set()
        for s in linhas:
            if s not in seen:
                unicas.append(s)
                seen.add(s)

        tokens, _ = processar(unicas, min_len=3)
        for s, t in zip(unicas, tokens):
            assert reconstroi(t, unicas) == s

        quebras = coletar_quebras_e_frags(unicas, tokens)
        info = simular_alocacao(unicas, tokens, quebras)

        candidatos = metrica_substrings_compartilhadas(
            unicas, info['sub_chave_usos'])
        m_uso = metrica_idx_uso(info['idx_usos'], info['idx_texto'],
                                  info['proximo_idx'])
        m_distr = metrica_distribuicao_idx(info['idx_usos'],
                                             info['proximo_idx'])
        m_realoc = metrica_realocacao_densa(info['idx_usos'],
                                              info['proximo_idx'])

        md = gerar_relatorio(ds, unicas, tokens, info, candidatos,
                              m_uso, m_distr, m_realoc)
        (OUT / f"{ds}.md").write_text(md, encoding="utf-8")

        soma_implicito = sum(c['ganho_implicito']
                              for c in candidatos if c['ganho_implicito'] > 0)
        soma_explicito = sum(c['ganho_explicito']
                              for c in candidatos if c['ganho_explicito'] > 0)
        resumo_global.append({
            'ds': ds,
            'frags': info['proximo_idx'] - 1,
            'usados_2plus': m_uso['usados_2_mais'],
            'usados_1x': m_uso['usados_1x'],
            'inline_potencial': m_uso['inline_potencial_bytes'],
            'realocacao_densa': m_realoc['economia'],
            'no_intermediario_implicito': soma_implicito,
            'no_intermediario_explicito': soma_explicito,
        })
        print(f"  {ds:<25}  frags={info['proximo_idx']-1:<3} "
              f"usados2+={m_uso['usados_2_mais']:<3} "
              f"1x={m_uso['usados_1x']:<3} "
              f"inline={m_uso['inline_potencial_bytes']:>3}B "
              f"realoc={m_realoc['economia']:>3}B "
              f"intermed_impl={soma_implicito:>3}B "
              f"intermed_expl={soma_explicito:>3}B")

    # consolidado
    md = []
    md.append("# M4.A — Resumo consolidado")
    md.append("")
    md.append("Limites teoricos de economia por tecnica, sem implementar.")
    md.append("")
    md.append("| Dataset | Frags | Usados 2+ | Usados 1x | Inline | Realoc densa | Intermed (impl) | Intermed (expl) |")
    md.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    tot = {'inline_potencial': 0, 'realocacao_densa': 0,
            'no_intermediario_implicito': 0, 'no_intermediario_explicito': 0}
    for r in resumo_global:
        md.append(f"| {r['ds']} | {r['frags']} | {r['usados_2plus']} | "
                  f"{r['usados_1x']} | {r['inline_potencial']} | "
                  f"{r['realocacao_densa']} | "
                  f"{r['no_intermediario_implicito']} | "
                  f"{r['no_intermediario_explicito']} |")
        for k in tot:
            tot[k] += r[k]
    md.append(f"| **TOTAL** | — | — | — | **{tot['inline_potencial']}** | "
              f"**{tot['realocacao_densa']}** | "
              f"**{tot['no_intermediario_implicito']}** | "
              f"**{tot['no_intermediario_explicito']}** |")
    md.append("")
    md.append("## Baseline para comparacao")
    md.append("")
    md.append("- M1.E nos canonicos: 676 bytes")
    md.append("- M2.A nos canonicos: 666 bytes (-10 vs M1.E)")
    md.append("- M3.A/M3.B: 676 (sem ganho liquido)")
    md.append("")
    md.append("## Como ler")
    md.append("")
    md.append("- **Inline frags 1x**: frags alocados mas usados 1x onde "
              "texto inline custa menos que o idx. Ganho real se "
              "implementarmos idx-por-demanda (M4.B).")
    md.append("- **Realocacao densa**: idx baixos (1 char) pros mais usados, "
              "altos (2 chars) pros menos usados. Ortogonal ao inline.")
    md.append("- **No intermediario (implicito)**: limite superior se "
              "criassemos nos compartilhados com idx implicito (sem preambulo). "
              "Ignora conflitos.")
    md.append("- **No intermediario (explicito)**: idem mas com declaracao "
              "explicita estilo M3. Net real ja' descontado custo de decl.")
    md.append("")
    md.append("Ganhos sao **limites teoricos** — implementacao real")
    md.append("pode ficar abaixo por conflitos entre tecnicas.")
    (OUT / "_resumo.md").write_text("\n".join(md), encoding="utf-8")

    print()
    print(f"Relatorios em: {OUT}/")
    print(f"  - _resumo.md (consolidado)")
    print(f"  - <dataset>.md (por dataset)")


if __name__ == "__main__":
    main()
