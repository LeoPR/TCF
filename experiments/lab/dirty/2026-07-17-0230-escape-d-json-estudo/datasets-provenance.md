# Proveniência

100% sintético didático, construído à mão para exercitar o alfabeto do escape (`\`, `n`, LF, `z`)
em todas as combinações relevantes — viés declarado: casos de DESIGN escolhidos por serem os
pontos de ambiguidade do mecanismo, mais 1 caso realista (log multilinha com path Windows).
A varredura de injetividade é exaustiva sobre o alfabeto crítico (len 0..3) e o fuzz é seedado
(20260717). Nenhum dado externo; nenhum acesso a Z:.
