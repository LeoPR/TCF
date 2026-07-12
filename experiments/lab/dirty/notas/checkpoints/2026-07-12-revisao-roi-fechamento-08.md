# Checkpoint 2026-07-12 — revisão por ROI para fechar o núcleo 0.8

**Tipo**: pausa explícita + rota de retomada. **Força**: probatório; registra o estado observado.
A ordem que constitui o trabalho é o dispositivo
[`T-REL-08-CLOSEOUT`](../../../../../tickets/T-REL-08-CLOSEOUT.md); em divergência, ele vence.

## Decisão de prioridade do owner

Fechar o núcleo `#TCF.8` e o pacote `0.8.0` antes de abrir pesquisa `.9` ou hardening amplo.
Bugs e bordas não somem: são classificados pelo domínio que afetam.

- **Preempta o `.8`**: quebra RT de entrada aceita pelo encoder, impede o artefato de release ou
  invalida evidência/documentação embarcada.
- **Não preempta por default**: blob deliberadamente corrompido, checksum, reparador, orçamento
  defensivo e contrato definitivo pré-1.0.
- **F5 não é uma fase obrigatória de invenção**: default NO-ACTION; só abre candidato medido que
  bloqueie ou feche diretamente o release.

## Estado observado

- `#TCF.8` é o formato multi-col default; versão fonte `0.8.0`; PyPI ainda em `0.7.1`.
- T-QA-8 F0 + F1 + F2 concluídos. F2: 29/29 RT e material em
  `experiments/results/evidencia-0.8/f2/`.
- Suíte local completa, incluindo hubs `requires_data`: **600 passed, 2 skipped**.
- F1/F2 estão commitidos; na avaliação a branch `main` estava 10 commits à frente de
  `origin/main`. Nenhum push ou release foi feito.
- Resíduos preexistentes preservados: `.claude/scheduled_tasks.lock` deletado e
  `experiments/lab/dirty/2026-07-08-2355-f3-bn-seletivo/run.log` não rastreado.
- A revisão não alterou `src/tcf/`.

## Achado que muda a fila

**BUG-14, domínio válido**: `encode` aceita `\v`, `\f`, NEL (`U+0085`), `U+2028` e `U+2029`
dentro de valores, mas os dois níveis do decoder usam `splitlines()`. Repro executado em
2026-07-12: 5/5 casos retornaram `['a', 'b']` para um único valor `a<sep>b`.

Isto viola `decode(encode(x)) == x` para entrada pública aceita, portanto é **R0 antes de F3**.
Registro e critério red→green:
[`T-QA-8` BUG-14](../../../../../tickets/T-QA-8-material-comprobatorio.md).

## Fila de retomada por ROI

| ordem | atividade | condição de saída |
|---|---|---|
| **R0** | BUG-14: teste parametrizado → menor fix LF-only → suíte/pinos | RT válido restaurado; aprovação explícita para tocar `src/tcf` |
| **R1.1** | T-QA-8 F3: sintéticos, curva de escala, identidade/speedup paralelo | evidência reproduzível; decisão informada do parallel budget |
| **R1.2** | T-QA-8 F4: começar pelos 6 hubs prontos; depois completar matriz prevista | tabela pública consolidada + nota metodológica |
| **R2.1** | F5 apenas se a telemetria apontar blocker; caso contrário fechar NO-ACTION | nenhuma pesquisa oportunista no `.8` |
| **R2.2** | F6: README EN/PT, referência, metadata, workflow/wheels, smoke clean-room | superfície publicável coerente com o core |
| **R3** | T-DIST C3, somente após go explícito do owner | tag/publicação e closeout `closed-done` |

## Preservado para depois

- **0.8.1**: BUG-12 (não terminação sob blob corrompido) + lote defensivo relacionado.
- **Pré-1.0**: orçamento de expansão/RLE, contratos de API/omissão/meta e checksum/tcfx.
- **0.9**: codec `H`, bN/specs induzidas, quoting avançado, V2-B B/C e estratégias H.
- **Paralelo, sem bloquear release**: reparador de corrupção e governança Strata recorrente.

## Primeiros passos na próxima sessão

1. Ler `STATUS.md` apenas no bloco **ESTADO VIGENTE**.
2. Ler a seção **Regra vigente de ROI** de `T-REL-08-CLOSEOUT`.
3. Ler este checkpoint e a última entrada do diário.
4. Pedir/confirmar aprovação antes de tocar `src/tcf`; começar pelo teste red do BUG-14.
5. Após o green, rodar suíte completa + pinos e seguir diretamente para F3.

Não iniciar `.9`, BUG-12, checksum ou otimização especulativa enquanto a fila acima estiver aberta,
salvo decisão nova do owner registrada no T-REL-08.
