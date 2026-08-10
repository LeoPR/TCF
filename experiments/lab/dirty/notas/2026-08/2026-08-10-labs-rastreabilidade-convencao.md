# Rastreabilidade de lab — o diagnóstico, a análise crítica, e a convenção estendida

**Data**: 2026-08-10
**Tipo**: nota de processo + dispositivo (estende `dirty-lab-convencoes.md` aos labs clean)
**Origem**: feedback do owner sobre o EXP-017 — *"vc sempre vai diluindo o ambiente de
testes (…) precisa ter mais rastreabilidade no que é achado, além do registro do roundtrip
pra contra-prova na pasta output que vc frequentemente esquece (…) se eu olhar
`outputs/valv-ym-unicode.tcf` eu não sei qual input foi usado pra gerar ele, nem quais
parâmetros nem nada (…) a rastreabilidade visual permite que eu confira o que vc fez"*
**Evidência**: auditoria de 4 lentes sobre os 20 labs clean, 112 labs dirty e as regras
canônicas.

---

## 1. O diagnóstico: procede, e era pior do que o relato

O owner apontou 2 falhas. A auditoria achou **7**, e a mais grave nenhum de nós tinha visto.

| # | falha | gravidade |
|---|---|---|
| 1 | **`outputs/` do EXP-017 era invisível ao git** — `.gitignore:49 `output*`` engole qualquer pasta `outputs/`; só o EXP-016 tinha exceção nominal. **0 de 30 artefatos versionados** | bloqueia inspeção |
| 2 | zero `roundtrip.json` — a contra-prova só existia como `assert` em memória, e evaporava | bloqueia inspeção |
| 3 | 17 dos 27 casos **não tinham input em disco** (só lambda em `casos.py`) | bloqueia inspeção |
| 4 | sem `intermediates/` — a convenção manda 3 estágios | viola a convenção |
| 5 | sem `datasets-provenance.md` — e o lab usa **dados reais** | viola a convenção |
| 6 | *join-key* quebrada: `outputs/real-tpch-orderdate-nat.tcf` ← `inputs/tpch-orderdate.natural.json` (stems não casam) | atrapalha |
| 7 | 2 wires **órfãos** de execução anterior convivendo com os atuais, byte-idênticos | atrapalha |

A #1 é a que dá o nome certo ao "diluindo o ambiente de testes": **não é descuido de
arquivo, é uma armadilha sistêmica** — todo lab clean novo perde os artefatos em silêncio,
a menos que alguém lembre de abrir exceção nominal no `.gitignore`.

## 2. Análise crítica do que o owner pediu (a parte que ele cobrou)

O owner pediu explicitamente para eu **checar o que ele diz**, não só obedecer. Três pontos:

### 2.1 "os nomes têm que deixar mais claro o que foi feito" — com uma tensão real

Nome longo e descritivo **conflita com estabilidade**: o EXP-016 define o nome do caso como
*"identificador estável (vira nome de arquivo em `outputs/`)"*, e renomear quebra o PIN, o
histórico e o `diff` entre execuções. Aconteceu **neste ciclo**: renomeei `real-football-nat`
→ `real-football` e o arquivo antigo sobreviveu como órfão.

O próprio owner ofereceu a saída: *"ou, pelo arquivo de índice, mostrar a ideia"*. Adotado
**os dois, com papéis separados**: nome **curto e estável** (join-key) + **índice gerado**
que carrega o significado. O índice é gerado pelo `run.py` a partir do campo `porque` que já
existia em `casos.py` — índice escrito à mão apodrece; gerado, não.

### 2.2 "mesmo que os outros lab cleans estivessem menos arrumados"

Aqui o owner está corrigindo uma lacuna real da regra: `AGENTS.md` §6 diz *"Estrutura de lab
**dirty** — OBRIGATÓRIA"*. Os clean nunca estiveram no escopo. A auditoria confirma:
**nenhum** dos 20 labs clean limpa `outputs/`; só 2 gravam contra-prova (EXP-015 e EXP-016);
17 de 20 são invisíveis ao git. Não é que o EXP-017 saiu da linha — **não havia linha**.

Por isso esta nota não conserta um lab: **estende a convenção** (§3).

### 2.3 "você constrói rápido mas conclui com muitos erros" — verdade, e o padrão é diagnosticável

Procede, e a lista deste ciclo é longa. Mas os erros **não são aleatórios** — caem em duas
famílias, e nomeá-las vale mais que aceitar a crítica genérica:

- **Erro de montagem de comparação** (comparei coisas que não eram comparáveis): a rota
  do candidato da nature vs a rota plena; o input do `sf01` que era duplicata do `sf001`.
- **Defeito induzido por conserto** (a correção cria o próximo bug): o guard de
  canonicidade do ADR-0040 virou amplificador de recursos.

As duas têm a mesma raiz: **eu não declaro o que estou segurando constante**. Daí a
contramedida entrar na estrutura do lab, não na minha atenção: `intermediates/<caso>.candidatos.json`
agora tem um campo `CONSTANTE_na_comparacao`, explícito, por caso.

## 3. A convenção — estendida aos labs CLEAN

Vale para lab clean **e** dirty. O que muda em relação ao `dirty-lab-convencoes.md`: os
itens marcados **[novo]**.

### 3.1 Estrutura

```
lab/
├── README.md ......... com "Guia de nomes" [novo] e "Como conferir sem ler código" [novo]
├── report.md / result.md ..... GERADO pelo runner sempre que possível
├── run.py ............ regenera TUDO; LIMPA outputs/ e intermediates/ antes [novo]
├── datasets-provenance.md .... origem + anonimização + VIÉS declarado
├── inputs/
│   ├── <caso>.entrada.json ... array PURO — o lado esquerdo do diff [novo]
│   └── <caso>.fonte.json ..... metadados: gerador, params, seed, ideia, pin, hash [novo]
├── intermediates/ ..... a trilha: como se decidiu, com `CONSTANTE_na_comparacao` [novo]
└── outputs/
    ├── INDEX.md ....... índice GERADO: nome → ideia → input → veredito → prova [novo]
    ├── <caso>.tcf
    ├── <caso>.roundtrip.json ... byte-idêntico à entrada (o diff é a prova)
    └── <caso>.meta.json ........ procedência do wire [novo]
```

### 3.2 Regras duras

1. **Todo caso tem input em disco** — inclusive o sintético. Lambda em `.py` não é evidência.
2. **Toda contra-prova é arquivo**, não `assert`. `diff entrada roundtrip` tem de sair vazio,
   e o runner faz esse mesmo `diff` como prova.
3. **`inputs/*.entrada.json` e `outputs/*.roundtrip.json` usam a MESMA formatação JSON** —
   senão o `diff` nunca fecha e a prova vira decorativa.
4. **O runner limpa `outputs/` e `intermediates/`** antes de gerar. Órfão é indistinguível
   de resultado.
5. **Lab novo entra no `.gitignore`** com exceção nominal, no mesmo commit. **[novo]**
   Sem isso o lab não existe para quem revisa.
6. **Nome curto e estável + índice gerado.** O significado mora no índice, não no nome.
7. **Todo número publicado tem arquivo.** Se o `report.md` cita algo que o `run.py` não
   mediu (ex.: resultado de caçada adversarial), **atribuir a fonte no próprio texto**. **[novo]**
8. **Declarar o que ficou constante** em toda comparação. **[novo]**

### 3.3 A armadilha do `.gitignore` (a dívida que fica)

`output*` na linha 49 é cego. Hoje há exceção nominal para `dirty/**`, EXP-016 e EXP-017.
**Todo lab clean futuro repetirá a falha** até que a exceção seja generalizada
(`!experiments/lab/clean/**/outputs/**`) ou que o runner **falhe alto** quando detectar que
seus próprios artefatos estão ignorados. Fica registrado como dívida — a generalização
arrastaria os EXP-001..015 pré-convenção, e essa é decisão do owner, não minha.

## 4. O que foi feito no EXP-017

Refeito com a estrutura de §3: 27 casos, 0 falhas, com `inputs/<caso>.entrada.json` +
`.fonte.json`, `intermediates/<caso>.candidatos.json` + `.payloads.json`,
`outputs/<caso>.{tcf,roundtrip.json,meta.json}` + `INDEX.md`, `datasets-provenance.md`, e
exceção no `.gitignore` (56 arquivos agora versionados). O teste de inspeção do owner
(`valv-ym-unicode.tcf`) passa: origem, parâmetros, candidatos, vencedor e contra-prova
respondidos **sem abrir o código**.
