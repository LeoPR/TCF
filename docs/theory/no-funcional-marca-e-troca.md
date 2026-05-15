# No funcional — marca e troca (estudo)

**Data**: 2026-05-17
**Tipo**: nota teorica (direcao futura registrada)
**Origem**: observacao no D9 M10 output 2026-05-17 (linhas 11-17).

> **Status**: nao implementado. Para estudo + eventual experimento
> futuro. Relaciona-se com o item 6 do roadmap (slot variavel em
> wrapper) mas e' mais geral.

## Observacao motivante

D9 M8.A output tem 7 linhas seguidas com **mesma estrutura, parte
variavel no meio**:

```
17,9,5
17,10,5
17,11,5
17,12,5
17,13,5
17,14,5
17,15,5
```

Pattern: `17,X,5` onde X percorre {9, 10, 11, 12, 13, 14, 15}.

M8.A atual emite cada linha completa — ~7 chars × 7 = ~49 chars
para o conjunto.

## Ideia — no funcional (template node)

Em vez de emitir cada linha por completo, **declarar a estrutura
uma vez** e emitir apenas o que varia.

Sintaxe-sketch (apenas conceito):

```
no19=17,?=9,5      # 1a aparicao: define no19 com estrutura
                   # (17 fixo, ? slot variavel com valor 9, 5 fixo)
no19==10           # subsequente: trocar apenas o slot
no19==11
no19==12
no19==13
no19==14
no19==15
```

Decoder:
- 1a linha cria template `no19 = [17, SLOT, 5]` com SLOT=9.
- Linhas `no19==X` substituem SLOT por X e emitem a linha completa.

## Algebra rascunho

Para pattern `A,?,B` repetido R vezes (uma 1a aparicao + R-1 reusos):

- Sem template: R * len(`A,X,B`) ~ R * (len(A) + len(X) + len(B) + 2)
- Com template:
  - 1a: `noN=A,?=X,B` ~ 4 + len(N) + len(A) + len(X) + len(B) + 2 = len(N) + len(A) + len(X) + len(B) + 6 chars
  - Reusos: `noN==Y` ~ 4 + len(N) + len(Y) chars

Diff por reuso vs sem template:
- `noN==Y` (4+len(N)+len(Y)) vs `A,X,B` (len(A)+len(X)+len(B)+2)
- Save = (len(A)+len(B)+2) - (4+len(N))
- Para 2-char A e B (`17` e `5`) com 2-char N (`19`): save = (2+1+2) - (4+2) = 5 - 6 = **-1 chars**

Ou seja, pra slot pequeno **piora 1 char por reuso**. Overhead de
`noN==` mata o ganho.

**Save real ocorre quando**:
- A, B sao longos (varios chars cada)
- OU multiplos slots compartilhados
- OU template aparece em MUITOS reusos (R grande)

D9 caso especifico: pattern `17,X,5` curto, save negativo se aplicado
ingenuamente. Precisa otimizar sintaxe (no minimo, omitir `==` e usar
algo como bare value `,X`).

## Sintaxe mais economica (variante)

Em vez de `noN==Y`, emitir apenas `Y` no contexto de no funcional
ativo:

```
no19=17,?=9,5
10                 # implicito: usar no19 com slot=10
11
12
13
14
15
```

Aqui cada reuso vira ~2 chars (o valor do slot). Save:
- Sem template: 7 chars
- Com template implicito: 2 chars
- Save por reuso: 5 chars

Para R=7 reusos: 6 save de 5 = 30 chars - overhead da 1a (~10 chars
def) = ~20 chars economizados.

Mas:
- Decoder precisa saber "esse numero solto = slot do template ativo"
- Ambiguidade com refs normais (numero solto na linha tambem indica
  alias use)
- Resolucao: marker explicito (`@10`, `*10`, etc.) ou bloco
  delimitado.

## Conexao com sequencias

Caso particular D9: slot vai 9, 10, 11, ..., 15 — sequencia
consecutiva. Compactavel adicionalmente como **range** (`9..15`).

Sintaxe imaginada:
```
no19=17,?=9..15,5     # define template + slot percorre 9 a 15
```

Decoder gera 7 linhas automaticamente. **Maxima compressao** para
este caso. Mas e' um caso particular (RLE de slot).

Generalizando: slot percorre **lista** explicita:
```
no19=17,?,5:[9,10,11,12,13,14,15]
```

Mais flexivel (lista nao precisa ser sequencia).

## Pontos a estudar

1. **Detector**: como detector encontra esses padroes? Olhar linhas
   adjacentes para diff em UMA position central, mantendo bordas
   iguais. Diferente do detector atual (que olha sub-tuplas em uma
   refs piece).
2. **Multi-slot**: linhas com MAIS de uma position variavel —
   `17,X,5,Y,8` onde X e Y variam independentemente.
3. **Slot tipado**: range vs lista vs livre. Diferentes overheads.
4. **Sintaxe sem ambiguidade**: marker explicito para slot value vs
   bare ref.
5. **Interacao com composicional**: slot em template pode conter
   composicao? E.g., `no19=17,?,5` onde slot e' `a~b`?
6. **Pre-tx delta + template**: combinar — slot percorre delta+base
   em vez de literal.

## Relacao com roadmap

- Item 6 do roadmap (slot variavel em wrapper) e' subcaso desta
  ideia. Wrapper = template `head?tail` com slot no meio. No
  funcional generaliza pra qualquer arranjo de fixos+slots.
- Item 4 (decomposicao pos-detector) compartilha tematica: detectar
  estrutura comum em padroes ja' emitidos.

## Direcao para experimento futuro

Antes de implementar, definir:
- (a) Sintaxe definitiva (marker, posicao de slot, etc.)
- (b) Detector (alguma forma de "linha-diff" entre linhas adjacentes)
- (c) Algebra completa (com varios casos de R, lens)
- (d) Comparacao com baseline M8.A em datasets onde aparece (D9
  obviamente; talvez D5, D7 tambem).

**Nome candidato pra macro futuro**: M11-no-funcional-template ou
similar. Nao priorizar agora (welding pro src/ vem antes).

## Conexoes

- [[roadmap-hipoteses.md]] — item 6 (slot variavel em wrapper)
- [[../2026-05-17-M9-stress-adversarial/notas/conclusoes_M9.md]] —
  observacao original do limite D9
- [[../2026-05-17-M10-datasets-elevation/]] — onde a observacao
  surgiu (D9 output)
