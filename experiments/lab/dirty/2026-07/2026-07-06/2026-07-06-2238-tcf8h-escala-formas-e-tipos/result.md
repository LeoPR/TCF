# Resultado — escala de formas + decisão de tipo A/B/C (Ciclo 1b) [probatório]

Números: `artifacts/` (`python run.py`). Decisão do owner: "medir os dois, decidir com número".

## Thread 1 — TIPO: A-explícita × B-dedução × C-híbrida (`01-tipos-A-B-C.txt`)

| caso | A bytes/tags/RT | B bytes/tags/RT | C bytes/tags/RT |
|---|---|---|---|
| T1-escalares-tipados | 68/4/**OK** | 62/0/**LOSSY** | 65/1/**OK** |
| T2-array-tipado | 52/2/OK | 47/0/OK | 47/0/OK |
| T3-aninhado-misto | 127/5/OK | 119/0/OK | 119/0/OK |
| NUM-numeros-dominam | 41/3/OK | 38/0/OK | 38/0/OK |
| AMB-strings-ambiguas | 51/1/**OK** | 50/0/**LOSSY** | 52/2/OK |

### Decisão (do número)

- **C-híbrida = default.** Lossless como A; deduz número/bool de graça, tag só a colisão (string-ambígua
  → `s`, null → `n`). Nos casos onde números dominam (T1/T2/T3/NUM) **C ≤ A** e é lossless.
- **REGRA de crossover**: `custo_A = #não-string`; `custo_C = #mal-deduzidos` (strings-ambíguas + null).
  **C < A  ⟺  (não-strings bem-deduzidos) > (strings-ambíguas).**
  Em **AMB** (2 strings ambíguas `cep`/`flag` > 1 número) **C=52 > A=51** — **A vence lá**. Não é "C sempre".
- **B pura descartada** como default: corrompe em silêncio — `"01310"`→1310 (perde zero à esquerda e o tipo),
  `"true"`→bool, null→`""`. É exatamente o problema self-description (igual ao hex).
- **A = fallback**: tudo taggeado, simples/auditável, e **menor** quando strings-ambíguas dominam.

> Conexão hex (T-OPT-INFERENCE): tipo e base numérica têm a **mesma forma** — default deduzível + marcador
> só na colisão. C-híbrida do tipo = o análogo do hex-default com dedução.

## Thread 2 — FORMA: escala de borda (`02-formas-fronteiras.txt`)

| forma | resultado | meta / motivo |
|---|---|---|
| SH1 aninhamento fundo `{a:{b:{c:{d:1}}}}` | **RT-OK** | `#TCF.8H a{b{c{d` (omit-closes come os 3 `}}}`) |
| SH2 array vazio `{nome,tags:[]}` | **RT-OK** | `#TCF.8H nome,tags[` (nome bare, tags sem colunas → `[]`) |
| SH3 chave ausente `[{a,b},{a}]` | **FRONTEIRA** | `KeyError b` — tabela **não-retangular** |
| SH4 null-em-array-misto `[{x:1},{x:null}]` | **FRONTEIRA** | `ValueError int('')` — coluna de **tipo misto** |

- **SH1/SH2 fecham RT** → funcionalidade estendida de graça (aninhamento arbitrário + array vazio).
- **SH3/SH4 = fronteiras honestas**: o modelo colunar supõe retângulo homogêneo. Chave-ausente precisa de
  **presença** (bitmap/sentinela); null-em-array-misto precisa de **nullable** (tag por-coluna `i?` ou máscara).
  Ambas são **família do link posicional** (peça 10/11, rep/def levels do Dremel) → **Ciclo 1c**.

## Saída pro 1c

As 4 fronteiras convergem: **chave-ausente**, **null-em-coluna-tipada**, **array-em-array**, **N:N** — todas
pedem um canal de **presença/posição** que o retângulo homogêneo não tem. 1c caracteriza (não
necessariamente resolve em v0): o que é presença (bitmap), o que é nullable (máscara), o que é rep/def level.

## Limites (v0)

- Coluna homogênea ainda é premissa (SH4 quebra); a decisão A/B/C é por-coluna.
- Amostras minúsculas + 5 casos de tipo; escala real (synthetic/real-world) e o custo de C em árvore grande
  ficam pro fechamento do Ciclo 1 / convergência.
