# Proveniência das entradas

Sintéticas realistas, escritas à mão para representar os **clássicos de transmissão**
cliente-servidor em JSON — material de FUNCIONALIDADE/FORMA, não medida de ganho.
Nomes/valores fictícios; domínio de exemplo; CPF de dígitos repetidos (fake seguro).

| entrada | clássico | forma que exercita |
|---|---|---|
| `inputs/01-cadastro-clientes.json` | cadastro/CRM | objeto 1:1 aninhado (endereco⊃geo) + **DUAS listas irmãs** (telefones[] E emails[]) + lista vazia (Carla sem emails) |
| `inputs/02-pedidos-itens.json` | pedido/e-commerce | **array aninhado** (pedidos[{itens[]}]) + registro com `pedidos:[]` vazio |
| `inputs/03-telemetria-dispositivos.json` | telemetria/IoT | objetos 1:1 aninhados (sensores{temperatura,umidade}) + **série temporal** (leituras[] de objetos) |

Escolhidas para cobrir, juntas, as formas comuns de transmissão: múltiplas listas
irmãs, aninhamento de array, objetos 1:1 profundos, listas vazias. Tudo string por
design (tipos são camada ortogonal, fora deste lab). Todas ficam na classe coberta
(uma raiz, chaves uniformes por nível).
