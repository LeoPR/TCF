# O header do `.8H` em casos sintéticos mínimos

Gerado por `run.py`. Re-rode com `python run.py`.

**15 casos, 15 com round-trip OK.**

Cada caso é o MENOR que exercita uma produção da gramática do meta.
O detalhe de cada um (entrada, wire, header decomposto, RT) está em
`outputs/<caso>.header.md`.

| caso | produção | header | H? | RT | hdr/wire |
|---|---|---|:-:|:-:|---:|
| `raiz_dataset` | dataset `list[dict]` — SEM disc de raiz (o caso base) | `#TCF.8Ha` | sim | ok | 8/13 B |
| `raiz_objeto` | `#O` — objeto único na raiz | `#TCF.8H#Oa:2,b` | sim | ok | 14/19 B |
| `raiz_valor` | `#V` + nome de campo `\z` — escalar solto na raiz | `#TCF.8H#V\z` | sim | ok | 11/14 B |
| `raiz_vazio_dict` | `#E` — `{}`, sem corpo nenhum | `#TCF.8H#E` | sim | ok | 9/10 B |
| `raiz_contagem` | `#D<N>` — lista de objetos SEM campo (só a contagem sobrevive) | `#TCF.8H#D3` | sim | ok | 10/11 B |
| `campo_dois` | dois campos escalares, separados por `,` | `#TCF.8Ha:4,b` | sim | ok | 12/21 B |
| `campo_nulo` | máscara `?:<size>` — vem ANTES da coluna do campo | `#TCF.8Ha?:5` | sim | ok | 11/19 B |
| `campo_ausente` | ragged: campo que falta numa linha (também usa máscara) | `#TCF.8Ha:4,b?:4` | sim | ok | 15/26 B |
| `campo_aninhado` | `{` — objeto dentro de campo, achatado no caminho | `#TCF.8Ha{b` | sim | ok | 10/15 B |
| `campo_array` | `#:<size>[` — coluna de contagem + coluna de itens | `#TCF.8Ha#:6[` | sim | ok | 12/25 B |
| `tipo_numero` | tag `n` na forma do campo | `#TCF.8Ha:6n` | sim | ok | 11/18 B |
| `tipo_bool` | tag `b` na forma do campo | `#TCF.8Ha:11b` | sim | ok | 12/24 B |
| `tipo_misto_de_campos` | campos de tipos DIFERENTES lado a lado (str, n, b) | `#TCF.8Hs:4,n:6n,b:11b` | sim | ok | 21/43 B |
| `nome_vazio` | `\z` — chave vazia num objeto | `#TCF.8H#O\z` | sim | ok | 11/14 B |
| `nome_com_separador` | nome que contém os separadores do meta (`,` `:` `#`) | `#TCF.8Ha\,b:4,c\:d` | sim | ok | 18/27 B |
