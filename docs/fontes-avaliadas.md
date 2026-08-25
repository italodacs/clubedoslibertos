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

| Fonte | Categoria | Seletor | Itens | Observação |
|---|---|---|---|---|
| Vagas.com Trainee | `trainee` | `.informacoes-header` | 40 (39 únicos) | `titulo: bloco` — o link diz só "Trainee"; o bloco traz a empresa |
| Vagas.com Estagio | `estagio` | `.informacoes-header` | 40 (39 únicos) | idem: o link diz só "Estagiário" |
| Sebrae Cursos Online | `educacao` | `.product-card__title` | 50 (43 únicos) | O catálogo marca "Gratuito" em cada curso e não há preço na página — confirmado |
| Escola Virtual Gov | `educacao` | `.card-title` | 12 | Cursos gratuitos do governo federal; único domínio com TLS válido daqui |

## Reprovadas

| Candidata | Motivo |
|---|---|
| Fundação Bradesco (`ev.org.br/cursos`) | O primeiro link de cada card é "Favoritar", com href `#menu-de-acesso` — 12 itens, 1 título único. Nenhum seletor testado devolveu o curso em si |
| CIEE (`portal.ciee.org.br`) | A home não é listagem; os itens encontrados eram menu (`.elementor-icon-list-item`). A busca de vagas fica atrás de aplicação JS |
| Santander Open Academy | Página inteiramente renderizada por JavaScript — zero links com texto no HTML servido |
| FGV cursos gratuitos | Idem: depende de JS |
| Estudar Fora (`/bolsas/`) | **Parseia, mas serve o propósito errado.** Devolve artigos de blog ("Harvard: tudo sobre a mais prestigiada universidade"), não editais com prazo. Encheria a newsletter de leitura, não de oportunidade |
| Fundação Lemann | HTTP 502 na avaliação |
| CNPq chamadas públicas | HTTP 404 na URL testada; o portal gov.br também responde 401 a robô em outras rotas |
| Nube (`/vagas`) | HTTP 404 |
| empregosafirmativos.com.br | Domínio não resolve |
| indiqueumapreta.com.br | Domínio não resolve |
| afrolab.com.br | Domínio não resolve |
| maisdiversidade.com.br/vagas | HTTP 404; os itens da home eram menu |

## Lacunas conhecidas

**`edital` não tem fonte fixa.** Nenhuma das candidatas de edital e bolsa passou:
as que respondem servem artigo em vez de chamada, e os portais públicos bloqueiam
robô. A categoria continua coberta pelo `discovery`, e **segue declarada em
`CATEGORIAS`** de propósito — tirá-la de lá faria o `discovery.interpretar`
descartar todo edital que o Gemini encontrasse.

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

Se os títulos vierem genéricos e repetidos, tente `"titulo": "bloco"` antes de
reprovar a fonte.
