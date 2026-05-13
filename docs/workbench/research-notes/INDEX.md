# Research notes — workbench v0.6

Esta pasta contém **apenas** notas vivas do ciclo v0.6 (reset
2026-05-10). Tudo anterior está em [`_archive/`](_archive/) como
blueprint não-canônico.

## Nota viva

| Data | Nota | Conteúdo |
|------|------|----------|
| 2026-05-11 | [sintese-algoritmos-v06](2026-05-11-sintese-algoritmos-v06.md) | Síntese dos exps 01-15 do dirty lab v0.6 + mapa da literatura de compressão de strings + posição do TCF |

## Fonte da verdade

A fonte da verdade do trabalho atual é o **dirty lab v0.6**:

```
experiments/lab/dirty/
  README.md                          ← índice e convenções do ciclo
  2026-05-10-01-amostras-iniciais/   ← exp 01
  2026-05-10-02-patricia-nomes/      ← exp 02
  ...
  2026-05-11-15-online-com-fix/      ← exp 15 (estado atual)
  notas/                             ← notas técnicas do ciclo
```

A síntese acima consolida o que esses 15 experimentos
estabeleceram. Para revisão histórica, ler os READMEs e
`conclusoes.md` dos próprios experimentos.

## Sobre `_archive/`

Contém notas e consolidados das versões anteriores (v0.0 a v0.5).
**Não são referência canônica para v0.6.** Servem para:

- Localizar bugs e armadilhas já encontradas em ciclos anteriores
- Resgatar ideias antigas que podem ser **rebatizadas como
  hipóteses novas** e re-testadas no dirty v0.6 (não importadas)
- Rastreabilidade histórica

Nenhuma conclusão dos `_archive/` deve ser citada como evidência
em ticket, finding ou paper sem ser re-validada pelo dirty v0.6.
