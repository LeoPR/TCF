# 8. Discussao

*Este capitulo sera preenchido apos conclusao dos experimentos.*

## 8.1 Quando TCF ajuda e quando nao

*Analise das condicoes em que formato columnar supera row-oriented.*

## 8.2 RLE: beneficio real vs overhead

*Compressao vs custo de colunas sorted em datasets com pouca repeticao.*

## 8.3 Compressao vs Interpretabilidade

*TCF pode ser mais compacto mas menos interpretavel? Ou o contrario?*

## 8.4 Impacto do Prompting

*CoT/PoT mudam o ranking de formatos? Se sim, formato importa menos que tecnica.*

## 8.5 Modelos grandes vs pequenos

*F6 mostra que math_control separa modelos. Formato e secundario a capacidade base?*

## 8.6 Limitacoes e Ameacas a Validade

- **Interna:** Dataset pequeno (41 linhas)
- **Externa:** Modelos locais quantizados vs APIs comerciais
- **Construto:** Perguntas em portugues (vies linguistico)
- **Estatistica:** Sem Bonferroni correction nas fases iniciais
- **Vies F7:** CSV/JSONL desnormalizados vs TCF normalizado em Phase 1
