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

Cinco fontes.

| Fonte | Categoria | Seletor | Itens | Observação |
|---|---|---|---|---|
| Seja Trainee | `trainee` | `.jeg_post_title` | 35 (33 únicos) | Melhor fonte de trainee: cada item é um texto sobre o processo seletivo, com nome da empresa e edição no título |
| Cia de Estagios | `estagio` | `.vagas__card:not(.--expired)` | 11 | Saída mais limpa de todas. O seletor exclui as vagas que a própria página marca como encerradas |
| Estagio Trainee | `estagio` | `a[href*="/post/"]` | 16 | Site em Wix: as classes são hashes gerados que mudam a cada rebuild, então o href é a única âncora estável |
| Sebrae Cursos Online | `educacao` | `.product-card__title` | 50 (43 únicos) | O catálogo marca "Gratuito" em cada curso e não há preço na página — confirmado |
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
| Escola Virtual Gov | **Removida em 26/08/2026 por decisão da Presidência** — era escolha minha, não da lista definida por ela. Também vinha instável em produção: timeout de leitura em 20s nas duas primeiras execuções e `504 Gateway Time-out` quando o limite subiu para 60s |
| Vagas.com (trainee e estágio) | **Removida em 25/08/2026 por decisão da Presidência.** Parseava bem (40 itens cada), mas misturava anúncio comum na listagem de trainee: entraram três variações de "Agente Stone — Executivo de Contas Externo", que a deduplicação não colapsou porque a cidade muda o título. As fontes especializadas cobrem o mesmo terreno com qualidade melhor |
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

- **Seja Trainee** publica também post promocional ("Nova Era Trainees:
  prepare-se...", "Conheça a Cursoria..."), que parece oportunidade mas é
  publicidade de curso preparatório.
- **Estudar Fora** alterna chamada real ("Harvard seleciona pesquisadores",
  "Bolsas de estudo abertas em agosto") com artigo editorial ("As melhores
  universidades do mundo em 2025", "Vídeo: o que é o SAT?").

É exatamente para isso que existe a etapa de revisão humana antes do envio. Se
o ruído incomodar toda semana, o caminho é uma lista de palavras que reprovam
um item no `curator`.

## Lacunas conhecidas

**Não há fonte afirmativa fixa, e a busca não procura por ela.** Três domínios
de empregabilidade para pessoas negras não resolveram DNS, e em 26/08/2026 a
Presidência decidiu não manter consultas afirmativas dedicadas na busca — a
complexidade não se pagava. O que continua de pé: quando o classificador
reconhece uma oportunidade como afirmativa, ela recebe o selo "Vaga afirmativa"
no email e prioridade no ranking. Ou seja, ela aparece se aparecer, mas nada no
pipeline vai atrás dela de propósito.

**`educacao` ficou com uma fonte só** (Sebrae), depois da saída da Escola
Virtual Gov. Se o Sebrae cair, a categoria depende inteiramente da busca.

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
