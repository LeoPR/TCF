# 2026-08-06-2250 — A verificação de b64: ligada ou desligada?

> *"não sei ainda se ele fica ligado ou desligado (…) por um lado é uma garantia com
> integridade, mas gasta processamento; por outro, é suspeitar que o arquivo tenha defeitos.
> Talvez fazer algo como pra transmitir manter desligado, e em arquivo ligado."*

A pergunta pressupõe um **trade-off**. Medindo os dois lados, ele não existe nesta escala — e
a intuição sobre *qual* checagem é a cara **se inverte**.

## A — o custo

| n | payload | as 3 checagens = |
|---:|---:|---:|
| 200 | 67 ch | **0,58%** do `decode` |
| 20 000 | 6 667 ch | **0,17%** |
| 200 000 | 66 667 ch | **0,18%** |

O `tamanho exato` é uma subtração. O `validate=True` é um **flag em C** — nas escalas grandes
some no ruído. O único com custo mensurável é a **re-codificação**, ~0,17%.

## B — o que cada uma realmente segura

| sonda | nenhuma | só `validate` | `validate`+tamanho | as três |
|---|:-:|:-:|:-:|:-:|
| char inválido | rejeita | rejeita | rejeita | rejeita |
| quatro `!!!!` | passa (igual) | rejeita | rejeita | rejeita |
| **caixa trocada** | **VALOR ERRADO** | **VALOR ERRADO** | **VALOR ERRADO** | **rejeita** |
| padding `==` extra | passa (igual) | rejeita | rejeita | rejeita |
| extensão zero `+AAAA` | passa (igual) | passa (igual) | rejeita | rejeita |
| truncado | rejeita | rejeita | rejeita | rejeita |

`passa (igual)` = o wire foi adulterado, o decode aceita, **mas devolve os valores certos**.

## C — o cruzamento que decide

| checagem | custo | protege VALOR? |
|---|---|:-:|
| `validate=True` | ~0 (flag em C) | **não** |
| tamanho exato | ~0 (subtração) | **não** |
| **re-codifica** | ~0,17% | **SIM** — a única |

**A intuição se inverte.** A única checagem com custo mensurável é a única que fica entre um
wire adulterado e **dado silenciosamente errado**. As duas gratuitas só detectam adulteração
que devolveria valores corretos.

Se alguma fosse opcional, seriam as **gratuitas** — o que não faz sentido.

## Sobre "desligado na transmissão, ligado em arquivo"

O raciocínio tem base: TCP e TLS já carregam checksum/MAC, então corrupção de **transporte**
é pega uma camada abaixo.

Mas a re-codificação **não protege contra corrupção de transporte**. Ela protege contra uma
propriedade do **próprio base64**: o último char de um payload que não fecha em grupo de 3
bytes carrega bits mortos, e existem várias grafias para os mesmos dados. Isso não vem do
canal — vem de **quem produziu** o wire: encoder com bug, biblioteca de terceiro, ou
adulteração deliberada. O TLS entrega intacto exatamente o que o outro lado mandou,
**inclusive** se o outro lado mandou grafia não-canônica.

E há o argumento inverso do streaming: quem lê incremental quer falhar **cedo**, não depois
de ter emitido metade dos valores.

## Recomendação

**Manter as três ligadas, sem toggle** — não por princípio, por medição:

- o custo total é **< 1%**, e as duas que sobrariam num toggle "barato" são justamente as que
  **não** protegem valor;
- desligar a re-codificação é aceitar **duas grafias para o mesmo dado** — o invariante S1.2
  que o formato já trava no cabeçalho (ADR-0036) e no modo denso. Um decoder leniente faria
  `canônico` deixar de ser propriedade do **formato** e virar política do **leitor**.

**Se um dia o custo importar** (payload enorme, CPU crítica), a saída barata não é desligar:
é trocar a re-codificação por uma checagem dos **bits mortos do último char** — mesma
garantia, O(1) em vez de O(n). Registrado como `T-B64-BITS-MORTOS`; **não medido aqui**.

## Um bug do próprio lab

A primeira rodada deu **"rejeita" nas 24 células**: meu `_partes` devolvia as linhas sem o
cabeçalho, e o wire mutado saía decapitado. A tabela uniforme demais foi o que denunciou —
quando toda célula concorda, geralmente o instrumento está quebrado, não o fenômeno.

## Rodar

```
python run.py
```
`le_parcial(wire, quais)` decodifica aplicando só o subconjunto de checagens pedido — é o que
permite isolar o que cada uma segura.
