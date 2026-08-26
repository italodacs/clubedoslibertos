# Prompt da pesquisa semanal (Claude app)

Este é o prompt da rotina semanal no app do Claude. Ela pesquisa as
oportunidades e devolve o conteúdo pronto para colar em
`newsletter/edicao.md`, que é o que o pipeline lê.

**Como usar:** no app do Claude, crie uma tarefa recorrente (sugestão: domingo à
noite, para o envio de segunda) e cole o prompt abaixo. Depois pegue a saída e
cole no arquivo `newsletter/edicao.md`, editando direto pelo github.com.

**Por que JSON:** o Apps Script tem `JSON.parse` nativo e não tem parser de
YAML. E JSON não tem a ambiguidade de tabela ou lista markdown, onde um
travessão fora de lugar muda o resultado em silêncio.

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

Responda SOMENTE com JSON, sem texto antes nem depois, sem cerca de código,
neste formato exato:

{"itens": [
  {
    "titulo": "Alpargatas — Programa Trainee Expert 2027",
    "url": "https://exemplo.com/trainee",
    "categoria": "trainee",
    "prazo": "2026-09-21",
    "local": "Nacional, remoto",
    "afirmativa": false,
    "contexto": "O que a pessoa ganha e para quem serve, em uma ou duas frases."
  }
]}

Onde `categoria` é trainee, estagio, educacao ou edital; `prazo` está em
AAAA-MM-DD e pode ser null apenas para curso sem data; e `afirmativa` é true
quando for vaga afirmativa para pessoas negras.
```

---

## Formato esperado

A saída vai colada num Google Doc, que o Apps Script lê e passa por
`JSON.parse`. Campos:

| Campo | Obrigatório | Regra |
|---|---|---|
| `titulo` | sim | precisa nomear a organização |
| `url` | sim | absoluta, `https://` |
| `categoria` | sim | `trainee`, `estagio`, `educacao` ou `edital` |
| `prazo` | sim, exceto em `educacao` | `AAAA-MM-DD` ou `null`, não pode estar no passado |
| `local` | não | usado no ranking e exibido no email |
| `afirmativa` | não | `false` quando ausente |
| `contexto` | não | insumo para o Gemini escrever o resumo |
