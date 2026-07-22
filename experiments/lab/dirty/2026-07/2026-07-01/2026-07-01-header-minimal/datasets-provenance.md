# Proveniência [probatório]

Fixtures **triviais sintéticas** (inline em `run.py`), para o caso EXTREMO "registro mínimo":

- `cpf` = `111.444.777-35` (CPF de **teste** clássico, não real). `nome` = `Joao Silva` (genérico).
- Break-even: N registros DISTINTOS de alta entropia gerados deterministicamente
  (`f"{i:03d}.{(i*13)%1000:03d}..."`) — pouco afixo comum, pra o body crescer ~linear e o header amortizar.

Determinístico; só bytes de header/body (nenhum dado real). Objetivo: medir o **piso** do header, não performance.
