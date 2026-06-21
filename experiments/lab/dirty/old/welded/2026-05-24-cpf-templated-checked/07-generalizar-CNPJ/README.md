---
title: Sub-exp 07 — Generalizar pra CNPJ (categoria abstraida)
status: stub
---

# Sub-exp 07 — CNPJ via mesma maquina

## Motivacao (H3)

CPF eh instancia de "Templated + Checked + Unique-Discrete". CNPJ eh
outra instancia da mesma categoria. Se mesma maquina serve, categoria
abstraida e' valida.

## Design

```python
TemplatedCheckedEncoder(
    name="cnpj",
    template="NN.NNN.NNN/NNNN-DD",   # 14 digit body + 2 check
    body_alphabet="0123456789",
    body_length=12,                  # 14 - 2 check
    check_fn=mod11_cnpj_dupla,
    encoded_alphabet=BASE94,
    encoded_length=6,                # ceil(log_94(10^12)) = 6
)
```

vs CPF:
```python
TemplatedCheckedEncoder(
    name="cpf",
    template="NNN.NNN.NNN-DD",
    body_alphabet="0123456789",
    body_length=9,
    check_fn=mod11_cpf,
    encoded_alphabet=BASE94,
    encoded_length=5,
)
```

Mesma classe, parametros diferentes.

## Dataset

D-CNPJ-uniform: 1k CNPJs validos uniformes (similar D-CPF-uniform).

## Criterio de aceite

- Mesma classe `TemplatedCheckedEncoder` funciona pra ambos
- D-CNPJ-uniform: ratio similar a D-CPF-uniform (~45%)
- RT byte-canonical 100%
- Validar que mod11_cnpj_dupla (2 passos) funciona vs mod11_cpf simples
