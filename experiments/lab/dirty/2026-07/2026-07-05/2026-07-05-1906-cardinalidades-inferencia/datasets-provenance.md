# Proveniência [probatório]

4 tabelas planas **sintéticas mínimas** (3-4 linhas cada), construídas para exibir **uma cardinalidade
cada** (viés declarado — feitas pra ilustrar 1:1/1:N/N:1/N:N):

- **1:1** cpf–nome (bijeção) · **1:N** pessoa–telefone · **N:1** produto–categoria · **N:N** pessoa–curso.

Valores fictícios (`leonardo` = exemplo do owner; telefones/cpf/produtos inventados). Fixtures **limpas**
(sem ruído) — proposital: ver a lógica de FD antes de lidar com FD aproximada. Determinístico; só contagem
de distintos (nenhum dado real). Definidas inline em `run.py`.
