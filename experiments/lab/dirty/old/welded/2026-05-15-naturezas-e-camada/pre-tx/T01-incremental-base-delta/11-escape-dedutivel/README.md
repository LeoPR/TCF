# 11 — Escape dedutivel (TCF v2 smart-escape)

**Estado**: aberto (11a iteracao do T01)
**Macro pai**: [`../README.md`](../README.md)
**Origem**: principio [feedback-abstrato-minimal-materializacao] descoberto inspecionando D11h tcf

## Pergunta cientifica

Encoder canonical (HCC) sempre escapa digit-runs com `\`. Pode-se
**deduzir** que um digit-run e' literal (sem ambiguidade com ref)
e omitir o `\`?

**Princípio**: digit-run de valor `N` e' literal-sem-ambiguidade
sempre que `N > current_node_count` no momento do parse — nao pode
ser ref `^N` porque nao existe node N.

## Hipotese

V2 (smart-escape) reduz bytes em 10-18% nos datasets T01 sem perda
de informacao. RT byte-canonical preservado.

## Mecanismo

Encoder rastreia `count = nodes declarados ate' aqui`:
- Linha 1: count_before=0 → todos digits literais sem ambiguidade
- Linha N: count_before=K → digit-run V e' literal sem-ambiguidade se V > K

Decoder smart simetrico (smart_decode): em lit context, bare digit e' literal.

**Limitacao desta iteracao**: assume **1 lit piece por linha**
(T01 incremental). Compositions complexas (D9, etc.) precisariam
de parser estrutural completo — fora do escopo.

## Estrutura

```
11-escape-dedutivel/
├── README.md                # este arquivo
├── lib/
│   └── smart_escape.py      # smart_encode + smart_decode
├── run.py
├── outputs/
│   └── <D11x>/
│       ├── _SUMMARY.md
│       ├── v1.tcf           # canonical (input do sub-exp 10)
│       ├── v2.tcf           # smart escape
│       ├── decoded-v2-pretx.txt
│       ├── decoded-v2-final.txt
│       └── validation.txt
└── result.md
```

## Como rodar

```bash
python experiments/lab/dirty/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/11-escape-dedutivel/run.py
```

## Datasets

Os 8 D11x do sub-exp 10. v1.tcf vem direto do `outputs/<D11x>/5-encoded/output.tcf`
do sub-exp 10 — single source of truth.

## Critério de fechamento

- [ ] RT 8/8 OK (linhas reconstruidas = input original)
- [ ] v2 < v1 em todos os datasets (savings positivos)
- [ ] Demonstrar primeira-linha-todos-removidos
- [ ] result.md mostra ganho consolidado

## Implicacao estrutural

**NAO welded em src/tcf**. Sub-exp dirty so'. Decisao sobre v1→v2
no canonical:
- Versionamento do formato
- Backward compat ou migracao explicita
- Revalidacao D1-D9 baseline

Registrado como Track 2 estudo **L06** em [META-TYPE-ENCODERS.md](../../../../../../tickets/META-TYPE-ENCODERS.md).

## Conexoes

- [feedback-abstrato-minimal-materializacao](#) — princípio
- [`../10-pacote-completo-com-validacao/`](../10-pacote-completo-com-validacao/) — v1 source
- [`../../../../../tickets/META-TYPE-ENCODERS.md`](../../../../../tickets/META-TYPE-ENCODERS.md) — Track 2 L06
