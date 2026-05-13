# 06 — aninhado em emails e URLs

## Princípio / motivação

Repete o experimento [05](../2026-05-10-05-patricia-aninhado/) com
**dados mais ricos**: emails e URLs hierárquicas. O algoritmo de
encoder, decoder e Patricia é byte-idêntico — o objetivo é ver como
o aninhamento se comporta em hierarquias naturais com prefixos
longos e cadeias profundas reais.

Ferramenta atemporal: o encoder aninhado do 05 funciona sob
qualquer dataset; aqui validamos isso em entradas de aplicação
realista.

## Propósito

Responde a duas perguntas:

1. **Viabilidade em dados realistas**: a serialização aninhada
   suporta cadeias Patricia de 3+ níveis com prefixos longos
   (URLs)?
2. **Comportamento**: como a árvore Patricia se distribui em
   emails (vários nomes, vários domínios) e URLs (path comum, ou
   multi-recurso compartilhando um base path)?

## Comparação

- **Compara com**: [05](../2026-05-10-05-patricia-aninhado/).
- **É comparável?** Parcialmente. Algoritmo idêntico, datasets
  diferentes. Não é teste do algoritmo (já validado em 05), é teste
  de **comportamento em entrada realista**.
- O que se mostra: a árvore Patricia produzida + o TCF gerado lado
  a lado para 4 cenários novos.

## Cenários e valores possíveis

20 linhas cada, com repetições e dispersão.

| Dataset | Conteúdo | Hipótese sobre Patricia |
|---|---|---|
| D1 — emails-um-dominio | `user001..user010@gmail.com`, 10 únicos | Prefixo `user00` + `user0`; user010 cai em `user0` lateral |
| D2 — emails-multi-dominio | 4 nomes (`maria.silva`, `joao.souza`, `ana.lima`, `pedro.alves`) × 3 domínios | Cada nome vira pai `nome@`; 3 filhos por nome (gmail, hotmail, yahoo) |
| D3 — urls-path-comum | `https://api.example.com/v1/users/N` com N de 1 a 10 | Um único pai grande com o path inteiro |
| D4 — urls-multi-recurso | mix de `users/N`, `orders/10X`, `products/5N` sob mesma base | Avô `https://api.example.com/v1/` + 3 filhos intermediários (users, orders, products) + folhas |

## Resultado observado

Roundtrip **4/4 OK**.

| Dataset | linhas | nós | top | filhos | RLE | bytes |
|---|---:|---:|---:|---:|---:|---:|
| D1 | 20 | 12 | 1 | 11 | 20 | 533 |
| D2 | 20 | 16 | 4 | 12 | 20 | 632 |
| D3 | 20 | 11 | 1 | 10 | 20 | 435 |
| D4 | 20 | 16 | 1 | 15 | 20 | 566 |

### Cadeias aninhadas observadas

- **D1**: aninhamento de **3 níveis** numa única linha:
  ```
  no1: filho_de(no2=decl filho_de(no3=decl folha "user0") + "0") + "1@gmail.com"
  ```
  Linha única declara 3 nós em cascata: `no3="user0"`, `no2="user00"`,
  `no1="user001@gmail.com"`.

- **D4**: aninhamento de **3 níveis** + reaproveitamento do avô em
  ramos paralelos:
  ```
  no1: filho_de(no2=decl filho_de(no3=decl folha "https://api.example.com/v1/") + "users/") + "1"
  no4: filho_de(no5=decl filho_de(no3) + "orders/10") + "0"
  no8: filho_de(no9=decl filho_de(no3) + "products/5") + "0"
  ```
  Primeira linha declara o avô `no3`. Linhas seguintes (orders,
  products) reaproveitam `no3` para declarar novos filhos
  intermediários (`no5`, `no9`).

Ver [conclusoes.md](conclusoes.md) para o TCF completo de cada
cenário com leitura linha a linha.

## Limitações

- 4 datasets pequenos (20 linhas). Não fala sobre escala.
- Patricia só detecta **prefixos** comuns. Em emails como
  `user001@gmail.com`, o sufixo `@gmail.com` é compartilhado mas
  não fatorado pelo algoritmo atual. Sufixo-DICT seria outra
  ferramenta.
- Distribuição de domínios em D2 é uniforme por construção
  (cada nome aparece em todos 3 domínios). Realidade tem
  distribuição mais skewed.
- URLs em D3/D4 são sintéticas com base path fixo. URLs reais com
  query strings, fragmentos, ports, etc não foram testadas.
- Bytes reportados não são comparados com formato compacto nem com
  CSV/JSON. Apenas registrados como descritivos.
- Algoritmo Patricia herda as decisões do exp 02 (gulosa,
  MIN_PREFIXO=3, MIN_GRUPO=2). Outras heurísticas não foram
  testadas.

## Como reproduzir

```bash
cd experiments/lab/dirty/2026-05-10-06-aninhado-emails-urls
python run.py
```

Imprime estatísticas + árvore + TCF inteiro para cada cenário.
Arquivos em `encoded/*.tcf` e `decoded/*.csv`.
