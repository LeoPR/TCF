# 2026-08-17-2100 — grupo × array (H-13-06), o bloqueador

Executa o [plano de 2000](../../../notas/2026-08/2026-08-17-2000-plano-grupo-x-array.md).

## A hipótese e o veredito

**Hipótese**: substituir a coluna de ITENS por N colunas de grupo é **ortogonal** aos
mecanismos de array — `count`, `emask` e máscara de campo ficam **byte-idênticos**.

**Veredito: sustentada. Nenhuma falsificação disparou.**

| critério | resultado |
|---|---|
| **F1** count/emask/máscara mudam | **0/9** — byte-idênticos em todos |
| **F2** perde RT com grupo mas mantém sem | **0/9** |
| **F3** exige coluna de controle nova | **0/9** |
| RT com grupo | **9/9** |

Os blocos de controle, medidos com e sem grupo (mesma coluna, mesmos bytes):

```
A5 (null em elemento)   count sem=3 B com=3 B   ·   emask sem=9 B com=9 B
A6 (campo ausente)      mask  sem=5 B com=5 B   ·   count sem=3 B com=3 B
```

Isso confirma a leitura da sondagem: **a contagem é de nível de ARRAY, os itens são de
nível de ITEM**. A coluna de itens já vem densa e achatada entre registros; trocar 1 por N
não toca nada acima.

## Os 9 casos

| caso | agrupou | sem | com | delta | gate |
|---|:-:|--:|--:|--:|---|
| A1 uniforme | sim | 61 | 79 | +18 | |
| A2 contagens variadas (1,3,0,7) | sim | 76 | 96 | +20 | |
| A3 array vazio em alguns | sim | 50 | 68 | +18 | |
| **A4 todos vazios** | **não** | 34 | 34 | 0 | *sem itens — nada de onde tirar template* |
| A5 null em elemento (emask) | sim | 66 | 84 | +18 | |
| A6 campo ausente (2 máscaras) | sim | 61 | 79 | +18 | |
| **A8 template não-uniforme** | **não** | 52 | 52 | 0 | *não-uniforme em `'1.234,56'`* |
| **A9 item único** | **não** | 36 | 36 | 0 | *nenhum campo varia* |
| A10 data ISO (3 campos) | sim | 64 | 89 | +25 | |

As três recusas do gate são **limpas** — devolvem motivo e caem no caminho sem grupo, sem
quebrar. A4 é a que eu mais temia (zero itens, nada de onde inferir template) e ela se
resolve sozinha.

## O que este resultado NÃO diz

**O grupo ficou MAIOR em todos os casos que agruparam (+18 a +25 B).** Isso é esperado e não
contradiz nada: são datasets de **3 a 4 registros**, e o marcador (template + N entradas de
meta) é **custo fixo**. Nos labs anteriores, com n de 24 a 20 000, o grupo ficava menor.

**Este lab não mede ganho** — mede **composição**. A pergunta era *"quebra?"*, não *"paga?"*.
Medir ganho aqui exigiria arrays com muitos itens, e isso é outro lab.

## O bug que este lab teve — e a classe dele

A primeira rodada deu **RT 7/9**: A2 e A10 quebravam com `IndexError`. Não era falsificação
(F2 exige *perde com grupo mas mantém sem* — os dois mocks quebravam). Era **bug meu**, e da
classe que venho repetindo:

```python
def melhor_coluna_modo(rot, blob):
    for m in ("!", "@", ""):
        try:
            decoda_coluna(blob, m); return m     # <- o 1o que não levanta
        except Exception:
            continue
```

O `_decode_raw_body` **abre um corpo `tcf` sem reclamar** e devolve os tokens crus:

```
valores  ['1','3','0','7']   corpo tcf  b'\1\n\3\n\0\n\7\n'
  modo '!'  -> ['\\1','\\3','\\0','\\7','']   *** VALOR ERRADO, SEM LEVANTAR ***
  modo ''   -> ['1','3','0','7']              CORRETO
```

Um helper que **adivinha** e devolve valor errado em silêncio. **Conserto**: o modo passou a
**viajar no meta**, como o `.8M` real faz com `!`/`@` — que era o certo desde o início.
Depois disso, **RT 9/9**.

É a mesma assinatura da guarda do `remonta` e do `outputs/` vazio: eu confiei em inferência
onde o formato já tinha a resposta explícita.

## O que segue aberto

- **F4** (ordem DFS / "última coluna omite size") **não foi exercitado**: o mock usa uma
  ordem própria e não reproduz a regra de omissão do `.8H` real.
- **F5** (gate por-registro) não disparou, mas o gate aqui é **global por coluna** por
  construção do mock — não provei que o gate real se comporta assim.
- **A7 (array-em-array) não foi executado** — o mock cobre um nível só. É o caso que resta
  do plano.
- **Ganho** não medido (ver acima).
- Datasets minúsculos, sintéticos, uma execução.

## Evidência

27 wires (por caso: `.8H-real`, `mock-sem-grupo`, `mock-com-grupo`) + 9 roundtrips, com
portão de completude.

## Conexões

- Plano: [`notas/2026-08-17-2000`](../../../notas/2026-08/2026-08-17-2000-plano-grupo-x-array.md)
- [`1700`](../2026-08-17-1700-grupo-como-combinador-do-H/) (o combinador) ·
  [`1800`](../2026-08-17-1800-o-que-de-fato-falta/) (a tese do marcador) ·
  [`1900`](../2026-08-17-1900-vale-a-pena/) (o memo de decisão)
- [roadmap-hipoteses Pacote 13](../../../notas/2026-05/roadmap-hipoteses.md)
