# A polaridade SOLDADA — single-col stamp (2026-07-27-1535)

Os quatro labs anteriores (`1853`/`1913`/`1954`/`2126`) propunham; o mecanismo vivia no lab e os artefatos eram `.tcfp`, que o núcleo não lia. **Aqui ele está em `src/tcf`** (ADR-0035) e os artefatos em `outputs/` são `.tcf` de verdade — lidos pelo `decode` público.

O *antes* é reconstruível byte a byte sem checkout: a grafia anterior era exatamente `'#TCF.8\n' + _encode_column(dados)`, porque o corpo canônico não mudou — só ganhou uma camada de borda. A comparação é **exata**, não estimada.

## A — antes × depois

### Sintéticas

| coluna | n | antes | depois | Δ | escapes | sufixo | RT |
|---|---:|---:|---:|---:|---:|:-:|:-:|
| `cpf-mascara` | 200 | 3807 | 3009 | **-798** | 800 | `!!` | OK |
| `cnpj-mascara` | 200 | 3947 | 3411 | **-536** | 719 | `!!` | OK |
| `cartao` | 200 | 4805 | 4008 | **-797** | 800 | `!!` | OK |
| `cep` | 200 | 2404 | 2010 | **-394** | 396 | `!!` | OK |
| `telefone` | 200 | 3421 | 3066 | **-355** | 556 | `!` | OK |
| `ip` | 200 | 1695 | 1441 | **-254** | 256 | `!!` | OK |
| `mac` | 200 | 685 | 669 | **-16** | 18 | `!!` | OK |
| `uuid` | 200 | 57 | 51 | **-6** | 8 | `!` | OK |
| `data-iso` | 200 | 2374 | 2208 | **-166** | 381 | `!` | OK |
| `data-br` | 200 | 2224 | 2052 | **-172** | 386 | `!` | OK |
| `timestamp` | 200 | 4539 | 3899 | **-640** | 872 | `!` | OK |
| `moeda` | 200 | 2544 | 2172 | **-372** | 414 | `!!` | OK |
| `coord` | 200 | 2602 | 2216 | **-386** | 388 | `!!` | OK |
| `isbn` | 200 | 3688 | 3203 | **-485** | 687 | `!` | OK |
| `placa` | 200 | 1997 | 1608 | **-389** | 394 | `!!` | OK |
| `sku` | 200 | 2007 | 1809 | **-198** | 200 | `!!` | OK |
| `texto` | 200 | 715 | 715 | 0 | 0 | `—` | OK |
| `frase` | 200 | 6007 | 6007 | 0 | 0 | `—` | OK |
| `nomes` | 200 | 2207 | 2207 | 0 | 0 | `—` | OK |
| `email` | 200 | 2586 | 2586 | 0 | 257 | `—` | OK |
| `binario-01` | 200 | 607 | 607 | 0 | 2 | `—` | OK |
| `sem-digito` | 200 | 1807 | 1807 | 0 | 0 | `—` | OK |
| `uma-linha` | 1 | 14 | 14 | 0 | 1 | `—` | OK |
| `vazia` | 0 | 7 | 7 | 0 | 0 | `—` | OK |
| `so-vazio` | 1 | 8 | 8 | 0 | 0 | `—` | OK |

### Reais (fixtures do repo)

| coluna | n | antes | depois | Δ | escapes | sufixo | RT |
|---|---:|---:|---:|---:|---:|:-:|:-:|
| `retail-stockcode` | 200 | 1240 | 1164 | **-76** | 179 | `!!` | OK |
| `retail-description` | 200 | 3896 | 3896 | 0 | 21 | `—` | OK |
| `lineitem-comment` | 200 | 5314 | 5314 | 0 | 0 | `—` | OK |
| `cnpj-doc` | 200 | 3000 | 2849 | **-151** | 457 | `!` | OK |
| `cnpj-data-inicio` | 200 | 321 | 312 | **-9** | 28 | `!` | OK |
| `pessoas-cpf` | 100 | 1907 | 1509 | **-398** | 400 | `!!` | OK |
| `ibge-municipio` | 100 | 1243 | 1243 | 0 | 0 | `—` | OK |
| `tpch-phone` | 20 | 400 | 335 | **-65** | 78 | `!!` | OK |

## B — o FLOOR

- colunas medidas: **33** (25 sintéticas + 8 reais)
- a polaridade **ativa** em **21**, **recusa** em **12**
- **pior caso: +0 B** — nenhuma coluna sai maior. O FLOOR inclui o custo do próprio sufixo, e o empate fica com a grafia de hoje.
- ganho somado: **-6663 B**
- RT estrito (valor **e** tipo, com guarda de comprimento) pelo `decode` REAL: **33/33**

As que recusam, e o motivo — sempre o mesmo, contado:

| coluna | escapes | por quê |
|---|---:|---|
| `texto` | 0 | coluna sem corrida de dígito literal |
| `frase` | 0 | coluna sem corrida de dígito literal |
| `nomes` | 0 | coluna sem corrida de dígito literal |
| `email` | 257 | 257 escapes não pagam as transições + o sufixo |
| `binario-01` | 2 | 2 escapes não pagam as transições + o sufixo |
| `sem-digito` | 0 | coluna sem corrida de dígito literal |
| `uma-linha` | 1 | 1 escapes não pagam as transições + o sufixo |
| `vazia` | 0 | coluna sem corrida de dígito literal |
| `so-vazio` | 0 | coluna sem corrida de dígito literal |
| `retail-description` | 21 | 21 escapes não pagam as transições + o sufixo |
| `lineitem-comment` | 0 | coluna sem corrida de dígito literal |
| `ibge-municipio` | 0 | coluna sem corrida de dígito literal |

## C — os três gates byte-canônicos

| gate | pinado | medido | bate? |
|---|---:|---:|:-:|
| **D1-D9** (9 single-col) | 1545 | 1545 | OK |
| **D17a** (multi-col `.8M`) | 300 | 300 | OK |
| **real-world** (3 × 2k) | 89430 | 89430 | OK |

Detalhe do D1-D9 — quais datasets a polaridade tocou:

| dataset | pinado | medido | RT |
|---|---:|---:|:-:|
| D1-emails-simples | 125 | 125 | OK |
| D2-emails-quote-id | 173 | 173 | OK |
| D3-stress-substring | 184 | 184 | OK |
| D4-caos-mix | 120 | 120 | OK |
| D5-padroes-multiplos | 267 | 267 | OK |
| D6-poucos-em-ruido | 274 | 274 | OK |
| D7-aninhamento | 222 | 222 | OK |
| D8-cabeca-cauda | 107 | 107 | OK |
| D9-frequencia-alta | 73 | 73 | OK |

`D17a` **não mudou**: o `.8M` está fora do escopo do weld. Confirma que a solda ficou onde foi declarada.

## D — os casos da auditoria adversarial, agora como regressão

A auditoria do lab `2126` reproduziu dois defeitos de eleição do char. A `FAIXA` passou a excluir por **classe** (só pontuação). Os dois casos, re-rodados contra o código soldado:

| caso | o que quebrava | agora |
|---|---|---|
| dígito eleito | `0` eleito funde com a corrida | `#TCF.8:` — char `:` (pontuação), RT OK |
| letra eleita | `b` eleito vira `#TCF.8b` de bool | `#TCF.8{` — char `{` (pontuação), RT OK |

`FAIXA` = `!"#$%&'()+-./:;<=>?@[]_`{}` (26 chars). Nem dígito, nem letra, nem gramática.

