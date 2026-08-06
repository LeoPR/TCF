# Direção 2026-08-01 — fallback em camadas (o padrão SPEC) e o equilíbrio .8/.9

> Direção do owner, registrada verbatim no essencial. Governa **como** o lazytype bool
> (lab `2026-08-01-0229-lazytype-bool-extras`) e a tipagem interna futura entram no código
> quando forem soldados — e o critério .8 × .9 de tudo o mais.

## 1. O padrão: filtro com fallback, não `if` por caso

> *"Os filtros de SPEC têm fallback quando não caem no filtro; uma lógica parecida pode ser
> aplicada. A organização do flow e da modularização das camadas é importante; engessar tudo
> com um monte de ifs pra cada caso é ruim. O ideal é fazer funcionar MAS depois de ver que a
> ideia funciona, mover e adaptar pros locais mais adequados, deixando as lógicas
> generalizadas."*

O padrão já existe em 3 níveis no código, e a direção é **estendê-lo, não inventar ifs**:

| nível | onde | o fallback |
|---|---|---|
| **por valor** | natures (`templated_checked.py:16`) | valor não casa o formato → literal |
| **por coluna** | FLOOR `min()` (encoder/multi) | modo não compensa → candidato menor |
| **por rota** | `_lista_flat` / `_tipo_single_col` | coluna não é flat/tipada → próxima rota |

O lazytype bool é **o 1º nível aplicado à rota tipada**: o valor casa {null,true,false} → slot
congelado; não casa → cai no domínio declarado (slot 3+). Mesma lógica do SPEC, camada
diferente. A implementação, quando vier, deve nascer **generalizada** (filtro-tenta/fallback
como idioma), não como `if tipo == "bool" and tem_extra: ...`.

## 2. O equilíbrio .8 × .9 (vigente)

> *"O .8 é mais para ter as funcionalidades e ver se o roundtrip fecha, com alguma adaptação
> pra próxima etapa. O .9 vai focar em organizar e otimizar tudo. Ou seja: o .8 pode fazer
> ambos, mas o equilíbrio é PRIORIZAR O FUNCIONAMENTO, adaptar e otimizar se for fácil. O .9
> vai priorizar otimizações pra tentar fechar o 1.0, mas pode voltar e ver se faltou coisa pra
> fechar na arquitetura."*

- **.8 (agora)**: funcionalidade + RT fecha; adaptar/otimizar **só se for fácil**.
  Protótipo que funciona no lab pode entrar remendado, desde que no lugar certo o bastante
  pra não fechar porta (ver o guia de encaixe pro `.9`,
  `notas/2026-07/2026-07-27-guia-de-encaixe-para-o-dot9.md`).
- **.9 (próximo)**: organizar + otimizar mirando o 1.0 — incluindo **voltar** e fechar o que
  faltou de arquitetura no .8.
- **1.0**: o passado morre no git (sem `if .7`/`if .6`).

## 3. Consequências práticas registradas

- Welds recentes (b2 ADR-0037, slots ADR-0038) seguiram a forma certa: candidato a mais no
  `min()` existente, zero `if` de caso novo — o FLOOR **é** o fallback.
- `tipos_internos.py` nasceu como **mapa de dados, não lógica** — mesma direção (o mapa
  externalizável futuro, T-TIPOS-CONFORTO-MAP, herda isso).
- Qualquer weld do lazytype (T-LAZYTYPE-BOOL, pendente) deve: entrar como candidato no FLOOR
  da rota tipada, com o fallback SPEC-like por valor; decode misto = contrato novo, decisão
  separada do owner.

Cross-links: lab lazytype `../../2026-08/2026-08-01/2026-08-01-0229-lazytype-bool-extras/` ·
mapa de tipos `2026-08-01-0141-mapa-tipos-internos-direcao.md` ·
contrato externalizado `../2026-07/contrato-externalizado-e-aceleradores.md` (mesma família:
não engessar, externalizar decisões).
