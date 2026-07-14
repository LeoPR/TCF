# Proveniência das entradas

Ambas **sintéticas**, escritas à mão para reproduzir a estrutura já deduzida
(tabelão + RLE de pai) — material de FORMA, não medida de ganho. Nomes/itens
fictícios; domínio de exemplo.

| entrada | o que é | por que |
|---|---|---|
| `inputs/01-pessoas-telefones.json` | 4 pessoas (nome, cidade) com `telefones` = array de strings, ragged 1–3 | o exemplo canônico do owner (nome com N telefones); mostra RLE de pai + array de escalares |
| `inputs/02-pessoas-pedidos.json` | 3 clientes (cliente, plano) com `pedidos` = array de objetos {item, qtd} | mostra o bracket `[campos]` + o motor multi-col cruzando colunas (ref `^1`, seq-RLE) no tabelão |

Multiplicidades escolhidas para exercitar runs RLE distintos (2, 1, 3, 2 nos
telefones) e valores de pai que se repetem entre registros (Sao Paulo, Premium)
— para checar que o re-nest agrupa pela TUPLA de pais, não por coluna isolada.
