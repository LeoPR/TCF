# T01 — Especificação do Formato TCF v0.1

**Status:** DEFINIDO  
**Tipo:** Design  
**Deps:** nenhuma

---

## Decisão de Base

Usar **Markdown + estilo INI/YAML** como base. Justificativa:
- Markdown é onipresente em dados de treino (GitHub, Stack Overflow, docs)
- `chave: valores` é reconhecido em YAML, INI, Python docstrings
- O LLM não precisa "aprender" o formato — ele já o conhece em partes

RLE (`N:valor`) é secundário e auto-descritivo. A notação existe em documentação
de Parquet, compressão geral, e é legível por humanos.

---

## Formato TCF v0.1

### Estrutura geral

```
# TCF v0.1
> N:val = val repetido N vezes. Sem N = 1 ocorrência.
> Colunas [sorted] estão ordenadas — não correlacionar posição entre colunas.

## <tabela> n=<linhas>
<coluna>: <v1> <v2> <v3> ...
<coluna>[sorted]: <N1>:<v1> <N2>:<v2> ...
```

### Regras

| Elemento | Sintaxe | Exemplo |
|----------|---------|---------|
| Cabeçalho do arquivo | `# TCF v0.1` | — |
| Instrução (comentário) | `> texto` | `> N:val = N repetições` |
| Seção de tabela | `## nome n=N` | `## vendas n=41` |
| Coluna em ordem original | `col: v1 v2 v3` | `vl: 2.5 11.0 1.0` |
| Coluna ordenada + RLE | `col[sorted]: N:v1 M:v2` | `id_produto[sorted]: 5:22 4:33` |
| RLE: 1 ocorrência | omitir N | `1.5` (não `1:1.5`) |
| RLE: N ocorrências | `N:val` | `3:banana` |
| Valores separados | espaço | — |
| Coluna PK (referência) | `col[key]` | `id[key]: 1 2 3 4` |

### Por que `[sorted]` muda o jogo

Quando uma coluna é marcada como `[sorted]`:
1. Os valores estão ordenados — RLE comprime runs consecutivos
2. A posição não pode ser usada para correlacionar com outras colunas
3. **A informação de frequência está embutida no próprio RLE**

Exemplo: `id_produto[sorted]: 4:11 5:22 4:33 3:44 ...`  
→ LLM lê diretamente: produto 22 aparece 5 vezes (mais frequente), 11 aparece 4 vezes, etc.
→ Total de linhas = soma dos prefixos: 4+5+4+3+... = 41 ✓

### O que NÃO faz na v0.1

- Sem FK resolve (relações entre tabelas aparecem como IDs brutos)
- Sem dict encoding de nomes (uma tabela por vez)
- Sem correlação entre colunas de uma mesma linha quando `[sorted]`
- Sem queries que cruzem tabelas

Essas capacidades são para v0.2 (T03).

---

## Exemplo Real: dados vendas/pessoas/produtos

```
# TCF v0.1
> N:val = val repetido N vezes. Sem N = ocorrência única.
> Colunas [sorted] estão ordenadas — não correlacionar posição entre colunas.

## pessoas n=30
id[key]:  1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30
nome:     Ana Bruno Carla Diego Elisa Felipe Gabriela Henrique Isabela João Karen Lucas Mariana Nicolas Otávio Paula Rafael Sofia Thiago Vitória William Yasmin Zeca Alice Bianca Caio Duda Eduardo Flávia Guilherme

## produtos n=12
id[key]:  11 22 33 44 55 66 77 88 99 111 122 133
nome:     Lápis Caneta Caderno Borracha Marca-texto Apontador Régua Cola Tesoura Grampeador Clips Post-it

## vendas n=41
vl:               2.50 11.00 1.00 3.75 2.90 4.50 3.20 5.90 6.50 7.30 12.00 1.80 8.40 1.20 2.70 10.90 2.60 4.10 3.00 5.50 6.10 7.80 11.50 1.40 8.90 1.10 2.30 10.50 2.80 4.30 3.40 5.20 6.20 7.10 12.40 1.60 8.10 1.30 2.20 10.20 2.40
id_pessoa:        1 2 1 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 1 2 3 4 5 6 7 8 9 10
id_produto:       22 33 11 22 44 55 66 77 88 99 111 122 133 11 22 33 44 55 66 77 88 99 111 122 133 11 22 33 44 55 66 77 88 99 111 122 133 11 22 33 44
id_pessoa[sorted]: 3:1 2:2 2:3 2:4 2:5 2:6 2:7 2:8 2:9 2:10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30
id_produto[sorted]: 4:11 5:22 4:33 4:44 3:55 3:66 3:77 3:88 3:99 3:111 3:122 3:133
```

---

## Métricas (dados reais, medido)

| Formato | Chars | Observação |
|---------|-------|------------|
| CSV vendas.csv | 471 | dado bruto |
| JSON Lines expandido (com nomes) | 2336 | 5× maior |
| TCF `vendas` sem sort | 499 | inclui labels |
| TCF `vendas` sorted | 436 | menor que CSV |
| TCF completo (3 tabelas) | ~900 | estimado |

---

## Queries que funcionam com TCF v0.1

| Query | Como o LLM responde | Coluna usada |
|-------|--------------------|-|
| Soma de `vl` | lê a linha `vl:` inteira, soma | `vl` |
| Média de `vl` | soma / 41 | `vl`, `n=41` |
| Maior/menor `vl` | vl[sorted] (ou min/max da linha) | `vl` |
| Produto mais vendido | lê `id_produto[sorted]`, pega maior N: | `id_produto[sorted]` |
| Quantas vendas pessoa 1 (Ana) | conta ocorrências de `1` em `id_pessoa` | `id_pessoa` |
| Quantas pessoas distintas compraram | conta valores únicos em `id_pessoa` | `id_pessoa` |

---

## Próximos Passos

- [ ] T05: implementar encoder Python que gera esse formato
- [ ] T04: testar queries acima no Ollama com esse formato vs CSV vs JSON Lines
- [ ] T02: decidir se floats ficam raw (2.50) ou truncados (2.5) para economizar tokens
- [ ] T03: v0.2 — adicionar dict encoding para resolver FK pelo nome
