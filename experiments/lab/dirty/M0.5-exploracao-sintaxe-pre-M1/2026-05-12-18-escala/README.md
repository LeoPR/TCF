# 18 — escala (algoritmo do exp 16 em N=50, 200, 1000)

## Princípio / motivação

O algoritmo do exp 16 tem complexidade teórica O(N² · L) — para
cada string nova, compara com todas as anteriores (LCP/LCS em
chars). Os exps 13-17 testaram apenas N=6 a 12 — não fala sobre
viabilidade em N maior.

Pergunta dirigida: a curva de tempo é tractable em N=1000? A
cobertura ref% se mantém ou degrada quando o conjunto cresce?

## Propósito

Resposta às **perguntas 1 e 2** do dirty (viabilidade técnica em
escala + comportamento). Não muda o algoritmo — só os dados.

## Comparação

- **Compara com**: [16 (online cleanup)](../2026-05-11-16-online-cleanup/)
  e [17 (famílias variadas)](../2026-05-11-17-familias-variadas/).
- **É comparável?** Sim na dimensão **qualitativa** (cobertura ref%
  por família). Não em bytes absolutos (datasets diferentes).
- O algoritmo é exatamente o mesmo arquivo `online.py` copiado do
  exp 16 sem alteração.

## Cenários

4 famílias do regime A do exp 17 × 3 tamanhos = 12 casos.

| Família | N=50 | N=200 | N=1000 |
|---|---:|---:|---:|
| urls | 50 únicas | 200 únicas | 1000 únicas |
| iso | 50 únicas | 200 únicas | 1000 únicas |
| ips | 50 únicas | 200 únicas | 1000 únicas |
| codigos | 50 únicas | 200 únicas | 1000 únicas |

Geração determinística em [`gerar.py`](gerar.py). Reproduzível.

## Resultado observado

Roundtrip **12/12 OK**.

### Tabela 1 — Tempo (ms)

| Família | N=50 | N=200 | N=1000 |
|---|---:|---:|---:|
| urls | 7.9 (proc 7.1) | 76.4 (proc 73.9) | **3840 (proc 3829)** |
| iso | 5.8 (proc 5.2) | 143.1 (proc 140.7) | **3443 (proc 3431)** |
| ips | 2.6 (proc 2.2) | 35.9 (proc 34.2) | **1607 (proc 1595)** |
| codigos | 4.6 (proc 4.2) | 71.3 (proc 69.1) | **1477 (proc 1469)** |

Encode e decode são desprezíveis (<10ms mesmo em N=1000). O custo
está em `processar` (LCP/LCS sobre todas as anteriores).

### Tabela 2 — Cobertura cresce com N

| Família | N=50 | N=200 | N=1000 |
|---|---:|---:|---:|
| urls | 93.9% | 97.7% | **98.8%** |
| iso | 82.9% | 93.8% | **98.7%** |
| ips | 75.8% | 84.4% | **96.3%** |
| codigos | 93.3% | 95.4% | **95.9%** |

Em todas as 4 famílias a cobertura **aumenta** com N. Os literais
de introdução se diluem: viram fração cada vez menor do total.

### Tabela 3 — Unidades por string (eficiência por linha)

| Família | N=50 | N=200 | N=1000 |
|---|---:|---:|---:|
| urls | 4.56 | 2.77 | **2.25** |
| iso | 5.38 | 3.24 | **2.26** |
| ips | 3.68 | 2.77 | **2.09** |
| codigos | 2.38 | 2.13 | **2.07** |

Convergem para **~2 unidades por string** em N=1000. Faz sentido:
em regime estável cada nova string vira `ref-pref + ref-suf` = 2
unidades, sem literal residual.

### Tabela 4 — Distribuição em N=1000

| Família | puro ref | r+lit≤4 | r+lit>4 | só lit |
|---|---:|---:|---:|---:|
| iso | **875** | 121 | 3 | 0 |
| ips | 760 | 237 | 0 | 2 |
| urls | 623 | 372 | 4 | 0 |
| codigos | 500 | 499 | 0 | 0 |

`iso` é o caso mais favorável: 87.5% das strings ficam puro ref em
N=1000. As 2 strings "só lit" em ips correspondem a introduções
de sub-redes novas que não tinham match parcial com anteriores.

### Tabela 5 — Validação da curva O(N² · L)

| Família | N=200 / N=50 | N=1000 / N=200 |
|---|---:|---:|
| urls | 10.4× | 51.8× |
| iso | 27.1× | 24.4× |
| ips | 15.6× | 46.6× |
| codigos | 16.4× | 21.2× |

Esperado teórico: 16× (200/50) e 25× (1000/200) se O(N²) puro.

- A razão 200/50 fica próxima de 16× na média (variação 10-27×)
- A razão 1000/200 mostra mais variabilidade (21-52×). O excesso
  acima de 25× indica que `L` (comprimento médio) também conta:
  urls tem ~46 chars vs ips ~12 chars, e urls escala pior

A curva é compatível com O(N² · L) na prática.

## Observações operacionais

- N=1000 em Python puro single-threaded: 1.5-4 segundos. Útil
  para batches off-line, lento para uso interativo.
- Memória: cresce O(N · L) com cache de strings. Em N=1000
  permanece em poucos MB.
- Encode/decode são lineares e desprezíveis no tempo total.

## Limitações

- **Apenas até N=1000.** Não fala sobre N=10k, 100k, 1M. Linear
  extrapolação sugere ~5 min em N=10k (O(N²) × 100 = 6.4 min para
  urls), ~8 h em N=100k. Sem otimização, inviável em escala
  maior.
- **Geração determinística mas viesada**: cada família tem
  estrutura forte por construção. Datasets reais podem ter
  cobertura menor ou maior.
- **Todas strings únicas (RLE adjacente não atua).** Em casos
  reais com repetição, o RLE compactaria adicionalmente.
- **Python puro**. C/Rust deve dar 50-200× speedup, viabilizando
  N até 50k-100k sem mudança algorítmica.
- **`min_len = 3` fixo.** Não testado se `min_len` adaptativo
  ajudaria em escala.

## Como reproduzir

```bash
cd experiments/lab/dirty/2026-05-12-18-escala
python gerar.py    # gera 12 CSVs determinísticos em data/
python run.py      # roda os 12 casos + 5 tabelas
```

Saída: 5 tabelas em stdout, TCFs em `encoded/`, decoded em
`decoded/`.

## Conclusões

Ver [conclusoes.md](conclusoes.md). Pontos principais:

1. Algoritmo escala em **qualidade** (cobertura cresce com N)
2. Algoritmo escala em **tempo** como teorizado (O(N² · L))
3. N=1000 é viável em Python; N=10k+ exige otimização ou variante
   algorítmica
4. Próximo natural: **exp 19 (par A+B independente)** — para
   ganhar margem nas introduções residuais — ou **otimização do
   próprio algoritmo** (pruning, cache) para tornar tractable em
   escala maior
