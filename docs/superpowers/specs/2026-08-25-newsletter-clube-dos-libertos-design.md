# Newsletter do Clube dos Libertos — Design

**Data:** 2026-08-25
**Autor:** Italo Silva (Presidência / Clube dos Libertos)
**Status:** aprovado para planejamento de implementação

---

## 1. Contexto

O Clube dos Libertos é uma rede de profissionais e estudantes negros (black
network) com 17 membros ativos em agosto de 2026, distribuídos entre CE, BA, SP
e SE, em áreas que vão de Administração e Serviço Social a Arquivologia,
Engenharia e Computação.

O documento institucional *Ideias Adotadas* (agosto/2026) já define a Newsletter
como **Ideia 3**: canal de comunicação semanal do Clube e principal meio de
divulgação da Base de Talentos (Núcleo Ubuntu). A estrutura da edição e a
periodicidade vêm desse documento — este design não os reinventa, apenas
descreve como automatizar a produção da edição.

Este é um projeto voluntário, sem orçamento. Toda escolha técnica aqui privilegia
serviço gratuito e operação sem servidor próprio.

## 2. Objetivo

Produzir automaticamente, uma vez por semana, uma edição da newsletter com
oportunidades de **trainee, estágio, editais e programas de educação gratuitos
com inscrições abertas**, formatada na identidade visual do Clube, entregue como
**campanha em rascunho no Brevo** para revisão e envio manual pela Presidência.

### Não-objetivos (fase 1)

- Envio automático sem aprovação humana
- Edição segmentada por perfil de membro (depende da Base de Talentos preenchida)
- Painel ou dashboard próprio — o painel é o do Brevo
- Domínio de email próprio
- Gestão da lista de contatos em código (a lista vive no Brevo, gerida manualmente)

## 3. Decisões

| Decisão | Escolha | Por quê |
|---|---|---|
| Curadoria | Rascunho aprovado por humano | Protege contra link quebrado, vaga vencida e oportunidade inventada pela IA; é o que o documento institucional prevê |
| Busca | Híbrido: fontes fixas + IA com acesso à web | Fontes fixas garantem piso de conteúdo toda semana; a IA cobre o que está fora da lista |
| IA | ~~Gemini com grounding de Google Search~~ → **Serper (Google) para busca + Gemini para classificar e redigir** | A premissa original caiu na primeira execução: no free tier do Gemini o grounding responde `429 RESOURCE_EXHAUSTED` — o modelo tem cota, a ferramenta de busca não. Revisado em 26/08/2026 |
| Envio | Brevo (free tier) | Lista, descadastro automático, métricas e entregabilidade sem custo |
| Lista de contatos | Gerida direto no Brevo | Elimina módulo de sincronização, credencial do Google e risco de LGPD por sobrescrever descadastro |
| Execução | GitHub Actions com cron | Gratuito, não depende da máquina do autor estar ligada, segredos em Secrets, log por execução |
| Relevância | Ampla, com prioridade para afirmativas | Cobre a comunidade toda sem esvaziar a edição em semanas fracas |

### Reconciliação com a estrutura institucional

O documento institucional prevê seis blocos na edição. A automação não cobre
todos, e isso é intencional:

| Bloco | Origem |
|---|---|
| Abertura | Gerado pela IA a partir dos itens da semana |
| Vagas da semana | **Manual** — preenchido por quem revisa, no Brevo, quando houver |
| Editais e formações | Automático |
| Trainees e estágios | Automático |
| Cadastre-se na Base de Talentos | Fixo no template |
| Espaço do Clube | **Manual** — recado, evento ou conquista de membro |

Os blocos manuais aparecem no rascunho com um marcador visível e instrução curta
("preencha ou apague este bloco"), em cor de destaque para não passar batido. Não
há esconderijo automático: o Brevo envia exatamente o que está no editor, então
quem revisa preenche ou apaga o bloco antes de disparar. O marcador é chamativo
justamente para que passar batido seja difícil.

## 4. Arquitetura

Seis módulos, cada um com uma responsabilidade única e testável isoladamente.

```
sources.yml ──► collector ──┐
                            ├──► curator ──► writer ──► renderer ──► publisher ──► Brevo (rascunho)
       Gemini ──► discovery ─┘        │
                                      ▼
                                 history.json
```

### 4.1 `sources.yml` — configuração, não código

Lista de fontes fixas. Adicionar fonte é editar YAML, não programar.

```yaml
- nome: Escola Virtual Gov
  url: https://...
  tipo: rss | html
  categoria: educacao | trainee | estagio | edital
  seletor: ".card-curso"      # somente para tipo html
  afirmativa: false
```

A lista inicial é montada na primeira tarefa de implementação, validando cada
candidata (a fonte precisa responder e ter conteúdo parseável antes de entrar no
arquivo). Candidatas a verificar, por categoria:

- **Estágio e trainee:** CIEE, Nube, portais de programas de trainee
- **Educação gratuita:** Escola Virtual Gov, Fundação Bradesco, FGV cursos
  gratuitos, Santander Open Academy
- **Editais e bolsas:** Fundação Estudar, Fundação Lemann
- **Afirmativas:** iniciativas de empregabilidade para pessoas negras
  (verificar quais mantêm listagem pública e estável)

Nenhuma URL entra no arquivo sem ter sido verificada — fonte que não responde ou
não é parseável fica fora, com o motivo registrado.

### 4.2 `collector` — coleta determinística

Percorre `sources.yml`, busca cada fonte (RSS via feedparser, HTML via
BeautifulSoup) e devolve itens brutos. Uma fonte que falha não derruba as
outras: registra o erro e segue.

### 4.3 `search` + `discovery` — busca na web e classificação

**Revisado em 26/08/2026.** O desenho original usava o grounding de Google
Search do próprio Gemini. Não é viável no free tier: a ferramenta responde
`429 RESOURCE_EXHAUSTED` mesmo com o modelo respondendo normalmente.

A divisão passou a ser:

- **`search`** consulta a API do Serper (plano gratuito; 4 consultas por
  execução, uma por categoria). Em 26/08/2026 a Presidência decidiu não manter
  consultas afirmativas dedicadas: a complexidade não se pagava. Oportunidade
  afirmativa continua recebendo selo e prioridade no ranking **quando o
  classificador a reconhece** — mas nada no pipeline vai atrás dela.
- **`discovery`** manda o Gemini classificar os resultados: separa oportunidade
  real de artigo, extrai prazo, confirma categoria.

**Regra dura, agora estrutural:** `interpretar` só aceita item cuja URL esteja
entre os resultados da busca. Link inventado deixou de depender de o modelo
obedecer ao prompt — a URL só pode ter vindo do Serper. Categoria e flag
afirmativa da consulta prevalecem sobre o palpite do modelo, já que a consulta
sabia o que estava procurando.

### 4.4 `curator` — a parte que importa

Funções puras, sem rede, sobre a união de `collector` + `discovery`:

1. **Deduplicação** — por URL normalizada e por similaridade de título, contra os
   itens da semana e contra o `history.json`
2. **Validação de link** — descarta o que não responde HTTP 200 (única etapa com
   rede, isolada numa função injetável para poder ser mockada)
3. **Validação de prazo** — descarta inscrição encerrada; item sem data
   identificável é mantido mas marcado como "prazo não informado"
4. **Ranking de relevância** — afirmativas primeiro; depois aderência às áreas e
   estados dos membros; depois abrangência nacional ou remota
5. **Regra de domínio** — item de fonte fixa cujo link sai do domínio da fonte é
   descartado. A fonte da informação é o link: vaga listada pelo Cia de Estágios
   que aponta para `estagio.alupar.com.br` não é página do Cia de Estágios
6. **Seleção com folga** — passa adiante 3× a cota, porque o enriquecimento
   descarta boa parte
7. **Corte final** — cota por categoria, revisada em 26/08/2026: 6 trainees,
   5 estágios, 5 de educação e 5 de bolsas/intercâmbio (21 no total). A cota é
   por categoria e não por bloco: "Trainees e estágios" reúne duas categorias, e
   sem cota separada um dia farto de trainees ocuparia as vagas de estágio

### 4.4b `enrich` — abre a página de cada finalista

**Acrescentado em 26/08/2026.** A listagem quase nunca traz a data limite: ela
está dentro da página da vaga. Na edição de teste, **zero** dos 34 itens tinham
prazo. Esta etapa busca a página de cada finalista e o Gemini extrai empresa e
prazo dali.

Três regras duras: item sem prazo encontrado não publica; prazo vencido não
publica, mesmo com a página no ar; URL que o modelo devolver e que não estava na
lista é ignorada. O título ganha a empresa na frente, salvo quando ela já
aparece nele.

É também a peneira que as fontes fixas não tinham — antes item de fonte fixa ia
direto para a edição, o que deixava passar vídeo, artigo e programa encerrado que
continua publicado.

### 4.4c `qa` — análise da edição pronta

**Acrescentado em 26/08/2026.** Duas camadas: verificações determinísticas (ano
passado no título, prazo vencido ou ausente, título genérico, URL repetida) e um
parecer do Gemini sobre o que código não pega — item que parece publicidade,
título que não diz de quem é a vaga, resumo que contradiz o título.

É **alerta, não portão**: o relatório vai no email de aviso, para quem revisa
saber onde olhar. Roda depois de o rascunho existir, e falhar nela não custa a
edição

### 4.5 `writer` — redação

Gemini escreve a abertura da edição e um resumo curto por item (2 a 3 linhas),
no tom do Clube. O prompt recebe apenas os itens já curados: a IA redige, não
decide o que entra.

### 4.6 `renderer` — HTML do email

Template Jinja2 com CSS inline (requisito de cliente de email), na identidade
visual do Clube:

- **Paleta:** `#5C1A88` roxo · `#FFC812` amarelo · `#4B2B20` marrom · `#000000` preto
- **Tipografia:** Luciole (fonte do manual, com fallback web-safe). Adumu, por
  ser display, entra apenas como imagem no cabeçalho — cliente de email não
  carrega fonte customizada de forma confiável
- **Logo:** versão horizontal, PNG, hospedada como asset do repositório
- **Rodapé fixo:** Instagram (`instagram.com/clubedoslibertos`), LinkedIn
  (`linkedin.com/company/clube-dos-libertos-black-network`) e link de descadastro
  do Brevo
- **CTA Base de Talentos:** `https://forms.gle/TXvssihhk4QTnCJo6`

Precisa passar em teste de largura móvel (uma coluna, 600px) e ter texto
alternativo em toda imagem.

### 4.7 `publisher` — rascunho no Brevo

Cria a edição como **campanha em rascunho** apontada para a lista de membros, com
assunto gerado a partir da semana e do destaque. Nunca dispara envio.

**Notificação.** Ao terminar, envia um email curto para
`clubedoslibertos@gmail.com` pela API transacional do Brevo, com o resumo da
execução (quantos itens por bloco, quais fontes falharam) e o link direto da
campanha no painel. O mesmo caminho é usado nas falhas descritas na seção 6 —
uma única forma de aviso, tanto para sucesso quanto para erro, para que silêncio
signifique sempre "o job não rodou".

### 4.8 `history.json` — estado no próprio repositório

Registro do que já foi publicado (URL normalizada, título, data da edição). O
workflow commita o arquivo de volta ao repositório após a execução. Sem banco,
sem serviço pago, e o histórico fica auditável em git.

## 5. Fluxo semanal

1. Segunda, 07:00 (BRT) — cron do GitHub Actions dispara
2. `collector` varre as fontes fixas
3. `discovery` consulta o Gemini
4. `curator` deduplica, valida e ordena
5. `writer` redige; `renderer` monta o HTML
6. `publisher` cria a campanha rascunho no Brevo
7. Workflow commita o `history.json` atualizado
8. Presidência revisa no Brevo, ajusta os blocos manuais e envia

O cron é escrito em UTC (`0 10 * * 1`) com o horário de Brasília em comentário.

## 6. Tratamento de erros

| Falha | Comportamento |
|---|---|
| Uma fonte fixa indisponível | Registra e segue com as demais |
| Todas as fontes fixas falham | Segue somente com o resultado do `discovery` |
| Gemini indisponível ou sem cota | Segue somente com as fontes fixas; a abertura usa texto padrão |
| Ambos falham, ou zero itens após a curadoria | **Aborta sem criar rascunho** e notifica a falha — edição vazia não vira rascunho |
| Brevo indisponível | Salva o HTML como artifact do workflow e notifica, para não perder a edição |

## 7. Configuração e segredos

Em GitHub Secrets:

| Segredo | Uso |
|---|---|
| `GEMINI_API_KEY` | Busca e redação |
| `BREVO_API_KEY` | Criação da campanha rascunho |
| `BREVO_LIST_ID` | Lista de destinatários |

Em arquivo de configuração versionado: remetente
(`clubedoslibertos@gmail.com`), links de redes sociais, link do formulário da
Base de Talentos, limites por bloco.

**Atenção na criação da chave do Gemini:** ela precisa ser gerada em um projeto
do Google Cloud **sem billing ativo**. Chave criada em projeto com billing cai
para cota zero no free tier — foi o que travou o projeto Slide Generator.

## 8. Testes

- `curator` — testes unitários com fixtures: item duplicado, prazo vencido, item
  sem data, ordenação com e sem afirmativa, corte por bloco
- `collector` e `discovery` — respostas HTTP e de API salvas em arquivo; a suíte
  roda offline e não consome cota do Gemini
- `renderer` — comparação com HTML de referência, mais checagem de que toda
  imagem tem texto alternativo
- `publisher` — Brevo mockado; nenhum teste cria campanha real
- Um teste end-to-end com todas as fontes mockadas, verificando que o pipeline
  produz HTML válido a partir de dados de entrada conhecidos

## 9. Riscos conhecidos

**Entregabilidade do remetente `@gmail.com`.** Desde 2024 Gmail e Yahoo
endureceram as exigências para envio em massa. Email disparado de um endereço
`@gmail.com` através de um serviço terceiro autentica pior que de domínio
próprio e tende a cair em "Promoções" ou spam. Aceitável para a fase 1, com o
Clube ainda em 17 membros. Mitigação futura: domínio próprio com SPF e DKIM
configurados — a troca é só de configuração.

**Fragilidade de scraping.** Fonte que muda o HTML para de funcionar. Mitigado
por: fonte que falha não derruba a execução, o `discovery` cobre a lacuna, e o
log de cada execução mostra qual fonte parou de responder.

**Cota do free tier.** Gemini e Brevo têm limites. Com uma execução semanal a
folga é grande, mas o log registra o consumo para dar visibilidade antes de
virar problema.

**Continuidade.** O projeto depende de uma chave do Gemini e uma conta Brevo
pessoais. Como o repositório é a única infraestrutura, a transferência para
outra pessoa do Clube exige apenas repassar o repositório e recriar os dois
segredos.

## 10. Evolução prevista

- Edição segmentada por área e estado, cruzando com a Base de Talentos
- Domínio próprio de email
- Envio automático com validação técnica forte, quando as fontes estiverem
  maduras e o histórico mostrar que a curadoria manual não está mais corrigindo nada
