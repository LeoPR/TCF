# EXP-019: a 0.8.4 é consistente?

**Verificação, não protótipo.** A 0.8.4 já está soldada; o que falta é a pergunta do conjunto.
Os testes unitários cobrem cada peça em isolamento. Este experimento pergunta se as peças
**concordam entre si**, em dado real e em volume, e é o pedido do owner: *"um experimento
verificando tudo que fizemos e se está consistente."*

`src/tcf` **não é tocado**: o lab só importa a API pública e mede.

## Estado: era / foi / é / será

- **Era**: a grafia da entrada escolhia o arsenal (`list[dict]` ia para o `.8H`, que emite só
  a rota `tcf`), e o `sort_by` reordenava sempre, custasse o que custasse.
- **Foi**: dois ADRs no mesmo commit. O [0049](../../../../docs/adr/0049-marcador-r-a-forma-da-entrada-e-metadado.md)
  canoniza a tabela retangular e a manda para o `#TCF.8R`; o
  [0050](../../../../docs/adr/0050-sort-by-vira-candidato-o-floor-decide.md) faz do `sort_by`
  um candidato. Junto vieram quatro defeitos de superfície, uma correção de docstring e a
  vetorização do `group_count`.
- **É**: sete portões sobre oito amostras reais estratificadas. **7 de 7 passam**, e o conjunto
  encolheu **25,6%**.
- **Será**: o `.9`, onde a otimização é o assunto e o `bench_perf` é a ferramenta.

## Os sete portões

| | portão | o que reprovaria |
|---|---|---|
| G1 | round-trip | o contrato. Se cair, nada mais importa |
| G2 | dominância | `.8R` maior que o `.8H` que a mesma entrada emitia, uma vez que seja |
| G3 | equivalência | as duas grafias da mesma tabela darem corpos diferentes |
| G4 | FLOOR nunca-pior | `sort_by` fazer o wire crescer, em qualquer coluna-chave |
| G5 | paridade da view | `select() != decode()`, ou `agg_by != group_sum` |
| G6 | fronteira | algo que precisa do `.8H` ser roteado para fora dele |
| G7 | `group_count` | a leitura estrutural divergir de contar o decode |

G2 e G6 são os dois que carregam risco de verdade. O G2 testa a **premissa** do ADR-0049, que
é estrutural (`corpo(.8M) = min(tcf, raw, dict, split) ≤ corpo(.8H) = tcf`): uma única violação
a derruba, e a solda teria de voltar. O G6 testa a **guarda**, ou seja o que aconteceria se o
roteamento tivesse ficado guloso: perda de capacidade calada, que é a pior regressão possível
aqui, porque o usuário não pediu e não é avisado.

## As amostras

Oito tabelas de oito fontes reais, todas pelo Shaper, todas com estratificação proporcional. A
variedade é o método: consistência não se testa contra um corpus favorito.

| amostra | linhas | cols | estratos | TVD |
|---|---:|---:|---:|---:|
| adult-census | 800 | 15 | 16 | 0,0031 |
| online-retail | 800 | 8 | 38 | 0,0206 |
| ibge-municipios | 800 | 8 | 27 | 0,0054 |
| br-identidades | 800 | 6 | 27 | 0,0048 |
| tpch-orders | 800 | 9 | 3 | 0,0006 |
| tpch-lineitem | 800 | 16 | 3 | 0,0003 |
| receita-cnpj | 800 | 8 | 5 | 0,0017 |
| wine-quality | 800 | 13 | 7 | 0,0018 |

O TVD é a distância entre a distribuição da amostra e a da população, e o Shaper o grava junto
com JSD, Hellinger e o qui-quadrado. Os traces completos ficam em `intermediates/`.

## Como reproduzir

```
python run.py
```

Exige os SQLite preparados (`Z:\tcf-data\interim\`); sem eles o Shaper falha alto dizendo qual
comando os monta. Evidência: `inputs/`, `intermediates/` (traces do Shaper),
`outputs/` (24 wires, o `.8R`, o `.8M` e o `.8H` de cada amostra), `resultado.json` e
[`saida.txt`](saida.txt).

Achados: [`report.md`](report.md). Proveniência: [`datasets-provenance.md`](datasets-provenance.md).
