# Pesquisa — CEP + ideia de "dicionário externo / codebook compartilhado" [análise]

**Data**: 2026-06-16 · análise (não implementa). Origem: owner — "se CEP/CPF e afins
referenciam siglas mais econômicas, usar um dicionário externo mapeado, com data e versão."

## Estrutura do CEP (manuais dos Correios)
8 dígitos `NNNNN-NNN`. Os **5 primeiros = hierarquia decimal**: 1=Região (0-9), 2=Sub-região,
3=Setor, 4=Subsetor, 5=Divisor de subsetor. Os **3 do sufixo** = identificador de distribuição
(logradouro/localidade/unidade). Ou seja, o CEP **já é** um código-caminho mínimo (cada dígito
é significativo), não uma sigla expansível.

## A ideia: "outer dict" (codebook compartilhado, versionado)
Mapear o valor → um **índice num dicionário-padrão EXTERNO que os dois lados já têm**; transmitir
só o índice + uma referência `(codebook-id, versão)` no header. É a técnica de **shared-dictionary
compression** (dicionários custom do Brotli/Zstandard; HTTP Compression Dictionary Transport).
Difere do **V2-B** (que embute a tabela de únicos no próprio blob): o outer-dict **não embute nada**
— assume o codebook nos dois lados. A versão+data são obrigatórias (o codebook muda → decode
lossless precisa da versão exata).

## CEP — é vantajoso? (medido)
**Não, na maioria dos casos** — e o motivo é que o TCF **já resolve**:
- **O TCF já trata CEP losslessly, com zeros à esquerda, e já explora o prefixo.** Numa coluna de
  CEPs concentrados (Sao Paulo, 013xx), o `encode` deu **93 B vs 119 B raw** (78%), **RT preserva
  os zeros** — OBAT compartilha o prefixo `0131` + dedup `^N` dos repetidos. O **split estrutural
  (ADR-0026, welded)** generaliza isso em colunas maiores, guardando os campos como **strings**
  (preserva zeros à esquerda — ao contrário do `TemplatedPaddedSpec`, que faz `int()`). **CEP não
  precisa de nature especial nem de codebook pra ser bem comprimido em coluna.**
- **O único "outer dict" real do CEP é o DNE** (Diretório Nacional de Endereços, ~1M+ entradas,
  pago/pesado). Índice de ~1M ≈ 3 chars base-94 vs 8 dígitos → economia de poucos chars, **mas
  exige o DNE nos dois lados**. Vantajoso só em nicho: **payload minúsculo / CEP avulso** (sem
  coluna pra deduplicar) E ambos com o DNE. Não compensa o acoplamento no caso geral.
- As "siglas econômicas" (região→nome, prefixo→UF) são **deriváveis do CEP**, não substituições
  que economizam bytes (você ainda precisa do prefixo pra localizar).

## CPF/CNPJ — não se aplica
São **IDs únicos** (não referenciam tabela/codebook). Não há sigla mais econômica; o **pack
base-94** (9 dígitos → 5 chars) já é o ótimo. A ideia de outer-dict não cabe.

## Veredito geral
A técnica do **outer-dict / codebook compartilhado versionado** é válida, mas **na maioria do caso
TABULAR do TCF é subsumida pelo V2-B (dict inline) + split** — que já capturam a redundância
**sem dependência externa**. O nicho do outer-dict: **payloads minúsculos / valores avulsos** que
indexam uma **tabela-padrão grande** que ambos os lados já têm (ex.: município IBGE ~5570, CNAE
~1300, ISO país/moeda). Mesmo aí, só ganha **além** do que o V2-B inline já faz (economiza os bytes
da tabela inline — relevante só em payload pequeno).

## Encaminhamento
- **CEP**: **nenhuma ação** — o TCF já trata (split/OBAT+dict, lossless, zeros preservados). Não
  construir dependência do DNE.
- **Conceito outer-dict** (codebook externo versionado): registrar como hipótese de baixa
  prioridade. Liga-se ao header carregar `(codebook-id, versão)` — mesma infra do **H-NAT-MARK-01**
  (spec/codebook viaja no header, alvo 0.8). Candidatos reais: códigos que indexam tabela-padrão
  grande (IBGE/CNAE/ISO) **em payload minúsculo**. Gate ≥15% weighted antes de qualquer weld.

## Fontes
- Estrutura do CEP: [dbins — Tudo sobre o CEP](https://www.dbins.com.br/tudo-o-que-voce-queria-saber-sobre-o-cep.php) ·
  [Central do Frete — CEP em detalhes](https://blog.centraldofrete.com/tudo-sobre-o-cep-dos-correios-o-codigo-postal-em-detalhes/)
