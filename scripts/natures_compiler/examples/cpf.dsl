# CPF — Templated + Checked (mod-11). Regenera SPEC_CPF do core a partir do DSL.
name: cpf
template: NNN.NNN.NNN-DD     # N = digito do corpo, D = verificador, . - = literais
body_length: 9
check_length: 2
check_algorithm: mod11-cpf  # biblioteca fechada; nunca codigo do usuario
