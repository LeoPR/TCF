# Proveniencia — dominio primeiro / streaming (2026-07-27-2211)

## Sinteticas — deterministicas, sem RNG

Rotulos fixos (`ativo`, `inativo`, `suspenso`, `cancelado`, `revisao`, `arquivado`,
`pendente`) ciclados por `i % k`. **Sem `random`, sem relogio, sem rede.** Nao ha' documento
(CPF/CNPJ/cartao) sintetizado neste lab.

| coluna | por que existe |
|---|---|
| `str-k2`..`str-k7`, com e sem null | o recorte pedido (bool + 3 a 7 tipos) |
| `num-k4` (`100`..`103`) | dominio que o **seq-RLE COLAPSA** em 1 linha — e' o caso que derruba "leia k linhas" |
| **`veneno-igual`** | valor de dominio comecando com `=`, para QUEBRAR a variante F2 |

O `veneno-igual` existe para produzir resultado negativo, e produziu: F2 falha, F1 passa.
`=` nao e' char exotico em dado — formula de planilha, base64 embutido, query string.

## Reais — fixtures ja' committadas

**Nenhum download.** Todas de `datasets/samples/`, versionada no repo:

| coluna | arquivo | campo | k |
|---|---|---|---:|
| `adult-sex` | `adult-census/adult-sample.csv` | `sex` | 2 |
| `adult-workclass` | idem | `workclass` | 6 |
| `cnpj-situacao` · `cnpj-uf` | `receita-cnpj/cnpj-2k.csv` | `situacao`, `uf` | 2 · 28 |
| `pm25-cbwd` | `beijing-pm25/beijing-pm25-sample.csv` | `cbwd` | 4 |

`cnpj-uf` (n=2000, k=28) e' o caso que separa os dois eixos: 1 byte de diferenca entre as
montagens, 17x de diferenca no prefixo.

Valores vazios sao pulados; leitura e' fail-loud em nome de coluna inexistente.

## Validacao — e por que nao e' circular

Cada montagem tem o **seu proprio leitor independente** (`le_f1`..`le_f4`), que reimplementa a
semantica — le' o cabecalho posicionalmente, acha o limite do bloco pelo mecanismo daquela
variante, desempacota os bits e mapeia pelo dominio. O alvo da comparacao sao os **dados
originais**, nunca a inversa da montagem.

Foi essa independencia que fez o `veneno-igual` significar alguma coisa: se o leitor fosse a
inversa, ele cortaria no mesmo lugar errado que o emissor e passaria.

Licao aplicada do lab `2026-07-26-0038`, retratado por validacao circular.

## Limites declarados

- **Nada soldado**; `src/tcf` intocado. Os `.tcfp` sao proposta — o `decode` publico nao os le'.
- A metrica de prefixo e' **analitica** (cabecalho + dominio + 1 quarteto de b64), nao
  cronometrada num transporte real.
- **gzip e CPU nao medidos.**
- Nao medi o caso de o **dominio em si** chegar em pedacos (stream dentro do stream).
- A grafia `#TCF.8B<w><n>L<linhas>` e' notacao do lab; o namespace real nao foi decidido.

## Reprodutibilidade

`python run.py` regenera byte a byte — sem RNG, sem relogio, sem rede. Sai `0` so' se todos os
RT dos leitores independentes passarem (a falha esperada do F2 no veneno e' reportada na
tabela, nao conta como falha do lab).
