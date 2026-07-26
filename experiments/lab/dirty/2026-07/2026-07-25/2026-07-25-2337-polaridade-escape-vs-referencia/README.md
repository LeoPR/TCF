# 2026-07-25-2337 — Polaridade do escape: literal × referência

Ideia do owner, retomando uma análise antiga: no corpo, **dígito nu é referência** e o literal
numérico paga `\` (1 B por corrida de dígitos). Em coluna cheia de número isso é caro — o wire
que ele apontou tem **998 barras invertidas em 8863 B**.

> *"dependendo das condições, se mediria se tem mais escapes que referências, aí só trocar.
> na verdade é sobre os elementos nativos vs os índices das referências — o que tiver mais,
> obviamente troca."*

```
NORMAL   \168116  = literal   ·   1   = referência ao fragmento 1
FLIP     168116   = literal   ·   \1  = referência ao fragmento 1
```

## O ganho é real, e grande onde você esperava

| coluna | NORMAL | FLIP | Δ |
|---|---:|---:|---:|
| ruído 1e6, n=1000 | 7854 | 6856 | **−998 B** |
| cpf-like, n=200 | 3800 | 3000 | **−800 B** (−21%) |
| uuid-hex, n=200 | 2663 | 2200 | **−463 B** |
| preços, n=200 | 1175 | 1027 | **−148 B** |
| ruído 1e6, n=100 | 793 | 693 | **−100 B** |

## E perde onde o texto domina — por isso é `min()` por coluna

| coluna | NORMAL | FLIP | Δ |
|---|---:|---:|---:|
| emails, n=200 | 2095 | 2316 | **+221 B** |
| texto sem dígito | 718 | 743 | **+25 B** |

7 de 10 colunas encolhem, 2 crescem. Exatamente o que você descreveu: **o que tiver mais,
troca** — e nunca um default novo.

## Dois achados que só apareceram por materializar

### 1. A estimativa por contagem estava errada

Antes de prototipar eu contei escapes e referências e previ **−38 B** para emails. O real é
**+221 B**. A contagem tratava `1~2` como *uma* referência, mas no flip **cada corrida
numérica precisa do próprio escape** (`\1~\2`). Contagem não é medição.

### 2. BLOQUEADOR: o flip nem sempre é expressável

`B-datas-n200` falhou a involução — 74 ocorrências. O motivo é estrutural:

```
normal : 1\2-*\0*\2     ref(1) seguido do literal "2"
flip   : \12-*0*2       \12 lê a corrida INTEIRA = ref(12)   ✗
volta  : 12-*\0*\2      não retorna ao original
```

**O escape é guloso sobre a corrida de dígitos.** Em NORMAL, uma referência nua termina no `\`
seguinte, então `1\2` é inequívoco. Em FLIP, `\1` colado num literal-dígito colapsa — não há
como escrever os dois adjacentes.

O problema é **espelhado**: NORMAL também não expressa literal-seguido-de-referência (`\2` +
`1` viraria `\21`); o encoder simplesmente nunca produz essa forma. O flip trocaria qual das
duas adjacências é proibida — e a proibida no flip **ocorre** em dado real (datas).

Detectei a adjacência com um contador independente, e ele **casa exatamente** com a falha de
involução (assert no `run.py`): 74 nas datas, 0 nas outras nove.

## Estado: a ideia é boa, o esquema simples não fecha

Antes de soldar, falta resolver a adjacência. Caminhos possíveis (nenhum medido ainda):

- **marcador auto-delimitado** para a referência no modo flip (algo que não consuma a corrida
  seguinte), em vez de reusar o `\` guloso;
- **restringir o flip** às colunas sem a adjacência — mede-se e desiste quando aparece (é o
  que o detector já faz), aceitando cobrir 9 de 10;
- **separador explícito** entre referência e literal adjacentes, que custaria 1 B nas
  ocorrências e provavelmente anularia o ganho justo onde ele é pequeno.

O flag caberia no índice 7 (o char de modo), que hoje já é lido para a tag `n` — mas isso é
detalhe de grafia, não o bloqueador.

## Rodar

```
python run.py     # 10 casos; regenera evidências + result.md
```

`outputs/<ID>-corpo-normal.tcfp` e `<ID>-corpo-flip.tcfp` são os dois corpos lado a lado;
`<ID>-wire.tcf` é o wire REAL de hoje. **Não toca `src/tcf`.**
