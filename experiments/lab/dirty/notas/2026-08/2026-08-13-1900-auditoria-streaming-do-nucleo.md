# Auditoria: o núcleo suporta o modelo de streaming do owner?

**2026-08-13** · 4 lentes sobre o código real (busca interrompível · dicionário congelado ·
dependência do fim · booleano sob demanda), com file:line e medição. Os 4 verificadores
adversariais morreram no limite de gasto; os achados **críticos foram re-verificados à mão**
(marcados ✔ abaixo). O que não foi re-verificado está marcado ⚠ e vale como indicação.

As 3 afirmações auditadas, do owner:

> **(A)** *"o núcleo tem maleabilidade para parar a busca e entregar pedaços… se em algum
> momento passar um tempo, é possível pegar o que já foi coletado, entregar adiante.
> obviamente existe o risco dele não conseguir melhores comparações"*
> **(B)** *"depois que ele para pra entregar, ele fica com dicionários cada vez mais
> fechados, pois ele precisou congelar o que deu pra entregar em cada etapa"*
> **(C)** *"numa cadeia de true e false, mandar pedaços não faz diferença… o decode fica
> coletando e descomprimindo de acordo com a demanda. Ele só falha se tiver algo no final."*

---

## O achado que reordena tudo: o critério já está soldado ✔

O critério de (C) — *"só falha se tiver algo no final"* — **não é uma proposta nova; é o
critério que já governou uma decisão de design do projeto**, e está escrito em
`src/tcf/encoder.py:484-489`:

> *"Só o modo `B` (domínio primeiro) concorre por DEFAULT. O `C` (domínio por último) é ~1 B
> menor e por isso venceria SEMPRE num min() cego — mas ele **NÃO STREAMA**: o leitor precisa
> do payload inteiro antes de emitir o 1º valor (17× mais buffer numa coluna de 2000 linhas).
> **Trocar streaming por 1 byte, calado, seria a decisão errada tomada pelo critério errado.**"*

O projeto já recusou 1 byte de ganho para preservar entrega progressiva. Não há o que
convencer — há um invariante a **nomear** e a estender às rotas que ainda o violam.

E de fato **nenhuma rota emitida hoje tem trailer**: `.8M` e `.8H` põem o meta na linha 1,
single-col é header+corpo, bN emitido é o `B` (domínio antes dos bits). A única grafia com
"algo no final" é o `#TCF.8C` — decodável e deliberadamente nunca emitido.

## (C) — o wire dá razão ao owner; o `decode()` é que recusa ⚠

Um leitor de prefixo escrito à mão (header → domínio até `=` → grupos base64 completos →
bits) **entrega valores corretos de prefixos que o `decode()` público rejeita**: numa coluna
categórica, o 1º valor sai com 33% do fio; a 50% saem 60 valores, todos corretos.

O que recusa é uma checagem de integridade, não o layout:
`valida_payload_b64` exige `len(raw) == ceil(n*w/8)` **exato**
(`composicional/dominio_bn.py:182-187`), usada pelas três rotas densas. É guarda contra wire
adulterado — e é exatamente o que impede consumo parcial, porque "90% do que chegou" é
indistinguível de "wire truncado" para o validador.

Ou seja: **a afirmação (C) descreve corretamente o WIRE e incorretamente o CÓDIGO.**

Duas correções ao enquadramento, ambas medidas:

- **O exemplo escolhido é o pior caso, não o mais fácil.** Uma cadeia de true/false cai na
  rota densa (`#TCF.8b1`), onde o decode recusa **100%** dos prefixos. Régua fechada para o
  bool denso: multiplicador ≈ `1 + 90/valores_por_fatia` — acima de ~1000 valores/fatia é
  1,07× (o owner está certo), abaixo de ~150 passa de 1,5×. E o **pior caso da régua inteira**
  é bool de baixa entropia: constante em 60 fatias = 52,5×, e 494× em fatias de 10 — pior que
  data com spec (16,46×).
- **No `.8M`/`.8H` não há "algo no final" — há tudo do começo espalhado até o final.** O
  layout é colunar: a linha 0 só fecha depois de **67% a 97%** do fio (4 a 32 colunas).
  Entregar linhas em pedaços ali não é ajuste de decoder, é outro layout.

E uma suspeita minha **refutada**: `min_header=True` (última coluna sem size) não é
dependência do fim — é a única coluna que o encoder poderia emitir sem saber o tamanho. O
bloqueio do ADR-0018 vale para as colunas **não-últimas** do `.8M`/`.8H`, e é **falso** no
single-col, que não tem size no header.

## (A) — metade do núcleo já é online; a outra metade é passada-a-passada ⚠

- **O OBAT já decide-enquanto-varre e nunca revisita** (`core/online.py:210-248`): consulta
  só índices anteriores, insere o corrente **depois** da decisão. É a peça que sustenta a
  intuição do owner, e ela já existe.
- **O HCC é o oposto**: `while True:` com `Counter` zerado no topo de cada volta
  (`composicional/syntax.py:384-398`), re-varrendo tudo. Só a re-contagem é ~54% do encode
  da coluna.
- **O preço de parar está medido**: 1 alias adotado em vez de 99 custa **+0,68% a +4,43%**
  de bytes e devolve **5,8× a 8,8×** de tempo, com round-trip verde em toda a varredura. É
  exatamente o *"risco de não conseguir melhores comparações"* que o owner antecipou —
  pequeno e proporcional.
- **Já existe um budget, e ele está SATURADO** ✔: `if len(iter_traces) >= 99: break`
  (`syntax.py:522`). Colunas de texto livre batem no teto exato; soltando para 200 o wire
  **encolhe** 0,71% e 1,09%. Não é budget de tempo, não é configurável, e já está deixando
  compressão na mesa. `grep` por `time.|perf_counter|deadline|timeout|budget|elapsed` em
  `src/tcf/`: **zero ocorrências**.
- **Bloqueios duros para entregar de fato**: `min_len` é global (decide os tokens das
  primeiras linhas a partir da coluna inteira); a **polaridade** elege o char do byte 6
  varrendo o corpo todo (acrescentar um valor no fim muda o byte 6); o **FLOOR** compara
  wires completos (um valor novo no fim vira a rota inteira); e `_detect_compositions`
  reescreve in-place **38% a 66%** das linhas a cada alias adotado — linha já entregue seria
  invalidada retroativamente. **58% a 86%** do encode roda antes da primeira linha de corpo
  existir.

## (B) — a propriedade existe no wire; o encoder faz o contrário ✔

A tabela de fragmentos da rota core é **append-only** e cada referência é índice posicional
global (`syntax.py:836-839`). Isso é literalmente o *"congela o que já emitiu"*. E pulsos que
compartilham o dicionário do anterior **já são wires válidos hoje** — verificado à mão em 600
e-mails, cortando o wire pronto no limite de linha:

```
prefixo 1 linha  →   1 valor,  todos ok
prefixo 2 linhas →  10 valores, todos ok
prefixo 3 linhas → 100 valores, todos ok
prefixo 4 linhas → 600 valores, todos ok
```

**Mas o encoder de hoje não fica "com dicionários cada vez mais fechados" — ele joga o estado
fora e recomeça do zero a cada `encode()`.** Não existe assinatura que aceite ou devolva
estado (`_encode_column`, `processar`, `Syntax.encode`). A unidade mínima de congelamento é
uma chamada completa — justamente a que descarta o dicionário.

### ⚠ ARMADILHA VERIFICADA: concatenar corrompe calado ✔

A intuição natural de quem for implementar pulsos — *encoda o pedaço 1, encoda o pedaço 2,
concatena* — **produz dado errado sem erro nenhum**. Verificado à mão, 600 e-mails em dois
blocos de 300:

```
decode(cabeçalho + corpo_A + corpo_B)  →  600 valores, 299 ERRADOS, zero exceção
```

A causa: as referências são índices posicionais na tabela **acumulada**, e a gramática não
tem marcador de reset — o pulso 2 sempre fala do dicionário do pulso 1. Nas outras rotas é
fail-loud (bN: *"conteúdo após o bloco de bits"*), só a core cala.

**Cortar** um wire pronto é seguro; **concatenar** wires independentes é corrupção silenciosa.
São operações opostas e parecem a mesma coisa.

### E um contra-intuitivo medido ⚠

Fatias que compartilham dicionário são **mais caras** que fatias independentes nos tipos de
dicionário forte: em categoria k=5, o wire cortável custa 5,10× o emitido (1769 B contra
347 B); em booleano-string, 10,67×. O que morre ao cortar **não é o dicionário** — é o
bit-packing/RLE que roda sobre a coluna inteira. Congelar dicionário não recupera isso.
Onde o compartilhamento paga é no **afixo** (600 e-mails: 73 B contra 383 B = 5,25×), e ali
ele já é expressável — falta API, não formato.

## Achado colateral: 4% a 17% do encode é desperdício puro ⚠

`build_trace` e `build_rede` são chamados **incondicionalmente** no encode do HCC, mesmo sem
`side_outputs` (`syntax.py:762-777` — confirmado por leitura ✔). Custo exclusivo medido:
4,2% / 3,7% / 7,3% em colunas reais e **17,1%** numa cadeia true/false. Contradiz o contrato
*"overhead zero sem side_outputs"* escrito em `side_outputs.py:10-12`. Condicionar devolve
esse tempo **sem mudar um byte do wire**.

## O que sai daqui, em ordem de custo

1. **Condicionar `build_trace`/`build_rede`** a `side is not None` — devolve 4-17% do encode,
   zero byte alterado, alinha código e contrato escrito.
2. **Transformar o teto `>= 99` em parâmetro** (`PipelineConfig` é o lugar pronto) — o efeito
   já está medido nos dois sentidos: apertar dá 5,8-8,8× de tempo por +0,7-4,4% de bytes;
   soltar para 200 encolhe o wire ~1%.
3. **Retomada do decode**: `frags`/`prox_idx`/`nos_decl` são 3 locais de um laço que já é um
   fold (`syntax.py:904-967`); expor como entrada/saída torna entrega progressiva O(n) em vez
   de O(n²) — hoje re-decodar o prefixo custa 446× (1116 ms contra 2,5 ms em 600 pulsos).
4. **Modo de leitura parcial** ao lado do canônico, para as rotas densas — mudança de
   decoder, zero mudança de formato (o leitor à mão já provou que os bits estão lá).
5. **Guarda contra concatenação** — hoje a rota core aceita e corrompe calado.

Nada disso é `.8`. O item 1 é o único que não muda comportamento nenhum.
