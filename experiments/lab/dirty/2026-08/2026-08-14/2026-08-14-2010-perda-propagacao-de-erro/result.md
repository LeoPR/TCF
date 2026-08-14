# Resultado — a perda por cinco lentes

3000 linhas reais de `online-retail` (preço **e** quantidade, para haver um produto de verdade),
5 lentes × 5 precisões × 2 métodos, **0 falhas**. Orienta, não fecha.

## A tabela

Arredondando `UnitPrice`. Baseline 5053 B.

| d | método | bytes | red% | **por valor** | **soma** | **receita** | rec/linha |
|---:|---|---:|---:|---:|---:|---:|---:|
| 2 | ambos | 5053 | 0,0% | 0% | 0% | 0% | 0% |
| 1 | ingênuo | 4090 | 19,1% | **66,67%** | 0,18536% | 0,25024% | 66,67% |
| 1 | maior-resto | 4156 | 17,8% | 66,67% | **0,00029%** | 0,16606% | 66,67% |
| 0 | ingênuo | 2710 | 46,4% | 100% | 0,51048% | **2,46778%** | 100% |
| 0 | maior-resto | 2710 | 46,4% | 100% | **0,00067%** | 2,05257% | 100% |

`d=4,3,2` são no-op: `UnitPrice` já tem ≤2 casas. O primeiro corte real é `d=1`.

## As cinco leituras

1. **A soma dilui em três ordens de grandeza.** Erro de **66,67%** num valor vira **0,185%** na
   soma — os erros têm sinal e se cancelam. E o maior resto leva a **0,00029%**, ~640× melhor
   que o ingênuo.
2. **O produto NÃO dilui.** O erro relativo passa **intacto** pelo multiplicador: 66,67% no
   preço é 66,67% na receita daquela linha. Só o *total* da receita dilui, e menos que a soma
   simples (0,25% contra 0,185%), porque a quantidade re-pondera.
3. **Preservar a soma custa bytes.** A `d=1` o maior resto gasta **4156 B contra 4090** — ele
   cria valores distintos que o ingênuo colapsaria. A soma exata não é de graça.
4. **Preservar um agregado pode degradar outro.** O maior resto é ~640× melhor na soma e só
   1,5× melhor na receita — ele redistribui o resíduo **sem saber o multiplicador**. Nenhum
   vocabulário da literatura cobre esse conflito entre agregados.
5. **O formato continua lossless sobre os arredondados** em 10/10 casos. A perda é do round,
   não do TCF — e essa checagem é justamente a que faltou no PoC de junho.

## A lente que quebra: diferença de próximos

`margem = venda − custo`, com custo = 97% da venda (margem estreita de propósito):

| d | erro nos **operandos** | erro na **margem** | trocaram de **sinal** |
|---:|---:|---:|---:|
| 3 | 0,000% | 7,4% | 0 / 500 |
| 2 | 0,000% | 85,2% | 0 / 500 |
| 1 | 11,111% | **825,9%** | **203 / 500** |

**Quarenta por cento das margens trocaram de sinal** — lucro virou prejuízo. E note a `d=2`:
erro **zero** nos operandos e ainda **85%** na margem, porque o custo tinha mais casas que a
venda e só ele foi truncado.

Pelo **lema de Sterbenz** a subtração em si é **exata**; o erro veio inteiro dos inputs já
arredondados. O fator de amplificação é `|x| / |x−y|`, ilimitado.

## O que isto orienta

**A pergunta "posso arredondar 1%?" é malformada.** A mesma perda é:

| operação | o que acontece |
|---|---|
| soma / média | **dilui** (erros com sinal se cancelam) — e o maior resto zera |
| produto | **passa intacto** por linha; o total re-pondera |
| diferença de próximos | **amplifica sem limite**, e troca de sinal |

Logo o contrato de perda **não pode ser um número só**. O vocabulário mínimo precisa declarar
*sob qual operação* a promessa vale — os eixos `quantum` / `abs` / `rel` / `agg-exact` mais o
qualificador `mode`, registrados na nota irmã.

E há uma consequência direta de **formato**: decidir *"gravar a diferença ou deduzi-la do par"*
deixa de ser questão de bytes e vira **cláusula do contrato de erro**. Se a derivada é deduzida,
a tolerância tem de ser declarada **nela** e propagada para trás, apertando os pais. Isso toca
`materializacao-minimal` e o DERIVED-DROP (`H-LOSS-02`).

## Ressalva de honestidade

Estes números **não** são os que eu publiquei antes deste lab (medidos em scratchpad, com outra
amostragem: 28,57% / 0,54% / 506% / 162-de-500). **Valem os desta tabela** — são os que têm
input, wire e contra-prova gravados. A nota irmã foi corrigida.
