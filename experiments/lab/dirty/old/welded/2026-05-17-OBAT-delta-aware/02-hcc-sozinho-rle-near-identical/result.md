# Resultado — Tentativa 02 (HCC sozinho seq-RLE)

**Data**: 2026-05-17
**Estado**: concluido
**Plano**: [README.md](README.md)
**Detalhes por dataset**: [summary.md](summary.md) e `outputs/<ds>/`

## Resumo executivo

| Metric | Valor |
|---|---|
| RT byte-canonical | **8/8 OK** |
| Bytes totais (D11a-h) baseline | 958 |
| Bytes totais fork | 745 |
| Reducao total | **-213 bytes (-22.2%)** |
| Datasets com ganho | 7/8 |
| Maior ganho individual | D11d -33.6% (-37 bytes) |
| Sem ganho (esperado) | D11b (bordas, sem padrao consecutivo) |

## Tabela por dataset

| Dataset | canon | fork | Δ bytes | Δ % | runs detectados |
|---|---:|---:|---:|---:|---|
| D11a (dias)         | 87  | 84  | -3   | -3.4%  | 2 runs (lines 3-5 Δ=+1; lines 8-9 Δ=+5) |
| D11b (bordas)       | 173 | 173 | 0    | 0.0%   | 0 (esperado) |
| D11c (mensal)       | 109 | 78  | -31  | -28.4% | 1 run (lines 3-9, Δ=+1) |
| D11d (datetime min) | 110 | 73  | -37  | -33.6% | 1 run (lines 3-10, Δ=+1) |
| D11e (datetime mes) | 121 | 90  | -31  | -25.6% | 1 run (lines 3-9, Δ=+1) |
| D11f (ms)           | 115 | 78  | -37  | -32.2% | 1 run (lines 3-10, Δ=+1) |
| D11g (us)           | 120 | 83  | -37  | -30.8% | 1 run (lines 3-10, Δ=+1) |
| D11h (ns)           | 123 | 86  | -37  | -30.1% | 1 run (lines 3-10, Δ=+1) |

## Exemplos visuais

### D11d (datetime/min) — body antes/depois

Antes (110 bytes):
```
\2026-\05-\15 \09:*\0*\0*:\00
1~2\1*4
5\2*4
5\3*4
5\4*4
5\5*4
5\6*4
5\7*4
5\8*4
5\9*4
1\1*3,4
1~15,6,4
16,7,4
```

Depois (73 bytes):
```
\2026-\05-\15 \09:*\0*\0*:\00
1~2\1*4
*8+1|5\2*4
1\1*3,4
1~15,6,4
16,7,4
```

8 linhas compactadas em 1. RT byte-exato.

### D11a (dias) — 2 runs detectados

Antes (87 bytes, 12 linhas body):
```
...
8\7
8\8
8\9
7\2*\2
7~13\3
15\4
15\9
...
```

Depois (84 bytes, 10 linhas body):
```
...
*3+1|8\7        ← run 1: 3 linhas Δ=+1
7\2*\2
7~13\3
*2+5|15\4       ← run 2: 2 linhas Δ=+5 (savings 0 mas detectado)
...
```

Run 2 nao economiza bytes (savings 0) mas mantem RT correto. Pode-se
adicionar guarda `if savings <= 0: skip` em refinamento futuro.

## Revisao da hipotese Q15

> **Q15 (registrada antes)**: Se um no e' quebrado onde tem
> diferenca, talvez o unico esforco depois seja verificar se essa
> diferenca faz parte da estrutura anterior e como otimiza-la.
> OBAT pode estar quase pronto.

**Status: confirmada (forte evidencia empirica).**

Argumentos:
1. OBAT canonical (intocado) emitiu tokens onde 8 linhas consecutivas
   (D11d 3-10) ja' tinham estrutura identica — `P(1,15) + L(digit) + S(1,3)`
2. HCC canonical materializa esses tokens em body lines
   estruturalmente identicas — `5\digit*4` — mas com literal diferente
3. Fork de HCC pos-processou body lines, detectou o padrao
   estrutura-identica + literal-aritmetico, compactou em `*8+1|5\2*4`
4. Reducao de 33.6% no body, **sem alterar OBAT**

OBAT ja' faz a quebra no lugar certo. A unica intelig-encia adicional
necessaria vive no HCC: reconhecer que tokens consecutivos com mesma
estrutura + literais em sequencia aritmetica podem ser agrupados.

## Implicacao pra Pre / OBAT / HCC

Antes desta tentativa, conjecturava-se que talvez OBAT precisasse:
- emitir token novo (`TokRefDelta`) com metadata relativa
- saber tipo via dica generica
- decidir se "cabe" emitir delta

Esta tentativa mostra que **nada disso e' necessario** para o caso
de datasets D11a-h:
- OBAT permanece type-agnostic, intocado
- Pre nao precisa nem existir
- HCC sozinho extrai todo o ganho

A linha cinzenta entre OBAT e HCC, pelo menos pra este caso, **nao
existe**. HCC pega todo o trabalho.

## Onde o ganho NAO aparece

**D11b (bordas)**: 0 runs detectados, 0 bytes economizados.
- Cada linha cruza uma borda diferente (fim de mes, leap year, ano)
- Estruturas de token variam — sem 2 linhas consecutivas com mesmo
  esqueleto
- Esperado. Nao e' falha do detector — e' caracteristica do dataset.

Conclusao: **delta-awareness so' ajuda quando ha' cadencia regular**.
D11b confirma que dados realmente sem padrao consecutivo nao ganham
nada — o que e' coerente com o framework.

## Bug-fix posterior (2026-05-17 pos sub-exp 04)

Durante sub-exp 04 (H-DA-07), descoberto bug no detector
`compare_for_seq` deste fork: exigia TODAS posicoes dentro de
escape-digit runs em diffs. Quebrava casos onde literal multi-digit
muda so' um char (`\10` → `\11` diff so' posicao 3, mas run inteira
e' int 10 → 11).

**Fix aplicado em `hcc_fork.py`** (este sub-exp): relaxar checagem
pra "todas diffs DENTRO de runs + delta unico entre runs".

**Impacto neste sub-exp**: zero. OBAT canonical (usado em t02) nao
produz literais multi-digit (so' digitos isolados). Bytes mantidos
em 745 total apos re-execucao. **Sem regressao.**

**Impacto em sub-exp 04**: dobrou o ganho (-46 → -93 bytes), pois
OBAT fork shape-preserve produz literais "10", "11", "12" exatamente
o caso que o bug bloqueava.

## Otimizacoes ORTOGONAIS observadas mas NAO cobertas

Durante a revisao dos bodies fork, foi identificada otimizacao
**independente** de delta-awareness que esta tentativa nao cobre:

**Escape automatico** (H-ED-01 a H-ED-04 no
[`../../../notas/roadmap-hipoteses.md`](../../../notas/roadmap-hipoteses.md)).

Exemplo: body line 1 do D11a fork e' `\2026-\0*\5*-*\1*\5` — 7
backslashes. Como linha 1 nunca tem refs (primeira declaracao),
em principio o escape `\` poderia ser deduzido pelo decoder.
Estimativa: ~50-60 backslashes na linha 1 dos 8 datasets se
todos fossem deduziveis.

**Por que NAO foi incluida aqui**:
- Ablacao: misturar duas otimizacoes confunde qual deu qual ganho
- Tentativa 02 ja' fechada com hipotese isolada (Q15)
- Escape-deduction merece dirty lab proprio (ver roadmap Pacote 2)

**Quem percebeu**: user (apontou apos ver
`outputs/D11a-datas-dia/2-body-fork.tcf` line 1). Assistant havia
focado em delta e nao flagueou os escapes como concern independente.

## Limitacoes conhecidas

1. **Run de 2 linhas com savings <= 0**: detector emite a compactacao
   mesmo quando nao economiza (D11a run 2). Mais cosmetico que
   problematico. Refinamento: adicionar `if savings <= 0: skip`.

2. **Transicao de cardinalidade (\\9 -> \\10)**: detector quebra o
   run quando o literal muda de tamanho. Esperado — runs param na
   transicao 9->10 em todos os datasets D11. Caso pos-transicao
   (linhas 11-13 em D11d/h/etc) tem estruturas diferentes, nao
   formam novo run.

3. **Detector funciona em escape-digit positions apenas**: nao
   detecta delta em refs ou separadores. Coerente com a sintaxe
   atual; estender (delta em refs) exigiria sintaxe maior.

4. **Δ != +1 sem ganho real**: a sintaxe `*N+delta|<tmpl>` aceita
   qualquer delta, mas runs com Δ grande (ex: +5) provavelmente nao
   economizam porque sao tipicamente curtos (2 linhas).

## Implicacao pras tentativas 03 e 04

Tentativa 02 sozinha:
- Cobre D11a (parcial), D11c-h (forte)
- Nao cobre D11b (esperado)

**Tentativa 03 (OBAT com dica `byte_window`)** ainda faz sentido?
- Argumento pro: validar que dica generica e' viavel/util (Q16, Q17)
- Argumento contra: ganho de bytes ja' esta extraido pelo HCC
- **Recomendacao**: rodar mas com expectativa reduzida — exploratoria
  pra validar o conceito de dica generica, nao pra ganhar bytes
  adicionais

**Tentativa 04 (OBAT relativo + HCC integrado)** ainda faz sentido?
- Argumento pro: testar a integracao tripartite end-to-end
- Argumento contra: HCC sozinho ja' extrai o ganho; OBAT relativo
  acrescenta complexidade sem ganho mensuravel adicional nesses
  datasets
- **Recomendacao**: re-avaliar apos tentativa 03. Pode-se descobrir
  cenarios onde HCC sozinho falha e OBAT relativo ajuda — por
  exemplo, datasets com cadencia irregular mas comparativa relativa
  detectavel

## Decisao registrada

Q15 confirmada empiricamente. **HCC sozinho extrai a maior parte do
ganho de delta-awareness em D11a-h**. OBAT permanece intocado.

Proximo passo: avaliar se tentativa 03 ainda agrega valor
(provavelmente como exercicio conceitual, nao como ganho de bytes).

## Welding pra src/tcf?

**Nao ainda**. Esta tentativa e' POC dirty. Pra welding canonical:
1. Validar em mais datasets (D1-D9 atuais, datasets reais sem cadencia
   forcada)
2. Refinar sintaxe (`*N+delta|` pode ter casos de borda)
3. Decidir se merece nome (`M8.B-seq-rle`?) ou se vira default
4. Documentar formalmente em `docs/algorithms/HCC.md`

Pos-welding eventual, OBAT seguiria intocado.

## Arquivos gerados

```
02-hcc-sozinho-rle-near-identical/
├── README.md          (plano original, mantido como referencia)
├── hcc_fork.py        (encoder + decoder com seq-RLE)
├── run.py             (executor)
├── summary.md         (tabela rapida)
├── result.md          (este doc — analise final)
└── outputs/<ds>/
    ├── 1-body-canonical.tcf
    ├── 2-body-fork.tcf
    ├── 3-diff-canonical-vs-fork.md
    ├── 4-seq-runs.md
    └── 5-rt-status.txt
```
