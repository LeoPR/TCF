# TCF em 1 página — material de divulgação

> Rascunho no estilo **post de LinkedIn** pra mostrar o que o TCF faz. Tom direto,
> escaneável. Números reais (saída do `encode`). Use/adapte à vontade.

---

## Post (versão curta)

**E se desse pra transmitir uma tabela com bem menos bytes — sem virar um arquivo
binário que ninguém mais abre e lê?** 🧩

É isso que o **TCF (Tabular Compact Format)** faz: compressão de tabelas de strings que
**continua texto ASCII inspecionável**.

Um cadastro pequeno, nos três formatos (bytes reais):

```
JSON  596 B   →   CSV  277 B   →   TCF  244 B
```

O TCF fatora o que se repete e referencia o resto — e o resultado **você ainda abre e lê**.
Não é um blob opaco.

Ele ocupa uma faixa própria: **compacto como um compressor, legível como texto.**
(Precisa de ratio máximo? gzip/brotli rodam por cima — eles se compõem.)

🔗 `pip install tcf-format` · MIT · pré-1.0

#dados #compressão #python #opensource #dataengineering

---

## Post (versão capacidades)

**TCF — compressão de tabelas que continua legível.** O que ele já faz:

✅ **Lossless** — `decode(encode(x)) == x`, sempre.
✅ **Textual e inspecionável** — a saída é ASCII; os agrupamentos (`*N|` = N linhas iguais)
   ficam **à vista**, sem descomprimir.
✅ **Por coluna, escolhe a menor representação** — TCF / raw / dicionário / split estrutural,
   automático (nunca pior que o cru).
✅ **Filtros por natureza** (opt-in) — CPF/CNPJ/IP guardados sem a pontuação e sem o dígito
   verificador (recalculado no decode): `123.456.789-09` → 5 chars.
✅ **Compõe com gzip/brotli/zstd** — dá pra comprimir por cima pra transporte.

E o que já dá pra fazer (gadget funcional):

✅ **Consultar quase sem descomprimir** (gadget `tcf_lazy`, 27 testes). Uma view *lazy* que só
materializa a coluna (e as linhas) que o agregador precisa:

```python
v = view(blob)
v.sum("valor")                                # toca: valor
v.where("cidade", "Sao Paulo").sum("valor")   # toca: cidade, valor  (nunca abre o resto)
```

`count / sum / min / max / avg` + filtro, com **descompressão seletiva** e pouca memória —
onde um compressor binário obrigaria descomprimir tudo antes de qualquer conta.

🔗 github.com/LeoPR/TCF · `pip install tcf-format`

#dados #compressão #python #dataengineering #opensource

---

## Notas pra quem for postar (não vai no post)

- **Comparativo com nuance de escala**: no cadastro **minúsculo** (4 linhas), `csv+brotli`
  (162 B) ganha do `tcf+brotli` (185 B) — a moldura domina e não há o que fatorar. Mas em
  **multi-coluna real** (milhares de linhas) **inverte**: `tcf-0.7+brotli` vence o `csv+brotli`
  (ex.: Adult 3k linhas: 21,8 KB vs 30,4 KB, −28%) — e quanto mais TCF, menor o pós-brotli.
  Pitch correto: TCF é **cru + legível + consultável** E, **com volume, melhor pré-processo pro brotli**.
- **Estado real**: pré-1.0 (`#TCF.7`). A `view()` lazy é **gadget funcional** (`scripts/tcf_lazy/`,
  27 testes, L1–L5) — real/testado, mas **não** é API estável de `src/tcf` ainda. Os filtros
  **auto-descritivos** (marcador de nature no header, H-NAT-MARK-01) seguem **proposta** (alvo 0.8).
- **Não competir com gzip/brotli/zstd** no discurso — são outra categoria (binários opacos).
  O eixo do TCF é textual/explicável.
- Fontes dos números: `README.md` (exemplo do cadastro) e `experiments/lab/dirty/old/welded/2026-06-16-lazy-query/`.
