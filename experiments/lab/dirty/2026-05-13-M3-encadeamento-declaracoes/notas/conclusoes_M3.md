# Conclusoes Macro M3 — encadeamento de declaracoes

## Resultado consolidado

| Sintaxe | D1-D4 total | DE7 |
|---|---:|---:|
| M1.E (base) | 676 | 119 |
| M3.A (no compartilhado) | 676 | 119 |
| M3.B (encadeamento) | 676 | 119 |

**Net 0 em todos os datasets**, incluindo o desenhado para
favorecer M3 (hierarquia profunda).

RT 14/14 OK em todas as combinacoes.

## Diagnostico estrutural

### Funcao de eficiencia do alias

Para substring de Lt chars com Lr chars na serializacao M1.E,
usada em R linhas:

```
Net_absoluto  = R * (Lr - 2) - (4 + Lt)
Net_encadeado = R * (Lr - 2) - (5 + len(P) + len(ext))
```

Encadeamento compensa absoluta quando: `len(ext) < Lt - 1 - len(P)`.

### Por que Lr e' pequeno nos datasets

O algoritmo do exp 16 produz pref/suf com refs **sequenciais** no
namespace global de frags. M1.E (range `a..b`) comprime essas
sequencias para 4 chars tipicamente — independente de quantos
frags cobrem.

Exemplo DE7 eid 2 (`https://api.example.com/v1/users/002`):
- Tokens: P(1, 35) + L('2')
- P(1, 35) herda 5 frags consecutivos do eid 1: [1, 2, 3, 4, 5]
- M1.E serializa: `1..5` = 4 chars

Para substituir por `&1=texto_35_chars`:
- Custo decl absoluta: 4 + 35 = 39
- Economia/uso: 4 - 2 = 2
- Para R = 2: net = 4 - 39 = -35

R precisaria ser >= 20 para compensar — fora do regime D1-D4 + DE7.

## Comparacao com Lab 20-21 (`old/`)

Lab 20 antigo reportou ganho substancial em hierarquia profunda
(C7 -72% vs literal). A diferenca metodologica explica:

- **Lab 20 antigo**: NAO tinha range. Refs viravam `1,2,3,4,5`
  (9 chars). Alias `&1` substituia por 2 chars. Economia/uso = 7.
- **M3 atual**: M1.E ja' comprime para `1..5` (4 chars).
  Economia/uso = 2. Margem desaparece.

**M1.E ocupa estruturalmente o nicho que M3 tentaria atacar.**
Range e' mais barato (sem custo de declaracao) e cobre o caso
geral de refs sequenciais.

### Onde M3 ainda poderia compensar (teorico, nao testado)

1. Algoritmo base SEM range (regressao — nao faz sentido)
2. Substrings com R >> 10 (datasets reais grandes, fora do dirty)
3. Cadeias profundas (4+ niveis) com pais ja declarados (DE7 so'
   tem 3 niveis)
4. Refs nao-sequenciais (raras no regime exp 16)

Nenhuma dessas condicoes ocorre nos datasets sinteticos do dirty.

## Decisao M3

**Fechar M3.** Macro mapeou dimensao "agrupamento de nos" via 2
micros (M3.A absoluto, M3.B encadeado). Ambos dominados
estruturalmente por M1.E no regime testado.

Hipotese do user (nos compostos) **confirmada como mapeada** mas
sem ganho liquido. Resultado matematicamente coerente — agrupamento
sintatico interno (M1.E) compete com agrupamento via alias (M3)
pelo mesmo recurso (refs sequenciais).

## Estado final dirty lab v0.6

Macros completos:

| Macro | Foco | Dimensoes mapeadas | Ganho liquido sobre baseline |
|---|---|---|---|
| M1 | marcacao local | 6 (A, A', B, C, D, E) | -10.6% (M1.E vs M1.A) |
| M2 | redundancia entre linhas | 1 (alias tupla) | -1.5% (D1 D2 D3 D4) |
| M3 | encadeamento de declaracoes | 2 (compartilhado, encadeado) | 0 |

**Notas matematicas relevantes**:
- M1.E + escape escopo: funcao de eficiencia 4/(2K-1) → 0 para K
  grande (refs sequenciais)
- M2.A: funcao R · (Lt-2) - (4+Lt), escala linear com R
- M3: dominado por M1.E porque ataca o mesmo recurso (refs
  sequenciais)

**Conclusao da fase dirty**: explorada redundancia local (M1),
redundancia entre linhas (M2) e redundancia em declaracao de no
fonte (M3). Nenhuma dimensao adicional do escopo tabular textual
ficou nao mapeada.

## Proximos passos

1. **Reorganizar dirty/** em M0, M0.5, Mobsolete conforme combinado
2. **Ir para prototipo** com candidatos confirmados:
   - Base: algoritmo exp 16
   - Sintaxe: M1.E (range + escape escopo)
   - Camada opcional: M2.A (aliases de tupla)
   - Cleanup: remover `[/]` delimitadores, adicionar header formal
3. **M3 fica registrado como dimensao mapeada sem ganho** — pode
  ser revisitado se algoritmo base mudar ou se dados reais
  revelarem regime distinto
