# Post curto para o LinkedIn (a peça de leitura rápida)

> Pronto para publicar. Todo número foi medido com roundtrip validado e é reproduzível por
> `python scripts/verifica_divulgacao.py`.
> Fonte: [`2026-09-04-fonte-0.8.4.md`](2026-09-04-fonte-0.8.4.md).
>
> **O que este texto é:** o resumo que leva ao artigo e ao repositório. Objetivo e
> informativo, com fluxo, sem suspense e sem jogo de pergunta e resposta. Apresenta o assunto,
> mostra o que o formato faz, dá os limites por inteiro, e entrega o link. A teoria fica no
> artigo, e a íntegra no repositório.
>
> **As três primeiras linhas** são as que aparecem antes do "ver mais", e elas não têm jargão
> de propósito. Quem não trabalha com compressão precisa entender a primeira frase.
>
> **Os blocos de código são a saída real do `encode`**, não ilustração. Como o wire do TCF é
> texto legível, aqui a "figura" pode ser o próprio dado.

---

**Comprimir uma tabela sem transformar ela num arquivo que ninguém consegue abrir**

Quando dois sistemas trocam uma tabela, o formato mais usado repete o nome de cada campo em
toda linha. Num cadastro pequeno, quatro pessoas e cinco campos, isso pesa: são 451 bytes em
JSON contra 277 em CSV, que joga os nomes fora e fica só com as linhas.

O TCF é uma terceira via. Ele fatora o que se repete, referencia o resto, e o resultado
continua sendo texto que você abre e lê. O mesmo cadastro dá 242 bytes:

```
#TCF.8M!2c=nome,2a=email,1c=cidade,14=plano,!cpf
Ana Souza
Bruno Lima
Carla Nunes
Diego Rochaan*a*@acme.com.br
brun*o3
carl2,3
dieg5,3
*3|Sao Paulo
Rio de Janeiro
*2|Premium
Basic
^1
111.111.111-11
222.222.222-22
333.333.333-33
444.444.444-44
```

A objeção óbvia é gzip, e ela merece medição em vez de defesa.

Em transmissão, a compressão do canal é negociada pelo transporte e é invisível ao seu código.
Quando o seu handler lê o corpo, ele já foi inflado, então você não escolhe ela contra nada.
Onde ela vira decisão visível, em disco, ela cobra opacidade: para ler qualquer coisa, você
infla tudo.

É aí que a diferença aparece. Sobre um TCF dá para perguntar sem descomprimir:

```python
v = view(wire)
v.distinct('cidade')        # ['Rio de Janeiro', 'Sao Paulo']
v.group_count('plano')      # {'Premium': 3, 'Basic': 1}
v.where('plano', 'Premium') # 3 linhas, sem materializar as outras
```

Nenhuma dessas chamadas decodifica a tabela inteira. Um blob comprimido não faz isso, porque
não existe nada para ler até o payload inteiro voltar a existir.

O que torna a adoção barata é o contrato de tamanho. Para cada coluna, o codificador gera as
candidatas e grava a menor entre o TCF, o dado cru, o dicionário e o split. É nunca pior por
construção, então não é preciso testar para descobrir se o formato piorou o seu dado.

Os limites, que importam mais que os ganhos. Sob `gzip` os formatos empatam dentro de 1 byte.
No tamanho minúsculo, o CSV passa o TCF depois de comprimido. E escrever é caro: o trabalho
está concentrado no encode, e o ciclo de otimização de algoritmo é o próximo, ainda não
começou.

Onde ele compensa hoje é dado cacheável, que paga o encode uma vez e distribui muitas, e
conjunto grande. Em 8 datasets reais o conjunto caiu 25,6%, com a faixa indo de 4,1% a 46,6%
conforme o dado.

`pip install tcf-format` · Python 3.10 ou mais novo · zero dependências · MIT · pré-1.0.

Escrevi um artigo com as medições, o contrato de tamanho e os limites de onde isto se aplica:
👉 [link do artigo, preencher depois de publicar]

O código, as medições e a documentação do que não funciona:
👉 https://github.com/LeoPR/TCF

#Python #Compressao #DataEngineering #OpenSource #FormatosDeDados
