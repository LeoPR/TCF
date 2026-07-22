# Proveniência [probatório]

Fixtures **sintéticas, focadas na ESTRUTURA** (não performance), reaproveitadas da peça 3 (mesmo estudo):
- **S4** `pessoa{nome} ⊃ telefones[{tel}]` — exemplo-base do owner.
- **S6** `pessoa{nome} ⊃ endereco{rua,cidade,geo{lat,lon}} + telefones[{tel}]` — árvore (multi-nível/filho).

## Anonimização

- `nome` = "leonardo" (exemplo do próprio owner; sem PII de terceiros). `tel` = `(41) 99999-9999` /
  `(41) 99994-9999` (fictícios). `endereco`/`geo` = rótulos sintéticos (`Rua Sintetica 100`, `Cidade X`,
  lat/lon aproximados fictícios).

Minúsculo/determinístico — proposital: ver a **forma** antes de escalar. Valores tratados como string.
