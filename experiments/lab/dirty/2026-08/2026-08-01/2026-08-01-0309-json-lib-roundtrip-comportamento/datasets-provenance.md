# Proveniência — json-lib × TCF round-trip comportamento (2026-08-01-0309)

## Por que este lab existe

Estudo aprovado pelo owner: mapear empiricamente o que `dataset → json lib → dataset` e
`dataset → TCF → dataset` preservam, alteram ou rejeitam, para definir a régua do futuro
"modo json" do TCF (param hipotético: quando o TCF preserva o que o json
perderia/rejeitaria, ele ALERTA como o json alertaria; sem o flag, TCF faz tudo que pode;
ambíguos "fogem" pro comportamento json). **LAB APENAS — `src/tcf` intocado.**

## Corpus — um gerador no `run.py`, seed fixa (não há RNG), viés declarado

O corpus é **construído pra testar esta hipótese** (29 casos, um por entrada, cobrindo a
malha do estudo: tipados puros / int×float / -0.0 / NaN-±Inf / int gigante / união mista /
chave não-str / chave duplicada / tuple / bytes / estruturas / chave float-nan). Declarado
em `inputs/corpus.json`. Dois casos merecem nota:

- **`chave-duplicada`**: NÃO expressável em Python puro (dict não tem chave duplicada) —
  o input é o TEXTO json cru (`'{"a": 1, "a": 2}'`) e o RT da lib começa do parse; o TCF
  é classificado `NÃO-EXPRESSÁVEL`.
- **`str-lf` × `str-unicode`**: separados porque o TCF recusa LF embutido (LF delimita
  linha) mas preserva unicode/emoji — um caso só mascararia a diferença (o primeiro
  `\n` abortava o encode).

## Validação — e por que não é circular

```
x -> json.dumps -> json.loads  (a LIB real, default permissivo)
x -> tcf.encode -> tcf.decode  (o codec real, src/tcf público)
ambos comparados com o INPUT por cmp_estrito: deep == + tipo, CHAVES de dict inclusas,
-0.0 por copysign (em Python -0.0 == 0.0), NaN==NaN aceito como identidade de valor.
```

Nenhuma reimplementação: os dois lados usam as funções públicas reais. O caso
`chave-vazia` (TCF altera COM `UserWarning`) é capturado com `warnings.catch_warnings` e
reportado como achado — não falha do lab, porque não é corrupção silenciosa (o encoder
avisa); fica registrado como candidato a ticket.

Knobs do NaN **medidos** (não citados de memória): `json.dumps([nan])` default emite
`NaN`; `allow_nan=False` rejeita no dumps; `parse_constant` rejeita no loads — em
`outputs/knobs-nan-medidos.json`.

## Limites declarados

- **json lib = `json` do Python 3, default permissivo.** Cross-ecossistema (JS/number
  perdendo > 2^53, schemas estritos) é NOTA registrada, não medida.
- O corpus é sintético e dirigido — mede COMPORTAMENTO de borda, não frequência real-world.
- **Nada soldado**; nenhum arquivo de `src/tcf` tocado.
- `chave-vazia` é a única divergência "TCF altera" conhecida por este corpus; corpus
  maiores podem achar outras — este não exaure o espaço.

## Reprodutibilidade

`python run.py` regenera `inputs/corpus.json`, `intermediates/*-roundtrip-obtidos.json`,
`outputs/{matriz.csv, alteracoes.json, knobs-nan-medidos.json}` e `result.md` — sem RNG,
sem relógio, sem rede.
