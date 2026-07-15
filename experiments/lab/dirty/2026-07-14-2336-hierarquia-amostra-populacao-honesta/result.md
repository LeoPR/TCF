# Resultado — amostra de população com seleção honesta (hierarquia / ligações diversas)

**[probatório]** `study.py` (Shaper honesto + codec weldado, read-only). Números:
[outputs/01-estudo.txt](outputs/01-estudo.txt).

## (A) RT em estratos HONESTOS — 18/18 byte-exato

Amostragem estratificada proporcional (Shaper `fk_preserving`) por `c_mktsegment` e `c_nationkey`,
volumes {0.1, 0.3, 0.6} × seeds {7, 42, 101} = **18 estratos honestos**. Todos RT byte-exato.
Representatividade alta (TVD 0.0011–0.029). **Distribuição de multiplicidade** exercitada (o que
estressa o codec): pedidos/cliente min=2 **max=32** média=15; itens/pedido 1–7; **500 clientes SEM
pedido** (cauda de array vazio). Se RT dependesse de fatia de sorte, falharia em algum estrato —
passar em 18/18 com a cauda incluída = **estrutural**.

## (B) FRONTIER honesto — ligações diversas NÃO cobertas

- `partsupp`: 8000 arestas **N:N** (part até 4 suppliers; supplier até 80 parts) → não é árvore.
- `lineitem`: multi-pai (orders + part + supplier) → snowflake.
- **Veredito**: o weld cobre **contenção 1:N**; N:N/multi-pai = super-hierarquia (FK/junção,
  H-HIER-MULTITABELA-01), hoje **fail-loud (não corrompe)**. `1:N ≡ N:1` por ponto de vista (a N:N
  vira 1:N ao escolher a raiz); falta representar **múltiplas raízes/junção simultâneas**.

## (C) 2ª fonte REAL — br-identidades

`pessoa → [empresas onde é sócio]` (projeção 1:N da N:N real sócio↔empresa): **RT=True**, 500 pessoas.
Domínio diferente do TPC-H → não é uma fonte só.

## (D) Valores-quebradores — 0 nesta população (com ressalva honesta)

Varredura de `\n`/controle nas colunas free-text reais (comments, address, clerk): **0 ocorrências**.
Ressalva **explícita**: é achado desta amostra; o contrato `\n`-em-valor (T-API-BOUNDARY-CONTRACTS)
segue **pendente** — não deduzir "nunca ocorre".

## Síntese honesta (cobertura E fronteira)

- **Coberto**: contenção 1:N — estrutural (18/18 estratos honestos + 2ª fonte real), não sorte.
- **Fronteira declarada**: ligações diversas (N:N/multi-pai/snowflake) — fail-loud, alvo de super-hierarquia.
- **Limite de população**: só TPC-H (rico, mas **sintético**) + br-identidades (1 FK) têm ligação no
  repo. O Shaper mitiga com amostra honesta; ampliar (mais fontes reais ligadas OU Shaper GERANDO
  estruturas hierárquicas realistas) fica registrado como próximo.

`confianca: Alta` p/ contenção 1:N (honesto por construção). A auditoria adversarial (workflow) das
lacunas de honestidade é registrada abaixo/no ticket quando rodar.
