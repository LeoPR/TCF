# Conclusões — debug bidir em D2

## Achado central

A árvore Patricia reverse **detectou a hierarquia de sufixos
completa** em D2 (e em D2-mini): `.com` → `mail.com` →
`@hotmail.com` ou `@gmail.com` → ... → folhas individuais. **Mas
a fase de decomposição usa apenas o pai imediato da folha**, o que
em D2 leva a sufixos muito específicos (`a@hotmail.com`,
`a@gmail.com`) que entram em overlap com o prefixo forward
(`maria.silva@`, etc), forçando descarte de um dos lados.

A consequência: composição prefix+mid+suf nunca ativa em D2.

Esse comportamento foi reportado no exp 08 como "heurística de
overlap descarta um lado em toda string". O debug deste experimento
mostra **por que**: não é que não haja sufixo mais raso compartilhado —
existe (`mail.com`, `.com`). É que a função de decomposição não o
busca; pega o pai imediato e processa overlap.

## D2-mini — passos detalhados

### Construção forward (3 iterações)

1. Escolheu `"maria.silva@"` (len 12, count 3). Absorveu 3 strings
   de maria.
2. Escolheu `"joao.souza@"` (len 11, count 3). Absorveu 3 strings
   de joao.
3. STOP: só 2 top-level (`maria.silva@`, `joao.souza@`), sem
   prefixo comum significativo.

Árvore final forward:
```
no7 = "maria.silva@"     no1, no2, no3 (folhas com gmail/hotmail/yahoo.com)
no8 = "joao.souza@"      no4, no5, no6 (folhas com gmail/hotmail/yahoo.com)
```

Plana, 2 níveis. Esperado.

### Construção reverse (5 iterações)

1. Escolheu `"moc.liamtoh@a"` (len 13, count 2). Absorveu 2 strings
   `@hotmail.com`.
2. Escolheu `"moc.liamg@a"` (len 11, count 2). Absorveu 2 strings
   `@gmail.com`.
3. Escolheu `"moc.oohay@a"` (len 11, count 2). Absorveu 2 strings
   `@yahoo.com`.
4. **Escolheu `"moc.liam"` (len 8, count 2)**. Top-level agora são
   3 nós-pai (`moc.liamtoh@a`, `moc.liamg@a`, `moc.oohay@a`). Os 2
   primeiros começam com `"moc.liam"`. Absorveu como filhos do novo
   pai `moc.liam`.
5. **Escolheu `"moc."` (len 4, count 2)**. Top-level agora são
   `moc.liam` (novo pai) e `moc.oohay@a`. Ambos começam com
   `"moc."`. Absorveu.

Árvore final reverse:
```
no11 = "moc."
  no9 = pai(no11) + "oohay@a"             # @yahoo.com (lateral)
    no3, no6 (folhas)
  no10 = pai(no11) + "liam"               # mail.com
    no7 = pai(no10) + "toh@a"             # @hotmail.com
      no2, no5 (folhas)
    no8 = pai(no10) + "g@a"               # @gmail.com
      no1, no4 (folhas)
```

**A hierarquia natural `.com → mail.com → @hotmail.com/@gmail.com`
está toda capturada.**

### Decomposição (a perda)

Para `maria.silva@hotmail.com` (len 23):

| Fonte | Pai imediato escolhido | Texto |
|---|---|---|
| fwd | no7 | `"maria.silva@"` (len 12) |
| rev | no7 | `"a@hotmail.com"` (len 13, sufixo natural) |

Overlap: 12 + 13 = 25 > 23. Descarta pref (mais curto).
Resultado: `pref="" + mid="maria.silv" + suf="a@hotmail.com"`.

**Avôs disponíveis na cadeia reverse** (não usados):
- avô 1 = no10 = `"mail.com"` (len 8). 12 + 8 = 20 < 23 → cabe.
- avô 2 = no11 = `".com"` (len 4). 12 + 4 = 16 < 23 → cabe.

Qualquer um dos avôs permitiria composição. O melhor (em termos de
bytes economizados pela maior cobertura) seria `mail.com` — len 8,
count 4 (aparece em 4 das 6 strings: as 2 de hotmail + as 2 de
gmail).

### Análise de cobertura (substrings que aparecem em ≥ 2 únicas)

Top 5 por `len * count`:

| len | count | ganho | substring |
|---:|---:|---:|---|
| 12 | 3 | 36 | `maria.silva@` ← capturado em fwd |
| 11 | 3 | 33 | `joao.souza@` ← capturado em fwd |
| 11 | 3 | 33 | `maria.silva` |
| **8** | **4** | **32** | **`mail.com`** ← capturado em rev mas não usado em decomp |
| 7 | 4 | 28 | `ail.com` |

`mail.com` tem **maior count que qualquer prefixo forward** (4 vs
3). Mas a decomposição não a usa porque preferiu o pai imediato.

## D2-completo — comportamento similar

Forward: 4 prefixos (`maria.silva@`, `joao.souza@`, `pedro.alves@`,
`ana.lima@`). 1 nível de profundidade.

Reverse: 5 níveis de profundidade.

```
no20 = "moc."                                       # .com (todas 12)
  no18 = "@yahoo.com" (via "oohay@")                # 4 yahoo
  no19 = "mail.com" (via "liam")                    # 8 (4 hotmail + 4 gmail)
    no14 = "@hotmail.com" (via "toh@")
      no13 = "a@hotmail.com" (via "a")
    no17 = "@gmail.com" (via "g@")
      no15 = "a@gmail.com" (via "a")
```

Mesmo padrão: hierarquia rica capturada, decomposição usa só pai
imediato. Mesmo overlap. Mesma composição zero.

## Pontos a registrar

1. **A árvore Patricia reverse já produz a hierarquia desejada**.
   Não há bug na construção. `mail.com`, `.com`, `@hotmail.com`
   etc. todos viram nós internos na árvore reverse.

2. **A limitação está na fase de decomposição** em
   `arvore_bidir.py` do exp 08:
   ```python
   def _prefix_de(s, fwd_arvore, fwd_str_to_eid):
       no = fwd_arvore[eid]
       if no.pai_id is None:
           return ""
       return texto_completo(no.pai_id, fwd_arvore)   # ← só pai imediato
   ```
   Mesma coisa para `_suffix_de`. A função sobe **um nível** e
   para. Não inspeciona a cadeia de avôs.

3. **Para D2, o pai imediato reverse é sempre o mais específico**
   (`a@hotmail.com`, `a@gmail.com`, `a@yahoo.com`), que tem len
   ~11-13 chars e quase sempre causa overlap com o prefixo forward.

4. **Avôs disponíveis** seriam quase sempre melhores para
   composição em D2:
   - `@hotmail.com` (len 12, descendo de `mail.com` + `toh@`)
   - `@gmail.com` (len 10)
   - `@yahoo.com` (len 10)
   - `mail.com` (len 8) — partilhado por hotmail+gmail
   - `.com` (len 4) — universal

5. **A heurística de escolha entre avôs disponíveis** não está
   resolvida. Opções:
   - Mais longo que ainda evite overlap (greedy local)
   - Maior cobertura global (count alto, mesmo se mais curto)
   - Ganho líquido por bytes (Fraenkel-Mor-Perl 1983)

6. **O experimento 09 não modifica algoritmo**. Apenas mostra que
   a oportunidade existe e onde implementar a melhoria.

## O que este experimento NÃO mostra

- Implementação de decomposição com cadeia de avôs.
- Comparação de bytes entre a decomposição atual e uma hipotética
  que usasse avôs.
- Heurística entre diferentes avôs disponíveis.
- Comportamento em outros datasets (D1, D3, D4). D2 foi escolhido
  porque foi o único onde a composição falhou no exp 08.
- Validação de roundtrip — este experimento não produz encoding,
  só relatório textual.

## Próximo passo natural

Experimento 10: implementar decomposição que **escolhe o melhor
nível** na cadeia de avôs do reverse (e também do forward, por
simetria), maximizando a chance de composição válida (sem overlap)
com maior cobertura. Validar em D2 e nos outros datasets para ver
se não degrada onde já funcionava.
