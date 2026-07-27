# Proveniencia — dominio comprimido + alinhamento (2026-07-27-1647)

## Sinteticas — deterministicas, sem RNG

Rotulos fixos (`ativo`, `inativo`, `suspenso`, `cancelado`, `revisao`, `arquivado`,
`pendente`) ciclados por `i % k`, e dominios literais nas tabelas de exemplo. **Sem `random`,
sem relogio, sem rede.** Nao ha' documento (CPF/CNPJ/cartao) sintetizado neste lab.

A varredura de alinhamento usa `f"v{i % k}"` — o dado mais neutro possivel, porque ali o que
se testa e' a aritmetica de bits, nao a compressao.

| eixo | varrido |
|---|---|
| alinhamento | `n` de **1 a 40** x `w` de **1 a 6** x 2 montagens x 2 grafias = **936** casos |
| foco | `k` de **2 a 7**, com e sem null (o recorte pedido: bool + 3 a 7 tipos) |
| dominios de exemplo | 2, 3, 4, 6 e 8 valores, curtos e longos |

## Reais — fixtures ja' committadas

**Nenhum download.** Todas de `datasets/samples/`, versionada no repo. Escolhidas por serem
categoricas com `k` na faixa do estudo:

| coluna | arquivo | campo | k |
|---|---|---|---:|
| `adult-sex` | `adult-census/adult-sample.csv` | `sex` | 2 |
| `adult-race` | idem | `race` | 5 |
| `adult-workclass` | idem | `workclass` | 6 |
| `cnpj-situacao` · `cnpj-uf` | `receita-cnpj/cnpj-2k.csv` | `situacao`, `uf` | 2 · 28 |
| `pm25-cbwd` | `beijing-pm25/beijing-pm25-sample.csv` | `cbwd` | 4 |

`cnpj-uf` (k=28) esta' fora do recorte 2-7 de proposito: e' o contraste que mostra o
comportamento em `k` grande. `cnpj-situacao` esta' aqui porque e' onde comprimir o dominio
**piora** (354 -> 356) — o contraexemplo.

Valores vazios sao pulados; leitura e' fail-loud em nome de coluna inexistente.

## Validacao — e por que nao e' circular

O `hoje` vem do `encode` **REAL** do `src/tcf`. As duas propostas sao lidas por **leitores
independentes** (`le_v_len`, `le_v_b64`), que reimplementam a semantica — leem o cabecalho
posicionalmente, deduzem ou leem o limite do bloco, desempacotam os bits e so' entao mapeiam
pelo dominio. O alvo da comparacao sao os **dados originais**, nunca a inversa da
transformacao.

Foi essa independencia que permitiu varrer 936 combinacoes de alinhamento com significado: se
o leitor fosse a inversa, ele erraria o rabo do mesmo jeito que o emissor e passaria.

Licao aplicada do lab `2026-07-26-0038`, retratado por validacao circular.

## Limites declarados

- **Nada soldado**; `src/tcf` intocado. Os `.tcfp` sao proposta — o `decode` publico nao os le'.
- Alinhamento varrido ate' `n=40`, `w=6`. Acima disso, nao exaustivo.
- **gzip e CPU nao medidos.**
- Largura **variavel** por valor (para nao desperdicar slots em k=3,5,6,7) nao foi estudada.
- A grafia `#TCF.8B<w><n_hex>` e' notacao do lab; o namespace real (`b2`/`b4`/`b8` reservados)
  nao foi decidido.

## Reprodutibilidade

`python run.py` regenera byte a byte — sem RNG, sem relogio, sem rede. Sai `0` so' se as 936
combinacoes de alinhamento e todos os RT dos leitores independentes passarem.
