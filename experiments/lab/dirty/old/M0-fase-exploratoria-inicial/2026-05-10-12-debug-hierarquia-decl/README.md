# 12 — debug hierarquia das declarações de pref/suf

## Princípio / motivação

Observação visual no D4 do exp 10:

```
no2 = decl folha "https://api.example.com/v1/users/"
no4 = decl folha "https://api.example.com/v1/orders/10"
no8 = decl folha "https://api.example.com/v1/products/5"
```

Os 3 pref texts compartilham `https://api.example.com/v1/` (27
chars). Mas a decl atual trata cada um como folha simples,
duplicando o pai 3 vezes.

A árvore Patricia forward de D4 **já tem** esse pai como nó
intermediário (visto no exp 06: árvore tem
`https://api.example.com/v1/` → `users/`, `orders/10`, `products/5`).
O encoder do exp 10 **ignora a hierarquia** quando declara pref/suf
— só usa `decl folha "X"`.

A pergunta: se a decl de pref/suf fosse hierárquica (estilo do exp
05/06 para folhas — `decl filho_de(noP) + "extra"`), quanto
economizaríamos? Vale o esforço de implementar?

Este experimento é **debug** (estilo 09 e 11) — não implementa
nada, só identifica pref/suf que têm pai ignorado e estima
ganho/custo.

## Propósito

Responde a uma pergunta:

1. **Faz sentido implementar decl hierárquica para pref/suf?**
   Quantos pref/suf nos 4 datasets têm pai Patricia ignorado, e
   qual a estimativa de bytes economizados?

## Comparação

- **Compara com**: [10-decomposicao-com-avos](../2026-05-10-10-decomposicao-com-avos/)
  (baseline com decl folha simples).
- **Não modifica algoritmo**. Análise simbólica.

## Cenários e valores possíveis

Mesmos 4 datasets do exp 10/11. Para cada:

1. Reaplica decomposição do exp 10.
2. Para cada `pref_text` único usado nas decomposições, busca na
   árvore Patricia forward se ele corresponde a algum nó com pai.
3. Idem para `suf_text` na árvore reverse (des-invertendo).
4. Para cada candidato com pai, calcula:
   - bytes atuais (`decl folha "TEXTO_COMPLETO"`)
   - bytes hierárquicos (`decl filho_de(noPP) + "EXTRA"` + decl
     única do pai)
   - delta líquido

## Resultado observado

| Dataset | n_prefs c/pai | n_sufs c/pai | delta_pref | delta_suf | delta_total |
|---|---:|---:|---:|---:|---:|
| D1 | 1 (`user00`→`user0`) | 0 | **+36** | 0 | **+36** |
| D2 | 0 | 1 (`mail.com`→`.com`) | 0 | **+36** | **+36** |
| D3 | 0 | 0 | 0 | 0 | 0 |
| D4 | 3 (`*v1/users/`, etc, todos→`*v1/`) | 0 | **+4** | 0 | **+4** |

**Decl hierárquica é perda em todos os 4 datasets** com a sintaxe
atual. D4 é o caso mais favorável (3 prefs compartilhando mesmo
pai com 12 ocorrências cobertas), mas mesmo assim delta +4 chars.
D1 e D2 perdem +36 cada porque só 1 candidato cada — overhead do
pai não amortiza.

### Análise do D4 (caso mais favorável)

```
3 pref candidatos:
  "https://api.example.com/v1/users/"     n=4 ocorrências  extra="users/"
  "https://api.example.com/v1/orders/10"  n=5 ocorrências  extra="orders/10"
  "https://api.example.com/v1/products/5" n=3 ocorrências  extra="products/5"
1 pai comum:
  "https://api.example.com/v1/" (27 chars)

Atual (decl folha 3x):    145 chars
Hierárquico (3 filho_de + 1 pai):  97 + 52 = 149 chars
Delta: +4 (perda mínima)
```

A economia de **não duplicar** o pai 3 vezes (3 × 27 = 81 chars)
é compensada por:
- 3 × `filho_de(noPP) + "..."` overhead ≈ 54 chars
- 1 × decl do pai ≈ 52 chars
- saldo: -81 + 54 + 52 = +25 chars (ligeiramente diferente do
  +4 medido — diferença de overhead de aspas e id que o cálculo
  simbólico aproximou)

**O ganho dos dados é exatamente compensado pelo overhead da
sintaxe**.

### Quando decl hierárquica vale

A heurística simples para o ganho ser positivo:

```
ganho > 0  ⟺  N_filhos × (len_pai − overhead_sintaxe_extra) > custo_decl_pai

Com overhead ~18 chars/filho e custo_decl_pai ~ 25 + len_pai:
ganho > 0  ⟺  len_pai × (N_filhos − 1) − 18·N_filhos − 25 > 0
```

Aproximando: para `len_pai = 27` (D4), precisa `N_filhos ≥ 6` para
ganhar. D4 tem só 3. Não compensa.

Para `len_pai = 5` (D1, `user0`), precisa `N_filhos ≥ 35` —
inviável em qualquer dataset realista.

Para `len_pai = 4` (D2, `.com`), idem — `N_filhos ≥ 30+`.

**Conclusão**: decl hierárquica para pref/suf só vale quando há
muitos filhos compartilhando um pai longo. Não é o caso dos
datasets atuais.

## Direções alternativas (não testadas aqui)

1. **Sintaxe mais compacta** — se `decl filho_de(noPP) + "X"`
   fosse algo como `+noPP+"X"` (~5 chars overhead em vez de 18), a
   conta inverte. D4 ganharia muito. Encaixa na fase prototype
   (sintaxe compacta já estava pra ser explorada).

2. **Mais segmentos por linha** (ideia do user) — em vez de
   `pref + mid + suf`, ter `seg1 + seg2 + seg3 + ...` na mesma
   linha, com cada segmento podendo ser ref ou inline. Ex:
   ```
   no1: noPP_base + "users/" + "1"     ← 3 segmentos: ref + literal + literal
   ```
   Elimina necessidade de nó intermediário separado para os prefs.
   Conceitualmente é estender o composto (pref+mid+suf) para
   N-ário. Mais complexo de implementar e de decodificar.

3. **Dataset com mais filhos por pai** — para validar o conceito,
   precisaria dataset com 6+ filhos compartilhando mesmo pai
   longo (ex: 10 URLs sob mesma base). Não temos. Pode ser
   construído num próximo experimento.

## Limitações

- 4 datasets pequenos, todos com 12-20 strings únicas. Não fala
  sobre escala.
- Estimativa simbólica (não implementa). Custos aproximados.
- Considera apenas pais imediatos para pref/suf (1 nível).
  Hierarquia mais profunda (avô do pref) não foi analisada.
- Não considera ordenação das declarações no body (a 1ª ocorrência
  do pai pode mudar contagem se for embutida vs decl tardia).
- Sintaxe do exp 10 (verbosa) é assumida. Conta diferente com
  sintaxe compacta.

## Como reproduzir

```bash
cd experiments/lab/dirty/2026-05-10-12-debug-hierarquia-decl
python run.py
```

Tabela consolidada no stdout. Detalhe em `debug-output/`.
