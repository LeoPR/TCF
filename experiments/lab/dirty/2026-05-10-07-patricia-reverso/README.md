# 07 — patricia reverso

## Princípio / motivação

Patricia forward (atual no exp 02..06) detecta apenas **prefixos
comuns** entre folhas. Dados como `user001@gmail.com`,
`user002@gmail.com`, ... têm sufixo comum `@gmail.com` que não é
fatorado.

Da literatura: **affix tree** (Maaß 1999/2003, "Linear Bidirectional
On-Line Construction of Affix Trees", *Algorithmica* 37:43-74)
combina suffix tree de S e de S^R via affix links. Construção
online linear. Permite estender um fator pelos dois lados.

Para nosso encoder textual demonstrativo, affix tree real é
overkill. A versão mínima do conceito: **inverter as strings antes
de construir Patricia**. A árvore resultante captura sufixos
comuns das strings originais. Decode reconstrói e inverte de volta.

A ferramenta é atemporal: o wrapper `encode_direcao` aceita
`forward` ou `reverse` e usa o mesmo `patricia.py` / `encode_aninhado.py`
sem modificação. Não há heurística, não há otimização, não há
casamento entre direções.

Implementação isolada do conceito teórico (não derivada de
`dirty/old/`, que foi excluído por contém defeitos).

## Propósito

Responde a uma pergunta:

1. **Viabilidade do espelho**: invertendo as strings antes de Patricia,
   o resultado é roundtrip-correto? Como o comportamento (estrutura
   da árvore, bytes) muda em comparação com forward, nos mesmos
   datasets?

## Comparação

- **Compara com**: [06-aninhado-emails-urls](../2026-05-10-06-aninhado-emails-urls/)
  (forward only nos mesmos 4 datasets).
- **É comparável?** Sim, mas com cuidado: forward e reverse produzem
  **árvores diferentes**, e portanto fragmentos diferentes. Comparar
  só a camada 2 (marcadores) é enganoso. A comparação correta usa
  **ref + dados** (camada 3 macro é constante, camada 4 inexistente).
- O que muda em relação ao 06: nenhum algoritmo (patricia, encoder
  aninhado, decoder) foi modificado. Apenas adicionamos um wrapper
  que inverte as strings na entrada e na saída, com marcador
  `<dir:forward>` ou `<dir:reverse>` no TCF.

## Cenários e valores possíveis

Mesmos 4 datasets do exp 06 (copiados em `data/`):

| Dataset | Conteúdo | Hipótese sobre direção dominante |
|---|---|---|
| D1 — emails-um-dominio | `user001..user010@gmail.com`, 10 únicos | Reverse: sufixo `@gmail.com` (10 ocorrências) cobre tudo. Forward fica fragmentado por `user010` não casar `user00`. |
| D2 — emails-multi-dominio | 4 nomes × 3 domínios | Forward: 4 prefixos `nome@`. Reverse: 3 sufixos `.dominio.com`. Aposta no forward (mais grupos). |
| D3 — urls-path-comum | `https://api.example.com/v1/users/N` | Forward: prefixo grande (33 chars) cobre tudo. Reverse: sufixos numéricos `1..10` não compartilham. |
| D4 — urls-multi-recurso | mix users/orders/products sob mesma base | Forward: hierarquia de 3 níveis. Reverse: nada estrutural. |

Cada cenário é encodado nas **duas direções**, com roundtrip
validado em ambas (8 verificações totais).

## Resultado observado

Roundtrip **8/8 OK**.

### Estrutura da árvore por direção

| Dataset | Forward (nós/top/filhos) | Reverse (nós/top/filhos) |
|---|---|---|
| D1 | 12 / 1 / 11 | 11 / 1 / 10 |
| D2 | 16 / 4 / 12 | 20 / 1 / 19 |
| D3 | 11 / 1 / 10 | 10 / 10 / 0 |
| D4 | 16 / 1 / 15 | 12 / 12 / 0 |

Em D3 e D4 reverse, Patricia não acionou (0 filhos) — todas as
strings ficaram top-level. Os IDs invertidos `1`, `2`, ..., `10`
não compartilham prefixo ≥ 3 chars entre si.

### Comparação válida — ref + dados

| Dataset | fwd (r+d) | rev (r+d) | delta | direção menor |
|---|---:|---:|---:|---|
| D1 | 518 | **456** | -62 | reverse |
| D2 | **617** | 726 | +109 | forward |
| D3 | **420** | 602 | +182 | forward |
| D4 | **551** | 710 | +159 | forward |

**Apenas D1 teve menos bytes em reverse**. Nos outros 3 cenários,
forward foi a direção com menos bytes totais.

### Observação importante — camada 2 isolada é enganosa

| Dataset | fwd_ref | rev_ref | delta (só ref) |
|---|---:|---:|---:|
| D1 | 401 | 376 | -25 (reverse menor) |
| D2 | 457 | 592 | +135 (forward menor) |
| D3 | 376 | 261 | -115 (reverse menor) ← engana |
| D4 | 487 | 275 | -212 (reverse menor) ← engana |

Em D3 e D4 reverse, ref é menor porque a árvore é plana (sem
aninhamento, sem decls recursivas). Mas isso é porque Patricia
não fatorou nada — então as strings inteiras ficam como dados
(`dados=341` em D3 reverse vs `44` em forward). A economia em ref
é mais que compensada pelo crescimento em dados.

**Conclusão metodológica**: na comparação entre forward e reverse,
as árvores são diferentes → fragmentos diferentes → camada 1
(dados) varia. **Comparar só camada 2 não é válido neste caso**.
Comparação correta é ref + dados (= total - macro).

Esta observação contrasta com o exp 04, onde comparávamos a mesma
árvore com 2 serializações diferentes (separada vs inline) — ali
camada 1 era constante e camada 2 isolada era a métrica certa.

## Limitações

- Apenas 4 datasets, 20 linhas cada. Não fala sobre escala.
- **Sem heurística de escolha automática** entre forward e reverse.
  Este experimento mostra as duas direções lado a lado; a decisão
  fica para um experimento posterior.
- **Sem casamento** entre direções (uma linha não pode usar prefix
  + suffix simultaneamente). Cada cenário é OU forward OU reverse.
- Algoritmo Patricia (`patricia.py`) é byte-idêntico aos exps
  anteriores. Mesma heurística gulosa, MIN_PREFIXO=3, MIN_GRUPO=2.
- Em D3 e D4 reverse, Patricia não fatora nada. Caso degenerado
  que ilustra "espelho não funciona universalmente".
- Não há comparação com formato compacto, CSV ou JSON.

## Como reproduzir

```bash
cd experiments/lab/dirty/2026-05-10-07-patricia-reverso
python run.py
```

5 tabelas + árvore + TCF lado a lado para cada cenário. Arquivos
em `encoded/{D}-{forward,reverse}.tcf` e `decoded/{D}-{forward,reverse}.csv`.
