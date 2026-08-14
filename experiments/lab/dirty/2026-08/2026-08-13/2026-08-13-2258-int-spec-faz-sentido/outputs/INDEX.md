# INDEX

| caso | ideia | espera | venceu | core | melhor | ganho |
|---|---|---|---|---:|---:|---:|
| [`prog-passo1-largura-varia`](./prog-passo1-largura-varia.tcf) | 1..600: o run QUEBRA em 9->10 e 99->100 (3 marcadores) | spec | **int-pad** | 36 | 26 | 1.38x |
| [`prog-passo7`](./prog-passo7.tcf) | passo 7, largura varia de 1 a 4 digitos | spec | **int-pad** | 48 | 27 | 1.78x |
| [`prog-largura-fixa`](./prog-largura-fixa.tcf) | mesma progressao com largura JA' constante — o nucleo resolve sozinho | core | **core** | 22 | 22 | 1.0x |
| [`prog-epoch`](./prog-epoch.tcf) | timestamp de 10 digitos, passo 60: o OBAT fragmenta antes do seq-RLE ver | spec | **int-offpad** | 81 | 29 | 2.79x |
| [`prog-descendente`](./prog-descendente.tcf) | descendente: o core JA' resolve em 25 B — PIN CORRIGIDO 2026-08-13 (eu esperava spec) | core | **core** | 25 | 25 | 1.0x |
| [`prog-base-alta`](./prog-base-alta.tcf) | 1e9+i: 10 digitos onde so' os 3 ultimos variam | spec | **int-offpad** | 65 | 26 | 2.5x |
| [`id-largura-fixa-6`](./id-largura-fixa-6.tcf) | ids aleatorios de 6 digitos: hoje o TCF nao ganha nada | spec | **int-b94** | 4209 | 3217 | 1.31x |
| [`id-largura-fixa-11`](./id-largura-fixa-11.tcf) | ids de 11 digitos (o regime do CPF, sem mascara) | spec | **int-b94** | 7209 | 4730 | 1.52x |
| [`faixa-pequena-0-100`](./faixa-pequena-0-100.tcf) | 0..100 aleatorio: cardinalidade baixa, o bN ja' morde | core | **core** | 1110 | 1110 | 1.0x |
| [`cardinalidade-5`](./cardinalidade-5.tcf) | k=5: territorio do bN de dominio | core | **core** | 333 | 333 | 1.0x |
| [`quase-constante`](./quase-constante.tcf) | k=4 desbalanceado: RLE do nucleo | core | **core** | 25 | 25 | 1.0x |
| [`negativos`](./negativos.tcf) | com sinal: offset+pad PIORA (0,89x) — o pad custa mais que o '-'. PIN CORRIGIDO | core | **core** | 2627 | 2627 | 1.0x |
| [`com-nulos`](./com-nulos.tcf) | slots nulos no meio da progressao | spec | **int-pad** | 240 | 232 | 1.03x |
| [`sujo-10pct`](./sujo-10pct.tcf) | 10% nao-inteiros: cada literal quebra o run E paga marcador; o FLOOR recusa. PIN CORRIGIDO | core | **core** | 751 | 751 | 1.0x |
| [`zeros-a-esquerda`](./zeros-a-esquerda.tcf) | ARMADILHA: '000001' NAO e' o inteiro 1 — o RT exige recusar | core | **core** | 22 | 22 | 1.0x |
| [`misto-largura`](./misto-largura.tcf) | larguras misturadas SEM progressao: o pad so' paga se houver run. PIN CORRIGIDO | core | **core** | 338 | 338 | 1.0x |

Candidatos por caso em `../intermediates/<c>.candidatos.json`; contra-prova em `<c>.roundtrip.json` (diff contra `../inputs/<c>.entrada.json`).
