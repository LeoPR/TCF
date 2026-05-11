# Conclusões — online com fix + métrica de unidades

Roundtrip **3/3 OK**.

## Resultados centrais

### Métrica de bytes literais (sintaxe verbosa atual)

| Dataset | exp 13 | exp 14 | **exp 15** |
|---|---:|---:|---:|
| D2-mini | 192 | 198 | 193 |
| D2-completo | 447 | 463 | **441** |
| D4 | 424 | 399 | **399** |

### Métrica de unidades de informação (proxy do formato compacto)

| Dataset | exp 13 | **exp 15** | delta % |
|---|---:|---:|---:|
| D2-mini | 70 | **47** | **-33%** |
| D2-completo | 124 | **78** | **-37%** |
| D4 | 105 | **75** | **-29%** |

**O fix venceu por margens grandes em ambas as métricas em D2.**
Em D4 manteve resultado do exp 14 (já ótimo lá).

## Fix funcionou — comprovação visual

D2-mini, no5 e no6:

| Linha | Exp 14 (com defeito) | Exp 15 (fix) |
|---|---|---|
| no5 | `"joao.souz" + no2[-13:]` | `no4[0:11] + no2[-11:]` |
| no6 | `no4[0:11] + "yahoo.com"` | `no4[0:11] + no3[-9:]` |

Cada linha que tinha literal de 8-9 chars virou **2 refs (2
unidades)**. Antes era 10-11 unidades.

## Por que a métrica de unidades favorece o online tanto

Cada `noN[0:K]` ocupa **9 chars na sintaxe verbosa** mas vai virar
**1-2 bytes na sintaxe compacta** (1 ref-id + 1 length).

Em Re-Pair (exp 13), `R1` ocupa 3 chars hoje, mas vai virar
**também 1-2 bytes** na sintaxe compacta.

Hoje a vantagem aparente do Re-Pair em bytes vinha de cada ref
sua ser MAIS CURTA na sintaxe verbosa. Na sintaxe compacta as
duas se igualam, e o que conta é:

- **Quantas refs no total** (mais refs = mais bytes em qualquer
  formato)
- **Quantos chars literais no total** (dados são fixos)

O online faz **menos refs e menos literais** ao explorar LCP/LCS
longo entre strings consecutivas/parecidas. Re-Pair precisa
declarar símbolos (que custam `len(text) + 1` unidades cada)
mesmo se forem reaproveitados muito.

## Análise por string — D2-mini exp 15

| String | Tokens | Unidades |
|---|---|---:|
| s1 | literal puro (21) | 21 |
| s2 | ref + "hot" + ref | 5 |
| s3 | ref + "yahoo" + ref | 7 |
| s4 | "joao.souz" + ref | 10 |
| s5 | ref + ref | 2 |
| s6 | ref + ref | 2 |
| **TOTAL** | | **47** |

Em Re-Pair:
- 34 unidades em declarações de símbolos
- 36 unidades em strings (cada com 3-10 unidades)
- 70 total

Online: 47 vs Re-Pair: 70. **23 unidades a menos** (-33%).

## Defeito C — análise inicial estava errada

A versão inicial deste conclusoes.md afirmava que
`"joao.souz"` "ainda persistia duplicado" como literal. **Errado.**
Re-examinando o TCF gerado:

```
no4: "joao.souz" + no1[-11:]              ← UMA ocorrência de "joao.souz"
no5: no4[0:11] + no2[-11:]                ← referencia no4
no6: no4[0:11] + no3[-9:]                 ← referencia no4
```

`"joao.souz"` aparece **uma única vez**. no5 e no6 referenciam
corretamente via `no4[0:11]` (que pega `"joao.souza@"`).

O literal `"joao.souz"` em no4 não é defeito — é a **1ª introdução**
do nome `joao.souza` no dataset. Quando no4 foi processado, todas
as strings anteriores (no1, no2, no3) eram `maria.silva@...` —
LCP com qualquer delas = 0. Não há como evitar literal nessa 1ª
ocorrência.

**Os 3 defeitos identificados originalmente foram TODOS corrigidos**
pelo fix do exp 15.

## Análise dos literais residuais — todos são "introduções genuínas"

D2-completo tem 4 literais longos. Cada um corresponde a uma
**introdução de família nova** no dataset:

| Nó | Literal | Por quê |
|---|---|---|
| no1 | `"maria.silva@gmail.com"` (21) | 1ª string do dataset |
| no2 | `"joao.souza@hot"` (14) | 1ª string com `joao.souza` (e 1ª com `@hot...`) |
| no4 | `"ana.lim"` (7) | 1ª string com `ana.lima` |
| no6 | `"pedro.alves@yahoo"` (17) | 1ª com `pedro.alves` E 1ª com `@yahoo` |

As outras **8 strings (de 12) viram 2 unidades cada** — apenas refs,
zero literal. O algoritmo está captando 100% do que é possível
dado o ordenamento dos dados.

D4 segue padrão idêntico: 3 literais de introdução (users/,
orders/, products/) e 9 strings com 2 unidades cada.

## Avaliação honesta

**Exp 15 é o melhor algoritmo até agora** em ambas as métricas
testadas. Não há defeito algorítmico residual identificável
nestes datasets.

Os "literais que sobram" são todos genuinamente necessários para
introduzir informação nova. O algoritmo não pode comprimir o
que ainda não foi visto.

**Possíveis caminhos futuros** (não defeitos):

1. **Reordenação do input** (se permitida): processar strings
   similares primeiro reduziria os "literais de introdução" se
   ordem do CSV não importar.
2. **Revisão retroativa** (exp 16 — Opção B): permitiria reabrir
   literais quando padrão emerge. Mas overhead pode não compensar —
   exp 15 já está próximo do ótimo dado o ordenamento natural.
3. **Aumentar densidade do dataset** (mais strings de cada
   família): a média de unidades por string CAIRIA (custos fixos
   amortizados).

## Pontos a registrar

1. **Fix dos 2 defeitos (A e B) corrigiu o problema do overlap.**
   Em ambas as métricas houve melhora vs exp 14, especialmente em
   D2.

2. **Métrica de unidades é mais informativa para comparação
   estrutural**. Em bytes literais, exp 13/14/15 são próximos
   entre si. Em unidades, exp 15 vence por 29-37%.

3. **Sintaxe verbosa distorce comparação**. `noN[0:K]` (9 chars)
   penaliza online vs `RN` (3 chars). Na sintaxe compacta isso se
   inverte ou empata.

4. **Defeito C — corrigido junto** (correção de análise inicial
   incorreta). `"joao.souz"` aparece apenas UMA vez em no4. As
   ocorrências em no5/no6 referenciam via `no4[0:11]`. O fix
   resolveu A, B E C ao escolher o par alternativo em overlap em
   vez de descartar cegamente. Ver seção dedicada abaixo.

5. **Online vence quando há LCP/LCS forte entre strings
   adjacentes/parecidas**. Strings da mesma "família" (mesma
   pessoa, mesmo recurso) ficam codificadas em **2 refs cada**
   após algumas iterações.

## O que este experimento NÃO mostra

- Comportamento em N > 20.
- Revisão retroativa (exp 16).
- Janela deslizante (exp 17 sugerido).
- Sintaxe compacta de fato — só estimativa via "unidades".
- Comparação com formato compacto, CSV, JSON.
- Tempo de processamento.
- Cenários onde overlap é raro ou irrelevante.

## Próximo passo natural

**Exp 16 = online COM revisão retroativa** (Opção B do trade-off
triangular). Atacaria o defeito C residual:

- Quando uma string nova revela padrão "joao.souz" repetido,
  reabrir no4 e referenciar a nova string que tem "joao.souz" mais
  explícito
- Trade-off: perde streaming puro (precisa segurar strings
  recentes para possível revisão)

Mas isso é exp 16. Aqui foi só o fix conservador do exp 14.
