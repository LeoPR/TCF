# Procedência — corpus real, e o viés da amostra

## A origem

`Z:/tcf-data/interim/*.db`, abertos em **somente leitura** (`file:...?mode=ro`). **Nada é
baixado** — o corpus já existe na máquina.

23 tabelas não-vazias em 8 bancos: `adult-census`, `br-identidades` (pessoas, empresas),
`ibge-municipios`, `online-retail`, `receita-cnpj`, `tpch-sf001` (8 tabelas), `tpch-sf01`
(8 tabelas), `wine-quality`. O `beijing-pm25.db` tem 0 bytes e é pulado.

## A amostragem, e por que esta

**Janela contígua do meio**, alvo 2000 linhas: `LIMIT 2000 OFFSET (n-2000)//2`.

É a régua estabelecida no lab [`0530`](../../2026-08-15/2026-08-15-0530-date-real-e-cpu/):
o **passo espalhado** (`v[::k]`), que é a convenção antiga do projeto, **destrói a adjacência**
e mede uma distribuição que não existe na coluna — lá foi medido |Δ| mediano **710** contra
**50** da coluna inteira. Do meio, e não da cabeça, para não reintroduzir o viés que o passo
espalhado existia para evitar.

## Vieses declarados

- **2000 linhas por tabela.** Em `br-identidades/pessoas` (500k) isso é **0,4%**; em
  `tpch-sf01/lineitem` (600k), **0,3%**. As proporções POR COLUNA são estáveis nesse regime,
  mas o **agregado do corpus** é o agregado da amostra — não do corpus inteiro.
- **`NULL` do SQLite vira string vazia.** O `.8M` é `dict[str, list[str]]`; não há
  representação de nulo nesta rota. Tabela com muitos nulos está sendo medida como tabela com
  muitas strings vazias, o que **favorece** os modos de baixa cardinalidade.
- **`tpch-sf001` é prefixo do `tpch-sf01`** — registrado no EXP-017 (*"LIMIT puro devolve as
  MESMAS linhas, md5 idêntico"*). As duas entram no agregado, então **o TPC-H tem peso
  dobrado** (16 das 23 tabelas). Sem elas o `.8M` ainda vence, por menos.
- **Não é stress.** É o corpus como ele é, no caminho normal — sem dado adversarial, sem
  nomes de coluna patológicos, sem volume extremo.
