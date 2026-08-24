<!-- l10n: doc_id=how-to-index · lang=en · canonical -->
# How-to guides

Task-oriented recipes: each page answers one question and stops. For the reference contract
see [`../reference/api.md`](../reference/api.md); for the format itself see
[`../algorithms/TCF-format.md`](../algorithms/TCF-format.md).

Pages marked *(Portuguese)* are written in pt-BR. English is the primary language of this
repository and these are on the translation list; the code in them is language-neutral.

## Using TCF on your data

| guide | answers |
|---|---|
| [Encode a CSV file](encode-csv-file.md) *(Portuguese)* | I have a `.csv` on disk: how do I get a `.tcf` and read it back? |
| [Use natures (CPF/CNPJ/IP)](use-natures.md) *(Portuguese)* | one column has a known shape: how do I opt into the spec, and how do I know it paid off? |
| [Feed dates to TCF](normalizar-data-antes-do-tcf.md) *(Portuguese)* | my dates come in several spellings: what do I normalize before encoding, and what does the format do by itself? |
| [Inspect the compression](inspect-compression.md) *(Portuguese)* | why did this column come out that size? Which candidate won? |

## Working on the project

Process for contributors, not for users of the library.

| guide | answers |
|---|---|
| [From hypothesis to production](fluxo-hipotese-producao.md) *(Portuguese)* | I have an idea for the format: what does it have to survive before touching `src/tcf`? |
| [Log run metadata](log-run-metadata.md) *(Portuguese)* | how do I record a measurement so it can be compared later? |
| [Audit docs and memory](audit-memorias-e-documentacao.md) *(Portuguese)* | how do I check that the documentation still matches the code? |

## Where this sits

`tutorials/` teaches the first use, `how-to/` (here) solves a task, `reference/` states the
contract, and `algorithms/` explains the mechanism. See [`../README.md`](../README.md).
