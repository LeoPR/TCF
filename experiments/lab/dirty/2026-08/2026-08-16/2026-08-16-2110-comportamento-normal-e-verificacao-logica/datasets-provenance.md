# Procedência — sintético determinístico, e o código temporário mora aqui

## O dado

`run.py::cadastro()`, `random.Random(20260816)`, n=300, sem `Z:`. Seis colunas de um cadastro
comum — `id`, `nome`, `cpf`, `email`, `nascimento`, `ativo`. É o **mesmo gerador** dos labs
`1400`/`1450`/`1530`, então os números são comparáveis entre eles.

CPF pelo gerador da suíte soldada (`tests/test_nature_compete.py:21-29`): base aleatória com
seed + DV mod-11 calculado. São CPFs-contador sintéticos, não amostrados de ninguém.

## O código temporário fica no lab

O Bloco 2 precisa medir determinismo **entre processos** (para variar o `PYTHONHASHSEED`),
o que exige um script separado. Ele é **escrito, executado e removido pelo próprio `run.py`**,
dentro da pasta do lab — nunca em scratchpad. É a regra do owner (2026-08-16): *"mesmo código
temporário tem que ser colocado no mesmo lab, pois pertence a ele"*.

## O que a enumeração cobre — e o que ela NÃO cobre

**Cobre totalmente**: o espaço do discriminador do C1 (128 chars ASCII — e o guard é
`in ("M","H")`, então chars fora do ASCII caem no ramo "roda", que é o comportamento
pré-existente).

**Cobre por comprimento**: o C2 foi enumerado para k=2 e k=3 colunas sobre um alfabeto de 5
símbolos (`None`, `"0"`, `"1"`, `"2"`, `"a"`). O alfabeto foi escolhido para conter os
**casos que colidem** (posicional vs numérico explícito) e um controle não-numérico. **Não é
prova para k arbitrário** — é cobertura total do espaço escolhido, e o guard é O(n) sem
estado, então o argumento para k maior é lógico, não empírico.

**Cobre a taxonomia declarada**: o C3 foi enumerado sobre as 8 formas de entrada que a API
documenta + 5 subconjuntos de colunas. **Não cobre** tipos exóticos (`tuple`, `set`,
gerador) — esses já têm fail-loud próprio e não passam pelo guard.

## Viés declarado

- **n=300, uma seed, um formato de cadastro.** É comportamento NORMAL de propósito — o owner
  adiou o teste em massa. Este lab não afirma robustez sob volume ou dado adversarial.
- **Determinismo medido em 5 seeds**, não exaustivo (o espaço de `PYTHONHASHSEED` é grande).
  O que os 5 descartam é a hipótese concreta de dependência de ordem de `set`.
