# 2026-08-20-2350 — CNPJ alfanumérico e placa Mercosul: uma causa, dois documentos

## O fato externo (pesquisado, com fonte)

**IN RFB nº 2.229/2024**: desde **julho de 2026** — *já vigente* — as **novas** inscrições de
CNPJ têm as **12 primeiras posições alfanuméricas** (`0-9` e `A-Z` maiúsculo); só os **2 DV
continuam numéricos**. A primeira inscrição alfanumérica sai em 31/07/2026. CNPJs existentes
**não mudam**.

O DV segue **módulo 11 com os mesmos pesos**. O que muda é a conversão caractere→valor:

```
valor = ASCII(c) − 48        '0'→0 … '9'→9   ·   'A'→17 … 'Z'→42
```

**Verificado neste lab, não copiado**: o exemplo publicado `12.ABC.345/01DE-35` fecha com o
`_cnpj_check_fn` que **já está em `src/tcf`**, sem tocar nos pesos. E a retrocompatibilidade
não é promessa: dígito converte para ele mesmo, logo a regra nova é **idêntica** à antiga no
domínio numérico. **2 000 CNPJs reais** da Receita (Shaper) validaram sob a regra nova, 0
divergências.

> **Portanto o `check_fn` do TCF já está certo.** O que não está é a **regex** (`^\d{2}\.…`)
> e o `body_length=12` contando dígitos.

## O que eu esperava medir, e o que realmente importa

Eu ia medir "a nature de CNPJ para de funcionar". **A nature já não dispara em dado real** —
o `FLOOR` prefere o `split`. A pergunta certa é outra:

> **O mecanismo que HOJE ganha no CNPJ real sobrevive ao alfanumérico?**

## Resultado — não sobrevive

| coluna (n=2000) | bytes | vs raw | mecanismo escolhido |
|---|---:|---:|---|
| **CNPJ numérico REAL** (Shaper/receita-cnpj) | 23 436 | **−38,32%** | `%` **split** |
| alfanumérico, estrutura realista¹ | 35 064 | **−7,72%** | core |
| alfanumérico uniforme (pior caso) | 38 012 | **+0,03%** | `!` **raw** |

¹ raiz de 8 alfanuméricos + ordem `0001` dominante (90%), como o cadastro real.

**−38,3% viram −7,7%.** No pior caso o TCF fica **maior que o texto cru**.

**A causa é o gate do split** — e é a mesma que o [lab `2300`](../2026-08-20-2300-h-13-04-template-declarado/)
achou: ele segmenta por **dígito × não-dígito**. Com letras no corpo, elas caem *dentro* do
que o gate trata como separador, e o template passa a variar a cada valor:

```
12.ABC.345/01DE-35   →  template ('', '.ABC.', '/', 'DE-', '')
A1.B2C.3D4/5E6F-71   →  template ('A', '.B', 'C.', 'D', '/', 'E', 'F-', '')
```

Templates diferentes ⇒ gate 100%-uniforme recusa ⇒ cai no core ou no raw.

**Integridade: nada corrompe.** Roundtrip OK em 6/6, inclusive na coluna mista
(numérico + alfanumérico). O alfanumérico **não quebra o TCF — ele só deixa de ganhar**.

## O conserto: decompor por POSIÇÃO, não por separador

A máscara é **fixa** (`XX.XXX.XXX/XXXX-XX`), então a posição de cada caractere não depende de
ele ser letra ou dígito. É a mesma ideia do [estudo do CEP](../../2026-08-17/) (entropia por
posição), aplicada como decomposição.

Medido sobre as **18 posições do valor formatado, separadores inclusive** — o wire se
auto-descreve e a comparação com o `%` (que guarda o template) fica justa:

| coluna | única | posicional | ganho do posicional |
|---|---:|---:|---:|
| **CNPJ numérico REAL** | 23 436 (−38,3%) | **20 799 (−45,3%)** | **−11,3%** |
| alfanumérico realista | 35 064 (−7,7%) | **23 684 (−37,7%)** | **−32,5%** |
| alfanumérico caos | 38 012 (+0,0%) | 29 271 (−23,0%) | −23,0% |

**O posicional bate o split ATÉ no CNPJ numérico real, hoje: −11,3%.** Isso não é sobre o
alfanumérico — é ganho disponível agora, no dado que já temos.

> **Conexão direta com a direção do grupo** (owner, 2026-08-17): *"é mais fácil pensar que
> eles são realmente duas colunas, só que indicar algo no header pra dizer que as duas
> colunas são um grupo de uma coluna só"*. É exatamente isto — **N colunas + marcador de
> grupo**. E o custo do marcador já está medido: **9–11 B constante em n**
> ([lab 1700](../../2026-08-17/)), irrelevante em n=2000.

## A mesma causa, outro documento: a placa Mercosul

**Pesquisado**: a placa Mercosul é **LLLNLNN** (3 letras, 1 dígito, **1 letra**, 2 dígitos) e
substituiu a antiga **LLLNNNN**. A conversão troca **o 2º dígito por uma letra** — `ABC-1234`
vira `ABC1C34`. Isso levou o espaço de ~175,8 milhões para **~457 milhões** de combinações. As
duas formas **coexistem** na frota.

**Não há corpus real de placa** — busca em `Z:/tcf-data/`: nenhum dataset tem a coluna
(`br-identidades` tem CNPJ/CPF, não placa). Sintético é legítimo aqui porque a pergunta é do
**gate**, que é lógico e não estatístico — mesmo argumento do H-13-04.

| coluna (n=2000) | bytes | vs raw | mecanismo | posicional |
|---|---:|---:|---|---:|
| placa antiga `LLLNNNN` | 16 013 | **+0,09%** | `!` raw | 14 356 (**−10,3%**) |
| placa Mercosul `LLLNLNN` | 16 013 | **+0,09%** | `!` raw | 14 378 (**−10,1%**) |
| frota mista (50/50) | 16 013 | **+0,09%** | `!` raw | 14 408 (**−9,9%**) |

**Achado que muda o enquadramento**: a Mercosul **não causa regressão** — o TCF já não ganhava
nada em placa. Sem separador na forma armazenada, o `split` nem se aplica (o gate exige ≥2
grupos de dígitos separados por não-dígito), e o TCF fica **0,09% maior que o texto cru**.
Placa não é uma perda nova; é uma **lacuna que já existia**, e a Mercosul só a torna
permanente (a letra no meio fecha qualquer saída baseada em dígito).

## Não medido (declarado)

- **Placa com dado REAL** — não existe corpus. O sintético é **uniforme**, ou seja **pior
  caso**: placas reais são emitidas por região e agrupam no prefixo de letras, então o ganho
  real deve ser maior. O gate do ROADMAP (`FILTROS-POPULARES`, ≥15% em 2+ reais) **continua
  bloqueado por dado**, exatamente como já registrado.
- **CNPJ alfanumérico com dado REAL** — não existe ainda (a primeira inscrição é de
  31/07/2026). O caso "realista" é uma hipótese de estrutura, não uma amostra.
- **O teto teórico**: placa em base-80 caberia em **5 chars** (`log₈₀(4,57×10⁸) ≈ 4,55`) contra
  7 do raw = −28,6%. O posicional entrega −10%. **A distância até o teto é a medida do que uma
  nature dedicada valeria** — e não foi explorada aqui.
- **CPF não muda** — nada na IN 2.229/2024 o afeta.
- Uma semente, um volume (n=2000). Sem `.9`/perf.

## O erro que o portão pegou

O campo `cnpj` do Shaper **já vem formatado** (18 chars). Eu apliquei a máscara **de novo**,
gerando strings de 22 chars — e a medição do caso real saiu **20 425 B / −55,60%**, que era
**falso**. O `assert` de validação de DV **passou mesmo assim**, por coincidência: remover os
separadores de uma string dupla-mascarada recupera os 14 dígitos originais.

Quem pegou foi o **assert de remontagem posicional**, que compara o objeto reconstruído com a
entrada. Número correto: **23 436 B / −38,32%**. Sem o gate de remontagem, o lab teria
reportado 17 pontos percentuais a mais de ganho.

## Evidência

[`inputs/`](inputs/) + [`outputs/`](outputs/) — 12 wires, 12 roundtrips, 12 entradas, portão
anti-órfão comparando conjuntos. [`resultado.json`](resultado.json) com os 6 casos de CNPJ, os
3 de placa e a regra verificada.

## Conexões

- Gate do split segmenta por separador: [lab `2300` / H-13-04](../2026-08-20-2300-h-13-04-template-declarado/)
- Grupo como forma do split (marcador 9–11 B): [labs `1600`–`1800`](../../2026-08-17/)
- `FILTROS-POPULARES` (placa, ALVO `.9`, bloqueado por dado): [`ROADMAP.md`](../../../../../../ROADMAP.md)
- `src/tcf/natures/templated_checked.py` (`SPEC_CNPJ`, `_cnpj_check_fn`) · `src/tcf/multi/split.py`

**Fontes**: [Receita Federal — CNPJ alfanumérico](https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/acoes-e-programas/programas-e-atividades/cnpj-alfanumerico) ·
[Receita Federal — notícia](https://www.gov.br/receitafederal/pt-br/assuntos/noticias/2024/outubro/cnpj-tera-letras-e-numeros-a-partir-de-julho-de-2026) ·
[Serpro — cálculo do DV](https://www.serpro.gov.br/menu/noticias/videos/calculodvcnpjalfanaumerico.pdf) ·
[cnpj.ws — algoritmo e exemplo](https://docs.cnpj.ws/blog/cnpj-alfanumerico) ·
[Canaltech — conversão da placa Mercosul](https://canaltech.com.br/carros/placa-mercosul-como-funciona-a-combinacao-de-letras-221999/)
