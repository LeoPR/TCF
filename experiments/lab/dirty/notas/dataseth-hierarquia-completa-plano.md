---
title: DatasetH - plano de pesquisa para hierarquia completa e escalares especiais
type: experiment
status: aberta
created: 2026-07-13
updated: 2026-07-13
ticket: tickets/T-STUDY-HIERARCHICAL-TCF.md
related:
  - experiments/lab/dirty/notas/estudo-tcf-hierarquico-mapa.md
  - experiments/lab/dirty/notas/tipos-como-specs.md
  - experiments/lab/dirty/notas/roadmap-hipoteses.md
  - tickets/T-CODE-TCF8H-WELD.md
  - experiments/lab/dirty/2026-07-13-dataseth-json-bridge/
---

# DatasetH - plano de pesquisa para hierarquia completa e escalares especiais

**[probatório]** Plano de pesquisa aberto a pedido do owner (2026-07-13). Ele registra a pergunta,
as alternativas e os falsificadores antes de criar outro protótipo ou alterar o formato. Não decide a
gramática `#TCF.8H`, não altera `src/tcf` e não cria `encode_json`.

## Enunciado

O objetivo não é "suportar JSON". O objetivo é transportar uma **estrutura hierárquica completa** por um
intermediário source-agnostic chamado provisoriamente **DatasetH**. JSON é apenas uma primeira fonte/saída
útil porque expõe objetos, arrays e alguns escalares; uma API, Arrow, uma árvore nativa, um banco ou outro
adaptador podem produzir o mesmo DatasetH.

"JSON-like" é apenas uma descrição de ergonomia: árvore com containers e folhas. Não é a gramática de
entrada do core nem limita o modelo ao JSON. Em particular, JSON padrão possui `null`, mas não possui
`NaN`, `+Infinity` ou `-Infinity`; esses valores podem vir de fontes numéricas, Arrow, Python ou de uma
fonte textual que use uma gramática JSON-like mais ampla.

## Hipótese registrada

**H-HIER-SCALAR-01 - escalares especiais são parte do domínio do DatasetH, não uma peculiaridade de JSON.**

`null`, `NaN`, `+Infinity` e `-Infinity` podem ser representados como folhas com tipo especial. Quando um
ramo ou coluna possui domínio pequeno, `bN` pode transportar seus índices compactamente. Como alternativa,
os valores podem ser tratados como strings especiais com escape ou marcador explícito. A escolha só é
aceitável se preservar a identidade entre o valor especial, a string que o soletra e a ausência estrutural.

**Falsificador mínimo:** a proposta falha se qualquer caso abaixo fizer colisão ou perder informação:

| categoria | exemplos que devem continuar distintos |
|---|---|
| presença | campo ausente; `null`; string vazia `""`; string `"null"` |
| não finitos | `NaN`; string `"NaN"`; `+Infinity`; string `"+Infinity"`; `-Infinity` |
| números | `1`; `1.0`; `"1"`; `"1.0"`; `-0.0` se a fonte declarar sinal relevante |
| containers | objeto vazio; array vazio; array misto com valor especial; array dentro de array |

`NaN` exige atenção adicional: em IEEE/Python, `nan != nan`. Portanto, o oráculo de round-trip não pode
usar igualdade ingênua de `float`; DatasetH precisa de uma identidade semântica declarada, por exemplo um
kind canônico de escalar especial, ou uma comparação que o trate explicitamente como reflexivo.

## O que já se sabe

- **H-TYPE-01** já caracterizou `null` como folha tipada (`n`) e mostrou que dedução pura é lossy:
  ela confunde `null` com string vazia. A fronteira `null` em coluna ou array misto ainda requer presença e
  nullable/definition level.
- **H-TYPE-02/04/07** já caracterizaram `bN` como domínio embutido mais índices bit-packed. `bN` é um
  **portador de domínio**, não uma definição de `null` ou de não finitos. Antes de usá-lo aqui, o domínio
  precisa carregar tipo para que `NaN` e `"NaN"` não recebam o mesmo índice.
- **H-TYPE-07** reservou rótulos de tipos especiais no estudo `bN`, mas não definiu semântica nem wire
  grammar para `NaN` ou infinitos. Esta pesquisa não aloca esses rótulos.
- O POC `2026-07-13-dataseth-json-bridge/` rejeita hoje `NaN`/`Infinity` para manter uma baseline de JSON
  padrão. Isso é um limite do POC inicial, não uma decisão do DatasetH.

## Alternativas a comparar

| alternativa | ideia | vantagem a testar | risco a refutar |
|---|---|---|---|
| A. folha tipada | `null`, `nan`, `pos_inf`, `neg_inf` são kinds explícitos; strings ficam strings | semântica clara e comparação confiável | custo de tag/framing por folha |
| B. domínio tipado + `bN` | A define os valores; `bN` guarda domínio tipado e stream de índices | baixo custo para repetição e baixa cardinalidade | `bN` não pode apagar tipo; ganho só é relevante no perfil terminal já medido |
| C. string especial escapada | valores especiais usam léxico reservado com escape reversível | reaproveita corpo textual | colisão com texto literal, regra de escape e semântica escondida |
| D. dicionário interno | código fixo para um conjunto pequeno, por exemplo bool/null | domínio de 0 bytes e acesso tipado | exige decisão de formato e não deve preceder a semântica/RT |

Nenhuma alternativa está escolhida. A e C devem ser comparadas primeiro; B e D só fazem sentido depois que
o domínio semântico estiver definido. O resultado pode ser híbrido: tipo explícito para identidade e `bN`
como representação escolhida pelo `min()` somente quando houver domínio pequeno e perfil terminal.

## Escopo da estrutura hierárquica

DatasetH deve separar **topologia**, **presença** e **folhas**:

- raiz única que pode ser objeto, array ou escalar;
- objetos com campos ordenados; arrays com itens ordenados; profundidade recursiva;
- folhas string, integer, finite number, boolean, null e os especiais em estudo;
- ausência como propriedade estrutural de um campo ou posição, nunca sinônimo de `null`;
- objetos e arrays vazios como valores presentes;
- arrays ragged, arrays de arrays e objetos dentro de arrays.

Grafos, referências compartilhadas, ciclos, múltiplas raízes e identidade de objeto não entram por inferência.
Se uma fonte tiver grafo em vez de árvore, o adaptador precisa materializar uma árvore ou declarar outra
semântica antes de chegar ao DatasetH.

## Plano de ataque

1. **P0 - registro e vocabulário**: este plano, H-HIER-SCALAR-01 e os ponteiros de navegação. Nenhum
   comportamento de POC ou core muda nesta fase.
2. **P1 - matriz semântica**: escrever fixtures mínimos para a tabela de falsificação e declarar a
   equivalência do DatasetH. Cobrir `null` versus ausência, strings colidentes, não finitos, vazios,
   arrays mistos e raiz escalar. Resultado esperado: contrato de teste, não codec.
3. **P2 - comparação de representações externas**: em um dirty lab novo e reproduzível, comparar A
   (folha tipada) e C (string escapada) em `DatasetH -> DatasetH`; medir RT, inspeção e bytes. Não tocar
   `src/tcf`. Se A sobreviver, testar B como portador de domínio tipado; D fica bloqueada por decisão de
   formato.
4. **P3 - fontes e saídas**: provar o mesmo DatasetH por duas origens. JSON padrão cobre `null`; uma
   origem não-JSON, como árvore Python/Arrow, cobre `NaN` e infinitos. O adaptador JSON-like, se houver,
   deve declarar sua gramática em vez de alegar que é JSON padrão.
5. **P4 - topologia completa**: cruzar os escalares especiais com presença, repetition/definition levels,
   arrays nested e objetos ragged. Uma solução que funcione apenas em uma folha plana não fecha o contrato H.
6. **P5 - decisão de representação**: só depois de P1-P4, escolher tags, escape ou domínio tipado;
   registrar uma ADR se a semântica ou wire grammar for aceita. Reavaliar `bN` contra V2-B e o perfil
   terminal, sem usar bytes como substituto de RT.
7. **P6 - codec e weld**: implementar `DatasetH -> TCF.H -> DatasetH` externamente, passar os gates do
   ticket T-CODE-TCF8H-WELD e pedir aprovação explícita antes de tocar `src/tcf`.

## Gates e evidência

| gate | prova exigida | reprova a etapa se |
|---|---|---|
| identidade | `decode(encode(dataset_h)) == dataset_h` sob igualdade semântica declarada | valor especial, string ou ausência colidem |
| fonte | duas fontes produzem o mesmo DatasetH | a semântica depender de `json.loads` ou de um parser específico |
| topologia | fixtures exercitam containers vazios, ragged e nested | tipos funcionam apenas em tabela plana homogênea |
| representação | comparação A/C/B registra RT, bytes e inspeção | bN/escape é escolhido só por microbytes sem preservar o domínio |
| formato | grammar e char registry aprovados | um rótulo reservado recebe semântica por acidente |
| core | non-regressão flat e aprovação explícita | qualquer mudança em `src/tcf` ocorrer antes dos gates anteriores |

## Estratificação e Diataxis

| camada/artefato | papel nesta pesquisa | local agora ou destino depois |
|---|---|---|
| **L0 Mneme** | topologia separada de valor; ausência separada de `null`; round-trip sem colisão | princípios neste plano e nos testes |
| **L1 Morfé** | DatasetH, tags, ADR, Diataxis e contrato de equivalência | formalizar somente após P1-P5 sobreviverem |
| **L2 Órganon** | Python, `json`, Arrow, `ijson`, POC atual e protótipos `bN` | labs/gadgets externos, trocáveis |
| **exploração probatória** | hipótese, fixtures, medições e resultados negativos | `experiments/lab/dirty/` |
| **decisão dispositiva** | aceitar semântica/grammar e autorizar weld | ADR + ticket de weld |
| **Explanation (Diataxis)** | por que DatasetH separa fonte, topologia e escalares | futuro `docs/theory/`, após confirmação conceitual |
| **Reference (Diataxis)** | grammar `#TCF.8H`, tags e contrato de decode | futuro `docs/algorithms/`, após formato aceito |
| **How-to (Diataxis)** | adaptar JSON, Arrow ou banco para DatasetH | futuro `docs/how-to/`, quando adaptadores estiverem estáveis |
| **Tutorial (Diataxis)** | primeiro fluxo completo para usuário | só depois de API e codec públicos |

O plano é o ponto de leitura enquanto a ideia está em pesquisa. Não criar ainda documentação estável em
`docs/theory/`, `docs/algorithms/` ou `docs/how-to/`: isso confundiria hipótese com contrato vigente.

## Update 2026-07-13 — P1+P2 executados (A vs C)

Lab [`2026-07-13-1835-dataseth-special-scalars/`](../2026-07-13-1835-dataseth-special-scalars/):
matriz de falsificação executável (21 casos × A/C, 10 pares de distinctness, 2 origens — árvore
Python e JSON-like com gramática declarada) + oráculo `semantic_key` (NaN reflexivo como kind;
`-0.0` ≠ `0.0` via repr; `==` ingênuo comprovadamente colapsa). **Resultado**: **A (folha tipada)
sobrevive a todos os falsificadores e nunca perde em bytes**; C (string escapada) = refutada-parcial
(RT ok, mas imposto de escape GLOBAL ao canal de string + semântica escondida). B recebeu depois uma
primeira prova separada de dominio tipado no header; D segue bloqueada. Detalhe: `result.md` do lab. P3 (duas origens) tem primeira
prova no mesmo lab; P4 (topologia × especiais) tem os casos mixed-array/array-de-array cobertos,
faltando def/repetition levels da forma regular. Stage 1 (topologia RT-exato, por-instância) está
no lab-ponte `2026-07-13-dataseth-json-bridge/` (codec_h). Próximo: P4 restante → P5 (decisão de
representação + gramática, com a nota de que o kind tipado deve sobreviver à forma por-instância E
à forma regular multirow-com-header).

## Update 2026-07-13 - primeira prova de B: dominio tipado no header

Lab [`2026-07-13-1921-dataseth-typed-header-domain/`](../2026-07-13-1921-dataseth-typed-header-domain/):
o desenho direto `null=index_ref` foi refutado na forma ingenua quando a indexacao ocorre depois da
stringificacao: `null` e string `"null"` caem no mesmo indice e o header ja nao tem informacao para
recuperar as ocorrencias. Duas formas tipadas passaram RT semantico e distinctness em cinco perfis
sinteticos:

- **HDOM**: header carrega o dominio inteiro com tag por entrada e body carrega indices `b1`/`b2`/`b4`.
   E a forma direta de `tipo -> index_ref`; funciona quando o dominio total e pequeno (`k<=16`).
- **HK**: header carrega somente o mapa de kinds ativos; body tem indices de kind mais um payload produzido
   pelo `tcf.encode(list[str])` comum para strings/inteiros/numeros. `null`/NaN/infinito nao levam payload;
   a string que os soletra continua no canal string e nao colide. Ele continua aplicavel no perfil de 100
   strings distintas, onde HDOM nao se aplica.

Isto torna B uma alternativa exercitada, mas nao uma decisao de formato: os bytes sao sinteticos, o stream
packed pertence ao territorio `bN`/V2-L, e os dois desenhos ainda precisam de P4 (topologia regular,
presence/repetition/definition) antes de P5. A gramatica usada e `#PROTO.*`, nunca `#TCF.8H`.

## Update 2026-07-13 — P4 (parcial): def-level+kind fecha presença na forma regular

Lab [`2026-07-13-1955-dataseth-regular-def-levels/`](../2026-07-13-1955-dataseth-regular-def-levels/):
na forma REGULAR, kind **só por folha** foi REFUTADO por contra-exemplo executável (`{}` e `{"b":{}}`
geram streams idênticos e colidem — mesma classe do `null=index` pós-stringificação: a informação
estrutural precisa existir no símbolo). **R2 def-level+kind** (funde `cut@i` + kind terminal num
símbolo por ocorrência; Dremel estendido com `null≠ausente` + especiais) fecha o contra-exemplo e
passa RT em cadeias opcionais com especiais, ragged e 100 linhas regulares. Generaliza o HK do lab
1921 para topologia. **Invariante emergente dos 3 labs**: kind tipado = semântica FIXA; a
representação do stream (tag por instância / domínio no header / def+kind por coluna) é
regime-dependente — candidatos do `min()`, filosofia FLOOR. Falta de P4: repetition levels completos
(objeto-em-array, array-de-array na regular). P5 decide alfabeto/grafia na gramática + dado real
(gate anti-incidente antes de `confirmada-empirica`). Detalhe: `result.md` do lab.

## Update 2026-07-13 — REDO com dados realistas: formatos lado a lado (material P5)

Pedido do owner: os labs anteriores provaram semântica com fixtures pobres; a decisão exige VER os
formatos com dados realistas. Lab
[`2026-07-13-2019-especiais-formatos-lado-a-lado/`](../2026-07-13-2019-especiais-formatos-lado-a-lado/):
entradas visíveis (clientes JSON padrão aninhado; telemetria JSON-like com NaN/Inf de export Python;
tabela tipada de sensores SEM hierarquia) → fluxo semântico (kind por valor) → arquivo de saída real
por formato (A per-instance; RH regular def+kind com payload `tcf.encode` REAL; HOJE stringify; FK
kind-channel) → roundtrip explícito. Fatos estabelecidos: (1) o contrato de especiais é **ortogonal à
hierarquia** (FK = mesmo alfabeto sem cuts); (2) HOJE é menor porque **descarta tipo** (perdas listadas
uma a uma); (3) RH < JSON original nos dois docs; (4) A×RH = regimes, não disputa. **SEM veredito** —
decisão de grafia/alfabeto é do owner (P5), com os arquivos na mão.

## Update 2026-07-13 — VOLTA À BASE: estrutura do tabelão recuperada (owner: "estávamos nos perdendo")

O owner puxou de volta ao insight fundador: hierarquia = **tabela combinatória denormalizada**,
idêntica à multi-col; pai repete por filho; RLE `*N|pai` colapsa e **o run = a multiplicidade**; header
de colchetes só guarda a árvore. Lab
[`2026-07-13-2301-tcf8h-tabelao-recuperado/`](../2026-07-13-2301-tcf8h-tabelao-recuperado/) reproduz isso
com o motor multi-col REAL (`tcf.encode`): `#TCF.8H nome:54,cidade:43,telefones[` + corpo com `*2|Ana`
(2 tel), `*3|Carla` (3 tel); RT-exato (263 B vs 452 B JSON) + array-de-objetos (167 B, com `^1` cross-ref
e seq-RLE do motor). É o dual do EXP-015 (que guarda o pai uma vez, ragged): aqui o pai repete e o RLE
conta — "exatamente a mesma estrutura". **Reordenação de prioridade**: os labs de nulos/NaN/def-levels/
tipos (1835/1955/2019) são a camada SEGUINTE, sobre esta base — não antes dela. Próximo sobre a base:
`{}` 1:1 aninhado, fronteira pai/filho carregada (ambiguidade FD do 1509), multi-array; SÓ ENTÃO tipos.

## Update 2026-07-13 — hierarquia FORTIFICADA + cardinalidade (sobre a base)

Owner: firmar a hierarquia primeiro (gramática do header + uso) + recuperar 1:1/1:N/N:1/N:N; tipos
especiais são ortogonais e vêm depois. Lab
[`2026-07-13-2325-hierarquia-cardinalidade/`](../2026-07-13-2325-hierarquia-cardinalidade/): header
recursivo firme `{}` 1:1 + `[]` 1:N aninhados (chaveado por CAMINHO — corrige o bug de nome-repetido do
1830), RT-exato (endereco⊃geo + telefones = 392 B vs 735 JSON; pedidos⊃itens aninhado = 175 B). **Estudo
de cardinalidade** (peça 7): 1:1→`{}` e 1:N→`[]` ANINHAM; N:1→coluna @dict low-card (não é ramo);
N:N→ponte (fail-loud, 2 arrays/nível = produto cartesiano). Eixo ortogonal (peça 8):
cardinalidade⊥compressibilidade (multiplicidade RLE↔fk vs largura-de-valor @dict). **Segurança**: encode
auto-verifica e recusa (`AmbiguityError`) o que a re-nestação por chave contígua não reverteria (limite
FD/chave — precisa repetition-level, peça 9) — nunca corromper calado. Falta p/ firmar: repetition-level,
N:N/link-posicional, gate real-world. Tipos/nulos = camada SEGUINTE, não bloqueiam.

## Update 2026-07-13 — dual do RLE MEDIDO (owner reapontou; já estava concluído na peça 9)

Owner: na hierarquia o pai não expande de fato (RLE deduzível; colunas com sincronismo). Confere e já
estava concluído — peça 9 (2328): multiplicidade DEDUZÍVEL do nº de filhos, "custo ZERO"; H-CARD-06
(Order Dependency = rep/def do Dremel); teoria §3-4 (RLE↔counts↔fk DUAIS, ×N conservada). Lab
[`2026-07-13-2356-rle-dual-multiplicidade-deduzida/`](../2026-07-13-2356-rle-dual-multiplicidade-deduzida/)
MEDE os dois: **Modelo A** (tabelão, protótipo 2301/2325 — RLE por coluna-pai, multiplicidade repetida
entre irmãs) vs **Modelo B** (nível-aware — colunas na sua granularidade + counts 1×). **Crossover por
largura**: estreito (1 campo-pai) A vence (135<140); largo (11 campos-pai) B vence (423<466). RT-exato
nos dois. Resposta TCF: A e B são candidatos de `min()` (como o FLOOR das natures) — o menor por documento.
Reconciliação: meu protótipo = A (dual explícito, simples); o mínimo p/ registro largo = B. Firmar = owner.

## Update 2026-07-14 — FUNCIONALIDADE + FLUXO do hierárquico FECHADOS (clássicos de transmissão)

Owner: sem payload de API real (isso é gate de PERFORMANCE = `.9`; dá pra simular com encode+compress+
decompress+decode). Agora fechar FUNCIONALIDADE + FLUXO encode/decode com os clássicos de transmissão
(cadastro, pedido, telemetria — a maioria JSON). Lab
[`2026-07-14-0111-hierarquico-fechar-fluxo/`](../2026-07-14-0111-hierarquico-fechar-fluxo/): codec por
SHREDDING em blocos + counts (generaliza envelope P2/P3 + Modelo B/2356). Fecha o que o tabelão integrado
NÃO fechava: **múltiplas listas irmãs** (cadastro tel[] E email[]), **arrays aninhados** (pedido⊃itens),
**ambiguidade de chave** (count ESCRITO, não deduzido), **arrays vazios**. Colunas-pai à granularidade da
pessoa (sem `*N|` redundante); multiplicidade nos `#count`. Dois fluxos RT-exatos: (A) funcional
encode/decode; (B) transmissão simulada encode→gzip/brotli→decode. TCF.H ~40-55% < JSON (forma; performance
= `.9`). Falta p/ firmar: ragged/presença (máscara def-level), N raízes, reconciliar ADR-0031, gate
real-world+perf, tipos (ortogonal). Sem firmar.

## Próxima leitura e próxima ação

Leia este plano junto com:

1. [T-STUDY-HIERARCHICAL-TCF](../../../../tickets/T-STUDY-HIERARCHICAL-TCF.md) - guarda-chuva e sequência R0-R5.
2. [tipos-como-specs.md](tipos-como-specs.md) - o que `bN` já mede e o que ele não decide.
3. [estudo-tcf-hierarquico-mapa.md](estudo-tcf-hierarquico-mapa.md) - topologia, cardinalidade e protótipos anteriores.

A próxima ação proposta é P4: cruzar as formas HDOM/HK com presence/definition/repetition levels, arrays
ragged e a forma regular multirow-com-header. Ela depende de revisão deste plano pelo owner; não há
autorização implícita para alterar o POC atual, o formato ou o core.