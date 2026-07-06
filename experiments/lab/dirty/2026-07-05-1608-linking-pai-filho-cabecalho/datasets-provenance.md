# Proveniência [probatório]

Fixtures sintéticas, **focadas na ESTRUTURA** (não performance). Exemplo-base fornecido pelo owner
(pessoa ⊃ telefones); S6 estende para exercitar multi-filho + multi-nível.

- **S4** `pessoa-telefones`: o exemplo mínimo do owner.
- **S6** `pessoa-endereco-geo`: estende com `endereco{rua,cidade,geo{lat,lon}}` — objeto aninhado 2
  níveis + array `telefones`.

## Anonimização

- `nome`: "leonardo" (exemplo do próprio owner; sem PII de terceiros).
- `tel`: `(41) 99999-9999` / `(41) 99994-9999` — **fictícios**. `endereco`/`geo`: rótulos sintéticos
  (`Rua Sintetica 100`, `Cidade X`, lat/lon aproximados fictícios).

Minúsculo e determinístico — proposital: ver a **ligação** antes de escalar.
