# Conclusão — TCF.8 + semântica de cardinalidade/hierarquia [probatório]

Peça 9 (ponte header-minimal × hierárquico). Números: `artifacts/` (`python run.py`).

- **Metodologia validada**: escrever a linguagem semântica COMPLETA (explícita, todos os itens) e depois
  DEDUZIR o que sai funciona — e a forma mínima **converge pro colchete da P5** (medido: S6 508B→74B, RT OK).
- **O que é IRREDUTÍVEL** (fica explícito, salvo contrato pré-acordado): **magic + arestas de hierarquia
  (pai→filho) + markers + sizes**. Tudo mais — flags M/N, kind, cardinalidade, rows, tipo-se-uniforme — é
  **deduzível** (do nº de colunas / do nº de linhas dos filhos / do default).
- **A hierarquia é o único item de schema irredutível**: não sai dos dados (o array-vs-objeto sai, mas
  "quem contém quem" não). É o que a peça 3 chamou de arestas pai/filho, e o que O-FMT-14 (header derivável)
  externaliza quando pré-acordado.
- **Resposta**: SIM, incluir cardinalidade/hierarquia no TCF.8. Custo transmitido ZERO (implícito = P5),
  explícito só sob demanda ou pré-acordado. **Cardinalidade ≡ hierarquia = a mesma camada**; é o "contrato"
  que fecha o frontier do header-minimal (O-FMT-14).

**Próximo (protótipo formal — exige aprovação, toca formato/src)**: um TCF.8 opt-in que carrega as **arestas
de hierarquia** (o irredutível) e **deduz o resto**; + o modo **derivável** (schema fora de banda). O gate:
`test_real_world_snapshots.py` + baselines re-pinados; opt-in não muda o default. A linguagem já está
caracterizada (peças 5-9); o welding é uma decisão de formato do owner.
