# Proveniência dos dados

**Todos sintéticos**, gerados por `run.py` (seed 20260813), materializados em
`inputs/<caso>.entrada.json`. Nenhum dado externo, nenhum acesso a `Z:`.

Sintético controlado é a escolha certa para **esta** pergunta: cada caso isola um regime
(progressão × largura × cardinalidade × sujeira) para saber *qual mecanismo* responde. Corpus
real misturaria regimes numa mesma coluna e a atribuição de causa ficaria ambígua.

**A contrapartida, explícita**: os ganhos medidos **não** são previsão para dado real. Eles
dizem *onde* o spec ajuda, não *com que frequência* isso aparece. Medir a frequência dos
gatilhos em colunas reais é o passo que falta antes de qualquer weld — é o corpus que dita o
default, e essa regra vale aqui como valeu para data.

| caso | regime isolado |
|---|---|
| `prog-passo1-largura-varia` | progressão + largura variando (1→2→3 dígitos) |
| `prog-passo7` · `prog-descendente` | progressão com passo ≠ 1 e sentido invertido |
| `prog-largura-fixa` | progressão já limpa (controle: o núcleo deve vencer) |
| `prog-epoch` · `prog-base-alta` | progressão com base alta (dígitos que não informam) |
| `id-largura-fixa-6` · `id-largura-fixa-11` | sem progressão, largura fixa (regime do CPF sem máscara) |
| `faixa-pequena-0-100` · `cardinalidade-5` · `quase-constante` | baixa cardinalidade (controle: bN/RLE) |
| `negativos` · `com-nulos` · `sujo-10pct` · `misto-largura` | bordas e sujeira |
| `zeros-a-esquerda` | armadilha de canonicidade (`000001` ≠ `1`) |

**CONSTANTE na comparação**: n=600; todos os candidatos passam pelo **mesmo** `encode()`
público (o FLOOR real decide); só o alvo varia, e os alvos são dimensionados pela própria
coluna — que é o que um auto-detector faria.

Nenhum dado pessoal: os ids de 11 dígitos são aleatórios de faixa, **sem** dígito verificador
válido — não são CPFs. O caso existe para medir o regime de largura fixa, não a nature de CPF.
