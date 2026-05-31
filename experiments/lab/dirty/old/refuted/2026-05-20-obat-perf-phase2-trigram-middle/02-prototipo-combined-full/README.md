# Sub-exp 02 — prototipo v4 (combined_full key)

**Decisao do sub-exp 01**: usar `combined_full` key
(`s[:3] + middle + s[-3:]`) — reduz max bucket em datas de 2160 → 9.

## Plano

- `obat_v4_combined_full.py` — variante com key combined_full
- `benchmark.py` — compara v0 (baseline) vs v3 (ADR-0009 welded)
  vs v4 (proposta) em D1-D9 + lineitem 1k/5k

## Variante v4

Igual v3 mas mudando duas linhas:
- `prefix_index.setdefault(s[:3], ...)` → `prefix_index.setdefault(make_key(s), ...)`
- Idem suffix

**Make_key**:
```python
def make_key(s, L):
    if L < 5:
        return s[:3] + s[-3:]  # fallback sem middle
    mid_start = (L - 3) // 2
    return s[:3] + s[mid_start:mid_start + 3] + s[-3:]
```

Note: usa MESMA key pra prefix_index E suffix_index (mais simples).
Decisao: testar isso primeiro vs separate keys.

Na verdade, pra preservar semantica de "match valido implica
substring de 3 chars iguais", precisa de keys SEPARADAS:
- `prefix_match`: precisa `s[:3] == prev[:3]` → key inclui `s[:3]`
- `suffix_match`: precisa `s[-3:] == prev[-3:]` → key inclui `s[-3:]`

Mas qualquer combined que CONTENHA s[:3] resolve pra prefix.
combined_full contem ambos, entao pode servir tanto pra prefix
match como suffix match.

**Logica**: pra um match de prefix, qualquer string com mesmo combined_full
tem mesmo s[:3] AND mesmo middle AND mesmo s[-3:]. Logo, qualquer match
de prefix vai estar no mesmo bucket combined_full.

PERO: pode haver MATCH DE PREFIX EM STRING COM MESMO s[:3] MAS combined
diferente! Ex: `"abcXYZ"` e `"abcDEF"` — ambos prefix-match em "abc"
mas combined_full differente (`abcbcXYZ` vs `abcbcDEF`).

ENTAO COMBINED NAO PODE SER A KEY PRA PREFIX MATCH — perde matches!

Reconsiderar.

## Reformulacao

Para preservar TODOS os matches:
- Prefix key MUST be `s[:3]` (qualquer string que possa fazer prefix match
  com s tem `s[:3]` igual)
- Suffix key MUST be `s[-3:]`

Tentativas de dispersao adicional analisadas:

**Multi-hash com INTERSECAO** (`prefix ∩ middle`): perde matches.
Match `lcp(s,prev)=4` pode ter `s[:3]=prev[:3]` mas `middle(s)!=middle(prev)`,
sendo excluido da intersecao. **REJEITADA**.

**Multi-hash com UNION** (`prefix ∪ middle`): EXPANDE candidatos,
nao reduz. **NAO AJUDA**.

**Index hierarchico** `prefix[s[:3]][middle]`: equivalente a intersecao.
Mesmo problema. **REJEITADA**.

**Index k=6 + skip ja-visitados**: pra l_shipdate, bucket k=3 ja' tem
2160 (todos), bucket k=6 tem ~30. Skip dos 30 visitados em k=3 deixa
2130 IDs ainda pra iterar (lcp 3-5 possible). **Mesmo trabalho total**.

## Conclusao do sub-exp 02 (sem rodar codigo)

**Hash-based tradicional NAO RESOLVE datas com prefixo popular + lcp
longo SEM quebrar byte-canonical**.

Pra ter speedup em datas preservando bytes, precisa de estrutura
**posicional** que retorne best LCP direto (sem iteracao):
- **Patricia trie** (radix tree): traverse O(L) retorna folha com lcp
  maximo. Em cada subtree mantem IDs ordenados → tie-break preservado.
  Custo: O(L) lookup vs O(B) bucket. **CANDIDATO REAL**.
- **Suffix array** (offline): build O(N log N), lookup O(L log N).
  Mais complexo, requer 2 estruturas (prefix + suffix).
- **Versionar formato** (quebra byte-canonical controlado): aceitar
  diferenca, marcar como v0.7. Solucao "drastica".

## Direcao revisada

Decisao no nivel ticket [META-PERF-PHASE2](../../../../tickets/META-PERF-PHASE2.md):

**Opcao A**: pausar H-PERF-04 (datas), focar em **H-PERF-05** (HCC opt).
Aceitar speedup 2x em datas vs 5x+ em outras cols como suficiente
no Pacote 4. Retornar pra datas com Patricia trie se H-PERF-05 nao
bastar.

**Opcao B**: prototipar **Patricia trie em sub-exp 03** (substitui
sub-exp 02 abortado). Risco: implementacao complexa em Python
(overhead de dict-of-dicts).

**Opcao C**: aceitar versionamento (formato v0.7 quebra D1-D9 baseline).
Risco politico: M9 e' regra invariante do projeto.

**Recomendacao**: Opcao A (pausar e focar HCC). Datas ja' tem 2x
speedup; HCC opt tem ganho potencial maior em pipeline global.
Retornar pra trie depois se necessario.
