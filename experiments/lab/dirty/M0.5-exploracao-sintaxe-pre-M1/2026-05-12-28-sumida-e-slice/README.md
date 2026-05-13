# 28 — Etapa 2: sumida implementada + análise de slice arbitrário

## Princípio / motivação

Continuação do flow semântico do exp 27. Esta etapa testa **2
hipóteses**:

1. **Sumida**: dígitos no literal podem ser omitidos quando o
   número formado não corresponde a idx existente. Decoder
   stateful detecta e trata como literal.

2. **Slice arbitrário**: substring no meio de um literal pode
   ser substituída por ref ao slice de outro nó. Sem
   implementação ainda — apenas análise de potencial.

Raiz: `online.py` do exp 16 (intocado).

## Sumida — implementação

`CompactV6SumidaSyntax` (versão v4-quote-fixed + sumida):

- Encoder: para cada fragmento literal **inteiramente de dígitos**,
  verifica se o número N > max_idx_existente. Se sim, **sumir**
  (emitir raw, sem aspas) quando posição na linha permite economia.
- Decoder: stateful, mantém dict frags{idx → texto}. Sequência
  de dígitos vira ref se idx N existe; caso contrário, literal +
  aloca idx (para manter coerência).

**Restrição**: sumida só aplica a fragmentos **puros de dígitos**.
Fragmentos misturados (letras + dígitos) exigem sub-divisão ou
slice arbitrário — fica para próxima etapa.

## Resultado da sumida em 2 datasets

| Dataset | v4-q-fix | v6-sumida | diff |
|---|---:|---:|---:|
| emails-quote-id | 198 | **197** | -1 (-0.5%) |
| stress-substring-meio | 233 | **231** | -2 (-0.9%) |

**Ganho consistente mas pequeno** (~1%). Sumida funciona, mas
captura pouco em datasets fatorizados pelo exp 16.

Onde sumida ganhou em emails-quote-id: Linha 1 (eid=1), literal
`"1"` entre dois outros literais:

```
v4-q-fix:  d'a*nge*lo*'1'@g*mail*.com   ← '1' com aspas (3 bytes)
v6-sumida: d'a*nge*lo*1*@g*mail*.com    ← 1 entre seps (2 bytes)
```

Aspas (`'1'`=3) > sumida + separador (`1*`=2) por 1 byte.

### Por que tão pouco?

Outras ocorrências de dígitos puros não conseguem sumir:

| Literal | eid | Contexto | Por quê não suma |
|---|---|---|---|
| `"42"` (eid=2) | 2 | entre refs `1,2,3` e `5,6,7` | separadores extras = empate com aspas |
| `"42"` (eid=10) | 10 | idem | idem |
| `"03"` (eid=3) | 3 | entre refs `1,2,3,4` e `5,6,7` | idem |
| `"1"` (eid=9) | 9 | entre literais "m'baye" e "@hot" | idx 1 EXISTE — não pode sumir |
| `"103"` em "o'connor103" | 11 | dentro de literal misto | não é frag puro de dígitos |
| `"256"` em "rcy256" | 12 | dentro de literal misto | idem |

Sumida tem ganho **estrutural mínimo** em datasets dominantemente
fatorizados. O algoritmo do online.py concentra ambiguidade em
posições onde sumida não ajuda (entre refs em ambos os lados).

## Análise de slice arbitrário — potencial medido

Procurar para cada literal misto (letras+dígitos), substring
contígua >= 3 chars que aparece em algum nó anterior. Sem
implementar encoder.

### emails-quote-id

| Literal | Substring | Em | Ganho potencial |
|---|---|---|---|
| `"o'connor103"` (eid=11) | `"103"` | eid=3 pos 8 | **3 chars → 1 ref ≈ 2 bytes** |
| `"rcy256"` (eid=12) | (nenhuma >=3) | — | 0 |

**Total**: 2 bytes potenciais de ganho.

### stress-substring-meio (novo dataset com padrões centrais)

```
api/users/00042/profile.json
api/users/00103/profile.json
api/orders/00042/items.json
web/users/00042/profile.json
...
```

| Literal | Substring | Em | Ganho potencial |
|---|---|---|---|
| `"orders/00"` (eid=7) | `"ers/00"` | eid=1 pos 6 | **6 chars → 1 ref ≈ 5 bytes** |

Apenas 1 oportunidade. **Pequeno ganho mesmo em dataset stress**.

### Por que o ganho é tão pequeno

O algoritmo do exp 16 **já fatora muito bem**. Quando há padrão
forte como `/users/`, ele captura via LCP/LCS, deixando poucos
fragmentos misturados.

Em stress-substring-meio, o algoritmo:
- Detectou `/users/` e `/orders/` via LCP/LCS
- Os literais residuais (`users/00`, `orders/00`) são pequenos
- Substring entre eles é curta (6 chars)

Slice arbitrário ganharia mais em datasets onde:
- O padrão central é grande (>=10 chars)
- O algoritmo não fatora (LCP=0 e LCS=0)
- Substring no meio é a única forma de capturar

Esses casos parecem **raros** em datasets reais bem-estruturados.

## Insights consolidados das Etapas 1 e 2

| Técnica | Ganho real medido | Limitação |
|---|---|---|
| **Sumida** (Etapa 2) | -1 byte em emails-quote-id (-0.5%) | só fragmentos puros de dígitos; restrito por contexto |
| **Slice arbitrário** (análise) | -2 a -5 bytes potenciais | poucos fragmentos mistos; algoritmo já fatorou |
| Escape vs aspas (exps 24-26) | empate teórico | depende do contexto |

**A pressão de otimização é pequena nesses datasets** porque o
algoritmo do exp 16 já faz a maior parte do trabalho.

## Limitações desta etapa

- **Sumida só para fragmentos puros de dígitos**: fragmentos
  misturados exigem sub-divisão (complexa) ou slice arbitrário
  (não implementado)
- **Análise de slice não considera oportunidades em fragmentos
  puros**: foi focada em mistos
- **Apenas 2 datasets**: emails-quote-id e stress-substring-meio
- **Slice arbitrário não foi implementado**: só medido

## Como reproduzir

```bash
cd experiments/lab/dirty/2026-05-12-28-sumida-e-slice
python run.py            # v4-q-fix vs v6-sumida em emails-quote-id
python analise_slice.py  # potencial de slice em 2 datasets
```

## Conclusões

Ver [conclusoes.md](conclusoes.md). Pontos principais:

1. **Sumida tem ganho estrutural pequeno** em datasets fatorizados
   pelo exp 16
2. **Slice arbitrário tem potencial pequeno** pelo mesmo motivo
3. **O algoritmo do exp 16 é muito bom** — está raspando os
   últimos bytes
4. **Próxima direção honesta**: ou implementar slice arbitrário
   completo (custo alto, ganho pequeno) ou parar de refinar
   sintaxe e medir externamente (benchmark com gzip)
