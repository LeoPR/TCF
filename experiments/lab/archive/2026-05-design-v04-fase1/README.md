# Arquivo: fase 1 do design TCF v0.4 (2026-04-27 → 2026-05-05)

Conjunto de 8 labs dirty da primeira fase de design do TCF v0.4.
Movidos para arquivo em 2026-05-05 ao "limpar a bancada".

## Conteudo

| Lab | Tema | Resultado |
|-----|------|-----------|
| 2026-04-27-flow-pessoas/ | header v0.4 minimal, encoding, line-ending | header `# TCF v0.4 lv=N` |
| 2026-04-28-flow-categoricos/ | sort vs grouped, SQL como otimizador | grouped suficiente p/ RLE |
| 2026-04-29-affix-dict-mesa/ | Proposta H validada | -50 a -80% em prefixos limpos |
| 2026-04-30-cross-column-dict-mesa/ | Proposta E reaberta | -22% em vocabs compartilhados |
| 2026-05-01-key-graus-mesa/ | Proposta I validada | -10 a -12% em FK grau 2 |
| 2026-05-02-chaves-didatico/ | visualizacao didatica de 4 graus | tensao bytes vs semantica |
| 2026-05-03-caminho-feliz-auto/ | banco didatico com auto-tudo | -19% em N=63 rows |
| 2026-05-04-mesa-ampla/ | escala N1..N4 + reflexao hipotetica | -42% em N=1100 rows |

## Documentos consolidados

- [docs/workbench/research-notes/2026-05-05-v04-design-recap.md](../../../../docs/workbench/research-notes/2026-05-05-v04-design-recap.md)
- [docs/workbench/tickets/open/M-chunks-v04.md](../../../../docs/workbench/tickets/open/M-chunks-v04.md)
- [docs/workbench/tickets/open/H-compression-v04-roadmap.md](../../../../docs/workbench/tickets/open/H-compression-v04-roadmap.md)

## Por que arquivar

- Labs ja deram intuicao matematica e validacao formal das propostas
- Decisoes consolidadas (D1-D16) e obsolescencias categorizadas
- Proxima fase precisa de bancada limpa para nomenclatura nova e
  exploracao focada

Para reabrir o contexto, consultar o recap acima ou navegar pelos
notes.md de cada lab.
