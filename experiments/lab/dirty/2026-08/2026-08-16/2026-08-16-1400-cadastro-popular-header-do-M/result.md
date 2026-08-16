# Resultado — o header do `.8M` num cadastro popular, com specs

n=500, 7 colunas, 0 falhas de RT, invariante de fronteira verificado por assert.

## 1. O wire principal (com specs): 21.047 B, linha 1 de 82 B

```
#TCF.8Mf=id,a56=nome,!bb7=cpf:cpf,1c11=email,%15ba=telefone,%7fb=nascimento,@ativo
```

| coluna | modo | nat | size hex | bytes | [ini:fim) | começo do corpo |
|---|---|---|---|---:|---|---|
| id | `tcf` | — | `f` | 15 | [0:15) | `*500+1\|\000001` (seq-RLE pega o contador) |
| nome | `tcf` | — | `a56` | 2646 | [15:2661) | `Carl*a* *S*ilva` (OBAT fatora afixos) |
| cpf | `raw` | **cpf** | `bb7` | 2999 | [2661:5660) | payload base-94 do spec |
| email | `tcf` | — | `1c11` | 7185 | [5660:12845) | OBAT |
| telefone | `split` | — | `15ba` | 5562 | [12845:18407) | template + campos |
| nascimento | `split` | — | `7fb` | 2043 | [18407:20450) | template `NNNN-NN-NN` + campos |
| ativo | `dict` | — | (EOF) | 514 | [20450:20964) | tabela 2 únicos + stream |

**Fronteiras**: as fatias `[ini:fim)` cobrem o corpo inteiro sem furo nem sobra (assert no
`run.py`); a última coluna não tem size e vai até o fim do arquivo (`min_header`,
ADR-0023/O-FMT-15). Os sizes são hex (`bb7` = 2999).

## 2. O FLOOR por coluna — quem pediu spec e o que aconteceu

| coluna | apply_rate | used | o que o header mostra |
|---|---:|---|---|
| cpf | 1.0 | **True** | `!bb7=cpf:cpf` — aplicou e venceu (25.497 → 21.047 B, **−17,5%** na tabela) |
| nascimento | 1.0 | **False** | `%7fb=nascimento` — aplicou, mas o **split ganhou o FLOOR** (2.043 contra ~3,9k do ordinal) |
| id (`int-pad`) | — | — | `int_pad_para(id)` = `None`: largura já uniforme, nada a normalizar (correto) |

O detalhe do cpf que vale registro: o modo saiu **`raw` (`!`)**, não `tcf` — sobre payload
base-94 denso o core custa mais que o corpo cru. O FLOOR compôs spec+raw sozinho.

## 3. As três grafias do mesmo conteúdo

| variante | linha 1 | total |
|---|---:|---:|
| default (`min_header`) | 82 B | 21.047 B |
| `min_header=False` | 86 B | 21.051 B |
| `drop_names=True` | **39 B** | **21.004 B** — `#TCF.8Mf,a56,!bb7:cpf,1c11,%15ba,%7fb,@` |

`drop_names` corta os nomes e o decode devolve posicionais `'0'..'6'` (valores conferem). É a
direção "contrato nas pontas": o header carrega só o que a outra ponta não deduz.

## 4. A fronteira: a flag como bool

| | rota | bytes |
|---|---|---:|
| flag `"ativo"/"inativo"` | `.8M` (com specs) | 21.047 |
| flag `True/False` | `.8H` | **33.996 (+61,5%)** |

Tipar **uma** coluna troca a rota da tabela inteira (`_tabela_flat`, `encoder.py:146`), e o
custo não é a tipagem — é o candidato único do `.8H` (`T-8H-UM-CANDIDATO-SO`). No `.8H` os
specs de coluna nem entram nesta chamada (a rota órfã não os consulta).

## 5. Flat × `.8M`, comparação JUSTA (spec dos dois lados)

| coluna | flat | modo flat | `.8M` | modo `.8M` | vence |
|---|---:|---|---:|---|---|
| id | 22 | core (seq-RLE) | 25 | tcf | flat |
| nome | 2.386 | **bN `B8`** | 2.658 | tcf | flat |
| cpf | 3.419 | `:cpf` (core) | **3.015** | **raw:cpf** | `.8M` |
| email | 7.192 | core | 7.198 | tcf | flat |
| telefone | 6.732 | polaridade | **5.579** | **split** | `.8M` |
| nascimento | 3.996 | `:dt` (core) | **2.062** | **split** | `.8M` |
| ativo | **108** | **bN `B1`** | 528 | dict | flat |

**Nenhum lado domina — 4/7 contra 3/7.** E os motivos são exatamente os candidatos que cada
rota não tem: o flat não tem `split` nem `raw`; o `.8M` não tem bN nem polaridade. `ativo` é o
caso extremo: bN 108 B contra dict 528 B (**4,9×**). A resposta registrada é a **união**
(`T-UM-CAMINHO-SO`), não a troca.

## 6. Ressalvas

- **Sintético.** Cadastro plausível, mas gerado; as proporções (−17,5% do cpf, 4,9× do ativo)
  são deste dado. O que transfere é o MECANISMO (quem vence o FLOOR e por quê), não o número.
- **`email` não tem candidato bom** em rota nenhuma (7,2 KB dos 21 KB = 34% do wire). Se
  houver um alvo futuro de spec neste cadastro, é ele.
- **n=500, uma seed.** Os modos por coluna podem virar com n/cardinalidade (o `ativo` some no
  bN com qualquer n; o split do telefone morre se UMA linha quebrar o template —
  `multi/split.py:40-41`).
