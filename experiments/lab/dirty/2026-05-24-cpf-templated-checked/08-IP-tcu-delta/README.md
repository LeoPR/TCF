---
title: Sub-exp 08 — IP com SlotBehavior delta (sub-categoria TCU-Delta)
status: stub
---

# Sub-exp 08 — IP com slots heterogeneos

## Motivacao (H3 refinado)

CPF eh TCU-Discrete (todos slots discrete, sem ordem entre instancias).
IP eh TCU-Delta (alguns slots delta — ultimo octeto varre 0-255 numa
sub-rede).

Testar se SlotBehavior por posicao consegue ativar pipelines diferentes
em slots diferentes dentro do mesmo template.

## Design

```python
@dataclass
class SlotBehavior:
    position: tuple[int, int]     # (start, end) no template
    kind: str                     # "discrete" | "delta" | "enumerated"
    encoder_hint: str | None      # delegado pra sub-encoder

TemplatedNatureSpec(
    name="ipv4",
    template="N.N.N.N",
    body_alphabet="0123456789",
    check_fn=None,
    slot_behaviors=[
        SlotBehavior(position=(0, ?), kind="discrete"),    # 1o octeto
        SlotBehavior(position=(?, ?), kind="discrete"),    # 2o octeto
        SlotBehavior(position=(?, ?), kind="discrete"),    # 3o octeto
        SlotBehavior(position=(?, ?), kind="delta"),       # 4o octeto (varia 0-255 numa sub-rede)
    ],
)
```

Slot delta usa encoder OBAT shape-preserve (similar ao Pacote 1) pra
detectar runs sequenciais.

## Dataset

D-IP-subnet: 1k IPs em 10 sub-redes /24 (10 prefixos `X.X.X.`, 100 IPs
cada com ultimo octeto 0-99).

## Criterio de aceite

- IPs em D-IP-subnet: ratio significativamente melhor que tratamento
  todos-discrete (esperado: ultimo octeto delta encoda eficientemente)
- Mesma maquina (TemplatedNatureSpec) com slot_behaviors mistos
- RT byte-canonical 100%
- Validar que slot kind="delta" aciona sub-encoder diferente sem
  hardcoded checks
