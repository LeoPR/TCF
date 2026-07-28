# Proveniencia — espaco completo de delimitacao (2026-07-27-2247)

## A varredura das 145 colunas

A afirmacao "o escape custaria zero no dado real" nao e' suposta: o lab varre **todos** os
CSV de `datasets/samples/`, pega toda coluna com `2 <= k <= 64` (145 colunas) e registra que
char inicia cada valor de dominio. Resultado: so' `> < - espaco ,` aparecem.

Nao e' amostra do mundo — sao as fixtures do repo. Esta' declarado nos limites.

## Sinteticas — deterministicas, sem RNG

Rotulos fixos ciclados por `i % k`, e `num-k4` (`100`..`103`) porque o seq-RLE COLAPSA esse
dominio. **Sem `random`, sem relogio, sem rede.** Sem documento (CPF/CNPJ/cartao) sintetizado.

## Venenos — construidos para quebrar

| coluna | ataca |
|---|---|
| `comeca-com-igual` | o marcador default do M2 (1 colisao) |
| **`todos-comecam-igual`** | o PIOR caso do M2 — 3 escapes, um por valor |
| `contem-backslash` | valor que ja' traz o char de escape |
| `e-o-marcador-m1` (`\|`) | o valor que E' o marcador do M1 |
| `so-digitos` | dominio que o seq-RLE colapsa |
| `com-linha-vazia` | valor vazio no dominio (colide com o padding do M4) |
| **`faixa-saturada`** | um valor usa a FAIXA inteira — o M3 fica sem char pra eleger |

Os dois em negrito produziram resultado: `todos-comecam-igual` mostra o M2 correto pagando 3
escapes; `faixa-saturada` faz o M3 **recusar**.

## Reais — fixtures ja' committadas

**Nenhum download.** De `datasets/samples/`: `adult-sex`, `adult-race`, `adult-workclass`,
`adult-class` (`adult-census/adult-sample.csv`), `cnpj-uf` (`receita-cnpj/cnpj-2k.csv`),
`pm25-cbwd` (`beijing-pm25/beijing-pm25-sample.csv`).

Valores vazios sao pulados; leitura e' fail-loud em nome de coluna inexistente.

## Validacao — e por que nao e' circular

Cada uma das sete montagens tem o **seu proprio leitor independente** (`le_m1`..`le_m7`), que
reimplementa a semantica e acha a fronteira pelo mecanismo daquela variante — sem receber `k`,
sem receber contagem, sem receber o char do marcador (exceto o M3, onde ele vem NO WIRE).
O alvo da comparacao sao os **dados originais**.

E' por isso que os venenos significam algo: um leitor que fosse a inversa da montagem erraria
no mesmo lugar que o emissor e passaria.

Licao aplicada do lab `2026-07-26-0038`, retratado por validacao circular.

## Limites declarados

- **Nada soldado**; `src/tcf` intocado.
- As 145 colunas sao as fixtures do repo, **nao uma amostra do mundo**.
- A garantia de `\<char>` vale para o corpo canonico **de hoje** (medida no lab
  `2026-07-27-2231`). Se `_escape_lit` mudar, muda.
- **gzip e CPU nao medidos.** A metrica de prefixo de streaming esta' no lab `2211`, nao aqui.
- `k=1` fora do escopo: o core resolve com RLE (`*N|valor`).
- A grafia `#TCF.8B<w><n_hex>` e' notacao do lab; o namespace real nao foi decidido.

## Reprodutibilidade

`python run.py` regenera byte a byte — sem RNG, sem relogio, sem rede. Sai `0` so' se todos os
RT dos sete leitores independentes passarem.
