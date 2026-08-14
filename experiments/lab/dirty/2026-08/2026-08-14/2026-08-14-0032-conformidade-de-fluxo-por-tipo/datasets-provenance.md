# Proveniência dos dados

**Todos sintéticos**, gerados por `run.py` (seed 20260814), materializados em
`inputs/<tipo>.<regime>.entrada.json` — com os tipos preservados no JSON (`true`/`42`/`4.2`/
`"x"`), de modo que abrindo o arquivo se vê a diferença de tipagem, não só no código.

Sintético é **obrigatório** para esta pergunta, e a razão é diferente da dos labs de ganho:
aqui o dado precisa ser **o mesmo regime conceitual em todos os tipos**, para que a matriz
seja comparável célula a célula. "Constante", "duas classes", "com nulo", "progressão" e
"baixa cardinalidade" existem em bool, int, float e str — corpus real não daria a mesma
coluna nos quatro tipos.

| regime | o que ativa | existe em |
|---|---|---|
| `constante` | RLE | todos |
| `duas-classes` | denso (bool) / bN (demais) | todos |
| `com-nulo` | slot 0 + o mecanismo do tipo | todos |
| `progressao` | seq-RLE | int, float, str (não faz sentido em bool) |
| `baixa-card` | bN de domínio | int, float, str |

**CONSTANTE na comparação**: n=600 em todas as células; o mesmo regime conceitual em cada
tipo; o mesmo spec (`SPEC_CPF`) no eixo 3; round-trip sempre comparado por
`type(x) is type(y) and x == y`.

Uma exceção declarada: no eixo 3, a linha de `str` usa **CPFs válidos** em vez do regime
"duas-classes". Sem isso o spec não morderia valor nenhum e o FLOOR recusaria por vacuidade —
o que a 1ª versão do lab classificou erradamente como "ignorado". Está comentado no `run.py`.

Os CPFs usados (`529.982.247-25`, `111.444.777-35`) são os mesmos já presentes na suíte de
testes do repositório como exemplos de dígito verificador válido; não correspondem a pessoa
real e não são publicados fora deste lab.

**Contrapartida honesta**: este lab não diz nada sobre **frequência** de regimes em dado real
— nem tenta. Ele mede estrutura, e estrutura não depende de distribuição.
