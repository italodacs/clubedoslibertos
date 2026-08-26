# Prompt da pesquisa semanal (Claude app)

Este é o prompt da rotina semanal no app do Claude. Ela pesquisa as
oportunidades e devolve o conteúdo da edição em markdown.

**Como usar:** no app do Claude, crie uma tarefa recorrente (sugestão: domingo à
noite, para o envio de segunda) com o prompt abaixo. Depois cole a saída no
Google Doc da edição, revise, e rode o Apps Script — que lê o Doc, pede ao
Gemini para escrever o email e envia para a lista da planilha.

**Por que markdown solto e não JSON:** o Apps Script não precisa entender o
formato. Ele manda o texto do Doc para o Gemini, que já vai ser chamado para
escrever o email de qualquer maneira — e o Gemini lê markdown sem esforço. Isso
elimina o parser e, principalmente, deixa o conteúdo editável à mão no Doc antes
do envio.

---

## O prompt

```
Você faz a curadoria semanal da newsletter do Clube dos Libertos, uma rede de
profissionais e estudantes negros no Brasil. Os membros estão no Ceará, na
Bahia, em Sergipe e em São Paulo, e atuam em Administração, Serviço Social,
Arquivologia, Geografia, Publicidade, Engenharia e Computação.

Pesquise na web e me devolva as oportunidades com INSCRIÇÕES ABERTAS HOJE,
nestas quantidades:

- 6 programas de trainee
- 5 programas de estágio
- 5 cursos ou formações gratuitas
- 5 editais, bolsas ou programas de intercâmbio

REGRAS, e elas importam mais que preencher a cota:

1. Confirme que a inscrição está aberta. Abra a página e verifique. Programa de
   edição passada que continua publicado é o erro mais comum — não vale.
2. A URL tem que ser a página da própria oportunidade, onde a pessoa se
   inscreve ou lê sobre o processo. Nunca uma busca, nunca a home de um portal.
3. Todo item de trainee, estágio ou edital precisa da data limite de inscrição.
   Se você não achar a data na página, descarte o item. Não estime.
4. Curso gratuito pode não ter prazo — matrícula sempre aberta é normal. Nesse
   caso deixe o prazo em branco.
5. O título precisa dizer de qual organização é a oportunidade.
6. Nada de artigo, vídeo, ranking, e-book, live, página institucional nem
   publicidade de curso preparatório. Só oportunidade em que a pessoa se
   inscreve.
7. Priorize, nesta ordem: vagas afirmativas para pessoas negras; oportunidades
   no Nordeste (CE, BA, SE) ou remotas; oportunidades nas áreas dos membros.
8. Se não achar a quantidade pedida numa categoria, devolva menos. Edição curta
   e verdadeira é melhor que edição cheia de item duvidoso.

Responda em markdown, agrupado por categoria, exatamente neste formato:

## Trainees

### Alpargatas — Programa Trainee Expert 2027
- Prazo: 21/09/2026
- Local: Nacional, remoto
- Link: https://exemplo.com/trainee
- Contexto: O que a pessoa ganha e para quem serve, em uma ou duas frases.

## Estágios

## Cursos e formações gratuitas

## Editais, bolsas e intercâmbio

Em curso sem data limite, escreva "Prazo: matrícula sempre aberta". Se a vaga
for afirmativa para pessoas negras, acrescente uma linha "- Afirmativa: sim".
Mantenha as seções na ordem acima, mesmo que alguma fique vazia.
```

---

## Formato no Google Doc

Você cola a saída no Doc e o Apps Script manda o texto inteiro para o Gemini,
que monta o email. Não há parser: o formato acima existe para **você** conseguir
ler e corrigir, não para a máquina.

Duas coisas que o Apps Script confere sozinho, sem IA:

- **Toda URL do email tem que existir no Doc.** Se o Gemini devolver um link que
  não estava lá, o envio para. É a mesma defesa estrutural do pipeline anterior:
  link inventado deixa de depender de o modelo se comportar.
- **Prazo no passado não sai.** Data vencida no Doc é erro de curadoria, e é
  melhor o envio falhar do que a newsletter anunciar inscrição encerrada.
