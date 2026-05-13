# Mesa: multi-sort + cabeçalho de seleção por coluna

**Dataset:** o mesmo da mesa anterior (`../2026-05-07-mesa-compressao-maxima/00-dataset.md`)
**Foco:** duas hipóteses lógicas que podem fixar quando RLE/DICT vale a pena.

---

## H1 — Multi-sort burro: ordenar por mais de uma coluna

Na mesa anterior, sort por uma coluna deixava as outras em ordem boa só por
correlação. Hipótese: **sort com 2+ chaves pode arrastar mais colunas para
runs RLE**, mesmo que isso fragmente a ordem secundária.

Combinações a testar:

| Ordem | Por quê pode ganhar |
|---|---|
| (produto, valor) | produto perfeito + valor parcialmente regrupado dentro de produto |
| (valor, produto) | valor perfeito + produtos parcialmente concatenados entre groups de valor |
| (produto, valor, qty) | adiciona qty como terceiro desempate |
| (valor, produto, qty) | mesma ideia, valor primeiro |
| (nome, produto)  | sort por nome (que não correlaciona) — controle negativo |
| (produto, nome)  | nome fica scrambled mas produto limpo — controle |

Pergunta: existe uma combinação multi-chave que **vence** sort de chave única?
Se sim, em que situação? Se não, por que o ganho marginal é zero/negativo?

---

## H2 — Cabeçalho explícito de seleção por coluna

Hipótese independente. Em vez do decoder inferir o esquema de cada coluna por
varredura inicial, o arquivo declara explicitamente. Proposta do usuário:
soma binária por coluna como bitmask.

### Codes binários propostos

| Code | Significado |
|---|---|
| `000` | literal (sem nada) |
| `001` | RLE |
| `010` | dict |
| `011` | RLE + dict (dict implícito + RLE em refs) |
| `100`–`111` | reservados (delta? prefix? outras) |

Notação do header para 4 colunas:
```
# L: 010, 011, 000, 010
```
ou — versão compacta com vírgulas-repetição:
```
# L: 010, 011,, 010      ← terceira coluna vazia = "mesmo da anterior"
```

Variantes de notação a considerar:
- 1 char por code (`L`, `R`, `D`, `B`)
- run-length no próprio header (`3D L` = 3 dicts seguidos de 1 literal)
- híbrida (`# L: DDLD` para arquivos pequenos)

### Perguntas

1. O header **economiza bytes** ou só serve como contrato explícito?
2. Quando vale a pena? Datasets pequenos (overhead é >% do total) vs grandes
   (overhead é desprezível).
3. Auto-detecção pelo decoder seria suficiente? Em que casos não?
4. O header pode declarar **operação composta** que o L0/L1/L2/L3 monolítico
   atual não consegue exprimir.

---

## Plano de execução

| Arquivo | Conteúdo |
|---|---|
| `01-multisort.md` | Aplicar 6 combinações de sort + C11-híbrido |
| `02-cabecalho.md` | Design e teste do bitmask header |
| `03-conclusoes.md` | Comparar tudo + responder se há "regra" estável |

Bytes aproximados (mesma metodologia da mesa anterior). Foco em **estrutura**.
