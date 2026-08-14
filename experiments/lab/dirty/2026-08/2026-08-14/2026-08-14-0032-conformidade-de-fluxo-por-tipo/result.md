# Resultado — o int já percorre o mesmo caminho; falta uma peça e sobra uma assimetria

4 tipos × 5 regimes × 3 rotas, **0 falhas de round-trip** (comparado por `type()`). Este lab
não mede compressão — mede **conformidade de fluxo**.

## Eixo 1+2+4 — dispatch e mecanismo vencedor, por regime

| tipo | constante | duas-classes | com-nulo | progressão | baixa-card |
|---|---|---|---|---|---|
| **bool** | `b` / RLE | `b1258` / **denso** | `b2258` / **denso** | — | — |
| **int** | `n` / RLE | `nB1258` / bN | `n` / core | `n!!` / seq-RLE | `nB3258` / bN |
| **float** | `n` / RLE | `nB1258` / bN | `n!!` / core | `n!!` / seq-RLE | `nB3258` / bN |
| **str** | *(vazio)* / RLE | `B1258` / bN | *(vazio)* / core | `!!` / seq-RLE | `B3258` / bN |

**Int, float e str são idênticos em todos os regimes** — muda a tag, não o mecanismo. Essa é
a prova de que o fluxo é generalizado de fato, e não só na intenção.

**A única divergência é o bool**, e é a justificada: onde os outros usam bN, ele usa o
**denso**. A razão está escrita no código (`encoder.py:566`): *"`bool` NÃO entra [no bN]: o
denso b1/b2 tem domínio IMPLÍCITO e vence por construção"*. Não é rota própria — é **um
candidato a mais** no mesmo `min()`.

## Eixo 3 — o que a API faz com `nature`

| chamada | bool / int / float | str |
|---|---|---|
| single `nature=` | **recusa fail-loud** | processado, FLOOR recusou |
| single `nature_per_col=` | **sem efeito e SEM AVISO** | **recusa fail-loud** |
| multi `nature_per_col=` | recusa fail-loud | aceito e aplicado |
| `.8H` `nature_per_col=` | recusa fail-loud | aceito e aplicado |

Duas leituras:

1. **A peça que falta**: `nature=` é recusado em coluna tipada nas três rotas. É o *"entra
   int, spec int, devolve int"* que não existe — já sabido, agora com a forma exata da
   recusa em cada rota.
2. **A assimetria que sobra**: `nature_per_col=` em single-col é **recusado com mensagem**
   para string (*"aplica a multi-col; pra single-col use nature="*) e **silenciosamente sem
   efeito** para tipado. Mesma chamada sem sentido, dois tratamentos. É lacuna de
   uniformidade, não de funcionalidade — e é barata de fechar.

## Eixo 5 — RT preserva o tipo

**12 de 12** combinações (4 tipos × 3 rotas) devolvem o tipo certo, comparado por `type()`.
Inclui `None` no meio, float em coluna de int, e `2⁶³`. A tipagem é sólida no que faz.

## Três defeitos do meu próprio instrumento, e por que isso importa

O lab levou **três correções antes de valer** — todas no eixo 3, todas do mesmo tipo: *tomar
"wire idêntico" como prova de "parâmetro ignorado"*.

1. **1ª versão**: usei `SPEC_CPF` numa coluna `['a','b']`. O spec não mordia valor nenhum, o
   FLOOR recusou corretamente, e eu classifiquei isso como "IGNORADO CALADO" para `str`.
2. **2ª versão**: passei a usar CPFs válidos. Melhor, mas ainda errado — o spec pode morder e
   o FLOOR recusar mesmo assim, por não pagar.
3. **3ª versão**: adotei `SideOutputs.nature_apply` como prova de processamento. Aí o `.8H`
   apareceu como "ignorado" — e **fui verificar antes de reportar**: ele processa
   normalmente (wire 1841 → 1826 B, header ganha `:cpf`, RT ok) e simplesmente **não popula
   essa telemetria**.

O critério final combina os dois sinais: wire mudou ⇒ aceito; wire igual + telemetria ⇒ FLOOR
recusou; wire igual + sem telemetria ⇒ sem efeito observável, e só a comparação **entre
tipos** diz se é contrato ou assimetria.

**Achado de carona, real**: a rota `.8H` não reporta `nature_apply` — lacuna de
instrumentação, não de funcionalidade. Quem depender dessa telemetria para auditar `.8H` não
a tem.

## A lista do que soldar para "padronizar pro int"

Em ordem de dependência:

1. **Spec na rota tipada** (`.8`, estrutura) — mais um `candidatos.append`, exatamente como o
   bool fez. Pontos já localizados: `encoder.py:539`, `decoder.py:410-411`, header
   `#TCF.8n [nome]:id` com slot livre.
2. **Fechar a assimetria do `nature_per_col` em single-col tipado** (`.8`, barato) — recusar
   como já se recusa para string.
3. **Telemetria de nature no `.8H`** (`.8`, barato, byte-neutro).
4. **Denso para int** (`.9`, atalho) — o `pack_w` de `bitpack.py` já é parametrizado por
   largura; é o `b1`/`b2` generalizado.

Os itens 1–3 não mudam um byte de quem não usa spec. O item 4 é otimização pura, e é
exatamente o que o owner colocou no `.9`.

## O que este lab não responde

- **Frequência em corpus real** — continua sendo o que falta antes de qualquer weld.
- **A decisão do `OFFPAD`** (spec parametrizado × self-describing) segue em aberto; este lab
  não a toca.
- **Verificação adversarial externa**: não foi feita. O que houve foi auto-correção — três
  defeitos do instrumento achados e corrigidos aqui, incluindo um verificado à mão antes de
  virar reporte. Vale como diligência, não como contra-prova independente.
