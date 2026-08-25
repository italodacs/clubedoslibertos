# Fontes avaliadas

Histórico de avaliação das fontes fixas. **Registra também as reprovadas**, para
que ninguém gaste tempo retestando o que já foi descartado.

Última avaliação: **25/08/2026**.

## Método

Cada candidata foi buscada e passada pelo próprio `newsletter.collector`, com o
seletor candidato. Critério de aprovação: devolver 3 ou mais itens com título
informativo e URL absoluta que aponte para a página real da oportunidade.

> **Nota sobre a máquina de desenvolvimento:** a rede local intercepta TLS, e
> `requests` recusa o certificado de quase todo domínio externo (`SSLError`).
> A avaliação foi feita com `verify=False` **apenas na sondagem** — o código de
> produção mantém a validação ligada, e no GitHub Actions não há proxy no meio.
> A única candidata que respondeu com certificado válido daqui foi a Escola
> Virtual Gov.

## Aprovadas

Oito fontes, 216 itens coletados na verificação, nenhuma falha.

| Fonte | Categoria | Seletor | Itens | Observação |
|---|---|---|---|---|
| Seja Trainee | `trainee` | `.jeg_post_title` | 35 (33 únicos) | Melhor fonte de trainee: cada item é um texto sobre o processo seletivo, com nome da empresa e edição no título |
| Vagas.com Trainee | `trainee` | `.informacoes-header` | 40 (39 únicos) | `titulo: bloco`. Mistura anúncio comum na listagem — ver "Qualidade" abaixo |
| Cia de Estagios | `estagio` | `.vagas__card:not(.--expired)` | 11 | Saída mais limpa de todas. O seletor exclui as vagas que a própria página marca como encerradas |
| Estagio Trainee | `estagio` | `a[href*="/post/"]` | 16 | Site em Wix: as classes são hashes gerados que mudam a cada rebuild, então o href é a única âncora estável |
| Vagas.com Estagio | `estagio` | `.informacoes-header` | 40 (39 únicos) | `titulo: bloco` — o link sozinho diz apenas "Estagiário" |
| Sebrae Cursos Online | `educacao` | `.product-card__title` | 50 (43 únicos) | O catálogo marca "Gratuito" em cada curso e não há preço na página — confirmado |
| Escola Virtual Gov | `educacao` | `.card-title` | 12 | Cursos gratuitos do governo federal; único domínio com TLS válido daqui |
| Estudar Fora | `edital` | `.dce-post-title` | 12 (9 únicos) | Bolsas e intercâmbio. Mistura artigo com oportunidade — ver "Qualidade" abaixo |

## Reprovadas

| Candidata | Motivo |
|---|---|
| Santander Open Academy (`santander-tech`) | Página inteiramente renderizada por JavaScript — zero links com texto no HTML servido |
| Estudar.org | Só menu no HTML servido; `/bolsas/` responde 404. O conteúdo vem por Elementor/JS |
| Cia de Talentos | Só menu, tanto na home quanto em `/processos-seletivos/`. A listagem fica atrás de JS |
| Deloitte Brasil | HTTP 404 na página de programas de carreira |
| EY Brasil | HTTP 404 em `/careers/students`; o que veio era navegação |
| KPMG Brasil | Responde 200, mas só menu — sem listagem no HTML |
| PwC Brasil | HTTP 404; página depende de JS |
| Accenture Brasil | HTTP 404 no programa de estágio; o que veio era navegação |
| Fundação Bradesco (`ev.org.br/cursos`) | O primeiro link de cada card é "Favoritar", com href `#menu-de-acesso` |
| CIEE | A home não é listagem; a busca de vagas fica atrás de aplicação JS |
| FGV cursos gratuitos | Depende de JS |
| Fundação Lemann | HTTP 502 na avaliação |
| CNPq chamadas públicas | HTTP 404; o portal gov.br responde 401 a robô em outras rotas |
| Nube (`/vagas`) | HTTP 404 |
| empregosafirmativos.com.br | Domínio não resolve |
| indiqueumapreta.com.br | Domínio não resolve |
| afrolab.com.br | Domínio não resolve |
| maisdiversidade.com.br/vagas | HTTP 404; os itens da home eram menu |

**Sobre as consultorias:** as oito páginas de carreira testadas (Deloitte, EY,
KPMG, PwC, Accenture) não servem listagem parseável — ou respondem 404 na rota
pública, ou entregam só navegação porque as vagas vivem num ATS (Workday,
SuccessFactors) carregado por JavaScript. Programa de trainee de consultoria
chega hoje pelo Seja Trainee, que cobre esses processos em texto próprio.

## Qualidade do que entra

A verificação com dados reais mostrou que **parsear não é o mesmo que servir ao
propósito**. Duas fontes aprovadas trazem ruído junto:

- **Vagas.com** mistura anúncio comum na listagem de trainee e estágio. Na
  edição de teste entraram três variações de "Agente Stone — Executivo de
  Contas Externo", que não é programa de trainee, e a deduplicação não as
  colapsou porque a cidade muda o título.
- **Seja Trainee** publica também post promocional ("Nova Era Trainees:
  prepare-se...", "Conheça a Cursoria..."), que parece oportunidade mas é
  publicidade de curso preparatório.
- **Estudar Fora** alterna chamada real ("Harvard seleciona pesquisadores",
  "Bolsas de estudo abertas em agosto") com artigo editorial ("As melhores
  universidades do mundo em 2025", "Vídeo: o que é o SAT?").

É exatamente para isso que existe a etapa de revisão humana antes do envio. Se
o ruído incomodar toda semana, os caminhos são: cortar o Vagas.com (as fontes
especializadas cobrem melhor o mesmo terreno), ou criar uma lista de palavras
que reprovam um item no `curator`.

## Lacunas conhecidas

**Nenhuma fonte afirmativa fixa.** Três domínios de empregabilidade para pessoas
negras não resolveram DNS. Oportunidade afirmativa hoje chega pelo `discovery`,
que marca a flag `afirmativa` e ganha prioridade no ranking. Vale procurar uma
fonte estável: é o conteúdo de maior valor para a comunidade, e depender só da
IA para achá-lo é o ponto mais frágil do pipeline.

## Como avaliar uma nova candidata

```python
import requests
from newsletter.collector import coletar

UA = {"User-Agent": "Mozilla/5.0"}
fonte = {
    "nome": "Candidata",
    "url": "https://...",
    "tipo": "html",
    "categoria": "educacao",
    "seletor": ".card",
    "afirmativa": False,
}
itens, falhas = coletar([fonte], lambda u: requests.get(u, headers=UA, timeout=25).text)
print(len(itens), falhas)
for i in itens[:5]:
    print("-", i.titulo, "|", i.url, "|", i.prazo)
```

Se os títulos vierem genéricos e repetidos, tente `"titulo": "bloco"`. Se a
âncora do card for vazia, aponte `titulo` para um seletor CSS interno. Se as
classes do site forem hashes gerados, selecione pelo href
(`a[href*="/post/"]`). Só reprove depois disso.
