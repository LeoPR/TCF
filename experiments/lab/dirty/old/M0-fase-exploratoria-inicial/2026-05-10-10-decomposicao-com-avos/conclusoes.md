# Conclusões — decomposição com cadeia de ancestrais

Roundtrip **4/4 OK** em todos os datasets.

## Achado central (semântica vs bytes)

A mudança da decomposição entregou exatamente o que o exp 09
identificou como faltante: **acessar ancestrais (avô, bisavô) das
folhas em vez de só o pai imediato**. Em D2:

- exp 08: 0 strings compostas (overlap obrigatório com pai imediato).
- exp 10: **12/12 strings compostas**, usando `mail.com` (avô na
  cadeia reverse) e `.com` (bisavô) como sufixos compartilhados.

Mas a contagem de bytes ref+dados em D2 **aumentou +45 bytes**. A
captura semântica adicional não se traduziu em economia de bytes
no formato atual.

| Métrica | exp 08 | exp 10 |
|---|---:|---:|
| Compostas em D2 | 0/12 | 12/12 |
| Bytes ref+dados em D2 | 610 | 655 |
| Bytes em D1, D3, D4 | iguais | iguais |

**Diagnóstico**: a sintaxe verbosa atual (`noN: pref:noP + "X" + suf:noQ`)
adiciona ~12 chars por linha (a 2ª ref + o segundo `+`) que não são
compensados pela economia em middle (~6 chars/linha). Em datasets
onde uma direção sozinha já cobre bem, manter "só pref" ou "só suf"
é menos bytes — mas perde a informação estrutural de qual era o
prefix/suffix compartilhado.

## Trecho TCF — D2 do exp 10

```
no1:  pref:(no2=decl folha "maria.silva@") + "g"     + suf:(no3=decl folha "mail.com")
no4:  pref:(no5=decl folha "joao.souza@")  + "hot"   + suf:no3
no6:  pref:no2                              + "hot"   + suf:no3
no7:  pref:(no8=decl folha "ana.lima@")    + "g"     + suf:no3
no9:  pref:no5                              + "g"     + suf:no3
no10: pref:(no11=decl folha "pedro.alves@") + "yahoo" + suf:(no12=decl folha ".com")
no13: pref:no8 + "hot"   + suf:no3
no14: pref:no5 + "yahoo" + suf:no12
no15: pref:no11 + "g"   + suf:no3
no16: pref:no2  + "yahoo" + suf:no12
...
no17: pref:no8  + "yahoo" + suf:no12
no18: pref:no11 + "hot"   + suf:no3
```

Cada linha tem 3 elementos: pref + middle + suf. Pref reaproveitado
de 4 nomes únicos. Suf reaproveitado de 2 sufixos comuns
(`mail.com`, `.com`). Middle é o discriminador mínimo (1-5 chars).

## Decomposição de D2 — análise por caso

| String | pref | mid | suf | nível suf na cadeia |
|---|---|---|---|---|
| `maria.silva@gmail.com` | `maria.silva@` | `g` | `mail.com` | avô |
| `joao.souza@hotmail.com` | `joao.souza@` | `hot` | `mail.com` | avô |
| `pedro.alves@yahoo.com` | `pedro.alves@` | `yahoo` | `.com` | bisavô |
| `ana.lima@hotmail.com` | `ana.lima@` | `hot` | `mail.com` | avô |
| ... | | | | |

8 strings (hotmail + gmail) usam `mail.com` (avô — len 8). 4 strings
(yahoo) usam `.com` (bisavô — len 4). Em todos os 12 casos a
composição cabe sem overlap.

Por que yahoo cai em `.com` e não em algum sufixo intermediário?
Na árvore reverse, yahoo tem cadeia `.com → @yahoo.com → a@yahoo.com`.
Para `pedro.alves@yahoo.com` (21 chars):
- pref candidatos: `pedro.alves@` (12)
- suf candidatos: `a@yahoo.com` (11), `@yahoo.com` (10), `.com` (4)

Combinações sem overlap:
- (12, 0): cobertura 12
- (0, 11): cobertura 11
- (0, 10): cobertura 10
- (0, 4): cobertura 4
- (12, 4): cobertura 16 ✓
- (12, 10): 22 > 21 overlap
- (12, 11): 23 > 21 overlap

Melhor: (12, 4) — `pedro.alves@` + `yahoo` + `.com`. Cobertura 16.
A heurística escolheu corretamente.

## D1, D3, D4 — comportamento mantido

### D1 (emails 1 domínio)

Mantém 10/10 compostas com `pref="user00"` ou `pref="user0"` e
`suf="@gmail.com"`. Bytes iguais ao exp 08.

Cadeia na árvore reverse D1 é rasa (`@gmail.com` é único pai
top-level útil), então não há avô para ganhar. Cadeia forward
tem `user0` como avô de `user00`, mas o caso útil (user010 cair em
`user0`) já era resolvido no exp 08.

### D3 e D4 (URLs)

Mantêm 100% das strings com só pref. Reverse não detecta sufixo
comum entre IDs (`1`, `2`, ..., `10` invertidos não compartilham
prefixo significativo). A heurística não força composição quando
não há suf candidato válido. Bytes iguais ao exp 08.

## Pontos a registrar

1. **Estrutura informática correta** (objetivo principal do dirty):
   12/12 strings de D2 agora têm decomposição semântica completa
   (pref + suf compartilhados). Antes era 0/12.

2. **Bytes não acompanham semântica** com a sintaxe atual: +45
   bytes em D2. Esse é o **gap esperado** para a fase prototype.

3. **Robustez confirmada**: D1, D3, D4 mantêm comportamento idêntico
   ao exp 08. A melhoria na decomposição **não degrada** onde já
   funcionava.

4. **Heurística greedy simples funciona**: percorrer cadeia +
   escolher maior cobertura sem overlap é suficiente para os casos
   "óbvios" (como D2). Não há otimização de ganho líquido por bytes
   — fica para depois.

5. **Decisão registrada para fase prototype**: a sintaxe de encode
   precisa ser pensada para amortizar composição. Possíveis caminhos
   (não implementados aqui): marcadores mais curtos (`p:N` em vez
   de `pref:noN`), inferência de tipo pelo contexto (eliminar
   `pref:` e `suf:` quando ordem deixar claro), grupo de
   sufixos compartilhados num bloco. Cabe à fase prototype escolher.

6. **Comparação ponto-a-ponto registrada**:

   | Dataset | exp 08 | exp 10 | delta |
   |---|---:|---:|---:|
   | D1 | 494 | 494 | 0 |
   | D2 | 610 | 655 | +45 |
   | D3 | 372 | 372 | 0 |
   | D4 | 505 | 505 | 0 |

   3/4 datasets sem mudança numérica; D2 com perda em bytes mas
   ganho semântico estrutural.

## O que este experimento NÃO mostra

- Comportamento em N > 20 ou cardinalidade > 12.
- Heurística "ganho líquido em bytes" — só usamos cobertura.
- Sintaxe compacta — apenas a verbosa do exp 08.
- Datasets com forward profundo (hierarquia de 3+ níveis em
  pref) — D1 tem 2 níveis pequenos. Datasets com forward
  hierárquico poderiam ativar mais o lado pref da heurística.
- Composições com 3+ ancestrais válidos onde escolher entre
  combinações exige tie-break mais sofisticado.
- Comparação com formato compacto, CSV, JSON ou HTFC (front coding
  bucketed) — baseline natural sugerido pela literatura para a fase
  prototype.
- Validação contra inputs corrompidos.

## Próximos passos sugeridos

Para futuros experimentos do dirty (curto prazo):
- Dataset com forward hierárquico (ex: `ACME-FIN-USER-01..05`,
  `ACME-OPS-USER-01..05`, `TECH-FIN-USER-01..05`) — para exercitar
  cadeia de pref e ver se a heurística faz a escolha esperada.
- Dataset onde 2-3 avôs reverse e 2-3 avôs forward coexistem —
  estressar a busca da melhor combinação.

Para a fase prototype futura (registrado também em README.md):
- Reorganização da sintaxe (compacta).
- Comparação com baseline HTFC.
- Decisão sobre fusão de árvores em grafo (decidido aqui que é
  overkill para o regime atual, mas re-avaliar em escala maior).
- Heurística de escolha por "ganho líquido em bytes" em vez de
  cobertura.
