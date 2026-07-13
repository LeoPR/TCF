# Resultado — P4: def-level+kind fecha presença na forma regular

**[probatório]** `run.py` valida RT (oráculo semântico) antes de qualquer byte.
Contra-prova: `artifacts/04-rt-counterproof.txt`.

## Contra-exemplo (R1 refutado)

Kind **só por folha** perde a estrutura: `{}` e `{"b": {}}` geram o MESMO stream
(`absent`,`absent`) na folha `b.c` — o decode reconstrói as duas linhas iguais.
`artifacts/01-r1-counterexample.txt`. Mesma classe do achado do lab-irmão (`null=index`
pós-stringificação): **a informação estrutural precisa existir no símbolo, não ser
deduzida depois**.

## R2 (def-level+kind) — passa

Um símbolo por ocorrência: `cut@i` (a cadeia quebrou no elemento `i`) OU kind terminal
(`null`/`nan`/`pos_inf`/`neg_inf`/`false`/`true`/`str`/`int`/`num`). As 4 linhas do
killer viram `cut@0` / `cut@1` / `null` / `nan` — distintas e RT-exatas. Perfis com
cadeias opcionais + especiais, ragged com especiais e 100 linhas regulares: RT True.
Consistência é checável no decode (folhas sob o mesmo objeto compartilham o prefixo:
uma quebra acima ⇒ todas quebram no mesmo ponto; divergência = wire malformado, fail-loud).

## Bytes (estimativa declarada, após RT)

| perfil | folhas | símbolos de marca | b4-est | payload | V per-instance |
|---|---:|---:|---:|---:|---:|
| opt-chain-specials (5 linhas) | 2 | 10 | 5 B | 8 B | 159 B |
| ragged-arrays-specials (5) | 1 | 5 | 2 B | 10 B | 111 B |
| mixed-regular-100 | 3 | 300 | 150 B | 647 B | 4346 B |

Em dado REGULAR o schema amortiza no header e os streams ficam pequenos — o custo
por-instância do V (que repete estrutura em cada linha) domina. Coerente com a
observação do owner: a forma regular "tem quase tudo" via header; **as nuances (tipos,
presença, especiais) viajam nos streams**.

## Leitura consolidada (o quadro das formas)

| forma | semântica | onde vence | estado |
|---|---|---|---|
| **A per-instance** (V-tag) | kind por ocorrência no wire | árvore irregular / doc único | confirmada (lab 1835) |
| **B-HDOM** | domínio inteiro tipado no header | coluna low-card densa (k≤16) | provada sintética (lab 1921) |
| **B-HK** | kinds no header + payload TCF | coluna alta-card, especiais esparsos | provada sintética (lab 1921) |
| **R2 def+kind** (este) | HK generalizado p/ topologia (presença fundida no símbolo) | forma REGULAR c/ opcionais/ragged | provada sintética |
| C escapada | léxico no canal string | — | refutada-parcial (lab 1835) |
| D dict interno | código fixo | — | bloqueada (decisão de formato) |

**Invariante que emergiu dos 3 labs**: o **kind tipado é a semântica** (fixa,
sobrevive a qualquer forma); a **representação do stream de kinds é regime-dependente**
(tag por instância / domínio no header / def+kind por coluna) — candidatos que competem
no `min()`, exatamente a filosofia FLOOR do TCF. Nenhuma forma nova redefine o valor;
todas transportam os MESMOS kinds do DatasetH.

## O que falta para P5 (decisão de gramática)

1. Alfabeto de símbolos e sua grafia na gramática `#TCF.8H` (textual? packed b4 =
   V2-L?); profundidade >7 (b4 estoura) → b8 ou separar def de kind.
2. Repetition levels completos: objeto-em-array e array-de-array na forma regular
   (peça seguinte; o per-instance já cobre o irregular).
3. Dado real (gate): tudo até aqui é sintético — validar em documento aninhado real
   antes de `confirmada-empirica` (checklist anti-incidente 2026-05-21).
