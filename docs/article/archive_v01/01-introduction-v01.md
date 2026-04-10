# 1. Introducao

## 1.1 Contexto

Large Language Models (LLMs) sao cada vez mais utilizados para raciocinar sobre
dados estruturados — responder perguntas, calcular agregacoes, identificar padroes.
No entanto, LLMs recebem dados como texto plano, e a forma como esses dados sao
serializados afeta diretamente a capacidade do modelo de interpreta-los.

Formatos tradicionais como CSV, JSON e Markdown sao **row-oriented**: cada linha
representa um registro completo. Isso significa que nomes de colunas sao repetidos
em cada linha (JSON), ou que valores de uma mesma coluna ficam espalhados pelo texto
(CSV). Para um modelo que processa tokens sequencialmente, localizar "todos os valores
de uma coluna" requer ler o documento inteiro.

## 1.2 Problema

Formatos expandidos sao **token-ineficientes**. JSONL repete nomes de campo em cada
linha, consumindo tokens com informacao redundante. CSV e mais compacto mas nao
oferece contexto semantico (IDs numericos sem significado). Markdown Tables adicionam
caracteres de alinhamento (`|`, `---`) que nao carregam informacao.

Alem da ineficiencia de tokens, nao ha evidencia sistematica de qual formato
facilita o **raciocinio matematico** de LLMs sobre dados tabulares. Surveys recentes
(Sui et al., 2024) testaram formatos row-oriented mas nunca exploraram
representacoes **column-oriented** ou com **compressao** no input.

## 1.3 Contribuicao

Propomos o **TCF (Textual Columnar Format)**, um formato de serializacao textual
orientado a colunas com compressao RLE, construido como sublinguagem de Markdown.

Contribuicoes especificas:

1. **Primeiro formato columnar** proposto para consumo por LLMs
2. **RLE como compressao natural** — `N*val` e legivel por humanos e maquinas
3. **Metodologia diagnostica 3-layer** que separa capacidade aritmetica,
   compreensao de formato e capacidade computacional
4. **Ablacao sistematica** de componentes (numeric encoding, FK mode, sort mode)
5. **Analise Pareto** accuracy x token efficiency — tradeoff nao explorado na literatura

## 1.4 Organizacao do Artigo

- **Cap 2:** Trabalhos relacionados e posicionamento
- **Cap 3:** Design e especificacao do TCF
- **Cap 4:** Metodologia experimental (fases, metricas, datasets)
- **Cap 5:** Resultados: encode/decode e benchmark de compressao
- **Cap 6:** Resultados: compreensao de formato por LLMs (Phase 1)
- **Cap 7:** Resultados: ablacao, deducao, testes avancados (Phase 2+)
- **Cap 8:** Discussao
- **Cap 9:** Conclusao e trabalhos futuros
