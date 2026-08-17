# RESULTADO — sincronizacao docs x codigo

Gerado por `run.py`. Re-rode com `python run.py` pra reconferir.

**23/23 afirmacoes conferem com o codigo vivo.**

| # | doc | afirmacao | veredito | observado |
|---|---|---|---|---|
| 1 | `TCF-format.*` | None e' preservado, nao vira '' | OK | `decode=['x', None, 'y'] wire='#TCF.8\nx\n0\ny\n'` |
| 2 | `README.*` | `from tcf import view` existe | OK | `tcf.view = <function view at 0x0000022373CA84A0>` |
| 3 | `how-to/encode-csv-file` | `,` e `=` em nome de coluna sao ESCAPADOS, nao proibidos | OK | `header='#TCF.8M!3=id\\,bad,!email\\=principal' rt=True` |
| 4 | `how-to/encode-csv-file` | so' `\n` e' proibido em nome de coluna | OK | `ValueError: col name nao pode conter '\n' (separador de linha do meta): 'a\nb'` |
| 5 | `tutorials/getting-started` | Passo 1: wire tem o header `#TCF.8` | OK | `wire='#TCF.8\nabc\n1d\n1,2e\n'` |
| 6 | `tutorials/getting-started` | Passo 3: 15 raw -> 19 tcf (o TCF CRESCE aqui) | OK | `raw=15 tcf=19 ratio=126.7%` |
| 7 | `tutorials/getting-started` | Passo 3b: emails 100 raw -> 71 tcf | OK | `raw=100 tcf=71 ratio=71.0%` |
| 8 | `tutorials/getting-started` | Passo 4: wire multi-col | OK | `wire='#TCF.8M!5=id,!name\n1\n2\n3Alice\nBob\nCharlie'` |
| 9 | `tutorials/getting-started` | Passo 5: view().where().sum() == 30.0 | OK | `sum=30.0 touched=['cidade', 'valor']` |
| 10 | `how-to/use-natures` | sem filtro: 42 B, grafia com polaridade | OK | `bytes=42 wire='#TCF.8!!\n111.444.777-35\n529.982.247-25\n^1\n'` |
| 11 | `how-to/use-natures` | com filtro: 29 B, ratio 69,0% | OK | `bytes=29 ratio=69.0% wire='#TCF.8 :cpf\n%gc\\9g\n\\2y/h-\n^1\n'` |
| 12 | `how-to/use-natures` | os 4 rotulos de classify_value | OK | `{'111.444.777-35': 'compressible', '111.444.777-99': 'check_invalid', '11144477735': 'format_unmasked', '111-444-777-35': 'format_mismatch'}` |
| 13 | `how-to/use-natures` | fallback `_` + round-trip | OK | `enc='_111.444.777-99' status='check_invalid' volta='111.444.777-99'` |
| 14 | `how-to/use-natures` | CNPJ, IP e nature_per_col rodam | OK | `multi_rt=True cnpj_rt=True` |
| 15 | `how-to/inspect-compression` | multi-col: total/header/body = 46/18/28 | OK | `total/header/body = (46, 18, 28) (doc afirma (46, 18, 28))` |
| 16 | `how-to/inspect-compression` | build_schema multi-col idem | OK | `(4, 2, 46, 18, 28) (doc afirma (4, 2, 46, 18, 28))` |
| 17 | `reference/api` | tag `b` tem 3 modos: b1, b2, bB | OK | `b1: header='#TCF.8b118' rt=True \| b2: header='#TCF.8b218' rt=True \| bB: header='#TCF.8bB23' rt=True` |
| 18 | `reference/api + json-equivalence` | uniao FORA de bool+str segue fail-loud | OK | `int+str e bool+int seguem fail-loud` |
| 19 | `src/tcf/decoder.py` | `.8H` esta' VIVO (nao reservado/fail-loud) | OK | `header='#TCF.8Ha:6n,b{c:6n' rt=True` |
| 20 | `src/tcf/decoder.py` | tags b, n E s decodam | OK | `'#TCF.8b13'->rt=True \| '#TCF.8n'->rt=True \| '#TCF.8n!!'->rt=True \| s-explicita '#TCF.8s\nabc\ndef\n'->['abc', 'def'] \| s-explicita '#TCF.8s!!\nabc\ndef\n'->['abc', 'd` |
| 21 | `src/tcf/decoder.py` | legado #TCF.7/#TCF.6 esta' CORTADO | OK | `'#TCF.7 M' -> ValueError ok \| '#TCF.6 M' -> ValueError ok` |
| 22 | `algorithms/output-convention` | `[` e `]` sao VALORES, nao skipados | OK | `decode=['a', ']', 'b', '[']` |
| 23 | `core-data-model + README + specs` | gates 1545/300/89430 batem com os testes | OK | `D1-D9=1545 (doc afirma 1545) \| D17a=300 (doc afirma 300) \| real-world=89430 (doc afirma 89430)` |

## NAO COBERTO (declarado, nao varrido)

- **`docs/theory/**` e os blocos DATADOS do `STATUS.md`** — sao LOG historico, nao
  afirmacao normativa viva. Numeros antigos (1523/303/89616) la' dentro estao CERTOS
  pro momento que registram. Nao foram tocados, e por isso nao foram verificados.
- **`docs/adr/*.md`** — imutaveis por convencao (`docs/adr/README.md:8-11`). A vigencia
  vive no campo Status do INDICE, que foi atualizado (11 linhas).
- **Completude**: este verificador prova que as 23 afirmacoes ACIMA batem. Ele NAO
  varre os docs procurando afirmacoes novas — uma afirmacao errada que nao esteja
  nesta lista passa despercebida.

