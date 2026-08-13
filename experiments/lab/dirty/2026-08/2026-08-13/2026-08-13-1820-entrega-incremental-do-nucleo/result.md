# Resultado — o que o núcleo já entrega em pedaços, e o que não

9 casos, 0 falhas. O wire é encodado **uma vez** e entregue em prefixos de linhas
íntegras: custo em bytes **zero** por construção. A pergunta é *quanto cada pedaço
recebido já entrega*.

## A curva de entrega

| caso | wire | linhas de corpo | pontos de entrega | curva (valores corretos por prefixo) |
|---|---:|---:|---:|---|
| `bool-blocos` | 36 B | 3 | **3** | 200 → 400 → 600 |
| `texto` | 68 B | 5 | **5** | 1 → 2 → 10 → 100 → 600 |
| `email` | 73 B | 4 | **4** | 1 → 10 → 100 → 600 |
| `bool-alternado` | 124 B | 3 | 1 | –, –, 600 |
| `bool-aleatorio` | 124 B | 3 | 1 | –, –, 600 |
| `categoria-k5` | 346 B | 6 | 1 | –, –, –, –, –, 600 |
| `bool-tudo-true` | 17 B | 1 | 1 | 600 |
| `data-spec` | 26 B | 1 | 1 | 600 |
| `data-uteis-spec` | 34 B | 1 | 1 | 600 |

**"Pontos de entrega"** é a granularidade natural de streaming daquela coluna: em quantos
pedaços úteis o mesmo wire se deixa cortar, sem re-encodar nada.

## Sobre a afirmação (C) — está certa, e o regime decide

> *"quando se acha coisas como uma cadeia de true e false, mandar pedaços não faz diferença,
> pois o decode fica coletando e descomprimindo de acordo com a demanda"*

**Confirmado para booleano em blocos** — e de graça: o wire já sai como três marcadores
autocontidos, e cada um entrega 200 valores no ato.

```
#TCF.8
*200|true        ← entregue: 200 valores
*200|false       ← entregue: 400
*200|^1          ← entregue: 600     (`^1` = referência ao fragmento 1, PRA TRÁS)
```

**Não vale para booleano alternado/aleatório**, e a razão não é a que se esperaria. Nesse
regime o núcleo escolhe **bN de domínio** (ADR-0036), e o corpo fica assim:

```
#TCF.8B1258
true                                    ← o domínio, NA FRENTE
false                                   ← idem
=YUYr7WczJOQ28oWMpCnMGsX7Vdgo8bMph…     ← 600 índices empacotados em UMA linha
```

Ou seja: **não há nada no final**. O dicionário vem primeiro, as referências apontam para
trás. O formato satisfaz o seu critério. O que limita é a **implementação**: o decode corta
em fronteira de linha, e dentro daquela linha densa é tudo-ou-nada. Entregar metade dela é
possível em princípio (os índices são posicionais), só não está escrito.

## O que isso revela: granularidade e compressão são antagônicas

A granularidade de entrega é o número de **linhas** do corpo, e quem decide isso é o
mecanismo de compressão que venceu:

| mecanismo | forma no corpo | pontos de entrega |
|---|---|---:|
| RLE por bloco | uma linha por bloco | muitos |
| OBAT por afixo | uma linha por fragmento | vários |
| bN de domínio | domínio + **uma** linha densa | 1 |
| seq-RLE (`*N+d\|`, `*N~…\|`) | **uma** linha | 1 |

`data-spec` é o extremo: 600 datas em **26 bytes e uma linha**. Máxima compressão, mínima
granularidade — não há meio de entregar metade sem re-emitir.

Isso é a mesma tensão que o lab das 17h40 mediu pelo outro ângulo: lá, **re-emitir** fatias
custa caro justamente para quem comprime bem (data com spec: 16,46×); aqui, **cortar** o
wire pronto rende poucos pedaços justamente para os mesmos. Compressão global e entrega
progressiva puxam em direções opostas, e isso vale para qualquer tipo — não é traço da data.

## Correção de método em relação ao lab das 17h40

Aquele lab mediu **p wires independentes** (cada fatia re-encodada do zero), o que responde
"quanto custa emitir p wires" — não é o modelo descrito aqui. Os números de lá continuam
válidos para *aquela* pergunta (quando o emissor **não pode** manter estado entre pedaços);
este lab responde a outra (quando o wire já existe e só é entregue em partes). As duas
perguntas são reais e têm respostas diferentes; confundi-las foi erro meu.

## O que fica em aberto

- **(A) parar a busca por tempo** e **(B) dicionário congelado a cada entrega**: são sobre
  o *encoder*, não observáveis pela API pública — dependem de auditoria do código (em
  andamento) e, provavelmente, de instrumentação nova.
- **Entrega dentro de uma linha densa** (bN): os índices são posicionais, então um prefixo
  deveria render valores. Não está implementado — e é o que separaria `bool-aleatorio` de
  1 para ~N pontos de entrega.
- Nenhum caso desta rodada devolveu valor errado sem erro. (Com corte em byte **arbitrário**
  — corrupção, não streaming — isso acontece; ver a nota que acompanha.)
