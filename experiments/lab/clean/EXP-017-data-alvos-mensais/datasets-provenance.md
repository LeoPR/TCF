# Proveniência dos dados: EXP-017

Exigido pela convenção canônica (`dirty-lab-convencoes.md` §2: *"Entradas + proveniência:
origem + anonimização + viés declarado"*). Este lab usa **dados reais**, então a
proveniência é parte da evidência, não formalidade.

## Origem

Tudo vem de `Z:/tcf-data/` (o hub local do projeto). **Nada foi baixado**: regra do
projeto: quando o hub já tem, não se busca fora. O extrator é [`extrai.py`](extrai.py);
as fatias congeladas ficam em `inputs/fontes/` para o lab rodar **sem** `Z:`.

| coluna | origem exata | n | por que está aqui |
|---|---|---:|---|
| `tpch-orderdate` | `interim/tpch-sf001.db` → `orders.o_orderdate` | 3000 | data comercial clássica |
| `tpch-shipdate` · `commitdate` · `receiptdate` | `interim/tpch-sf001.db` → `lineitem.*` | 3000 | as 3 colunas irmãs |
| `tpch-sf01-orderdate` | `interim/tpch-sf01.db` → `orders.o_orderdate`, **OFFSET 90000** | 3000 | amostra distinta da mesma família |
| `br-data-cadastro` | `interim/br-identidades.db` → `pessoas.data_cadastro` | 3000 | cadastro BR, span curto |
| `br-data-abertura` | `interim/br-identidades.db` → `empresas.data_abertura` | 3000 | span longo |
| `receita-data-inicio` | `interim/receita-cnpj.db` → `estabelecimentos.data_inicio` | 3000 | grafia `YYYYMMDD` compacta |
| `retail-invoicedate` | `interim/online-retail.db` → `online_retail.InvoiceDate` | 3000 | **datetime com hora**, não é date puro |
| `football-date` | `external/football-results/results.csv` → `date` | 3000 | 1872..hoje, o maior span |

Cada coluna é congelada em **duas ordens**: `.natural.json` (a ordem de armazenamento) e
`.ordenado.json`, porque ordenar é a maior alavanca medida do projeto (lab
`2026-07-23-1832`: 6668 → 102 B numa coluna).

## Anonimização

Nenhuma das colunas extraídas é identificadora: são **datas**. Não há CPF, CNPJ, nome ou
endereço em `inputs/`. As medições de CPF/CNPJ citadas no `report.md` foram feitas fora
deste lab (scratchpad da caçada adversarial) e **nenhum dígito verificador válido foi
gravado**, regra dura do projeto.

## Viés declarado: o que estes dados NÃO representam

Isto é o achado central do lab, não uma ressalva de rodapé:

1. **Zero cadência mensal.** Varredura exaustiva (613 colunas em `Z:` + `datasets/`):
   todas as 13 colunas físicas de data têm os **31 dias-do-mês** com distribuição
   quase uniforme (dia dominante entre 3,3% e 4,6%; uniforme = 3,23%). O corpus é todo
   **fato transacional cru**. O regime que os alvos mensais atacam não está aqui, e é
   alcançável só por **derivação** (agregado mensal), não por amostragem.
2. **`N_MAX = 3000` é uma escolha, e ela move o resultado.** A mesma coluna TPC-H dá 0,3%
   em `n=3000` e **18,7%** em `n=4000` (penhasco entre 3850-3900, `T-PENHASCO-INICIO`).
   Qualquer número deste lab é *daquele* n.
3. **`LIMIT`/`OFFSET` sem `ORDER BY`** devolve a ordem física do SQLite. A variante
   `.natural.json` é essa ordem, não é "a ordem de negócio".
4. **TPC-H é sintético por construção** (dbgen). Aparece como 5 das 10 colunas: o corpus
   é mais uniforme do que o mundo. Foi exatamente por isso que `tpch-sf01` duplicava o
   `sf001` byte a byte antes do `OFFSET`, dbgen é determinístico.
5. **Sem colunas de data BR de vencimento/competência**, que é o regime onde os alvos
   mensais fariam sentido. Registrado como `T-CORPUS-DATA-MENSAL`.

## Reprodução

```
python extrai.py    # requer Z: montado; regrava inputs/fontes/
python run.py       # NÃO requer Z:; regrava inputs/*.entrada.json, intermediates/, outputs/
```
