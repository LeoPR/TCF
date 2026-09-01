---
title: "T-DOC-RELEASE-083-SUPERFICIE: reconciliar changelog, status e roadmap com a publicação"
type: task
status: open
priority: P2
created: 2026-08-29
updated: 2026-09-01
gate: "documentacao (continuo, sem ciclo) (triagem 2026-09-01)"
blocked-by: []
related:
  - CHANGELOG.md
  - STATUS.md
  - ROADMAP.md
  - tickets/T-DOC-TIPOS-MISTOS.md
  - tickets/T-QA-083-REVALIDACAO.md
  - experiments/lab/dirty/2026-08/2026-08-29/2026-08-29-2320-revalidacao-083-evidencia/
---

# T-DOC-RELEASE-083-SUPERFICIE

**[probatório → execução]** A publicação 0.8.3 está concluída, mas a superfície viva ainda a
descreve como preparada. A nota da release também faz três afirmações mais amplas que a evidência
ou o comportamento.

## Evidência

Fonte única desta revisão:
[`result.md`](../experiments/lab/dirty/2026-08/2026-08-29/2026-08-29-2320-revalidacao-083-evidencia/result.md).
A situação externa, os hashes das páginas locais e as linhas encontradas estão em
[`superficie.observacao.json`](../experiments/lab/dirty/2026-08/2026-08-29/2026-08-29-2320-revalidacao-083-evidencia/outputs/superficie.observacao.json).

| superfície | fato medido | divergência atual |
|---|---|---|
| `STATUS.md` / `ROADMAP.md` | PyPI responde `0.8.3`; `refs/tags/v0.8.3` existe no remoto | ainda dizem `0.8.2` publicada e 0.8.3 aguardando tag/push |
| título da 0.8.3 | bool+str é aceita no single e recusada em `.8M`/`.8H` por decisão | “the three families answer the same question the same way” é universal demais |
| mudanças de emissão | além de `?:` → `?0:`, `{"v": []}` muda de `.8H` (18 B) para `.8M` (12 B) | changelog diz “one change” e “nothing else” |
| compatibilidade | decoder 0.8.3 lê o wire denso-nulo 0.8.2 do caso; as duas versões da `view` o recusam | “0.8.3 reads every wire” não nomeia a superfície nem aponta uma matriz universal em disco |

O segundo wire não é regressão: ambos decodificam exatamente. O erro é a descrição da release.
Um único par byte-diferente é suficiente para refutar “nothing else”; ele não prova que só existam
duas diferenças.

## Fora deste ticket

Os post-its e a narrativa de transição nas três páginas de tipos mistos pertencem ao owner já
existente [`T-DOC-TIPOS-MISTOS`](T-DOC-TIPOS-MISTOS.md). Este ticket apenas reconcilia release e
estado; não duplica a redação didática.

## Critérios de aceite

- [ ] `STATUS.md` e `ROADMAP.md` carregam apenas o presente: 0.8.3 publicada e tag existente.
- [ ] O título da release descreve consistência de bordas sem prometer simetria de capacidade.
- [ ] O changelog enumera as duas mudanças de emissão já comprovadas.
- [ ] “Nada mais mudou” é removido; não substituir por outra universal sem matriz em disco.
- [ ] Compatibilidade é declarada por superfície (`decode` vs `view`) e limitada ao que foi medido.
- [ ] A correção não altera ADR aceito nem reescreve um lab histórico.
- [ ] O lab é reexecutado depois da correção; expectativas documentais passam a verificar o estado
      reconciliado, não a divergência antiga.
