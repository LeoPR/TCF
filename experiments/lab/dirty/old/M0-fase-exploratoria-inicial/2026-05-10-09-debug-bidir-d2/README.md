# 09 — debug bidir em D2

## Princípio / motivação

Não é experimento de implementação nova. É **instrumentação** dos
algoritmos do exp 08 (Patricia bidirecional + decomposição), para
entender em detalhe o que acontece no D2 — onde a composição
prefix+suffix não ativou e onde havia suspeita de padrões
intermediários não capturados (`mail.com`, `.com`).

Toca o ponto registrado no exp 08: D2 termina sem strings
compostas, e algumas strings ficam com `suf="a@hotmail.com"` ou
`suf="a@gmail.com"` quando talvez houvesse sufixo mais raso e
compartilhado (`mail.com` ou `.com`) com melhor cobertura
estrutural.

## Propósito

Responde a uma pergunta:

1. **Comportamento**: por que D2 produz composição zero? Existem
   padrões compartilhados não capturados? Onde está o
   estreitamento — na construção da árvore Patricia ou na fase de
   decomposição?

Não é experimento de comparação de bytes. Não modifica algoritmo.
Apenas instrumenta e analisa.

## Comparação

- **Compara com**: [08-patricia-bidir-composto](../2026-05-10-08-patricia-bidir-composto/).
- **É comparável?** Não numericamente. É experimento **paralelo
  de inspeção** sobre o mesmo dataset (D2) e o mesmo algoritmo do
  08. Não produz encoding; produz relatório textual.
- O que se produz: log iteração-a-iteração + decomposição por
  string + análise de padrões.

## Cenários e valores possíveis

Dois datasets:

| Nome | Strings | Conteúdo |
|---|---:|---|
| D2-mini | 6 | 2 nomes × 3 domínios (subset didático) |
| D2-completo | 20 (12 únicas) | mesmo do exp 06/07/08 |

Para cada: log completo das iterações do Patricia forward, depois
do Patricia reverse, depois decomposição por string única, depois
tabela de substrings comuns com `count ≥ 2`.

`min_prefixo = 3` (fixado; threshold já testado em 08, não fez
diferença).

## Resultado observado — achado principal

**A árvore Patricia reverse SIM capturou a hierarquia natural de
sufixos**, incluindo `mail.com` como intermediário. **A fase de
decomposição é que usa apenas o pai imediato da folha**, perdendo
os níveis intermediários.

### Árvore reverse de D2-mini (texto invertido — sufixos naturais)

```
no11 = "moc."                                       (= ".com")
  no9 = pai(no11) + "oohay@a"                       (-> "a@yahoo.com")
    no3, no6 (folhas)
  no10 = pai(no11) + "liam"                         (-> "mail.com")
    no7 = pai(no10) + "toh@a"                       (-> "a@hotmail.com")
      no2, no5 (folhas)
    no8 = pai(no10) + "g@a"                         (-> "a@gmail.com")
      no1, no4 (folhas)
```

Hierarquia natural detectada: `.com` → `mail.com` → `a@hotmail.com`
ou `a@gmail.com` → folhas. **A informação semântica está toda lá.**

### Árvore reverse de D2-completo

```
no20 = "moc."
  no18 = "@yahoo.com" (via "oohay@")
    folhas yahoo
  no19 = "mail.com" (via "liam")
    no14 = "@hotmail.com" (via "toh@")
      no13 = "a@hotmail.com" (via "a")
        folhas hotmail
    no17 = "@gmail.com" (via "g@")
      no15 = "a@gmail.com" (via "a")
        folhas gmail
```

5 níveis de profundidade. `.com` no topo, `mail.com` no segundo
nível, depois `@hotmail.com`/`@gmail.com`, depois `a@*`, depois
folhas individuais.

### Decomposição usa apenas o pai imediato

Exemplo de `maria.silva@hotmail.com` (D2-mini):

```
fwd: pai imediato = no7 = "maria.silva@" (len=12)
rev: pai imediato = no7 = "a@hotmail.com" (len=13)   ← pai mais profundo da cadeia
OVERLAP: 12 + 13 = 25 > 23 = len(s)
resolve: suf mais longo. Descarta pref.
FINAL: pref="" mid="maria.silv" suf="a@hotmail.com"
```

Se a decomposição olhasse os **avôs** da cadeia, poderia escolher:

- avô 1: `no7's parent = no10 = "mail.com"` (len=8)
- avô 2: `no10's parent = no11 = ".com"` (len=4)

Usando `mail.com` (avô) como suf:
```
pref="maria.silva@" (12) + mid="hot" (3) + suf="mail.com" (8) = 23 ✓
```

Cabe sem overlap! Composição ativaria.

Usando `.com` (bisavô) como suf:
```
pref="maria.silva@" (12) + mid="hotmail" (7) + suf=".com" (4) = 23 ✓
```

Também cabe. Múltiplas opções válidas.

A decomposição atual (do exp 08) escolheu o **pai imediato mais
longo** (`a@hotmail.com`), forçou overlap, descartou o pref. O
resultado é sub-ótimo em estrutura semântica (perde a partilha
`maria.silva@` com outras strings de maria).

### Resumo do achado

| Componente | Estado |
|---|---|
| Construção da árvore Patricia | **OK** — hierarquia profunda detectada |
| Fase de decomposição (em arvore_bidir.py do 08) | **Limitada** — usa só pai imediato; ignora avôs disponíveis |

Não é bug do algoritmo Patricia. É **escolha limitada** da
decomposição. Pode ser estendida em experimento posterior.

## Limitações

- Apenas D2 analisado (mini + completo). Não fala sobre outros
  cenários.
- Análise de "padrões não detectados" é manual no markdown; o
  output textual da tabela de substrings ajuda mas não é
  exaustivo.
- Não propõe nem implementa decomposição que olha cadeia de
  avôs. Apenas identifica que seria possível.
- Heurística para escolher entre avôs disponíveis também não está
  resolvida (mais longo? maior cobertura global? Fraenkel-Mor-Perl
  por ganho líquido?). Fica para experimento posterior.
- Logs textuais cresceram para 12-23 KB; difíceis de ler na
  íntegra. As partes essenciais estão extraídas neste README e
  em conclusoes.md.

## Como reproduzir

```bash
cd experiments/lab/dirty/2026-05-10-09-debug-bidir-d2
python run.py
```

Gera 2 arquivos em `debug-output/`:
- `D2-mini-debug.txt` (~13 KB)
- `D2-completo-debug.txt` (~23 KB)
