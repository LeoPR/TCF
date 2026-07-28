# 2026-07-27-2211 — Domínio PRIMEIRO: o eixo que faltava

Você apontou que eu medi o eixo errado sozinho:

> *"se deixar a lista depois e a transmissão for em stream, tem que esperar carregar tudo pra
> saber que é a lista. A lista no final é só pra uma questão de lote total."*

Está certo, e a diferença é de **ordem de grandeza** — não de bytes. Este lab põe os dois
eixos lado a lado:

```
bytes     quanto o wire ocupa
prefixo   quanto o leitor precisa BUFFERIZAR antes de emitir o 1º valor
```

## As quatro montagens

| | delimitação | bytes | prefixo |
|---|---|---|---|
| **F1** | contagem de linhas no cabeçalho (`L<hex>`) | +1-2 B | cabeçalho + domínio + 4 |
| **F2** | marcador `=` abrindo o b64, padding dropado | −0-2 B | cabeçalho + domínio + 4 |
| **F3** | b64 primeiro, domínio no fim | **+0 B** | **o wire inteiro** |
| **F4** | tamanho em bytes no cabeçalho (`:<hex>`) | +2-4 B | cabeçalho + domínio + 4 |

## Em bytes elas empatam; em prefixo, não

| coluna | n | k | F1 | F2 | F3 | F4 | prefixo F2 | prefixo F3 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `adult-sex` | 100 | 2 | 44 | 41 | 42 | 44 | **26** | 42 |
| `adult-workclass` | 93 | 6 | 120 | 118 | 118 | 121 | **74** | 118 |
| `cnpj-situacao` | 2000 | 2 | 358 | 355 | 356 | 358 | **24** | 356 |
| **`cnpj-uf`** | 2000 | 28 | 1767 | 1764 | 1764 | 1767 | **100** | **1764** |
| `pm25-cbwd` | 100 | 4 | 61 | 58 | 59 | 61 | **27** | 59 |

**As quatro ficam dentro de 3 B uma da outra** — ruído em qualquer coluna real. Mas em
`cnpj-uf` o prefixo é **100 B contra 1764 B: 17×**, para a mesma informação e 1 byte de
diferença.

Então sua conclusão — *"poderíamos ter os dois"* — é a certa, e a escolha **não é de bytes**:

| | quando |
|---|---|
| **domínio primeiro** | default: stream, pipe, resposta HTTP, consumo incremental |
| **b64 primeiro** | lote fechado, arquivo em disco, quando 1-3 B importam e ninguém lê incrementalmente |

## O `=` é deduzível — sua observação estava certa

O padding do base64 sai do número de bytes, que sai de `n` e `w`, que já estão no cabeçalho.
Dropar e recolocar reconstrói byte a byte (verificado de 1 a 9 bytes). Economiza 0-2 B.

Então o `=` **como terminador é mesmo dispensável**, e liberá-lo para **abrir** o bloco
resolveria a delimitação de graça.

## Mas o marcador `=` quebra — e isso é medição, não suposição

Se um valor do **domínio** começar com `=`, o leitor corta no lugar errado:

```
F2 (falha)                          F1 (passa)
#TCF.8B278                          #TCF.8B278L3
=SOMA(A\1)   ← o leitor corta aqui  =SOMA(A\1)
normal                              normal
outro                               outro
=GGGG…                              GGGG…
```

`=` não é char exótico em dado — fórmula de planilha, base64 embutido, query string. F1 não
tem esse risco porque a contagem de linhas não reserva char nenhum.

Se o `=` for mesmo o marcador, ele precisa ser **escapado no domínio** — e aí some a economia
que o justificava.

## Recomendação

1. **F1 como default** — domínio primeiro, contagem de linhas no cabeçalho. Custa 1-2 B,
   streama, e não reserva char.
2. **F3 como modo extra** — b64 primeiro, para lote fechado. É o *"formato de compressão
   extra"* que você descreveu.
3. **F2 fica registrado** — a ideia é boa e a economia do padding é real, mas o marcador
   colide com dado. Só fecha se o `=` for escapado, o que consome de volta o que ele
   economiza.

O par F1/F3 é a materialização do que você disse: **os dois**, escolhidos pelo modo de
transporte, não pelo tamanho.

## Limites

- **Nada soldado**; `src/tcf` intocado. Os `.tcfp` são proposta.
- A métrica de prefixo é **analítica** (cabeçalho + domínio + 1 quarteto de b64), não
  cronometrada num transporte real.
- Não medi CPU, nem gzip, nem o caso de o domínio **em si** chegar em pedaços.
- A grafia `#TCF.8B<w><n><L<linhas>>` é notação do lab; o namespace real não foi decidido.

## Rodar

```
python run.py
```
`montagens.py` tem as quatro montagens, os quatro **leitores independentes** e a métrica de
prefixo.
