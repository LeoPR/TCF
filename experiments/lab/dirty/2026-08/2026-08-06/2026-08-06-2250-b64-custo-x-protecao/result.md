# A verificação de b64: ligada ou desligada? (2026-08-06-2250)

A pergunta pressupõe um **trade-off** — garantia × processamento. Este lab mede os dois lados, e separa uma coisa que a formulação juntava: **quais checagens protegem VALOR e quais só detectam adulteração**.

## A — o custo, medido

| n | payload | `b64decode` | `+validate` | re-codifica | `decode` inteiro | as 3 = |
|---:|---:|---:|---:|---:|---:|---:|
| 200 | 67 ch | 0.9 µs | 0.8 µs | 1.1 µs | 224 µs | **0.50%** |
| 20000 | 6667 ch | 20.3 µs | 21.7 µs | 24.8 µs | 14022 µs | **0.19%** |
| 200000 | 66667 ch | 198.8 µs | 195.9 µs | 234.1 µs | 132478 µs | **0.18%** |

O `tamanho exato` é uma subtração — não aparece na tabela porque não é mensurável. O `validate=True` é um **flag em C**: nas escalas grandes some no ruído.

**As três juntas custam 0.18%–0.50% do `decode`.** O trade-off que a pergunta pressupõe não existe nesta escala.

## B — o que cada checagem realmente segura

Desligando por conjunto e vendo o que **passa como valor errado**:

| sonda | `nenhuma` | `só validate` | `validate+tamanho` | `as três` |
|---|:-:|:-:|:-:|:-:|
| `char-invalido` | rejeita | rejeita | rejeita | rejeita |
| `quatro-invalidos` | passa (igual) | rejeita | rejeita | rejeita |
| `caixa-trocada` | **VALOR ERRADO** | **VALOR ERRADO** | **VALOR ERRADO** | rejeita |
| `padding-extra` | passa (igual) | rejeita | rejeita | rejeita |
| `extensao-zero` | passa (igual) | passa (igual) | rejeita | rejeita |
| `truncado` | rejeita | rejeita | rejeita | rejeita |

`passa (igual)` = o wire foi adulterado e o decode aceita, **mas devolve os valores certos**. `VALOR ERRADO` = devolve dado diferente, em silêncio.

## C — o cruzamento que decide

| checagem | custo | protege VALOR? | o que segura sozinha |
|---|---|:-:|---|
| `validate=True` | ~0 (flag em C) | **não** | chars fora do alfabeto — que sem ela são **descartados** e o payload segue |
| tamanho exato | ~0 (subtração) | **não** | extensão com bytes zero e truncamento |
| **re-codifica** | ~0,17% | **SIM** | a **caixa trocada** — a única sonda que muda valores |

**A intuição se inverte.** A checagem com custo mensurável é a única que fica entre um wire adulterado e **dado silenciosamente errado**. As duas gratuitas só detectam adulteração que devolveria valores corretos.

Se alguma fosse opcional, seriam as **gratuitas** — o que não faz sentido.

## Sobre "desligado na transmissão, ligado em arquivo"

O raciocínio tem base: TCP e TLS já carregam checksum/MAC, então corrupção de **transporte** já é pega uma camada abaixo. Um arquivo em disco não tem essa garantia no nível da aplicação.

Mas a re-codificação **não protege contra corrupção de transporte** — ela protege contra uma propriedade do **próprio base64**: o último char de um payload que não fecha em grupo de 3 bytes carrega bits mortos, e existem várias grafias para os mesmos dados. Isso não vem do canal; vem de quem **produziu** o wire — encoder com bug, biblioteca de terceiro, ou adulteração deliberada. O TLS entrega intacto exatamente aquilo que o outro lado mandou, inclusive se o outro lado mandou uma grafia não-canônica.

E há o argumento inverso do streaming: quem lê incremental quer falhar **cedo**, não depois de já ter emitido metade dos valores.

## Recomendação

**Manter as três ligadas, sem toggle.** Não porque toggle seja ruim — porque aqui ele não compra nada:

- o custo total é **< 1%**, e as duas que sobrariam ligadas num toggle "barato" são justamente as que **não** protegem valor;
- desligar a re-codificação é aceitar **duas grafias para o mesmo dado**, que é exatamente o invariante S1.2 que o formato trava no cabeçalho (ADR-0036) e no modo denso. Um decoder leniente faria `canônico` deixar de ser propriedade do formato e virar política do leitor.

**Se um dia o custo importar** (payload muito grande, CPU crítica), a saída barata não é desligar: é trocar a re-codificação por uma checagem dos **bits mortos do último char** — mesma garantia, O(1) em vez de O(n). Fica registrado como `T-B64-BITS-MORTOS`, não medido aqui.

