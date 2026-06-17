# IPv4 — Templated + Padded (sem check). Regenera SPEC_IP do core.
name: ip
template: N.N.N.N            # documentacao; o regex vem de padding_slots + separator
check_algorithm: none
padding_slots: [3, 3, 3, 3]  # cada octeto cabe em 3 digitos
separator: .
