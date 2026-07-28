# Proveniencia — T-BN-TIPADO, ganho medido (2026-07-28-0829)

## Por que este lab existe

O owner cobrou: "voce disse que 'o ganho e' bem maior do que eu tinha registrado', cade' o lab
pra provar isso?". Os numeros que eu tinha apresentado sairam de um probe no terminal —
existiam so' no scrollback. Este lab materializa a evidencia.

## Sinteticas — deterministicas, sem RNG

Valores ciclados por `i % k` e aritmetica sobre o indice. **Sem `random`, sem relogio, sem
rede.** Nao ha' documento (CPF/CNPJ/cartao) sintetizado.

13 colunas de GANHO (bool/int/float x k x null) e 7 CONTRA-CASOS, construidos para a proposta
PERDER ou RECUSAR:

| contra-caso | o que ataca |
|---|---|
| `int-k200-unicos` · `int-ordenado` | alta cardinalidade — o dominio inteiro viaja |
| `float-alta-card` | idem, com valor longo |
| `bool-constante` · `int-k1` | `k<=1` — o core e' otimo com RLE, o bN deve RECUSAR |
| `n-pequeno-k2` (n=3) | cabecalho + dominio nao se pagam |
| `int-grande-k4` | valores de 16 digitos com k baixo — o dominio pesa, mas ainda ganha |

Colunas de borda de tipo, escolhidas a dedo:

| coluna | o que exerce |
|---|---|
| `misto-int-float` | `int` e `float` na mesma coluna — o dominio deduplica por STRING |
| `float-integral` (`1.0`/`2.0`) | float que parece int no `repr` |
| **`neg-zero`** | `-0.0` — em Python `-0.0 == 0.0`, so' o `copysign` pega a troca de sinal |

## Reais — fixtures ja' committadas

**Nenhum download.** De `datasets/samples/`. Os CSV dao STRING; o lab converte para
`int`/`float`/`bool`, que e' o que um consumidor faria antes de chamar o `encode` — mas e'
escolha DO LAB, nao do dado, e esta' declarado no README.

| coluna | arquivo | campo | conversao |
|---|---|---|---|
| `real-adult-sex-bool` · `real-adult-class-bool` | `adult-census/adult-sample.csv` | `sex`, `class` | -> bool |
| `real-adult-eduint` | idem | `education-num` | `int` |
| `real-cnpj-matriz-int` | `receita-cnpj/cnpj-2k.csv` | `matriz_filial` | `int` |
| `real-pm25-Is-int` · `Ir-int` · `month-int` | `beijing-pm25/beijing-pm25-sample.csv` | 3 campos | `int` |
| `real-tpch-acctbal-float` | `tpch-sf001/customer-sample.csv` | `c_acctbal` | `float` |

`Ir-int` e `month-int` RECUSAM (`k<=1` na fatia lida) — ficaram na tabela de proposito, sao
contra-exemplo.

## Validacao — e por que nao e' circular

O prototipo NAO reimplementa nada:

```
dados -> _tipo_single_col   (src/tcf)  -> tag + render
      -> dominio_bn.candidatos (src/tcf) -> o wire, com a tag injetada no indice 6
      -> dominio_bn.decode_bn  (src/tcf) -> list[str|None]
      -> decoder._cast_tipo    (src/tcf) -> os tipos de volta
      -> compara com os DADOS ORIGINAIS
```

`decode_bn` e `_cast_tipo` sao as funcoes REAIS que a solda usaria. O `hoje` vem do `encode`
publico. Entao o que se mede aqui e' o que a solda produziria — nao um proxy.

O RT compara **valor, tipo, SINAL e comprimento**. Sinal porque `-0.0 == 0.0` em Python;
comprimento porque `zip` trunca (licao do lab `2026-07-26-2126`).

## Limites declarados

- **Nada soldado**; `src/tcf` intocado. Os `.tcfp` sao proposta — o `decode` publico nao os le'
  (a rota tipada ainda nao conhece o modo `B`).
- As colunas reais tipadas sao **convertidas pelo lab**.
- **gzip e CPU nao medidos.**
- O modo `C` (dominio por ultimo) nao entra — mesma decisao do ADR-0036.
- `NaN`/`+-Inf` fora: `_tipo_single_col` os rejeita antes de chegar aqui.
- O impacto nos gates foi conferido lendo as CONSTANTES dos proprios testes, nao copiadas.

## Reprodutibilidade

`python run.py` regenera byte a byte — sem RNG, sem relogio, sem rede. Sai `0` so' se o RT
estrito passar em todas as colunas.
