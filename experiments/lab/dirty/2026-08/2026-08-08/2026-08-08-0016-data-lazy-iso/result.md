# Resultado — data lazy (spec ISO), e a avaliação crítica da direção

**2026-08-08 · dirty · 19 casos, `n=500`, RT completo conferido em todos**

---

## O que decide: **RT sobreviveu em 19 de 19**

Incluindo os casos que existem justamente pra quebrar:

| caso | o que testa | RT |
|---|---|:-:|
| `tudo-br` | o spec ISO erra em **100%** dos valores | **ok** |
| `ambiguo-br-us` | só dias 1..12 — BR e US indistinguíveis | **ok** |
| `misto-iso-br` | dois formatos na mesma coluna | **ok** |
| `bissexto-invalido` | `2026-02-29`, data que não existe | **ok** |
| `epoca-remota` | ano 1 e ano 9999 | **ok** |
| `sujo-50pct` | metade da coluna é lixo | **ok** |

---

## O achado de design: **a ambiguidade não precisa ser resolvida**

Este é o ponto onde eu discordo do que foi levantado, e o lab decide a favor de simplificar.

> *"lembra que os primeiros dados desambiguam, mas se nem os primeiros servem de template,
> podemos recorrer a algum tipo de grafia nossa ou de ISO"*

**Não é preciso desambiguar, e não é preciso grafia nova.** A transformação tem de ser
**inversível**, não **correta**:

- se o spec chuta BR e o dado era US, `01/02/2026` volta `01/02/2026` — byte-idêntico, porque
  a inversa aplica o mesmo chute;
- se o dado não parseia no chute (`02/13/2026` com spec BR: mês 13), ele **cai no literal** e
  custa **+1 byte**.

Medido: `tudo-br` com spec ISO tem **0% de compressível** e o RT é perfeito, ao custo de
**+4,9%**. `ambiguo-br-us` idem, **+1,7%**.

**Chute errado custa bytes, nunca dado.**

Isso muda o papel de olhar os primeiros valores: deixa de ser requisito de **correção** e
vira otimização de **bytes** — serve pra escolher *qual spec tentar*, e errar a escolha
degrada a compressão sem risco nenhum. É uma heurística que pode ser preguiçosa à vontade.

E o caso *"nem os primeiros servem de template"* não precisa de invenção: sem spec que
parseie, tudo cai no literal e o wire fica ~5% maior que hoje. Piso conhecido.

---

## Quanto rende, quando rende

| caso | hoje | lazy | Δ |
|---|---:|---:|---:|
| `limpo-mensal` | 4856 B | **23 B** | **−99,5%** |
| `virada-ano` | 1758 B | **22 B** | **−98,7%** |
| `limpo-diario` | 348 B | **22 B** | **−93,7%** |
| `com-nulo` (5% null) | 782 B | 407 B | −48,0% |
| `limpo-espalhado` | 4592 B | 3548 B | −22,7% |

O `limpo-espalhado` é o mais interessante: **mesmo sem regularidade nenhuma**, o ordinal
ganha 22,7% — porque 6 dígitos sem separador comprimem melhor que 10 chars com dois `-`.
O ganho não depende só do `*N+M|`.

## A válvula de escape **não** mata o ganho

Era a hipótese principal do lab, e ela caiu:

| sujeira | % compressível | Δ | vence |
|---|---:|---:|:-:|
| 1% | 99,0% | −16,6% | lazy |
| 5% | 95,0% | −14,0% | lazy |
| 10% | 90,0% | −11,9% | lazy |
| 25% | 75,0% | −18,4% | lazy |
| **50%** | 50,0% | **−3,1%** | **lazy** |

**Não existe ponto de virada na faixa testada.** Com metade da coluna sendo lixo, o lazy
ainda ganha. A razão: o literal não é opaco — o `_lixo` continua indo pro core, que comprime
o que der; e os compressíveis viram ordinais que o seq-RLE pega. As duas metades trabalham.

### Onde perde, e quanto

Três casos, e o pior é **+4,9%**:

| caso | Δ | por quê |
|---|---:|---|
| `tudo-br` | +4,9% | 100% literal: paga 1 byte por valor e não ganha nada |
| `ambiguo-br-us` | +1,7% | comprime, mas a coluna já era baixa-cardinalidade (12 datas) |
| `com-vazio` | +0,2% | string vazia vira `_`, e o core já lidava bem com ela |

O teto do prejuízo é o **marcador de 1 byte por valor**. É o mesmo limite do CPF.

---

## Avaliação crítica da direção

### Concordo

1. **Lazy para data que entra como string** — é exatamente o molde do CPF, e o lab mostra
   que funciona. `classify_value` → `MARKER + v` quando não dá. Nada novo a inventar.
2. **Data tipada no dataset é outro problema** — sim, e separar os dois simplifica os dois.
   Se o dataset já diz `date`, não há inválida nem ambígua; o trabalho vira só escolher a
   grafia de saída.
3. **Declarar o tipo no schema com comportamento lazy** — é a melhor das ideias levantadas.
   Elimina a adivinhação **e** mantém a rede de segurança. E o custo é o mesmo: o spec
   declarado é só um spec que não precisou ser adivinhado.
4. **Modo rígido opcional** — concordo, e é barato: um parâmetro. Default lazy (nunca falha),
   rígido para quem quer o erro.

### Discordo / refino

1. **"light warning"** — não. Warning que dispara em operação normal vira ruído que ninguém
   lê, e aí o warning que importa se perde no meio. O `SideOutputs` já existe, já é telemetria
   de custo zero, e é o lugar certo pra "N valores caíram no literal, motivos: …". Warning
   fica reservado pro que já tem precedente: **wire não-canônico**, que é outra coisa.
2. **"tipagem no head, ou no primeiro elemento"** — head. O precedente existe e está soldado:
   `#TCF.8 :cpf`, self-describing (ADR-0027). Pôr no primeiro elemento seria criar um segundo
   lugar para a mesma informação, e informação em dois lugares diverge.
3. **"escolhe duas"** — entendido que era exemplo. Mas vale registrar o inverso: o lab de
   ontem mostrou que **cada regime tem um vencedor diferente** (epoch, split, delta), então o
   número de candidatos vai crescer. Isso reforça o `T-FLOOR-MULTIVETOR` — com muitos
   candidatos, `min()` por byte fica cada vez mais grosseiro.

### O que eu escolheria matar primeiro

**O spec ISO, per-valor, com literal.** Maior retorno × menor esforço:

- o alvo (`*N+M|`) já existe e está soldado;
- o molde (nature do CPF) já existe e está soldado;
- o header self-describing já existe (ADR-0027);
- ISO é o formato mais comum e o mais fácil de parsear sem ambiguidade;
- o piso do prejuízo é conhecido e pequeno (+4,9%).

Os outros formatos (BR, US, compacto) são **o mesmo objeto com outro `fmt`** — 4 linhas cada.
Não precisam de decisão nova; precisam de medição.

---

## O que este lab NÃO fez

- **Não mediu o custo de declarar o spec no wire.** O CPF resolve com `#TCF.8 :cpf`, então há
  precedente e é custo fixo de header — mas nenhum número aqui inclui isso.
- **Não é wire.** A pré-tx roda fora do `src/tcf`; é protótipo, não weld.
- **A checagem de re-emissão não foi exercitada.** O caso `grafia-frouxa` (`2026-1-01`) foi
  pego antes, pelo filtro de comprimento. Para o ISO pode ser inalcançável — mas a guarda
  fica, porque outros `fmt` podem ter grafias não-canônicas do mesmo comprimento.
- **Portabilidade de `strftime` conferida só aqui**: anos 1/9/99/999 dão `%Y` com zero à
  esquerda neste Python/Windows. Se algum runtime der `1-01-01`, o RT quebra — a guarda de
  re-emissão pega, mas o valor cai no literal. **Vale re-conferir no port pra Rust.**
- Não testou timestamp com fuso, nem horário de verão, nem coluna com dois specs
  simultâneos.
