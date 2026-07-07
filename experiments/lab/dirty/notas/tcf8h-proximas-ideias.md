# TCF.8H — ideias registradas (a explorar, sem construir ainda) [dispositivo]

**Data**: 2026-07-05 · registro de direções do owner sobre o protótipo TCF.8H
([EXP-015](../../clean/EXP-015-tcf-hierarquico-csv-json/)). Guarda-chuva: T-STUDY-HIERARCHICAL-TCF; mapa:
[estudo-tcf-hierarquico-mapa](estudo-tcf-hierarquico-mapa.md). **Apenas registrado — vamos com calma.**

## 1. Camadas: montagem → otimização, pensadas em PÓS-otimização

As otimizações (última-sem-size, omit-closes, reorder, …) têm de ser avaliadas considerando o **consumo
final**, não só o byte transmitido. Ordem de pensar: **montagem** (a linguagem completa/explícita) →
**otimização** (deduzir/omitir) → mas **medir contra o pós-otimização** (o que o consumidor realmente faz).

## 2. Consumo DIRETO da estrutura (sem reconstruir o JSON)

Hipótese-chave: no consumo final, a hierarquia pode **não** precisar virar JSON de volta — o consumidor
**pega os dados direto da estrutura TCF**, como faria consultando um JSON (acesso por caminho/campo), **sem
materializar o JSON inteiro**. Ou seja, o TCF permite navegar/consultar a estrutura in-place.

Implicações:
- Muda o **RT-alvo**: se o consumo é estrutural (não JSON-exato), o **reorder order-free é aceitável** (a
  ordem das chaves não importa) — o que a peça 9/EXP-015 tratou como "order-free" vira o caso NORMAL.
- Liga com **lazy-query** (query toca 0,2–7,9% do blob sem descomprimir) e com a filosofia de
  explicabilidade/agrupamento-visível. O `#TCF.8H` já é navegável pelo colchete + sizes (dá pra saltar).
- A "reconstrução do JSON" vira um MODO (exportar), não o consumo default.

## 3. Enriquecimento por SPEC, com GABARITO (natures + template)

"Engordar" os dados com **specs** (naturezas, ADR-0015 / CAMADA 0 pre-tx) por cima da estrutura
hierárquica, e verificar se a **estrutura completa continua consistente** (RT). Specs a usar:
- **CPF** — já existe `SPEC_CPF` (`from tcf import SPEC_CPF`). Aplicar numa coluna de CPF.
- **CEP** — se a pessoa tiver 1+ CEPs (endereço); spec de formato `NNNNN-NNN`.
- **Telefone** — spec ao menos básico, formato clássico `(xx) xxxxx-xxxx`.

**A ideia do GABARITO (template implícito)** — o refinamento do owner:
- Uma coluna com spec tem um **gabarito** (template do formato padrão). O **primeiro item serve de
  referência de reconstrução**.
- Um spec que usa o formato **mais padrão** deixa o formato **implícito**: o primeiro valor que **segue** o
  padrão do spec **não precisa** carregar o gabarito (o spec JÁ é o template). Só um valor **diferente** do
  padrão carrega seu próprio gabarito explícito.
- Ex.: telefone `(xx) xxxxx-xxxx` — o spec define o molde; telefones clássicos entram minimamente (só os
  dígitos que variam); um telefone de formato diferente (ramal, internacional) carrega o gabarito próprio.
- É a mesma lógica do OBAT (primeira string = literal/molde, resto = afixo/delta) — mas **por natureza**,
  no nível do spec. Une natures (CAMADA 0) + a compressão de afixo (OBAT).

## 4. Cabeçalho: CONDIÇÕES de ganho (não "quem vence") + hex nos sizes

Correção de viés (owner 2026-07-05): a análise de fim-de-linha detecta a **situação**, não um vencedor.
Modelo (medido em [EXP-015/analise_header.py](../../clean/EXP-015-tcf-hierarquico-csv-json/analise_header.py)):
as duas otimizações atuam na **última folha** (DFS): `SAVING(L) = digits(size(L)) + depth(L)`
(última-sem-size dá os digits; omit-closes dá a depth).
- **omit-closes**: sempre bom, RT-exato.
- **reorder** (order-free): vale **SSE** `argmax_L(digits+depth) ≠ natural-última`. **Não é só profundidade** —
  uma folha rasa mas de size grande pode ganhar de uma profunda de size pequeno. (S6 empata por acaso.)
- **HEX nos byte-sizes** (ideia do owner, a explorar): `len(hex(s)) < len(str(s))` para `s∈[10,15]∪[100,255]∪
  [256,4095]…` (fronteiras 16ᵏ vs 10ᵏ). Economiza por-size no header TODO **e** pode mudar o argmax do reorder.
  Trade-off: hex é menos legível que decimal (pilar explicabilidade) — decidir onde vale (payload minúsculo?).
  Não totalmente explorado. Possível: um flag no magic dizendo a base dos sizes, ou hex sempre quando <256.

## Como explorar (quando o owner der o passo)

1. Terminar EXP-015 (feito: JSON exato + CSV plano + omit-closes; profundo-por-último FECHADO).
2. Adicionar **specs** ao codec (`nature_per_col`): CPF/CEP/telefone, com o gabarito implícito (1º-valor).
3. Medir a **consistência da estrutura completa** (hierarquia + specs) — RT.
4. Explorar o **consumo direto** (navegar a estrutura sem reconstruir JSON) — modo query vs modo export.

Cross-links: [EXP-015 report](../../clean/EXP-015-tcf-hierarquico-csv-json/report.md) ·
[teoria-cardinalidade](teoria-cardinalidade.md) · ADR-0015 (natures) · lazy-query.
