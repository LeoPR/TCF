# bN-dense base64 vs dict/V2-B ATUAL do TCF — dados reais (adult-census)

Amostra 10000 linhas. **total-vs-total self-contained**: TCF = `encode({col:vals})` completo (header + dicionário + corpo); bN = header + domínio + base64. `modo TCF` = `emitted_mode` real. `Δ` = bN − TCF (<0 = bN ganha). RT dos dois lados.

| coluna | k | w | TCF atual | modo TCF | bN-dense | Δ | razão | RT |
|---|---:|---:|---:|:---:|---:|---:|---:|:---:|
| sex | 2 | 1 | 10026 | dict | 1692 | -8334 | 0.17× | ✅ |
| class | 2 | 1 | 10028 | dict | 1691 | -8337 | 0.17× | ✅ |
| race | 5 | 4 | 10072 | dict | 6736 | -3336 | 0.67× | ✅ |
| relationship | 6 | 4 | 10086 | dict | 6742 | -3344 | 0.67× | ✅ |
| marital-status | 7 | 4 | 10108 | dict | 6780 | -3328 | 0.67× | ✅ |
| workclass | 9 | 4 | 10106 | dict | 6776 | -3330 | 0.67× | ✅ |
| occupation | 15 | 4 | 10222 | dict | 6885 | -3337 | 0.67× | ✅ |
| education | 16 | 4 | 10159 | dict | 6815 | -3344 | 0.67× | ✅ |
| native-country | 41 | 8 | 9111 | tcf | 13705 | +4594 | 1.50× | ✅ |

## Leitura

- **bN-dense ganha em 8/9 colunas reais.** A aritmética prevista se confirma: o dict/V2-B base-94 gasta ~1 char/símbolo INDEPENDENTE de k; o bN gasta `w/6` char/símbolo (empacota w bits, base64 = 6 bits/char). Logo bN ganha enquanto **w<6 (k≤16)** e perde em **w=8 (k>16)**, onde base-94 volta a ser melhor.
- **O ganho é maior quanto MENOR a cardinalidade**: k=2 → 1 bit/símbolo = 6 símbolos por char (~6× mais denso que 1 char/símbolo do base-94). É exatamente o caso bool/flag/status, que é comum em dado real.
- **Cruzamento em k=16 → regra de decisão trivial e determinística**: escolher bN quando `width_for(k) < 6` (isto é, k≤16), senão dict. Cabe como MAIS UM CANDIDATO no FLOOR/min por coluna que o TCF já tem (`min(tcf,raw,dict,split)` → + `bN`), sem máquina nova de segmentos. É o mecanismo LÓGICO bom; a calibragem fina fica pro .9.
- **Ressalvas honestas**: (a) o protótipo usa domínio embutido com separador `\x1f` e header simples — um weld real precisaria de escaping/gramática própria, o que muda alguns bytes; (b) medido só em adult-census (9 colunas) e amostra de 10k; (c) não mede latência/CPU, só bytes; (d) o dict/V2-B tem outras virtudes (ex. legibilidade do dicionário) não capturadas aqui.

**9 colunas · 0 falhas de RT · bN vence em 8.** Amostra N=10000. Regenera: `python run.py`.