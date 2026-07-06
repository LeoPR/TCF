# Conclusão (estrutura) [probatório]

**Sim, dá pra TCF.8 + aninhar dois TCFs.** Números/estrutura vêm de `artifacts/` (`python run.py`).

- **TCF.8 confirmado**: cada tabela vira um bloco `#TCF.8` (single-col via `stamp=True`) —
  `03-tcf8-bloco-{pessoa,telefones}.tcf.txt`. Decode OK.
- **Dois TCF.8 aninhados um após o outro** com envelope **auto-descritivo** (`@tree` + `@block`) —
  `03-tcf8-aninhado.tcf.txt`. **Decoda e reconstrói o JSON idêntico** — `04-decode-roundtrip.txt` (OK).
- **Estrutura antes de ganho** (teu ponto): correto — as duas tabelas + o envelope organizam a árvore;
  bytes ficam pra depois (e, pelo lab [1509](../2026-07-05-1509-tcf-hierarquico-tabelao-vs-2tabelas/),
  o schema/envelope compra **reconstrução**, não compressão).

Próximo: o owner redesenha o envelope (ver README §"Para REDESENHAR"). Depois: leaf multi-col, N raízes
(fk/ordenação), aninhamento recursivo (`telefones[i]` com sub-array).
