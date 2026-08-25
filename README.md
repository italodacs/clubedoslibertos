# Newsletter do Clube dos Libertos

Pipeline semanal que busca oportunidades de trainee, estágio, editais e
educação gratuita, monta o HTML na identidade visual do Clube e cria uma
campanha **em rascunho** no Brevo para revisão e envio manual.

Projeto voluntário do Clube dos Libertos — Black Network.

## Como funciona

Toda segunda, 07:00 (Brasília), o GitHub Actions roda o pipeline:

1. `collector` varre as fontes fixas de `newsletter/sources.yml`
2. `discovery` pergunta ao Gemini (com Google Search) o que há de novo
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

Categoria sem fonte fixa continua coberta pelo `discovery`.

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
| `GEMINI_API_KEY` | aistudio.google.com — **em projeto sem billing ativo**, senão a cota do free tier vira zero |
| `BREVO_API_KEY` | Brevo → SMTP & API → API keys |
| `BREVO_LIST_ID` | Brevo → Contacts → a lista de membros; o id aparece na URL |

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
