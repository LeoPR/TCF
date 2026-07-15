# Lab 2026-07-14-2336 — amostra de POPULAÇÃO com seleção HONESTA (hierarquia / ligações diversas)

**Status**: estudo de cobertura + fronteira, dado real, seleção honesta. **Ticket**:
[T-CODE-TCF8H-WELD](../../../../tickets/T-CODE-TCF8H-WELD.md) · relaciona
[tcf-camadas-arquitetura §multi-tabela](../notas/tcf-camadas-arquitetura.md).

Owner (2026-07-14): *"uma representação selecionada de dados não significa amostra de um todo. a
gente pode estar pegando, por muita sorte (ou azar), justamente o que funciona. Temos que usar o
conceito de amostra de população com seleção honesta — não só randômica; por isso fizemos o
Shaper... faltou um estudo pra bancos com hierarquia (ou estruturas com ligações diversas)."*

O teste em massa anterior ([lab 2231](../2026-07-14-2231-hierarquia-massa-shaper-tpch/)) usou a
população inteira do sf001 — honesto DENTRO do sf001, mas UMA topologia. Este estudo responde a
crítica de amostragem: será que o RT vale por sorte de fatia?

## O que roda (`study.py`)

- **(A) RT em ESTRATOS HONESTOS**: o Shaper (`fk_preserving`) tira amostras **estratificadas
  proporcionais (Neyman)** de `customer` por `c_mktsegment` e `c_nationkey`, com integridade
  referencial, em **volumes {0.1, 0.3, 0.6} × seeds {7, 42, 101}** (18 estratos). Cada um é aninhado
  (`customer→[pedidos]→[itens]`) e testado por RT byte-exato. Se RT fosse sorte de fatia, falharia em
  algum. Representatividade reportada (TVD/JSD/χ²).
- **(B) FRONTIER — ligações diversas**: mapeia o que NÃO é contenção 1:N — `partsupp` (ponte N:N
  part↔supplier), `lineitem` multi-pai (orders + part + supplier). Declara o limite honesto: o weld
  cobre árvore 1:N; N:N/multi-pai = super-hierarquia (H-HIER-MULTITABELA-01), hoje fail-loud.
- **(C) 2ª fonte REAL**: `br-identidades` (N:N sócio↔empresa) — projeção `pessoa→[empresas]` RT.
- **(D) VALORES-QUEBRADORES**: varre colunas free-text reais por `\n`/controle (conecta a
  T-API-BOUNDARY-CONTRACTS — não deduzir "nunca ocorre" de uma amostra).

## Honestidade

O estudo declara **cobertura E fronteira**: onde o RT vale (contenção, em múltiplos estratos
honestos + 2ª fonte) e onde NÃO vale ainda (ligações diversas). Pobreza de dados ligados no repo
(só TPC-H rico + br-identidades) é declarada como limite. Ver [inputs/datasets-provenance.md](inputs/datasets-provenance.md)
+ [result.md](result.md) + [outputs/01-estudo.txt](outputs/01-estudo.txt). Zero mudança em `src/tcf`.
