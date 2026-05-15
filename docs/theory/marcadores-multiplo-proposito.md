# Sintaxe composicional + revisao critica de M5

**Data**: 2026-05-14
**Tipo**: nota transversal
**Origem**: user apontou tres problemas em M5/M4.C1':
  (1) M2.A foi mantido com preambulo (regressao);
  (2) M4.C1' usa marker open-close (`~tupla~`) quando open-only basta;
  (3) (mais geral) markers entre refs deveriam ser OPERADORES
       composicionais: `,` sem criar ref, `~` criando novo ref
       auto-nomeado. Hierarquia natural emerge.

## Critica 1 — M2.A preambulo desnecessario

### Erro

M2.A importado para M5 sem refatorar. Mantem preambulo
`$N=tupla\n` no topo do body + uso `$N` em linha.

### Algebra do M2.A inline

```
M2A_preambulo_savings = R*(Lr-1-len(N)) - (Lr+3+len(N))
M2A_inline_savings    = R*(Lr-1-len(N)) - (Lr+1)
Diff = 2 + len(N) bytes/alias a favor de inline
```

Para len(N)=1: **3 bytes/alias** economia.

D1 com M2.A preambulo: 141 bytes (2 aliases).
D1 com M2.A inline projetado: ~135 bytes.
M4.C1' D1: 138 bytes.

**Reverte conclusao M5**: M2.A inline pode empatar ou ficar abaixo
de M4.C1' atual em alguns datasets. A "dominacao algebrica" do M5
estava enviesada pela forma com preambulo.

## Critica 2 — M4.C1' marker open-close redundante

### Erro

M4.C1' usa `~tupla~` (open + close). O close nao faz trabalho que
o separador natural seguinte (`*`, `,`, `\\n`) ja' nao faria.

Conceitualmente: subquebra (boundary de alias) e' **mesma natureza**
que quebra de string normal entre peers. A quebra ja' existe; marker
so' precisa anotar "esse grupo e' reusavel".

### Algebra do M4.C1' open-only

```
M4C1p_atual_savings    = R*(Lr-1-len(N)) - Lr - 1 + len(N)
M4C1p_open_only        = M4C1p_atual + 1 byte/alias
```

D1-D4 atuais usam 7 aliases. Economia projetada: 7 bytes (636 → 629).

## Critica 3 — sintaxe composicional (mais geral)

### Insight do user

Marker entre refs e' OPERADOR com semantica composicional:
- `,` entre refs: concat sem criar ref (efemero)
- `~` entre refs: concat **+ cria novo ref auto-nomeado**
- Reuso da composicao: apenas `N` (id), sem prefixo `&`

Alg16 ja' gera grupos de grupos naturalmente. Sintaxe expoe essa
hierarquia.

### Exemplo do user (ABCDEF)

Strings: ABCDEF, EF, CDEF, ABCDEF, CD

```
AB*CD*EF      # cria atoms: ref 1=AB, 2=CD, 3=EF (segmentação)
3             # usa ref 3 = EF
2~3           # usa refs 2 e 3 + cria ref 4 = CDEF
1,4           # usa refs 1 e 4 = AB+CDEF = ABCDEF
2             # usa ref 2 = CD
```

`2~3` simultaneamente:
- Decodifica como CD+EF = CDEF
- Cria ref 4 = CDEF para reuso

Line 4 `1,4` (3 chars) substitui `1,2,3` (5 chars) — save 2 chars.

### Algebra

Para composicao de K refs (Lr_inline chars) usada R vezes:

| Sintaxe | 1a aparicao | reuso | savings/reuso |
|---|---|---|---|
| M1.E | Lr_inline | Lr_inline | 0 |
| M4.C1' atual | Lr_inline + 2 | 1+len(N) | Lr_inline - 1 - len(N) |
| M4.C1' open-only | Lr_inline + 1 | 1+len(N) | Lr_inline - 1 - len(N) |
| **Composicional** | **Lr_inline** | **len(N)** | **Lr_inline - len(N)** |

Composicional economiza:
- 1 byte na 1a aparicao vs M4.C1' open-only
- 1 byte por reuso vs M4.C1' open-only

Total por alias R-uso: **R bytes/alias** vs M4.C1' open-only.

D1-D4 estimativa: 636 atual → ~615 composicional (~21 bytes).

### Binarizacao vs flat-chain

Para chain `1~2~3`:
- **Pairwise (binary, left-assoc)**: `1~2` cria ref 4 = AB+CD, depois `4~3` cria ref 5 = ABCDEF. 2 refs criados.
- **Flat-chain**: chain inteira cria 1 ref = ABCDEF.

Tradeoff: pairwise expoe niveis intermediarios (reusaveis); flat mais compacto. Escolha depende do que detector espera reusar.

Range `a..b` pode tambem auto-criar ref (caso particular de composicao por sequencia).

### Decisao M6 (2026-05-14)

Comecar com:
- **(p) pairwise**: cada `~` cria 1 ref (chain `1~2~3` cria 2 refs)
- **(s) range cria ref**: `a..b` auto-cria ref nomeado igual `a~a+1~..~b`

Caso particular flat-chain ou range-sem-ref ficam fora do M6 inicial.

### Extensao futura — nos pos-construcao (literal+ref composition)

User 2026-05-14: "posso criar o grupo BCD quando ele aparecer pra ser
agrupado, sem precisar ser antes". Composicao pode envolver
**literais novos + refs existentes**:

```
ABCDEFG
CD
BCD
DE
BCDE
```

Encoding (com nos pos-construcao):
```
AB*CD*EFG          # cria atoms 1=AB, 2=CD, 3=EFG (segmentacao gross)
2                  # ref 2 = CD
B~2                # NOVO LITERAL B + ref 2 = BCD; cria ref 4 = BCD
DE                 # novo literal DE (sem composicao)
4~DE               # ou 4,5 se DE virou atomo... depende do design
```

Vantagem: nao precisa super-segmentar line 1 pra expor 'B' como
atomo — cria atomo + grupo na hora que aparece.

Custo: parsing mais complexo (literal + ref + literal + ref...).
Detector mais dificil ("navegar nos nos pra achar padrao no padrao").

**Decisao**: registrado como direcao futura. Nao no M6. Talvez no
prototipo se a sintaxe simples mostrar gap relevante.

## Recalibracao das conclusoes M5

| Antes (M5) | Apos criticas 1+2+3 |
|---|---|
| M4.C1' atual dominante por 2+2*len(N) bytes/alias | Composicional domina M4.C1' por R bytes/alias |
| M2.A fora do prototipo | M2.A inline reentra como baseline; pode perder so' len(N) bytes vs M4.C1* mas e' ainda inferior a composicional |
| M4.C1' canonico para prototipo | **Composicional** e' o candidato real |
| Hierarquia: nao considerada | Vetor central — alg16 ja' tem hierarquia, sintaxe deve expor |

## Proximos passos

**M6 candidato** (a confirmar com user):

| Micro | Foco |
|---|---|
| M6.A | M2.A inline (refactor baseline; corrige regressao M5) |
| M6.B | M4.C1' open-only (refactor; -1 byte/alias) |
| **M6.C** | **Sintaxe composicional** (`~` cria ref, `,` nao) |

M6.C subsume M6.B; M6.B subsume forma `~tupla~`. M6.A subsume M2.A
com preambulo. Os tres podem coexistir como camadas comparaveis.

Detector M6.C precisa decidir `~` vs `,` por composicao — mesmo
problema do detector de M4.C1' mas com sintaxe mais limpa.

## Conexoes

- [[vetores-de-comparacao-alem-de-bytes.md]] — vetores nao-byte
  (velocidade, memoria, streaming) ainda a avaliar
- [[../../2026-05-14-M5-pilha-M2A-M4C1p/]] — M5 sob revisao
- [[comparacao-modular-camadas.md]] — pre-tx do prototipo
- [[quebra-de-linha-como-marcador.md]] — quebra como marker (analogia)
- [[2026-05-11-marcadores-compactos.md]] — possivel conexao (ver)
