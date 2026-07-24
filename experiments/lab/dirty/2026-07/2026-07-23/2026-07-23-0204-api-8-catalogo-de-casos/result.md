# Catálogo de casos da API .8 — resultado (gerado por run.py)

Um exemplo de cada situação de dispatch. Artefatos por caso em `inputs/` · `outputs/*.tcf` · `outputs/*.roundtrip.json` · `intermediates/*.debug.txt`.


## SINGLE

- **S1** — emails c/ prefixo/sufixo compartilhado — órfão (0 B header), OBAT+HCC
    - input `['ana@site.com', 'ana.b@site.com', 'carlos@site.com', 'carla@site.com']`
    - wire (37 B): `'an*a*@site.com\n1,2.b3\ncarl*os3\n5,2,3\n'`
    - header: (sem header — single-col órfão)
    - roundtrip: ✅ OK
- **S2** — linhas idênticas adjacentes — RLE de linha (*N|linha)
    - input `['ok', 'ok', 'ok', 'erro', 'ok', 'ok']`
    - wire (17 B): `'*3|ok\nerro\n*2|^1\n'`
    - header: (sem header — single-col órfão)
    - roundtrip: ✅ OK
- **S3** — version-stamp opt-in (#TCF.8\n) — magic p/ file/libmagic
    - input `['a', 'ab', 'abc']`
    - wire (16 B): `'#TCF.8\na\nab\nabc\n'`
    - header: single-col version-stamp (#TCF.8\n)
    - roundtrip: ✅ OK
- **S4** — nature CPF single-col — FLOOR compete (órfão vs #TCF.8 :cpf, fica a menor)
    - input `['111.111.111-11', '222.222.222-22', '333.333.333-33', '111.111.111-11', '222.222.222-22',`
    - wire (41 B): `'#TCF.8 :cpf\n%g$.u\n)K%\\7l\n.\\1&Cc\n^1\n^2\n^3\n'`
    - header: single-col + spec/nature · meta: ' :cpf'
    - roundtrip: ✅ OK

## MULTI

- **M1** — tabela mista — #TCF.8M, marcadores por-coluna (! raw · @ dict · % split), hex
    - input `{'hora': ['0', '1', '2', '0', '1', '2'], 'codigo': ['0000', '79b1', 'f362', '6d13', 'e6c4'`
    - wire (113 B): `'#TCF.8M!b=hora,!1d=codigo,nome\n0\n1\n2\n0\n1\n20000\n79b1\nf362\n6d13\ne6c4\n6075pedido_\\00*\\0*_descricao_unica\n*5+1|1\\1*3\n'`
    - header: multi-col #TCF.8M · meta inline: '!b=hora,!1d=codigo,nome'
    - roundtrip: ✅ OK
- **M2** — MESMA tabela, min_header=False + fallback=False — header explícito p/ inspeção
    - input `{'hora': ['0', '1', '2', '0', '1', '2'], 'codigo': ['0000', '79b1', 'f362', '6d13', 'e6c4'`
    - wire (131 B): `'#TCF.8M11=hora,27=codigo,2a=nome\n*3+1|\\0\n^1\n^2\n^3\n\\0000\n\\79b\\1\nf\\362\n\\6d\\13\ne\\6c\\4\n\\6075\npedido_\\00*\\0*_descricao_unica\n*5+1|1\\1*3\n'`
    - header: multi-col #TCF.8M · meta inline: '11=hora,27=codigo,2a=nome'
    - roundtrip: ✅ OK
- **M3** — sort_by='hora' + drop_names=True — linhas reordenadas + colunas anônimas
    - input `{'hora': ['0', '1', '2', '0', '1', '2'], 'codigo': ['0000', '79b1', 'f362', '6d13', 'e6c4'`
    - wire (113 B): `'#TCF.8Mb,!1d,\n*3+1|*2|\\0\n0000\n6d13\n79b1\ne6c4\nf362\n6075pedido_\\00*\\0*_descricao_unica\n*2-2|1\\3*3\n*2-2|1\\4*3\n1\\5*3\n'`
    - header: multi-col #TCF.8M · meta inline: 'b,!1d,'
    - roundtrip: ✅ OK (idempotencia-2a-geracao)
- **M4** — nature CNPJ por-coluna (nature_per_col) — o FLOOR escolhe por coluna
    - input `{'cnpj': ['11.222.333/0001-81', '11.444.777/0001-61', '11.222.333/0001-81', '11.444.777/00`
    - wire (68 B): `'#TCF.8M@1c=cnpj:cnpj,valor\n19\n!K\\9p\\5B$\n!Kx\\0n)$\n!"!"!"\\0\n*5+10|\\10\n'`
    - header: multi-col #TCF.8M · meta inline: '@1c=cnpj:cnpj,valor'
    - roundtrip: ✅ OK

## HIER

- **H1** — dataset (list[dict]) c/ escalares tipados + array — #TCF.8H dataset
    - input `[{'nome': 'Ana', 'idade': 30, 'ativo': True, 'fones': ['11 9999-0001', '11 3000-0002']}, {`
    - wire (128 B): `'#TCF.8Hnome:10,idade:9n,ativo:11b,fones#:8[\nAna\nBruno\n*2-5|\\30\ntrue\nfalse\n*2-1|\\2\n\\11 *\\9999-\\0001\n1\\3000-\\0002\n\\21 \\9888-\\7766\n'`
    - header: hierárquico #TCF.8H · DATASET (list[dict]) · meta 'nome:10,idade:9n,ativo:11b'
    - roundtrip: ✅ OK
- **H2** — objeto único (dict com valores escalar/nested) — #TCF.8H #O
    - input `{'cidade': 'SP', 'populacao': 12300000, 'capital': True, 'prefeito': {'nome': 'X', 'partid`
    - wire (89 B): `'#TCF.8H#Ocidade:3,populacao:10n,capital:5b,prefeito{nome:2,partido\nSP\n\\12300000\ntrue\nX\nY\n'`
    - header: hierárquico #TCF.8H · objeto único (#O) · meta '#Ocidade:3,pop'
    - roundtrip: ✅ OK
- **H3** — escalar solto — #TCF.8H #V (envelope; decode desembrulha)
    - input `42`
    - wire (19 B): `'#TCF.8H#V\\z:4n\n\\42\n'`
    - header: hierárquico #TCF.8H · valor escalar (#V, envelope) · meta '#V\\z:4n'
    - roundtrip: ✅ OK
- **H4a** — lista vazia [] — FLAT #TCF.8\n (weld #2 2026-07-24: canonicidade do vazio; era .8H #D0)
    - input `[]`
    - wire (7 B): `'#TCF.8\n'`
    - header: single-col version-stamp (#TCF.8\n)
    - roundtrip: ✅ OK
- **H4b** — dict vazio {} — #TCF.8H #E (definição)
    - input `{}`
    - wire (10 B): `'#TCF.8H#E\n'`
    - header: hierárquico #TCF.8H · objeto-vazio {} (#E) · meta '#E'
    - roundtrip: ✅ OK
- **H4c** — [{}, {}] — #TCF.8H #D2 (N registros, zero colunas)
    - input `[{}, {}]`
    - wire (11 B): `'#TCF.8H#D2\n'`
    - header: hierárquico #TCF.8H · dataset sem-colunas (#D<N>) · meta '#D2'
    - roundtrip: ✅ OK
- **H5** — tipos PRESERVADOS (int/float/bool/null) num objeto — decode devolve o tipo exato
    - input `{'i': 7, 'f': 3.5, 'b': False, 'n': None, 's': 'txt'}`
    - wire (55 B): `'#TCF.8H#Oi:3n,f:6n,b:6b,n?:3:0,s\n\\7\n\\3.\\5\nfalse\n\\0\ntxt\n'`
    - header: hierárquico #TCF.8H · objeto único (#O) · meta '#Oi:3n,f:6n,b:'
    - roundtrip: ✅ OK
- **H6** — aninhado profundo (objeto dentro de objeto, array de arrays)
    - input `[{'id': '1', 'geo': {'lat': '1.0', 'lng': '2.0'}, 'matriz': [['a', 'b'], ['c']]}]`
    - wire (76 B): `'#TCF.8Hid:3,geo{lat:6,lng:6},matriz#:3[#:8[\n\\1\n\\1.\\0\n\\2.\\0\n\\2\n*2-1|\\2\na\nb\nc\n'`
    - header: hierárquico #TCF.8H · DATASET (list[dict]) · meta 'id:3,geo{lat:6,lng:6},matr'
    - roundtrip: ✅ OK
- **H7** — nature CPF em FOLHA aninhada (nature_per_col path) no dataset .8H
    - input `[{'nome': 'Ana', 'doc': {'cpf': '111.111.111-11'}}, {'nome': 'Bru', 'doc': {'cpf': '222.22`
    - wire (50 B): `'#TCF.8Hnome:8,doc{cpf:13:cpf\nAna\nBru\n%g$.u\n)K%\\7l\n'`
    - header: hierárquico #TCF.8H · DATASET (list[dict]) · meta 'nome:8,doc{cpf:13:cpf'
    - roundtrip: ✅ OK

## CONTRATO

- **C1** — encode([1,2,3]) — array .8H TIPADO (int preservado; era single 1,2,3)
    - input `[1, 2, 3]`
    - wire (31 B): `'#TCF.8H#V\\z#:3[]:8n\n\\3\n*3+1|\\1\n'`
    - header: hierárquico #TCF.8H · valor escalar (#V, envelope) · meta '#V\\z#:3[]:8n'
    - roundtrip: ✅ OK
- **C2** — coluna com None — vira .8H, None PRESERVADO (não vira '')
    - input `{'a': ['x', None, 'y']}`
    - wire (33 B): `'#TCF.8H#Oa#:3?:8[\n\\3\n.\n\\0\n^1\nx\ny\n'`
    - header: hierárquico #TCF.8H · objeto único (#O) · meta '#Oa#:3?:8['
    - roundtrip: ✅ OK
- **C3** — dict ragged (colunas de tamanhos != ) — .8H OBJETO (cada campo = array)
    - input `{'a': ['1', '2'], 'b': ['x']}`
    - wire (40 B): `'#TCF.8H#Oa#:3[]:8,b#:3[\n\\2\n*2+1|\\1\n\\1\nx\n'`
    - header: hierárquico #TCF.8H · objeto único (#O) · meta '#Oa#:3[]:8,b#:'
    - roundtrip: ✅ OK
- **C4** — array de tipos MISTOS (int+null+str) — FAIL-LOUD (union fora do .8H)
  → `FAIL-LOUD (esperado): HierarchicalError: tipos escalares MISTOS {'s', 'n'} numa coluna — union/tipo-misto no mesmo slot está fora d`
- **C5** — tuple no lugar de lista — FAIL-LOUD (tipo não-JSON, não converte calado)
  → `FAIL-LOUD (esperado): HierarchicalError: valor escalar de tipo não suportado: tuple`
- **C6** — kwarg SÓ-flat (parallel) com entrada .8H — FAIL-LOUD (nunca ignora calado)
  → `FAIL-LOUD (esperado): ValueError: kwargs ['parallel'] nao se aplicam a entrada hierarquica (.8H); so' valem no flat (single/`

## FONTES (mesmo dado: CSV plano vs JSON aninhado)

- **F1-csv** (colunas planas): `'#TCF.8M!3=id,!9=nome,!cidade\n1\n2Ana\nBrunoSP\nRJ'` → multi-col #TCF.8M · meta inline: '!3=id,!9=nome,!cidade' · RT ✅
- **F1-json** (mesmos dados aninhados): `'#TCF.8Hid:8,nome:10,cidade\n*2+1|\\1\nAna\nBruno\nSP\nRJ\n'` → hierárquico #TCF.8H · DATASET (list[dict]) · meta 'id:8,nome:10,cidade' · RT ✅
  > mesma informação, WIRES diferentes: CSV plano vira multi-col `#TCF.8M`; JSON aninhado vira `#TCF.8H` (o TCF entende DATASET, o JSON/CSV é a materialização).

## COMPRESSÃO EXTERNA (comparação — gzip/brotli/zstd NÃO fazem parte do TCF)

- amostra 50 linhas · JSON raw=1818 B · **TCF=145 B** · gzip(json)=211 B · gzip(tcf)=109 B
  > o TCF é TEXTO inspecionável; gzip é sinal de redundância oculta, não critério.

---
**Roundtrip: 22 OK, 0 falhas** · fail-loud (contratos): C4/C5/C6 esperados. Regenera: `python run.py`.
