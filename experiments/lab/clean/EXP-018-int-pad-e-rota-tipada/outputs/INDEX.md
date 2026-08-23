# INDEX

| caso | ideia | espera | venceu | base | wire | ganho |
|---|---|---|---|---:|---:|---:|
| [`sint-progressao-largura-varia`](./sint-progressao-largura-varia.tcf) | 1..600: a largura varia (1->2->3 digitos) e quebra o marcador em 3 | spec | **spec** | 37 | 26 | 1.423x |
| [`sint-passo7`](./sint-passo7.tcf) | passo 7: largura de 1 a 4 digitos | spec | **spec** | 49 | 27 | 1.815x |
| [`sint-largura-ja-fixa`](./sint-largura-ja-fixa.tcf) | largura JA' uniforme: o pad e' no-op, o `dimensiona` nem oferece | core | **core** | 23 | 23 | 1.0x |
| [`sint-cardinalidade-5`](./sint-cardinalidade-5.tcf) | k=5: territorio do bN, o pad nao tem o que ativar | core | **core** | 334 | 334 | 1.0x |
| [`sint-aleatorio-largura-varia`](./sint-aleatorio-largura-varia.tcf) | largura varia mas NAO ha' progressao: o pad paga e nao ativa nada | core | **core** | 3541 | 3541 | 1.0x |
| [`sint-com-nulos`](./sint-com-nulos.tcf) | slots NULOS no meio da progressao, o null e' do tipo, nao da grafia | spec | **spec** | 241 | 232 | 1.039x |
| [`sint-negativos`](./sint-negativos.tcf) | com sinal: o spec RECUSA (format_mismatch) e o FLOOR fica no core | core | **core** | 2625 | 2625 | 1.0x |
| [`sint-quase-constante`](./sint-quase-constante.tcf) | k=4 desbalanceado: o RLE do nucleo resolve | core | **core** | 26 | 26 | 1.0x |
| [`real-tpch-orderkey`](./real-tpch-orderkey.tcf) | chave de pedido 1..12000: o maior ganho medido (2,73x) | spec | **spec** | 123 | 44 | 2.795x |
| [`real-tpch-partkey`](./real-tpch-partkey.tcf) | chave de peca 1..2000 (1,72x) | spec | **spec** | 50 | 28 | 1.786x |
| [`real-tpch-custkey`](./real-tpch-custkey.tcf) | chave de cliente 1..1500 (1,69x) | spec | **spec** | 49 | 28 | 1.75x |
| [`real-tpch-lineitem-orderkey`](./real-tpch-lineitem-orderkey.tcf) | chave REPETIDA (k=744 em 3000, 3 passos distintos): a repeticao quebra a progressao e o FLOOR recusa o pad | core | **core** | 5234 | 5234 | 1.0x |
| [`real-tpch-linenumber`](./real-tpch-linenumber.tcf) | k=7, largura 1: nada a padear, o bN domina | core | **core** | 1522 | 1522 | 1.0x |
| [`real-wine-quality`](./real-wine-quality.tcf) | nota 3..9: k=7, largura 1 | core | **core** | 1535 | 1535 | 1.0x |
| [`real-retail-quantity`](./real-retail-quantity.tcf) | quantidade com NEGATIVOS (-24..600): o spec recusa os negativos | core | **core** | 3785 | 3785 | 1.0x |
| [`real-ibge-municipio-id`](./real-ibge-municipio-id.tcf) | id de municipio: 7 digitos uniformes, sem progressao | core | **core** | 14543 | 14543 | 1.0x |
| [`real-tpch-availqty`](./real-tpch-availqty.tcf) | quantidade 4..9998: largura varia, sem progressao | core | **core** | 14879 | 14879 | 1.0x |
| [`real-tpch-nationkey`](./real-tpch-nationkey.tcf) | k=25, largura 1-2: baixa cardinalidade | core | **core** | 1357 | 1357 | 1.0x |

Contra-prova por caso: `diff outputs/<c>.roundtrip.json inputs/<c>.entrada.json` tem de dar VAZIO. Candidatos e baseline em `../intermediates/`.
