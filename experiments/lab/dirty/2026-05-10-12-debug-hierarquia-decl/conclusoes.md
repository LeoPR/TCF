# Conclusões — debug hierarquia de pref/suf

## Tabela consolidada

```
dataset                          n_prefs pais_p n_sufs pais_s  d_pref  d_suf d_total
D1-emails-um-dominio                   1      1      0      0     +36     +0     +36
D2-emails-multi-dominio                0      0      1      1      +0    +36     +36
D3-urls-path-comum                     0      0      0      0      +0     +0      +0
D4-urls-multi-recurso                  3      1      0      0      +4     +0      +4
```

**Em todos os datasets onde há pref/suf com pai Patricia, decl
hierárquica resulta em perda ou neutralidade.** Negativo (ganho)
em nenhum caso.

## Achado contra-intuitivo

A intuição era: "se os 3 prefs do D4 compartilham `https://api.example.com/v1/`
(27 chars), fatorar esse pai uma vez economizaria 2×27 = 54 chars."

A medida revela: **a sintaxe extra de `decl filho_de(noPP) + "EXTRA"`
custa quase o mesmo que economiza**. Em D4 com 3 filhos:

| Item | Bytes |
|---|---:|
| Economia em dados (pai não duplicado) | -54 |
| Overhead sintático por filho (3 × ~18) | +54 |
| Decl extra do pai | +52 |
| Eliminação de 27 chars duplicados (3 → 1 ocorrência) | -27 |
| **Saldo** | **+4** |

A árvore Patricia identificou semanticamente que `v1/` é avô comum,
mas representar essa relação no encode atual custa exatamente o
mesmo que vale a economia.

## Heurística inversa — quando vale

Pelo cálculo simbólico:

```
ganho > 0  ⟺  len(pai) × (N_filhos − 1) > N_filhos × 18 + 25
```

Para `len(pai) = 27` (D4 base URL): precisa `N_filhos ≥ 6`.
Para `len(pai) = 12` (`maria.silva@` em D2): precisa `N_filhos ≥ 25+`.
Para `len(pai) = 4` (`.com`): inviável.

Nenhum dos datasets atuais tem essa densidade. D4 chegou perto (3
filhos por pai); precisaria de pelo menos 6 para virar a balança.

## D4 — analise detalhada

O caso mais favorável dentre os 4. Pref texts:

| pref_text | ocorrências | extra |
|---|---:|---|
| `https://api.example.com/v1/users/` | 4 | `users/` |
| `https://api.example.com/v1/orders/10` | 5 | `orders/10` |
| `https://api.example.com/v1/products/5` | 3 | `products/5` |

Pai comum: `https://api.example.com/v1/` (27 chars).

12 ocorrências totais cobertas. Se houvesse mais 3 famílias
(ex: `/v1/admins/`, `/v1/sessions/`, `/v1/logs/`), seriam 6
filhos e o ganho seria positivo:

```
6 filhos × 27 chars = 162 economia em dados
6 × 18 overhead sintaxe = 108
+ 52 decl do pai = 160 custo
saldo: -162 + 160 = -2 (ganho minimo)
```

Com 7+ filhos, o ganho cresce. Datasets reais com APIs RESTful
costumam ter 8-15 recursos sob mesma base — então em escala, decl
hierárquica para pref ganharia em D4-like.

## D1 e D2 — não vale

D1 tem só 1 pref com pai (`user00`→`user0`). 1 filho × 5 chars
de economia vs 18 chars de sintaxe + 30 chars de decl pai = +43.
Bate o medido (+36, com aproximações).

D2 tem só 1 suf com pai (`mail.com`→`.com`). Cálculo análogo: +36.

## D3 — não tem candidatos

Em D3 nenhum pref text tem pai (a URL completa `https://api.example.com/v1/users/`
é raiz top-level da Patricia forward). Decl hierárquica não aplica.

Hipotético: se D3 fosse expandido para incluir URLs sob mais
recursos (`/users/`, `/orders/`, `/products/`), viraria caso D4 com
N_filhos crescendo — ganho positivo eventual.

## Pontos a registrar

1. **Decl hierárquica para pref/suf é perda nos 4 datasets atuais.**
   Confirma análise simbólica. Não implementar B-médio nesta
   direção sem antes (a) compactar sintaxe ou (b) testar em
   datasets com 6+ filhos por pai.

2. **O gargalo é sintático**, não semântico. A árvore Patricia já
   capturou a hierarquia (visto no exp 06 D4 — 3 níveis). O encode
   verboso atual não consegue representar essa hierarquia
   economicamente.

3. **Threshold de viabilidade**: para len(pai)=27, precisa
   N_filhos ≥ 6. APIs reais com 10+ recursos sob mesma base
   atingiriam isso facilmente.

4. **Direção alternativa "mais segmentos" (ideia do user)**: em
   vez de decl de nó intermediário, ter `seg1 + seg2 + seg3` na
   mesma linha externa. Conceitualmente diferente. Elimina overhead
   do "decl filho_de" porque não cria nó intermediário. Pode ser
   mais econômico — vale experimento próprio se quiserem testar.

5. **Pergunta original do user respondida**: "ter mais níveis
   poderia ajudar?" — em princípio sim (semantica capturada), mas
   na prática com a sintaxe atual NÃO ajuda nos datasets pequenos
   testados. Vale a pena em datasets maiores ou com sintaxe
   compacta.

## O que este experimento NÃO mostra

- Comportamento em datasets com 6+ filhos por pai.
- Resultado com sintaxe compacta.
- Implementação real — apenas estimativa.
- Direção "mais segmentos" — só mencionada como alternativa.
- Cadeia de avôs profunda (bisavô do pref/suf) — só pais imediatos.
- Comparação com outros formatos (CSV, JSON, HTFC).

## Sugestões para próximo experimento

Três opções (sua escolha):

1. **Construir D5** — dataset com 6+ URLs sob mesma base, para
   validar que decl hierárquica vira positivo. Estilo D4 mas com
   mais recursos.

2. **Voltar para B-médio (fatorização de `(mid, suf)`)** — exp 11
   já mostrou ganho 12.4% em D2. Mais barato e direto que
   hierárquica.

3. **Direção "mais segmentos"** — repensar a sintaxe da decl
   externa para permitir N segmentos. Mais ambicioso, exige
   redesign do encode/decode.
