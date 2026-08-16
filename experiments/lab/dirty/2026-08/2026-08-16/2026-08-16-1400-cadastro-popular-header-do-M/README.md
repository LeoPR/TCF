# Cadastro popular — a construção do header do `.8M` com specs, pra inspeção

> **Owner (2026-08-16)**: *"um cadastro simples e popular de transmissão, com o básico de
> nome, cpf, email, telefone, data de nascimento e um flag de ativo/inativo... a intenção
> agora é ver a construção do header com alguns specs variados... revisar a parte de término
> de coluna, quando uma acaba e outra começa... pode fazer o dirtylab como sempre, aí eu
> inspeciono."*

## A revisão "vital" pedida antes de começar — o que resolveu cada ponto

| ponto | resolução |
|---|---|
| **CPF em output commitado** (regra: DV-válido nunca publicado) | precedente da **suíte soldada**: `tests/test_nature_compete.py:21-48` gera CPF DV-válido **algoritmicamente** (base com seed + DV mod-11). Este lab usa o MESMO gerador — CPF-contador sintético, não amostrado de gente real |
| **flag ativo/inativo** | como **string** fica no `.8M`; como **bool** vira a rota da tabela INTEIRA pra `.8H` (**+61,5%**) — Bloco 4. É o `_tabela_flat` (`encoder.py:146`) + `T-8H-UM-CANDIDATO-SO` |
| **os 5 specs do registry** | o cadastro exercita **cpf** e **data-iso**; `int-pad` **não aplica** (id de largura uniforme → `int_pad_para` devolve `None`, comportamento correto); cnpj/ip não têm coluna natural aqui — fora de propósito |
| **telefone/email sem spec** | telefone é pego pelo **split `%`** (template uniforme); email não tem mecanismo dedicado (OBAT/tcf) |
| **nomes de coluna × `T-POLARIDADE-COME-NOME`** | nenhum nome termina em pontuação — o defeito não é acionado aqui (e a última coluna é `ativo`) |

## O que o lab mostra (resultado em [`result.md`](result.md))

- **A anatomia do header**, decomposta com o parser real do formato (`_parse_meta` — paridade
  por construção), com **fronteiras `[ini:fim)` por coluna** e invariante verificado por
  assert: as fatias cobrem o corpo inteiro, sem furo nem sobra.
- **O FLOOR decidindo por coluna**: `:cpf` aplica e **vence** (o header carrega `!bb7=cpf:cpf`);
  `:dt` aplica (rate=1.0) e **perde** pro split `%` — o header sai `%7fb=nascimento`, sem `:dt`.
- **Três grafias do mesmo conteúdo**: default 82 B de linha 1 · `min_header=False` 86 B ·
  `drop_names=True` **39 B** (nomes viram posicionais no decode).
- **O gap de candidatos NOS DOIS sentidos** (comparação justa, spec dos dois lados):
  flat vence 4/7 (bN em `nome`/`ativo`), `.8M` vence 3/7 (split em `telefone`/`nascimento`,
  e **`raw` sobre o payload do cpf** — que o flat não tem).

## Como rodar

```
python run.py    # sai 0 só se todos os RTs fecharem E o invariante de fronteira bater
```

Sem `Z:` — 100% sintético, `random.Random(20260815)`, n=500. `src/tcf` intocado.

## Onde olhar

| arquivo | o que é |
|---|---|
| `outputs/cadastro-com-spec.tcf` | **o wire principal** — abra e confira a linha 1 |
| `outputs/cadastro-sem-spec.tcf` · `-header-cheio.tcf` · `-sem-nomes.tcf` | as variantes de grafia |
| `outputs/cadastro-flag-bool.tcf` | a fronteira (o `.8H` que a flag bool provoca) |
| `outputs/INDEX.md` | a anatomia navegável, coluna a coluna |
| `resultado.json` | todos os números |

## Vínculo

`T-UM-CAMINHO-SO` (a união de candidatos) · `T-8H-UM-CANDIDATO-SO` (o custo da fronteira) ·
ADR-0023/0034 (min_header, header default) · ADR-0026 (split) · ADR-0027/0041 (`:id`) ·
`T-NATURE-IGNORADA-CALADA` situação (2) (coluna inexistente em `nature_per_col` é descartada
calada — cuidado com typo de nome ao passar specs) · `T-POLARIDADE-COME-NOME`
