# Proveniência das entradas

Sintéticas, escritas à mão para isolar a variável **largura do registro** (nº de
campos-pai) — material de FORMA/crossover, não medida de ganho. Fictícias.

| entrada | o que é | por que |
|---|---|---|
| `inputs/01-estreito-nome-telefones.json` | 3 pessoas, só `nome` (1 campo-pai) + `telefones[]` | mínimo de campos-pai → o `counts` do Modelo B não paga (tabelão vence) |
| `inputs/02-largo-cadastro-completo.json` | 3 pessoas, cadastro largo (11 campos-pai: cpf, plano, status, endereco{bairro,uf,cep,cidade,rua,geo{lat,lon}}) + `telefones[]` | muitos campos-pai → a multiplicidade repetida em cada coluna domina (nível-aware vence) |

As multiplicidades dos telefones (2,1,3) e os campos-pai foram escolhidos para
expor o crossover A×B. `cpf` fictício (dígitos repetidos = fake seguro). Tudo
string por design (tipos são camada ortogonal, fora deste lab).
