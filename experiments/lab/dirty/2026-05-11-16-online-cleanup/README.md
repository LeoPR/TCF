# 16 — online cleanup (refatoração do exp 15)

## Princípio / motivação

Continuação direta do [exp 15](../2026-05-11-15-online-com-fix/).
Antes de avançar para novas direções (revisão retroativa, par
A+B independente, escala) é preciso verificar se há **lixo fixado
em código** que aumenta superfície de bug e dificulta leitura.

Refatoração **estrutural pura**: nenhuma mudança de algoritmo. O
contrato é que os TCFs gerados sejam byte-idênticos aos do exp 15.

## Propósito

1. **Viabilidade**: o algoritmo do exp 15 pode ser expresso em
   menos código mantendo identidade byte a byte?
2. **Comportamento**: identificar dominância de candidatos no
   `_escolher_par` que justificou redução de 4 para 2.

## Comparação

- **Compara com**: [15 (online com fix)](../2026-05-11-15-online-com-fix/).
- **Datasets**: mesmos 3 (D2-mini, D2-completo, D4).
- **Métrica de equivalência**: bytes literais + unidades de
  informação + diff binário dos TCFs.

## Mudanças aplicadas

### online.py

1. **`_escolher_par`**: reduzido de 4 para 2 candidatos.
   - Análise: candidato (c) "só pref" `(bp_id, bp_len, 0, 0)` é
     **dominado por (a)**. Quando `espaco_suf < min_len`,
     `maior_suf_ate` retorna 0 e (a) coincide com (c). Quando
     `espaco_suf >= min_len`, (a) tem `novo_suf_len >= 0`;
     se >0, cobre mais que (c); se =0, é igual a (c).
   - Mesma análise para (d) "só suf" dominado por (b).
   - Conclusão: bastam (a) e (b).

2. **Funções auxiliares `_melhor_pref` / `_melhor_suf`**:
   substituem `maior_pref_ate` / `maior_suf_ate` antigas, com
   nome consistente e ciclo idêntico. Recebem `max_len` (`n`
   inteiro quando não há limite, `n - bs_len` quando há
   restrição de espaço).

3. **`reconstroi`**: removido guard `if tok.length > 0` da
   `TokRefSuf` — algoritmo nunca emite ref com `length=0`
   (linha `if bs_len > 0:` em `processar` garante).

4. **Renomeações**: `strings_originais` → `strings_unicas`
   (consistente com `processar`); `strings_anteriores` →
   `anteriores`.

5. **`processar`**: branch da primeira string mais direto
   (`if idx == 0:` em vez de `if not tokens_por_string:`).

### encode_online.py

1. **Comentário longo (linhas 42-49 do exp 15)** explicando que
   `string_id == eid` por construção: removido. Era observação de
   debug, não documentação de contrato.

2. **`render_token`** → `_render_token` (private).

3. **RLE adjacente** extraído para função `_rle_adjacente`.

4. **Lógica de declaração vs ref**: unificada via variável
   `prefixo` (`"{count}x "` ou `""`).

### decode_online.py

1. **Lógica de ref**: dois branches (`startswith("ref:no")` vs
   `re.match("...")`) unificados em um regex único
   `RE_REF` com `count` opcional.

2. **Lógica de decl**: regex único `RE_DECL` que captura `eid`,
   `count` opcional, e `forma`.

3. **`parse_token`** extraído para fora de `decode_online` (era
   closure interna); recebe `strings` como parâmetro.

## Resultado observado

Roundtrip **3/3 OK**.

| Dataset | bytes 16 | bytes 15 | diff | unidades 16 | unidades 15 | diff |
|---|---:|---:|---:|---:|---:|---:|
| D2-mini | 193 | 193 | 0 | 47 | 47 | 0 |
| D2-completo | 441 | 441 | 0 | 78 | 78 | 0 |
| D4 | 399 | 399 | 0 | 75 | 75 | 0 |

**Diff binário dos TCFs gerados**: idêntico em todos os 3
datasets. Refatoração não introduziu nenhuma divergência.

### Redução de código

| Arquivo | exp 15 | exp 16 | diff |
|---|---:|---:|---:|
| online.py | 192 | 168 | -24 (-12%) |
| encode_online.py | 86 | 66 | -20 (-23%) |
| decode_online.py | 90 | 83 | -7 (-8%) |
| **Total** | **368** | **317** | **-51 (-14%)** |

## Limitações

- Nenhuma mudança de algoritmo — limitações do exp 15 persistem
  (busca conservadora em overlap, sem revisão retroativa, escala
  não medida, sem teste em famílias variadas).
- Análise de dominância de candidatos foi feita por raciocínio
  manual; não há teste formal que prove dominância em todos os
  casos (mas a coincidência byte-a-byte em 3 datasets é
  evidência empírica forte).

## Como reproduzir

```bash
cd experiments/lab/dirty/2026-05-11-16-online-cleanup
python run.py
```

Saída esperada: tabela com `diff = 0` em todas as linhas e
mensagem "OK: exp 16 reproduz exp 15 byte a byte".

## Próximo experimento

[18 — famílias variadas](../) (ainda não criado): testar o
algoritmo do exp 16 em URLs profundas, UUIDs, datas ISO, IPs e
CPFs. Identificar onde a heurística atual degrada.
