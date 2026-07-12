# F2 — controle minúsculo (gerado por scripts/bench_evidencia_f2.py)

Registros completos nos `.jsonl` ao lado (schema evidencia-0.8/v1);
blobs `.tcf` = exemplos inspecionáveis (nenhum contém CPF DV-válido — §2.3).
Runner validado contra a régua ANTES da rodada (D1-D9/D17a/real-world).

## Casos medidos

| caso | total B | header B | body B | input B | modos | enc mediana ms | RT | nota |
|---|---:|---:|---:|---:|---|---:|---|---|
| a1-orfao-emails | 32 | 0 | 32 | 46 | - | 0.19 | OK | single órfão (header 0B) |
| a2-stamp-emails | 39 | 7 | 32 | 46 | - | 0.19 | OK | version-stamp '#TCF.8\n' (+7B) |
| a3-dict1col-emails | 45 | 13 | 32 | 46 | t | 0.23 | OK | multi de 1 coluna nomeada (#TCF.8M) |
| a4-d1-orfao | 118 | 0 | 118 | 190 | - | 1.76 | OK | D1 órfão (controle da régua, 118B) |
| c1-readme-default | 242 | 49 | 193 | 245 | !ttt! | 1.99 | OK | o exemplo do README (F6) |
| c2-readme-fallback-off | 258 | 47 | 211 | 245 | ttttt | 0.99 | OK | só candidato tcf |
| c3-readme-minheader-off | 245 | 52 | 193 | 245 | !ttt! | 2.10 | OK | todas as colunas com size |
| c4-readme-dropnames | 215 | 22 | 193 | 245 | !ttt! | 2.08 | OK | colunas anônimas |
| c5-readme-sortby | 239 | 49 | 190 | 245 | !ttt! | 2.11 | OK | order-free por cidade |
| c6-readme-parallel2 | 242 | 49 | 193 | 245 | !ttt! | 423.07 | OK | byte-idêntico ao serial (pool 2) |
| d1-escaping | 50 | 39 | 11 | 11 | !!! | 0.38 | OK | separadores escapados no meta |
| d2-hex-borda-f | 37 | 15 | 22 | 22 | !! | 0.30 | OK | 1a col raw=15B -> size hex 'f' |
| d3-hex-borda-10 | 39 | 16 | 23 | 23 | !! | 0.30 | OK | 1a col raw=16B -> size hex '10' |
| d4-hex-256 | 74 | 14 | 60 | 358 | tt | 1.36 | OK | 1a col >=256B -> size hex 3 dígitos |
| d5-multi-1col | 25 | 13 | 12 | 12 | ! | 0.13 | OK | multi de 1 coluna |
| d6-anon-ultima-tcf | 52 | 11 | 41 | 408 | tt | 0.75 | OK | última anônima em modo tcf (token vazio) |
| d7-col-vazias | 22 | 15 | 7 | 7 | !! | 0.23 | OK | coluna só-vazias (1 linha vazia é dado) |
| e1-v2b-width1 | 107 | 17 | 90 | 348 | @t | 2.21 | OK | V2-B K=3 (índice width 1) |
| e2-v2b-width2 | 904 | 18 | 886 | 5088 | @t | 21.96 | OK | V2-B K=120>94 (índice width 2) |
| e3-split | 112 | 20 | 92 | 150 | t! | 2.16 | OK | split '%' (template uniforme, campos low-card) |
| e4-hcc-implicito | 40 | 0 | 40 | 64 | - | 0.14 | OK | dict implícito HCC (refs ^N no body) |
| e5-nature-cpf-validos | 174 | 12 | 162 | 359 | - | 1.08 | OK | spec cpf, DV-válidos EFÊMEROS (apply_rate==1.0) |
| e6-nature-cnpj-validos | 212 | 13 | 199 | 455 | - | 1.37 | OK | spec cnpj, DV-válidos EFÊMEROS (apply_rate==1.0) |
| e7-nature-ip | 117 | 11 | 106 | 229 | - | 1.30 | OK | spec ip (sintético, sem PII) |
| e8-nature-cpf-anon-publicado | 92 | 12 | 80 | 59 | - | 0.35 | OK | FALLBACK-PATH publicável: DV re-invalidado (anonimização §2.3) cai literal |
| e9-nature-cpf-misto | 64 | 12 | 52 | 59 | - | 0.31 | OK | coluna MISTA 2 válidos + 2 anonimizados |
| e10-nature-placeholders-readme | 39 | 12 | 27 | 59 | - | 0.29 | OK | ACHADO: placeholders do README são mod-11-VÁLIDOS -> spec comprime (a 'invalidade' é convenção de cadastro; nota pro F6/README) |
| f1-v2b-cap-8192 | 98005 | 10 | 97995 | 131071 | @ | 5032.73 | OK | K=8192: candidato -> modo dict |
| f2-v2b-cap-8193 | 113296 | 9 | 113287 | 131087 | t | 2656.94 | OK | K=8193: SKIP (cap) -> modo tcf |

## Matriz de readers (F2-3)

| forma do blob | decode() | view() | paridade |
|---|---|---|---|
| orfao | True | não-suportado (fail-loud) | - |
| stamp | True | não-suportado (fail-loud) | - |
| spec-cpf(efemero) | True | não-suportado (fail-loud) | - |
| M | True | True | igual |
| M+escaping | True | True | igual |
| M+drop_names | True | True | igual |
| M+natures(invalidos) | True | True | igual |
| M+sort_by | True | True | igual |
| M (view.group_count('cidade')) | - | tocou 14.5% do corpo | touched=['cidade'] |

## Fail-loud paramétrico (F2-5, controles comportamentais)

| blob | resultado |
|---|---|
| `#TCF.8X...` | fail-loud OK (#TCF.8: discriminador 'X' desconhecido — nao dec...) |
| `#TCF.8H...` | fail-loud OK (#TCF.8: 'H' = multi-col hierarquico RESERVADO (A...) |
| `#TCF.9M...` | fail-loud OK (blob #TCF.9: versao desconhecida deste decoder (...) |
| `#TCF.6 M...` | fail-loud OK (formato legado '#TCF.6 M' nao suportado no 0.8 (...) |
| `meta vazio s/ body` | fail-loud OK (blob corrompido: meta vazio sem body ('#TCF.8M\n...) |
| `size>body` | fail-loud OK (body truncado: coluna 'a' declara 255B no header...) |

Notas fixas: view() cobre SÓ `#TCF.8M` (órfão/stamp/spec = fail-loud
por design — matriz acima); timing de F (boundary) é indicativo (n=1).
