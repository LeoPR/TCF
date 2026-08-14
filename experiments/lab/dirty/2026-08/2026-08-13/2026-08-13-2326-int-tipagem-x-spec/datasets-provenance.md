# Proveniência dos dados

**Todos sintéticos**, gerados por `run.py` (seed 20260813), materializados em disco **nas
duas fontes**: `inputs/<regime>.entrada-int.json` (números como números) e
`inputs/<regime>.entrada-str.json` (os mesmos valores como strings).

Os dois arquivos existem de propósito: é a comparação que o lab faz, e é o que o owner
apontou que faltava. Abrindo os dois lado a lado dá para ver que o JSON de um tem `1, 2, 3`
e o do outro tem `"1", "2", "3"` — a diferença de tipagem é visível no disco, não só no
código.

**CONSTANTE na comparação**: os **mesmos valores** nas 4 células; só variam a FONTE
(int × string) e o TRATAMENTO (core × spec). Os alvos são dimensionados pela própria coluna.
O round-trip é comparado com `type(x) is type(y) and x == y`, elemento a elemento — em Python
`True == 1` e `1 == 1.0`, e a comparação por valor mascararia o defeito de tipagem.

| regime | o que isola |
|---|---|
| `prog-passo1` | progressão com largura variando (1→2→3 dígitos) |
| `prog-passo7` | progressão com passo ≠ 1 |
| `prog-largura-fixa` | progressão já limpa (controle: o núcleo vence) |
| `prog-epoch` · `prog-base-alta` | base alta — dígitos que não informam |
| `id-aleatorio-6` · `id-aleatorio-11` | sem progressão, largura fixa |
| `faixa-0-100` · `cardinalidade-5` · `quase-constante` | baixa cardinalidade (controle: bN/RLE) |
| `negativos` | sinal na grafia |
| `com-nulos` | **slot nulo é do TIPO, não da grafia** — só existe de verdade no eixo int |
| `gigante-64bit` | acima de 2⁶³: fora do int64, borda de representação |
| `misto-int-float` | int e float na mesma coluna — o spec de int tem de recusar o float |

**A contrapartida, explícita**: sintético controlado diz *onde* cada mecanismo responde, não
*com que frequência* o regime aparece em dado real. Medir a frequência em colunas reais é o
passo que falta antes de qualquer weld — o corpus é que dita o default.

Nenhum dado pessoal: os ids de 11 dígitos são aleatórios de faixa, **sem** dígito verificador
válido — não são CPFs. O regime existe para medir largura fixa, não a nature de CPF.
