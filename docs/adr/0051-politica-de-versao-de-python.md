# ADR-0051: Política de versão de Python: o piso segue o CPython suportado, o máximo vai para o topo testado e para o ambiente de trabalho

- **Status**: **aceito** (2026-11-07, decisão do owner). Não muda o wire nem a API.
- **Origem**: pergunta do owner, *"até a 1.0, deixar compatível só com o último Python, sem se
  preocupar com os antigos? Gosto de tudo na versão máxima, e isso economiza desenvolvimento"*.
- **Preenche**: a cláusula *Python version compat (#2)* da [ADR-0017](0017-format-spec-v1-frozen.md),
  que a [ADR-0024](0024-pre-1.0-versioning-git-as-compat.md) não supersedeu. Ela fixava
  `python >= 3.10` e a matriz 3.10 a 3.13 sem regra para mudar nenhum dos dois.

## O fato

**O código já é neutro em versão.** `src/tcf` não tem nenhum código condicionado a versão de
Python, nenhum fallback de import da stdlib e nenhum `typing_extensions`. As regras `UP` do ruff
dão os mesmos achados em `src/tcf` com alvo de `py310` a `py315`. Subir o piso **não simplifica
nada**: fora de `src/tcf`, muda um ramo de teste e quatro `datetime.UTC` em scripts.

**O piso de hoje tem base no código, e a ADR-0017 registrou outra.** `src/tcf/core/online.py`
declara uma união PEP 604 em tempo de execução, e por isso `import tcf` falha em 3.9. O motivo
que a ADR-0017 escreveu, a ordem de inserção do `dict`, está garantido pela linguagem desde 3.7.

**O ganho de uma versão nova chega pelo interpretador de quem usa, não pelo piso.** O encode
pure-Python do TCF fica mais rápido em 3.15 do que em 3.13, e quem roda 3.15 recebe isso com
qualquer `requires-python`. O mesmo vale para o import adiado de `concurrent.futures`, que corta
o `import tcf` em todas as versões, e para o `__lazy_modules__` da PEP 810, que o 3.15 honra e as
versões anteriores ignoram sem custo.

**O piso decide quem alcança a versão nova**, e o regime alvo do `.9` (processo curto em função
sem servidor) vive em plataformas que andam atrás do CPython:

| piso | fração dos downloads do PyPI (out/2026) | fora, hoje |
|---|---|---|
| 3.10 | 84% a 91% | ninguém |
| 3.11 | 70% a 80% | Python do sistema no Ubuntu 22.04 e no RHEL 9 |
| 3.12 | 50% a 61% | o acima, mais o Debian 12 |
| 3.13 | 18% a 26% | o acima, mais o padrão da Vercel, o Azure Linux Consumption, o Ubuntu 24.04 e o RHEL 10 |
| 3.14 | 7% a 10% | o acima, mais Colab, Kaggle e Debian 13 |
| 3.15 | 0,3% a 1,2% | o acima, mais Lambda em produção, GCP, Azure, Vercel, Cloudflare, toda distro LTS |

**Ficar de fora é silencioso.** Desde o pip 9, quem está num Python abaixo do piso recebe, sem
aviso, a última versão compatível. O uv faz o mesmo, e bifurca a resolução por versão de Python.
O usuário não vê erro: só deixa de receber correção e, quando o minor do pacote abre era nova de
wire (ADR-0028), deixa de ler o formato novo.

**O topo estava atrasado.** O CI parava em 3.13, com o 3.14 lançado em 2025-10-07 e o 3.15 em
2026-10-09. O 3.10, piso declarado, chegou ao fim de vida em 2026-10-01.

## A decisão

**Três lugares, três regras.**

1. **Pacote** (`requires-python`): o CPython mais antigo que ainda recebe correção do upstream.
   O piso só é reavaliado num minor de formato (`0.N.0`), nunca num patch. Na `0.9.0` ele sobe
   para `>=3.11`. Na 1.0 vale a mesma regra, preferindo um piso com doze meses ou mais de suporte
   restante.
2. **CI**: do piso ao último CPython estável. Versão nova entra no CI no ciclo em que é lançada.
3. **Desenvolvimento, lab e bench**: o último CPython estável, com o build **exato** fixado por
   campanha de medição. O interpretador do bench só troca **entre** campanhas, com nova baseline
   ou com o cruzamento código × interpretador medido na mesma sessão.

**Código por versão** entra só quando o recurso compensa **e** cabe num mecanismo que o
interpretador mais antigo ignora sem custo, como o `__lazy_modules__`. Sintaxe que exige versão
acima do piso vigente não entra em `src/tcf`.

## Por que não "só o último Python até a 1.0"

- **Economiza zero.** O código já roda em todas; não há o que apagar.
- **Corta o regime alvo.** Com piso 3.15, nenhuma plataforma de função sem servidor em produção
  instala o pacote.
- **Prende em silêncio.** O usuário fica na `0.8.4` sem saber, e a mensagem da `0.8.4` não manda
  atualizar.
- **O alvo anda.** O 3.16 sai em 2027-10-05; se a 1.0 vier depois, o piso precisa subir de novo.
- **Volta mal.** O que se escrever exigindo 3.15 precisa sair se o piso da 1.0 for mais baixo.
- **Contamina a medida.** Toda a evidência de desempenho do `.9` está num build só, e trocar o
  interpretador no meio da campanha confunde mudança de código com mudança de interpretador.

O desejo de versão máxima é atendido onde ele rende: no topo testado e no interpretador de
trabalho, que passa a ser sempre o mais novo.

## O que esta decisão custa

- **Quem está em 3.10 deixa de receber a `0.9`**, e não fica sabendo por quê. Uma mensagem na
  última versão `0.8.x` que nomeie o caminho de volta mitigaria; não está decidido.
- **Some a única célula de CI com outra função de hash.** Só o 3.10 usa SipHash-2-4; de 3.11
  em diante, a semente zero dá a mesma ordem de `set`. Um job com `PYTHONHASHSEED=random` repõe a
  cobertura de determinismo, e roda desde já.
- **O CI ganha um job por versão nova**, que custa segundos num repositório público.

## As alternativas não escolhidas

- **Manter `>=3.10`**: o piso fica num interpretador sem suporte.
- **SPEC 0, hoje `>=3.13`**: alinha com a pilha científica, mas abre mão de uns cinquenta pontos de
  alcance sem ganho de código, e corta Ubuntu 24.04 e RHEL 10.
- **As duas últimas, hoje `>=3.14`**: corta Colab e Kaggle. A analogia com a janela N-1 da I8 não
  se aplica, porque a I8 serve só a era vigente; a anterior é lida pelo pacote antigo do PyPI.
- **Só a última, hoje `>=3.15`**: os motivos estão na seção acima.

## Aplicação

**Junto com esta ADR**: a matriz de testes do CI vai de 3.10 a 3.15, o job do acelerador
ganha 3.14, entra o job de semente aleatória, e os classifiers ganham 3.14 e 3.15.

**Na `0.9.0`**: `requires-python = ">=3.11"`, classifiers a partir de 3.11, 3.10 fora do CI,
`target-version` do ruff acompanhando o piso, `uv.lock` regenerado, e a documentação que cita o
piso, cada uma no seu tempo verbal (I1). As peças de divulgação datadas ficam como estão.

**No bench, antes da primeira troca de interpretador**: o manifesto grava o `sys.version`
completo e o executável, o comparador recusa par com interpretador diferente, e o projeto ganha
um `.python-version` com o patch exato.

## Evidência

Análise de 2026-11-06 em seis frentes, cada uma com verificação adversarial, registrada em
`experiments/lab/dirty/notas/2026-11/2026-11-06-politica-de-versao-python.md` (caderno local,
fora do git). Fontes primárias: [ciclo de vida do CPython](https://devguide.python.org/versions/),
[pypistats](https://pypistats.org/), [guia de remoção de versões antigas](https://packaging.python.org/en/latest/guides/dropping-older-python-versions/),
[resolução do uv](https://docs.astral.sh/uv/concepts/resolution/), [PEP 810](https://peps.python.org/pep-0810/)
e a documentação de runtimes de cada plataforma citada.
