# Proveniência das entradas

Todas **sintéticas**, escritas à mão para exercitar a estrutura (material de FORMA,
não medida de ganho). Nomes/valores fictícios; domínio de exemplo.

| entrada | o que é | por que |
|---|---|---|
| `inputs/01-clientes-endereco-telefones.json` | 3 clientes com `endereco{rua,cidade,geo{lat,lon}}` (1:1 aninhado 2 níveis) + `telefones[]` (1:N, ragged 1–3) | exercita `{}` recursivo + `[]` no mesmo registro; `plano`/`cidade` low-card p/ demonstrar N:1 |
| `inputs/02-clientes-pedidos-itens.json` | 2 clientes com `pedidos[{data, itens[{produto,qtd}]}]` (1:N aninhado 2 níveis) | exercita `[]` dentro de `[]` (re-nest recursivo por nível) |
| `inputs/03-cardinalidades-flat.csv` | 4 blocos (1x1/1xN/Nx1/NxN) de pares (A,B) | dados para o classificador FD (peça 7); casos canônicos: cpf-nome, pessoa-tel, produto-categoria, aluno-curso |

Multiplicidades e cardinalidades escolhidas para: runs RLE distintos (2,1,3),
valores compartilhados entre registros (Premium, Sao Paulo → N:1), e um par sem
FD (aluno-curso → N:N). A origem tipada não se aplica (tudo string por design;
tipos são camada ortogonal posterior).
