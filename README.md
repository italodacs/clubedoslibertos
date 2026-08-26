# Newsletter do Clube dos Libertos

Pipeline semanal que busca oportunidades de trainee, estágio, editais e
educação gratuita, monta o HTML na identidade visual do Clube e cria uma
campanha **em rascunho** no Brevo para revisão e envio manual.

Projeto voluntário do Clube dos Libertos — Black Network.

## Como funciona

Toda segunda, 07:00 (Brasília), o GitHub Actions roda o pipeline:

1. `collector` varre as fontes fixas de `newsletter/sources.yml`
2. `search` consulta o Serper (Google) e `discovery` manda o Gemini classificar o
   que voltou — separando oportunidade real de artigo sobre o assunto
3. `curator` deduplica contra o histórico, descarta link morto e prazo vencido,
   ordena por relevância (afirmativas primeiro) e corta na cota de cada categoria
4. `writer` redige a abertura e os resumos
5. `renderer` monta o HTML
6. `publisher` cria a campanha **rascunho** no Brevo
7. Chega um email em clubedoslibertos@gmail.com com o link da campanha

Quem revisa preenche ou apaga os blocos manuais ("Vagas da semana" e "Espaço do
Clube") e clica em Enviar. **O pipeline nunca envia sozinho.**

## Cotas por edição

| Categoria | Itens |
|---|---|
| Trainee | 10 |
| Estágio | 10 |
| Educação gratuita | 7 |
| Editais, bolsas e intercâmbio | 7 |

A cota é por categoria, não por bloco: trainee e estágio dividem o mesmo bloco
da edição, e sem cota separada uma semana farta de trainees ocuparia as vagas
de estágio.

## Fontes

Seis fontes fixas, todas verificadas contra o próprio collector. O histórico de
avaliação — inclusive o que foi reprovado e por quê — está em
[`docs/fontes-avaliadas.md`](docs/fontes-avaliadas.md).

Categoria sem fonte fixa continua coberta pela busca na web.

**Por que a busca é do Serper e não do Gemini:** a intenção original era usar o
grounding de Google Search embutido no Gemini, uma chave só para tudo. No free
tier essa ferramenta responde `429 RESOURCE_EXHAUSTED` — o modelo tem cota, a
ferramenta de busca não. O Serper cobre a busca no plano gratuito, e a divisão
acabou saindo melhor: **o Serper devolve as URLs e o Gemini só classifica o que
o Serper achou**, então link inventado é estruturalmente impossível, e não uma
questão de o modelo obedecer ao prompt.

## Rodar localmente

```bash
pip install -r requirements.txt
python -m pytest tests/ -q

export GEMINI_API_KEY=...
export BREVO_API_KEY=...
export BREVO_LIST_ID=...
python -m newsletter.main
```

> Em rede corporativa que intercepta TLS, a coleta falha com `SSLError` em quase
> toda fonte. Não é problema do código — no GitHub Actions não há proxy no meio.

## Segredos

Configurados em Settings → Secrets and variables → Actions. **Nenhum valor de
segredo entra em arquivo versionado, e nenhum deve ser colado em chat.**

| Segredo | Onde obter |
|---|---|
| `GEMINI_API_KEY` | aistudio.google.com. Só redação e classificação: o grounding de Google Search **não tem cota no free tier** (429), por isso a busca é do Serper |
| `SERPER_KEY` | serper.dev — plano gratuito. O pipeline usa 7 consultas por execução |
| `BREVO_API_KEY` | Brevo → SMTP & API → API keys |
| `BREVO_LIST_ID` | Brevo → Contacts → Lists; o id aparece na URL da lista (hoje: `3`, lista "Membros") |

## Configuração do Brevo

Duas coisas que precisam estar certas na conta, e que não são óbvias:

**Autorização por IP tem que ficar desligada** (`app.brevo.com/security/authorised_ips`).
Os runners do GitHub Actions trocam de IP a cada execução e não há faixa fixa
para cadastrar. Com a restrição ligada, a API responde `401 unrecognised IP
address` e o job falha toda semana — com o sintoma de "a newsletter não chegou",
sem pista óbvia.

**O remetente precisa estar verificado** em Senders. O email de cadastro da
conta já nasce verificado; qualquer outro endereço exige clicar no link de
confirmação antes de conseguir enviar.

## Manutenção

- **Adicionar fonte:** editar `newsletter/sources.yml`. Verifique antes que a
  fonte responde e é parseável — o roteiro está no fim de `docs/fontes-avaliadas.md`.
- **Fonte parou de funcionar:** o log da execução no Actions nomeia a fonte que
  falhou. Fonte quebrada não derruba a edição.
- **Lista de contatos:** gerida direto no Brevo, não neste repositório.
- **Membros mudaram:** `AREAS_MEMBROS` e `ESTADOS_MEMBROS` em
  `newsletter/config.py` alimentam o ranking de relevância.

## Documentos

- Design: [`docs/superpowers/specs/2026-08-25-newsletter-clube-dos-libertos-design.md`](docs/superpowers/specs/2026-08-25-newsletter-clube-dos-libertos-design.md)
- Plano de implementação: [`docs/superpowers/plans/2026-08-25-newsletter-fase-1.md`](docs/superpowers/plans/2026-08-25-newsletter-fase-1.md)
- Fontes avaliadas: [`docs/fontes-avaliadas.md`](docs/fontes-avaliadas.md)
