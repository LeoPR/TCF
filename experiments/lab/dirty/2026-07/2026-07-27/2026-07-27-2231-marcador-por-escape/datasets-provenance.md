# Proveniencia — marcador por escape (2026-07-27-2231)

## Varredura da gramatica — exaustiva, nao amostral

A afirmacao central ("o core so' emite `\` seguido de `* 0-9 \ ^ ~`") nao e' suposta: o lab
varre os **95 imprimiveis ASCII**, um por vez, como valor de coluna, e coleta todo char que
aparece depois de um `\` no corpo canonico. O conjunto medido e' comparado com o declarado
(`SEGUEM_ESCAPE`) — se divergir, o lab falha.

Nao varri **nao-ASCII**. Esta' declarado nos limites.

## Venenos — construidos para quebrar, nao para passar

| coluna | ataca |
|---|---|
| `comeca-com-igual` (`=SOMA(A1)`) | o marcador `=` cru do lab anterior |
| `contem-backslash` (`\temp`) | valor que ja' vem com o char de escape |
| `contem-pipe` (`a\|b`) | o char do marcador, sem o escape |
| **`e-o-proprio-marcador`** (`\|`) | o valor que **E'** o marcador |
| `so-digitos` (`100`,`101`,`102`) | dominio que o seq-RLE COLAPSA |
| `com-til-e-asterisco` | os outros chars que o core escapa |

Dois deles (`contem-backslash`, `e-o-proprio-marcador`) **falharam na primeira rodada** e
expuseram um bug no helper de grafia do dominio — nao no marcador. Esta' documentado no README.

Nenhum RNG, nenhum relogio, nenhuma rede. Sem documento (CPF/CNPJ/cartao) sintetizado.

## Reais — fixtures ja' committadas

**Nenhum download.** De `datasets/samples/`, versionada no repo:

| coluna | arquivo | campo | k |
|---|---|---|---:|
| `adult-sex` · `adult-workclass` | `adult-census/adult-sample.csv` | `sex`, `workclass` | 2 · 6 |
| `cnpj-uf` | `receita-cnpj/cnpj-2k.csv` | `uf` | 28 |
| `pm25-cbwd` | `beijing-pm25/beijing-pm25-sample.csv` | `cbwd` | 4 |

Valores vazios sao pulados; leitura e' fail-loud em nome de coluna inexistente.

## Validacao — e por que nao e' circular

O leitor (`le`) e' **independente**: ele acha a fronteira **pelo marcador**, sem receber `k`
nem a contagem de linhas. Recebe so' o wire. O alvo da comparacao sao os **dados originais**.

E' por isso que os venenos significam algo: se o leitor recebesse `k`, ele acertaria a
fronteira por fora e o teste do marcador nao testaria nada.

Licao aplicada do lab `2026-07-26-0038`, retratado por validacao circular.

## Limites declarados

- **Nada soldado**; `src/tcf` intocado. Os `.tcfp` sao proposta.
- A garantia do marcador vale para o **corpo canonico de hoje**. Se `_escape_lit` passar a
  escapar char novo, `SEGUEM_ESCAPE` muda — se isto for soldado, vira TESTE, nao comentario.
- Varredura sobre ASCII imprimivel; **nao-ASCII nao varrido**.
- Metrica de prefixo e' **analitica**, nao cronometrada num transporte real.
- **gzip e CPU nao medidos.**
- A grafia `#TCF.8B<w><n_hex>` e' notacao do lab; o namespace real nao foi decidido.

## Reprodutibilidade

`python run.py` regenera byte a byte. Sai `0` so' se a varredura da gramatica fechar e todos
os RT do leitor independente passarem.
