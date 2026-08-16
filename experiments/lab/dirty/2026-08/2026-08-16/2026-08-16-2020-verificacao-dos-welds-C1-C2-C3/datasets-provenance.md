# Procedência — o "dado" aqui é CÓDIGO, e ele vem do git

Não há dataset. As duas fontes deste lab são:

1. **o código pré-weld**, obtido por `git archive <sha>^ src` — o commit-pai de cada weld,
   extraído para `C:/Temp/tcf-preweld` (removido ao fim de cada verificação);
2. **o `src/` atual** do repo.

Os repros são **sintéticos e mínimos**, escritos no próprio `run.py` e gravados literalmente
em `inputs/<weld>-repro.fonte.json` — quem for conferir lê exatamente o que rodou.

## A CONSTANTE

O **mesmo** repro, byte a byte, roda contra as duas versões. A única variável é o `sys.path`
do subprocesso. Nenhum dado muda entre os lados.

## Prova de que a versão extraída é a certa

Antes de rodar qualquer repro, o lab confere que o **marcador do fix** (uma string que só
existe no código pós-weld) está **ausente** no extraído e **presente** no atual. Se essa
verificação falhar, o lab acusa e sai != 0 — não confia no `git` sem checar.

## Vieses e limites declarados

- **Depende do histórico git estar presente.** Num clone raso (`--depth 1`) os commits-pai
  podem não existir e o lab falha ao extrair — é limitação real, não silenciosa.
- **Os SHAs estão fixos no `run.py`.** Se os commits forem reescritos (rebase), o lab quebra
  alto em vez de verificar a coisa errada.
- **Prova comportamento, não ausência de outros defeitos.** Cada repro cobre o defeito que o
  weld endereça; não é uma auditoria do fix.
- **Windows**: usa `C:/Temp` como base do temporário para evitar o limite de path que
  derrubou a tentativa com `git worktree`.
