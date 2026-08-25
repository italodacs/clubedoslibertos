# Newsletter do Clube dos Libertos — Plano de Implementação (Fase 1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir o pipeline semanal que busca oportunidades de trainee, estágio, editais e educação gratuita, monta o HTML na identidade do Clube dos Libertos e cria uma campanha em rascunho no Brevo para aprovação manual.

**Architecture:** Seis módulos encadeados, cada um com uma responsabilidade única. `collector` (fontes fixas) e `discovery` (Gemini com Google Search) alimentam o `curator`, que é código puro sem rede — dedupe, validação de prazo, ranking e corte. O `writer` redige com o Gemini, o `renderer` monta o HTML com Jinja2, e o `publisher` cria a campanha rascunho no Brevo. Toda dependência externa (HTTP, Gemini, Brevo) entra nas funções por injeção, o que deixa a suíte de testes rodando offline.

**Tech Stack:** Python 3.14 · pytest · requests · feedparser · beautifulsoup4 · Jinja2 · PyYAML · google-genai · API REST do Brevo via `requests` (sem SDK) · GitHub Actions

**Spec:** `docs/superpowers/specs/2026-08-25-newsletter-clube-dos-libertos-design.md`

## Global Constraints

- **Máximo de 5 itens por bloco** da edição.
- **Item sem URL rastreável é descartado** antes de chegar ao curator.
- **O publisher nunca dispara envio** — só cria campanha em rascunho.
- **Edição vazia não vira rascunho:** zero itens após a curadoria aborta a execução.
- **Nenhum teste faz chamada de rede real** e nenhum teste consome cota do Gemini ou cria campanha no Brevo.
- **Paleta:** roxo `#5C1A88` · amarelo `#FFC812` · marrom `#4B2B20` · preto `#000000`.
- **Remetente:** `clubedoslibertos@gmail.com`.
- **Instagram:** `https://www.instagram.com/clubedoslibertos/`
- **LinkedIn:** `https://www.linkedin.com/company/clube-dos-libertos-black-network/`
- **Formulário da Base de Talentos:** `https://forms.gle/TXvssihhk4QTnCJo6`
- **Cron:** `0 10 * * 1` (10:00 UTC = 07:00 BRT, segunda-feira).
- **Segredos** vivem em GitHub Secrets: `GEMINI_API_KEY`, `BREVO_API_KEY`, `BREVO_LIST_ID`. Nenhum valor de segredo entra em arquivo versionado.
- **Idioma do código:** nomes de função, variável e teste em português, seguindo o vocabulário do projeto (`Oportunidade`, `curar`, `blocos`). Mensagens de commit em português, sem acento (o terminal do autor é Windows).

---

## Estrutura de arquivos

```
clubedoslibertos/
  newsletter/
    __init__.py
    models.py          # Oportunidade, mapeamento categoria -> bloco
    config.py          # links, remetente, limites, paleta
    history.py         # chave de dedupe, carregar/registrar historico
    curator.py         # dedupe, prazo, ranking, corte (puro)
    collector.py       # fontes fixas: RSS e HTML
    discovery.py       # Gemini com Google Search
    writer.py          # abertura e resumos
    renderer.py        # HTML via Jinja2
    publisher.py       # campanha rascunho no Brevo
    notifier.py        # email transacional de aviso
    main.py            # orquestracao e politica de falha
    sources.yml        # fontes fixas verificadas
    templates/
      edicao.html.j2
    assets/
      logo.png
  tests/
    conftest.py
    fixtures/
      feed_exemplo.xml
      pagina_exemplo.html
      resposta_gemini.json
    test_models.py
    test_history.py
    test_curator.py
    test_collector.py
    test_sources.py
    test_discovery.py
    test_writer.py
    test_renderer.py
    test_publisher.py
    test_main.py
  .github/workflows/newsletter.yml
  history.json
  requirements.txt
  pyproject.toml
  .gitignore
  README.md
```

Cada módulo tem uma responsabilidade e cabe em contexto sozinho. `curator.py` é o único que concentra regra de negócio; os demais são adaptadores finos para o mundo externo.

---

### Task 1: Scaffold do projeto e modelo de dados

**Files:**
- Create: `requirements.txt`, `pyproject.toml`, `.gitignore`, `newsletter/__init__.py`, `newsletter/models.py`, `newsletter/config.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Consumes: nada (primeira tarefa)
- Produces:
  - `newsletter.models.Oportunidade` — dataclass congelada com campos `titulo: str`, `url: str`, `categoria: str`, `fonte: str`, `prazo: datetime.date | None`, `afirmativa: bool`, `resumo: str = ""`
  - `newsletter.models.CATEGORIAS: tuple[str, ...]` = `("trainee", "estagio", "edital", "educacao")`
  - `newsletter.models.bloco_de(categoria: str) -> str` — retorna `"Trainees e estágios"` ou `"Editais e formações"`, e levanta `ValueError` para categoria desconhecida
  - `newsletter.config` — constantes `REMETENTE_EMAIL`, `REMETENTE_NOME`, `INSTAGRAM_URL`, `LINKEDIN_URL`, `FORM_BASE_TALENTOS_URL`, `LIMITE_POR_BLOCO`, `ROXO`, `AMARELO`, `MARROM`, `PRETO`, `AREAS_MEMBROS`, `ESTADOS_MEMBROS`

- [ ] **Step 1: Criar os arquivos de dependência e configuração do projeto**

`requirements.txt`:

```
requests==2.33.1
Jinja2==3.1.6
google-genai==2.4.0
feedparser>=6.0
beautifulsoup4>=4.12
PyYAML>=6.0
pytest>=8.0
```

As três primeiras estão fixadas na versão já instalada na máquina do autor e verificada. As demais ainda não estão instaladas — deixe o piso mínimo, e fixe a versão exata no primeiro `pip install`, com `pip freeze | grep -i -E "feedparser|beautifulsoup4|PyYAML|pytest"`. Fixar versão que ninguém verificou é o tipo de coisa que quebra o CI na primeira execução.

`pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
addopts = "-v"
```

`.gitignore`:

```
__pycache__/
*.pyc
.pytest_cache/
.venv/
venv/
.env
saida/
```

- [ ] **Step 2: Escrever o teste que falha**

`tests/test_models.py`:

```python
import datetime

import pytest

from newsletter.models import CATEGORIAS, Oportunidade, bloco_de


def test_trainee_e_estagio_vao_para_o_mesmo_bloco():
    assert bloco_de("trainee") == "Trainees e estágios"
    assert bloco_de("estagio") == "Trainees e estágios"


def test_edital_e_educacao_vao_para_o_mesmo_bloco():
    assert bloco_de("edital") == "Editais e formações"
    assert bloco_de("educacao") == "Editais e formações"


def test_categoria_desconhecida_levanta_erro():
    with pytest.raises(ValueError, match="categoria desconhecida"):
        bloco_de("vaga_efetiva")


def test_todas_as_categorias_tem_bloco():
    for categoria in CATEGORIAS:
        assert bloco_de(categoria)


def test_oportunidade_e_imutavel_e_tem_resumo_vazio_por_padrao():
    op = Oportunidade(
        titulo="Programa de Trainee 2027",
        url="https://exemplo.org/trainee",
        categoria="trainee",
        fonte="Exemplo",
        prazo=datetime.date(2026, 9, 30),
        afirmativa=True,
    )
    assert op.resumo == ""
    with pytest.raises(Exception):
        op.titulo = "outro"
```

- [ ] **Step 3: Rodar o teste e confirmar que falha**

Run: `python -m pytest tests/test_models.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'newsletter'`

- [ ] **Step 4: Implementar o mínimo**

`newsletter/__init__.py`: arquivo vazio.

`newsletter/models.py`:

```python
"""Modelo de dados central do pipeline da newsletter."""

import datetime
from dataclasses import dataclass

CATEGORIAS = ("trainee", "estagio", "edital", "educacao")

_BLOCOS = {
    "trainee": "Trainees e estágios",
    "estagio": "Trainees e estágios",
    "edital": "Editais e formações",
    "educacao": "Editais e formações",
}


@dataclass(frozen=True)
class Oportunidade:
    titulo: str
    url: str
    categoria: str
    fonte: str
    prazo: datetime.date | None
    afirmativa: bool
    resumo: str = ""


def bloco_de(categoria: str) -> str:
    """Devolve o bloco da edição em que a categoria aparece."""
    try:
        return _BLOCOS[categoria]
    except KeyError:
        raise ValueError(f"categoria desconhecida: {categoria!r}") from None
```

`newsletter/config.py`:

```python
"""Configuração versionada. Segredos NÃO entram aqui — vêm de variável de ambiente."""

REMETENTE_EMAIL = "clubedoslibertos@gmail.com"
REMETENTE_NOME = "Clube dos Libertos"

INSTAGRAM_URL = "https://www.instagram.com/clubedoslibertos/"
LINKEDIN_URL = "https://www.linkedin.com/company/clube-dos-libertos-black-network/"
FORM_BASE_TALENTOS_URL = "https://forms.gle/TXvssihhk4QTnCJo6"

LOGO_URL = (
    "https://raw.githubusercontent.com/italodacs/clubedoslibertos"
    "/main/newsletter/assets/logo.png"
)

LIMITE_POR_BLOCO = 5

ROXO = "#5C1A88"
AMARELO = "#FFC812"
MARROM = "#4B2B20"
PRETO = "#000000"

# Usados pelo ranking de relevância (agosto/2026).
AREAS_MEMBROS = (
    "administração",
    "serviço social",
    "arquivologia",
    "geografia",
    "publicidade",
    "engenharia",
    "computação",
    "tecnologia",
)
ESTADOS_MEMBROS = ("CE", "BA", "SP", "SE")
```

- [ ] **Step 5: Rodar o teste e confirmar que passa**

Run: `python -m pytest tests/test_models.py -v`
Expected: PASS, 5 testes

- [ ] **Step 6: Commit**

```bash
git add requirements.txt pyproject.toml .gitignore newsletter/ tests/
git commit -m "feat: modelo de dados e configuracao do projeto"
```

---

### Task 2: Histórico de itens publicados

**Files:**
- Create: `newsletter/history.py`
- Test: `tests/test_history.py`

**Interfaces:**
- Consumes: `newsletter.models.Oportunidade`
- Produces:
  - `newsletter.history.chave(url: str) -> str` — normaliza URL para comparação
  - `newsletter.history.carregar(caminho: str | Path) -> set[str]` — devolve conjunto de chaves já publicadas; arquivo inexistente devolve conjunto vazio
  - `newsletter.history.registrar(caminho, oportunidades: list[Oportunidade], data_edicao: datetime.date) -> None` — acrescenta as oportunidades ao arquivo, preservando o que já existia

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_history.py`:

```python
import datetime
import json

from newsletter.history import carregar, chave, registrar
from newsletter.models import Oportunidade


def _op(url, titulo="Titulo"):
    return Oportunidade(
        titulo=titulo,
        url=url,
        categoria="trainee",
        fonte="Exemplo",
        prazo=None,
        afirmativa=False,
    )


def test_chave_ignora_maiusculas_e_barra_final():
    assert chave("https://Exemplo.org/Vaga/") == chave("https://exemplo.org/Vaga")


def test_chave_ignora_parametros_de_rastreamento():
    limpa = chave("https://exemplo.org/vaga")
    assert chave("https://exemplo.org/vaga?utm_source=news&utm_medium=email") == limpa
    assert chave("https://exemplo.org/vaga?fbclid=abc") == limpa


def test_chave_preserva_parametro_significativo():
    assert chave("https://exemplo.org/vaga?id=42") != chave("https://exemplo.org/vaga")


def test_carregar_arquivo_inexistente_devolve_conjunto_vazio(tmp_path):
    assert carregar(tmp_path / "nao_existe.json") == set()


def test_registrar_e_carregar_faz_ida_e_volta(tmp_path):
    caminho = tmp_path / "history.json"
    registrar(caminho, [_op("https://exemplo.org/a")], datetime.date(2026, 8, 31))
    assert chave("https://exemplo.org/a") in carregar(caminho)


def test_registrar_preserva_o_que_ja_existia(tmp_path):
    caminho = tmp_path / "history.json"
    registrar(caminho, [_op("https://exemplo.org/a")], datetime.date(2026, 8, 31))
    registrar(caminho, [_op("https://exemplo.org/b")], datetime.date(2026, 9, 7))
    chaves = carregar(caminho)
    assert chave("https://exemplo.org/a") in chaves
    assert chave("https://exemplo.org/b") in chaves


def test_arquivo_guarda_titulo_e_data_para_auditoria(tmp_path):
    caminho = tmp_path / "history.json"
    registrar(
        caminho,
        [_op("https://exemplo.org/a", titulo="Trainee Alfa")],
        datetime.date(2026, 8, 31),
    )
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    registro = dados["itens"][0]
    assert registro["titulo"] == "Trainee Alfa"
    assert registro["data_edicao"] == "2026-08-31"
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `python -m pytest tests/test_history.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'newsletter.history'`

- [ ] **Step 3: Implementar o mínimo**

`newsletter/history.py`:

```python
"""Histórico de oportunidades já publicadas, versionado no próprio repositório."""

import datetime
import json
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from newsletter.models import Oportunidade

# Parâmetros de rastreamento que não mudam o destino do link.
_PARAMS_DESCARTAVEIS = ("utm_", "fbclid", "gclid", "mc_cid", "mc_eid")


def chave(url: str) -> str:
    """Normaliza a URL para servir de chave de deduplicação."""
    partes = urlsplit(url.strip())
    query = [
        (nome, valor)
        for nome, valor in parse_qsl(partes.query)
        if not nome.lower().startswith(_PARAMS_DESCARTAVEIS)
    ]
    caminho = partes.path.rstrip("/")
    return urlunsplit(
        (partes.scheme.lower(), partes.netloc.lower(), caminho, urlencode(query), "")
    )


def carregar(caminho: str | Path) -> set[str]:
    """Devolve as chaves já publicadas. Arquivo inexistente é histórico vazio."""
    arquivo = Path(caminho)
    if not arquivo.exists():
        return set()
    dados = json.loads(arquivo.read_text(encoding="utf-8"))
    return {item["chave"] for item in dados.get("itens", [])}


def registrar(
    caminho: str | Path,
    oportunidades: list[Oportunidade],
    data_edicao: datetime.date,
) -> None:
    """Acrescenta as oportunidades ao histórico, preservando o conteúdo anterior."""
    arquivo = Path(caminho)
    if arquivo.exists():
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
    else:
        dados = {"itens": []}

    for op in oportunidades:
        dados["itens"].append(
            {
                "chave": chave(op.url),
                "titulo": op.titulo,
                "url": op.url,
                "data_edicao": data_edicao.isoformat(),
            }
        )

    arquivo.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
```

- [ ] **Step 4: Rodar o teste e confirmar que passa**

Run: `python -m pytest tests/test_history.py -v`
Expected: PASS, 7 testes

- [ ] **Step 5: Commit**

```bash
git add newsletter/history.py tests/test_history.py
git commit -m "feat: historico de itens publicados com chave normalizada"
```

---

### Task 3: Curator — dedupe, prazo, ranking e corte

Esta é a tarefa central: é aqui que mora o risco de vaga vencida, link morto e item repetido. Tudo é função pura, exceto a verificação de link, que entra por injeção.

**Files:**
- Create: `newsletter/curator.py`
- Test: `tests/test_curator.py`

**Interfaces:**
- Consumes: `newsletter.models.Oportunidade`, `newsletter.models.bloco_de`, `newsletter.config.LIMITE_POR_BLOCO`, `newsletter.config.AREAS_MEMBROS`, `newsletter.config.ESTADOS_MEMBROS`
- Produces:
  - `newsletter.curator.deduplicar(oportunidades, historico: set[str]) -> list[Oportunidade]`
  - `newsletter.curator.remover_vencidas(oportunidades, hoje: datetime.date) -> list[Oportunidade]`
  - `newsletter.curator.pontuar(op: Oportunidade) -> int`
  - `newsletter.curator.curar(oportunidades, historico, hoje, verificar_link) -> dict[str, list[Oportunidade]]` — `verificar_link` é um callable `(str) -> bool`; devolve dicionário de bloco para lista já ordenada e cortada

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_curator.py`:

```python
import datetime

from newsletter.curator import curar, deduplicar, pontuar, remover_vencidas
from newsletter.history import chave
from newsletter.models import Oportunidade

HOJE = datetime.date(2026, 8, 31)


def _op(url, titulo="Titulo", categoria="trainee", prazo=None, afirmativa=False):
    return Oportunidade(
        titulo=titulo,
        url=url,
        categoria=categoria,
        fonte="Exemplo",
        prazo=prazo,
        afirmativa=afirmativa,
    )


def _aceita_tudo(url):
    return True


# --- deduplicacao ---


def test_remove_item_ja_publicado_no_historico():
    op = _op("https://exemplo.org/a")
    assert deduplicar([op], {chave("https://exemplo.org/a")}) == []


def test_remove_duplicata_dentro_da_propria_semana():
    a = _op("https://exemplo.org/a?utm_source=x")
    b = _op("https://exemplo.org/a")
    assert len(deduplicar([a, b], set())) == 1


def test_remove_titulo_praticamente_igual_com_url_diferente():
    a = _op("https://exemplo.org/a", titulo="Programa de Trainee 2027")
    b = _op("https://outro.org/b", titulo="programa de trainee 2027")
    assert len(deduplicar([a, b], set())) == 1


def test_mantem_titulos_diferentes():
    a = _op("https://exemplo.org/a", titulo="Trainee Alfa")
    b = _op("https://outro.org/b", titulo="Estagio Beta")
    assert len(deduplicar([a, b], set())) == 2


# --- prazo ---


def test_remove_inscricao_encerrada():
    vencida = _op("https://exemplo.org/a", prazo=datetime.date(2026, 8, 30))
    assert remover_vencidas([vencida], HOJE) == []


def test_mantem_prazo_de_hoje():
    hoje = _op("https://exemplo.org/a", prazo=HOJE)
    assert remover_vencidas([hoje], HOJE) == [hoje]


def test_mantem_item_sem_prazo_identificado():
    sem_prazo = _op("https://exemplo.org/a", prazo=None)
    assert remover_vencidas([sem_prazo], HOJE) == [sem_prazo]


# --- ranking ---


def test_afirmativa_pontua_mais_que_nao_afirmativa():
    afirmativa = _op("https://exemplo.org/a", afirmativa=True)
    comum = _op("https://exemplo.org/b", afirmativa=False)
    assert pontuar(afirmativa) > pontuar(comum)


def test_area_de_membro_pontua_mais_que_area_de_fora():
    dentro = _op("https://exemplo.org/a", titulo="Estagio em Servico Social")
    fora = _op("https://exemplo.org/b", titulo="Estagio em Medicina Veterinaria")
    assert pontuar(dentro) > pontuar(fora)


def test_estado_de_membro_pontua_mais_que_estado_de_fora():
    dentro = _op("https://exemplo.org/a", titulo="Trainee em Fortaleza - CE")
    fora = _op("https://exemplo.org/b", titulo="Trainee em Curitiba - PR")
    assert pontuar(dentro) > pontuar(fora)


def test_afirmativa_vence_aderencia_de_area():
    afirmativa_fora = _op(
        "https://exemplo.org/a", titulo="Trainee em Medicina Veterinaria", afirmativa=True
    )
    comum_dentro = _op("https://exemplo.org/b", titulo="Trainee em Administracao")
    assert pontuar(afirmativa_fora) > pontuar(comum_dentro)


# --- curar (integracao dos passos) ---


def test_curar_agrupa_por_bloco():
    itens = [
        _op("https://exemplo.org/a", categoria="trainee"),
        _op("https://exemplo.org/b", categoria="educacao", titulo="Curso Gratuito"),
    ]
    blocos = curar(itens, set(), HOJE, _aceita_tudo)
    assert list(blocos["Trainees e estágios"]) == [itens[0]]
    assert list(blocos["Editais e formações"]) == [itens[1]]


def test_curar_descarta_link_morto():
    itens = [_op("https://exemplo.org/morto")]
    blocos = curar(itens, set(), HOJE, lambda url: False)
    assert blocos["Trainees e estágios"] == []


def test_curar_corta_em_cinco_itens_por_bloco():
    itens = [
        _op(f"https://exemplo.org/{i}", titulo=f"Trainee {i}") for i in range(9)
    ]
    blocos = curar(itens, set(), HOJE, _aceita_tudo)
    assert len(blocos["Trainees e estágios"]) == 5


def test_curar_ordena_afirmativa_primeiro():
    comum = _op("https://exemplo.org/a", titulo="Trainee Comum")
    afirmativa = _op("https://exemplo.org/b", titulo="Trainee Afirmativo", afirmativa=True)
    blocos = curar([comum, afirmativa], set(), HOJE, _aceita_tudo)
    assert blocos["Trainees e estágios"][0] == afirmativa


def test_curar_verifica_link_apenas_do_que_sobrou():
    """Link morto e caro de checar: nao gastar rede em item que ja foi descartado."""
    visitados = []

    def registrando(url):
        visitados.append(url)
        return True

    itens = [
        _op("https://exemplo.org/vencida", prazo=datetime.date(2026, 1, 1)),
        _op("https://exemplo.org/viva", titulo="Outra"),
    ]
    curar(itens, set(), HOJE, registrando)
    assert visitados == ["https://exemplo.org/viva"]
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `python -m pytest tests/test_curator.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'newsletter.curator'`

- [ ] **Step 3: Implementar o mínimo**

`newsletter/curator.py`:

```python
"""Curadoria: decide o que entra na edição. Código puro, sem rede.

A única dependência externa é a verificação de link, que entra por injeção
para que os testes rodem offline.
"""

import datetime
import re
import unicodedata
from collections.abc import Callable, Iterable

from newsletter.config import AREAS_MEMBROS, ESTADOS_MEMBROS, LIMITE_POR_BLOCO
from newsletter.history import chave
from newsletter.models import Oportunidade, bloco_de

PONTOS_AFIRMATIVA = 100
PONTOS_AREA = 10
PONTOS_ESTADO = 5


def _normalizar(texto: str) -> str:
    """Minúsculas, sem acento e sem pontuação, para comparar títulos."""
    sem_acento = "".join(
        c
        for c in unicodedata.normalize("NFD", texto.lower())
        if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"[^a-z0-9 ]", " ", sem_acento).strip()


def deduplicar(
    oportunidades: Iterable[Oportunidade], historico: set[str]
) -> list[Oportunidade]:
    """Remove o que já foi publicado e o que repete dentro da própria semana."""
    resultado: list[Oportunidade] = []
    chaves_vistas: set[str] = set()
    titulos_vistos: set[str] = set()

    for op in oportunidades:
        k = chave(op.url)
        titulo = _normalizar(op.titulo)
        if k in historico or k in chaves_vistas or titulo in titulos_vistos:
            continue
        chaves_vistas.add(k)
        titulos_vistos.add(titulo)
        resultado.append(op)

    return resultado


def remover_vencidas(
    oportunidades: Iterable[Oportunidade], hoje: datetime.date
) -> list[Oportunidade]:
    """Descarta inscrição encerrada. Item sem prazo identificado é mantido."""
    return [op for op in oportunidades if op.prazo is None or op.prazo >= hoje]


def pontuar(op: Oportunidade) -> int:
    """Relevância: afirmativa primeiro, depois aderência a área e estado."""
    pontos = 0
    if op.afirmativa:
        pontos += PONTOS_AFIRMATIVA

    texto = _normalizar(f"{op.titulo} {op.resumo}")
    if any(_normalizar(area) in texto for area in AREAS_MEMBROS):
        pontos += PONTOS_AREA

    titulo_cru = op.titulo.upper()
    if any(
        re.search(rf"\b{estado}\b", titulo_cru) for estado in ESTADOS_MEMBROS
    ):
        pontos += PONTOS_ESTADO

    return pontos


def curar(
    oportunidades: Iterable[Oportunidade],
    historico: set[str],
    hoje: datetime.date,
    verificar_link: Callable[[str], bool],
) -> dict[str, list[Oportunidade]]:
    """Pipeline de curadoria completo, agrupando por bloco da edição.

    A ordem importa: dedupe e prazo são baratos e vêm antes da verificação de
    link, que gasta rede. Não se checa link de item que já foi descartado.
    """
    itens = deduplicar(oportunidades, historico)
    itens = remover_vencidas(itens, hoje)
    itens = [op for op in itens if verificar_link(op.url)]

    blocos: dict[str, list[Oportunidade]] = {
        "Trainees e estágios": [],
        "Editais e formações": [],
    }
    for op in itens:
        blocos[bloco_de(op.categoria)].append(op)

    for nome, lista in blocos.items():
        lista.sort(key=pontuar, reverse=True)
        blocos[nome] = lista[:LIMITE_POR_BLOCO]

    return blocos
```

- [ ] **Step 4: Rodar o teste e confirmar que passa**

Run: `python -m pytest tests/test_curator.py -v`
Expected: PASS, 16 testes

- [ ] **Step 5: Commit**

```bash
git add newsletter/curator.py tests/test_curator.py
git commit -m "feat: curadoria com dedupe, validacao de prazo, ranking e corte"
```

---

### Task 4: Collector — fontes fixas em RSS e HTML

**Files:**
- Create: `newsletter/collector.py`, `tests/fixtures/feed_exemplo.xml`, `tests/fixtures/pagina_exemplo.html`
- Test: `tests/test_collector.py`

**Interfaces:**
- Consumes: `newsletter.models.Oportunidade`
- Produces:
  - `newsletter.collector.buscar_http(url: str) -> str` — busca real, com timeout de 20s e User-Agent próprio
  - `newsletter.collector.coletar(fontes: list[dict], buscar: Callable[[str], str]) -> tuple[list[Oportunidade], list[str]]` — devolve as oportunidades e a lista de nomes de fontes que falharam

- [ ] **Step 1: Criar as fixtures**

`tests/fixtures/feed_exemplo.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Feed de Exemplo</title>
    <item>
      <title>Programa de Trainee 2027</title>
      <link>https://exemplo.org/trainee-2027</link>
      <description>Inscrições até 30/09/2026.</description>
    </item>
    <item>
      <title>Estágio em Tecnologia</title>
      <link>https://exemplo.org/estagio-tech</link>
      <description>Vagas abertas.</description>
    </item>
  </channel>
</rss>
```

`tests/fixtures/pagina_exemplo.html`:

```html
<html>
  <body>
    <div class="card-curso">
      <a href="/curso/dados">Curso Gratuito de Dados</a>
      <span class="prazo">Inscrições até 15/10/2026</span>
    </div>
    <div class="card-curso">
      <a href="https://exemplo.org/curso/gestao">Curso Gratuito de Gestão</a>
    </div>
    <div class="rodape">Não é um curso</div>
  </body>
</html>
```

- [ ] **Step 2: Escrever o teste que falha**

`tests/test_collector.py`:

```python
import datetime
from pathlib import Path

from newsletter.collector import coletar

FIXTURES = Path(__file__).parent / "fixtures"

FONTE_RSS = {
    "nome": "Feed de Exemplo",
    "url": "https://exemplo.org/feed.xml",
    "tipo": "rss",
    "categoria": "trainee",
    "afirmativa": False,
}

FONTE_HTML = {
    "nome": "Portal de Cursos",
    "url": "https://exemplo.org/cursos",
    "tipo": "html",
    "categoria": "educacao",
    "seletor": ".card-curso",
    "afirmativa": False,
}


def _buscador(mapa):
    def buscar(url):
        if url not in mapa:
            raise RuntimeError(f"fonte fora do ar: {url}")
        return mapa[url]

    return buscar


def test_coleta_itens_de_rss():
    buscar = _buscador({FONTE_RSS["url"]: (FIXTURES / "feed_exemplo.xml").read_text(encoding="utf-8")})
    itens, falhas = coletar([FONTE_RSS], buscar)
    assert falhas == []
    assert len(itens) == 2
    assert itens[0].titulo == "Programa de Trainee 2027"
    assert itens[0].url == "https://exemplo.org/trainee-2027"
    assert itens[0].categoria == "trainee"
    assert itens[0].fonte == "Feed de Exemplo"


def test_extrai_prazo_em_formato_brasileiro():
    buscar = _buscador({FONTE_RSS["url"]: (FIXTURES / "feed_exemplo.xml").read_text(encoding="utf-8")})
    itens, _ = coletar([FONTE_RSS], buscar)
    assert itens[0].prazo == datetime.date(2026, 9, 30)
    assert itens[1].prazo is None


def test_coleta_itens_de_html_com_seletor():
    buscar = _buscador({FONTE_HTML["url"]: (FIXTURES / "pagina_exemplo.html").read_text(encoding="utf-8")})
    itens, falhas = coletar([FONTE_HTML], buscar)
    assert falhas == []
    assert [i.titulo for i in itens] == [
        "Curso Gratuito de Dados",
        "Curso Gratuito de Gestão",
    ]


def test_resolve_link_relativo_contra_a_url_da_fonte():
    buscar = _buscador({FONTE_HTML["url"]: (FIXTURES / "pagina_exemplo.html").read_text(encoding="utf-8")})
    itens, _ = coletar([FONTE_HTML], buscar)
    assert itens[0].url == "https://exemplo.org/curso/dados"


def test_marca_afirmativa_conforme_a_fonte():
    fonte = {**FONTE_RSS, "afirmativa": True}
    buscar = _buscador({fonte["url"]: (FIXTURES / "feed_exemplo.xml").read_text(encoding="utf-8")})
    itens, _ = coletar([fonte], buscar)
    assert all(i.afirmativa for i in itens)


def test_fonte_que_falha_nao_derruba_as_outras():
    fonte_morta = {**FONTE_RSS, "nome": "Fonte Morta", "url": "https://morta.org/feed.xml"}
    buscar = _buscador({FONTE_RSS["url"]: (FIXTURES / "feed_exemplo.xml").read_text(encoding="utf-8")})
    itens, falhas = coletar([fonte_morta, FONTE_RSS], buscar)
    assert falhas == ["Fonte Morta"]
    assert len(itens) == 2


def test_item_sem_link_e_descartado():
    rss_sem_link = """<?xml version="1.0"?><rss version="2.0"><channel>
        <item><title>Sem link</title></item>
        </channel></rss>"""
    buscar = _buscador({FONTE_RSS["url"]: rss_sem_link})
    itens, _ = coletar([FONTE_RSS], buscar)
    assert itens == []
```

- [ ] **Step 3: Rodar o teste e confirmar que falha**

Run: `python -m pytest tests/test_collector.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'newsletter.collector'`

- [ ] **Step 4: Implementar o mínimo**

`newsletter/collector.py`:

```python
"""Coleta determinística das fontes fixas cadastradas em sources.yml."""

import datetime
import logging
import re
from collections.abc import Callable
from urllib.parse import urljoin

import feedparser
import requests
from bs4 import BeautifulSoup

from newsletter.models import Oportunidade

log = logging.getLogger(__name__)

TIMEOUT = 20
USER_AGENT = "ClubeDosLibertos-Newsletter/1.0 (+https://github.com/italodacs/clubedoslibertos)"

_DATA_BR = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")


def buscar_http(url: str) -> str:
    """Busca o conteúdo de uma URL. Levanta exceção em qualquer erro."""
    resposta = requests.get(
        url, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}
    )
    resposta.raise_for_status()
    return resposta.text


def _extrair_prazo(texto: str) -> datetime.date | None:
    """Procura uma data dd/mm/aaaa no texto. Ausência não é erro."""
    achado = _DATA_BR.search(texto or "")
    if not achado:
        return None
    dia, mes, ano = (int(g) for g in achado.groups())
    try:
        return datetime.date(ano, mes, dia)
    except ValueError:
        return None


def _do_rss(conteudo: str, fonte: dict) -> list[Oportunidade]:
    feed = feedparser.parse(conteudo)
    itens = []
    for entrada in feed.entries:
        url = entrada.get("link")
        if not url:
            continue
        itens.append(
            Oportunidade(
                titulo=entrada.get("title", "").strip(),
                url=url,
                categoria=fonte["categoria"],
                fonte=fonte["nome"],
                prazo=_extrair_prazo(entrada.get("description", "")),
                afirmativa=bool(fonte.get("afirmativa", False)),
            )
        )
    return itens


def _do_html(conteudo: str, fonte: dict) -> list[Oportunidade]:
    sopa = BeautifulSoup(conteudo, "html.parser")
    itens = []
    for bloco in sopa.select(fonte["seletor"]):
        ancora = bloco.find("a", href=True)
        if not ancora:
            continue
        itens.append(
            Oportunidade(
                titulo=ancora.get_text(strip=True),
                url=urljoin(fonte["url"], ancora["href"]),
                categoria=fonte["categoria"],
                fonte=fonte["nome"],
                prazo=_extrair_prazo(bloco.get_text(" ", strip=True)),
                afirmativa=bool(fonte.get("afirmativa", False)),
            )
        )
    return itens


def coletar(
    fontes: list[dict], buscar: Callable[[str], str]
) -> tuple[list[Oportunidade], list[str]]:
    """Percorre as fontes fixas. Fonte que falha é registrada, não propagada."""
    encontrados: list[Oportunidade] = []
    falhas: list[str] = []

    for fonte in fontes:
        try:
            conteudo = buscar(fonte["url"])
            if fonte["tipo"] == "rss":
                encontrados.extend(_do_rss(conteudo, fonte))
            else:
                encontrados.extend(_do_html(conteudo, fonte))
        except Exception as erro:
            log.warning("fonte %s falhou: %s", fonte["nome"], erro)
            falhas.append(fonte["nome"])

    return encontrados, falhas
```

- [ ] **Step 5: Rodar o teste e confirmar que passa**

Run: `python -m pytest tests/test_collector.py -v`
Expected: PASS, 7 testes

- [ ] **Step 6: Commit**

```bash
git add newsletter/collector.py tests/test_collector.py tests/fixtures/
git commit -m "feat: coleta de fontes fixas em rss e html"
```

---

### Task 5: `sources.yml` — fontes fixas verificadas de verdade

Esta tarefa tem trabalho de investigação, não só de código. **Nenhuma URL entra no arquivo sem ter sido verificada nesta sessão.**

**Files:**
- Create: `newsletter/sources.yml`, `docs/fontes-avaliadas.md`
- Test: `tests/test_sources.py`

**Interfaces:**
- Consumes: `newsletter.collector.coletar`, `newsletter.collector.buscar_http`, `newsletter.models.CATEGORIAS`
- Produces: `newsletter/sources.yml` válido contra o schema testado, e `newsletter.sources.carregar_fontes(caminho) -> list[dict]` em `newsletter/collector.py`

- [ ] **Step 1: Escrever o teste de schema que falha**

`tests/test_sources.py`:

```python
from pathlib import Path

import yaml

from newsletter.models import CATEGORIAS

SOURCES = Path(__file__).parent.parent / "newsletter" / "sources.yml"

CAMPOS_OBRIGATORIOS = {"nome", "url", "tipo", "categoria", "afirmativa"}


def _fontes():
    return yaml.safe_load(SOURCES.read_text(encoding="utf-8"))


def test_arquivo_existe_e_tem_pelo_menos_quatro_fontes():
    fontes = _fontes()
    assert isinstance(fontes, list)
    assert len(fontes) >= 4, "uma fonte por categoria, no minimo"


def test_toda_fonte_tem_os_campos_obrigatorios():
    for fonte in _fontes():
        faltando = CAMPOS_OBRIGATORIOS - set(fonte)
        assert not faltando, f"{fonte.get('nome')} sem os campos {faltando}"


def test_tipo_e_categoria_sao_validos():
    for fonte in _fontes():
        assert fonte["tipo"] in ("rss", "html"), fonte["nome"]
        assert fonte["categoria"] in CATEGORIAS, fonte["nome"]


def test_fonte_html_declara_seletor():
    for fonte in _fontes():
        if fonte["tipo"] == "html":
            assert fonte.get("seletor"), f"{fonte['nome']} e html e nao tem seletor"


def test_url_e_absoluta_e_https():
    for fonte in _fontes():
        assert fonte["url"].startswith("https://"), fonte["nome"]


def test_toda_categoria_tem_ao_menos_uma_fonte():
    categorias_cobertas = {fonte["categoria"] for fonte in _fontes()}
    assert set(CATEGORIAS) == categorias_cobertas
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `python -m pytest tests/test_sources.py -v`
Expected: FAIL com `FileNotFoundError` em `newsletter/sources.yml`

- [ ] **Step 3: Verificar as fontes candidatas, uma a uma**

Para cada candidata abaixo, execute este script de verificação, ajustando URL e seletor. **Só entra no `sources.yml` a fonte que devolver 3 ou mais itens com título e link.**

```python
# scripts/verificar_fonte.py — script de investigação, não versionado
import sys
from newsletter.collector import buscar_http, coletar

fonte = {
    "nome": sys.argv[1],
    "url": sys.argv[2],
    "tipo": sys.argv[3],          # rss | html
    "categoria": sys.argv[4],
    "afirmativa": False,
}
if fonte["tipo"] == "html":
    fonte["seletor"] = sys.argv[5]

itens, falhas = coletar([fonte], buscar_http)
print(f"falhas: {falhas}")
print(f"itens: {len(itens)}")
for item in itens[:5]:
    print(" -", item.titulo, "|", item.url, "|", item.prazo)
```

Candidatas a testar, por categoria:

| Categoria | Candidatas |
|---|---|
| `estagio` | CIEE, Nube, portais regionais de estágio |
| `trainee` | agregadores de programas de trainee |
| `educacao` | Escola Virtual Gov, Fundação Bradesco, FGV cursos gratuitos, Santander Open Academy |
| `edital` | Fundação Estudar, Fundação Lemann, editais de bolsa |
| afirmativas (marcar `afirmativa: true` em qualquer categoria) | iniciativas de empregabilidade para pessoas negras que mantenham listagem pública e estável |

Registre o resultado de **cada** candidata em `docs/fontes-avaliadas.md`, incluindo as reprovadas e o motivo (não responde, exige JavaScript, não tem listagem estável, bloqueia robô). Esse documento é o que evita retestar as mesmas fontes no futuro.

- [ ] **Step 4: Escrever o `sources.yml` só com as aprovadas**

Formato, com exemplos ilustrativos que devem ser substituídos pelas fontes reais aprovadas no passo anterior:

```yaml
# Fontes fixas da newsletter. Toda fonte aqui foi verificada — veja
# docs/fontes-avaliadas.md para o histórico de avaliação, inclusive as reprovadas.
- nome: Nome do Portal
  url: https://exemplo.org/feed.xml
  tipo: rss
  categoria: estagio
  afirmativa: false

- nome: Outro Portal
  url: https://exemplo.org/cursos
  tipo: html
  categoria: educacao
  seletor: ".card-curso"
  afirmativa: false
```

Se alguma categoria não tiver nenhuma fonte aprovada, **não invente uma**: registre a lacuna em `docs/fontes-avaliadas.md`, remova a categoria de `CATEGORIAS` em `newsletter/models.py` e ajuste `test_toda_categoria_tem_ao_menos_uma_fonte`. Categoria sem fonte fixa continua coberta pelo `discovery`.

- [ ] **Step 5: Acrescentar o carregador de fontes ao collector**

Em `newsletter/collector.py`, ao final do arquivo:

```python
def carregar_fontes(caminho: str | Path = None) -> list[dict]:
    """Lê sources.yml. Sem argumento, usa o arquivo ao lado deste módulo."""
    import yaml

    arquivo = Path(caminho) if caminho else Path(__file__).parent / "sources.yml"
    return yaml.safe_load(arquivo.read_text(encoding="utf-8"))
```

E acrescente `from pathlib import Path` aos imports do módulo.

- [ ] **Step 6: Rodar toda a suíte e confirmar que passa**

Run: `python -m pytest tests/ -v`
Expected: PASS, incluindo os 6 testes de `test_sources.py`

- [ ] **Step 7: Commit**

```bash
git add newsletter/sources.yml newsletter/collector.py tests/test_sources.py docs/fontes-avaliadas.md
git commit -m "feat: fontes fixas verificadas e carregador de sources.yml"
```

---

### Task 6: Discovery — busca pelo Gemini com Google Search

**Files:**
- Create: `newsletter/discovery.py`, `tests/fixtures/resposta_gemini.json`
- Test: `tests/test_discovery.py`

**Interfaces:**
- Consumes: `newsletter.models.Oportunidade`, `newsletter.models.CATEGORIAS`
- Produces:
  - `newsletter.discovery.PROMPT: str`
  - `newsletter.discovery.interpretar(texto_json: str) -> list[Oportunidade]` — converte a resposta do modelo em oportunidades, descartando item inválido
  - `newsletter.discovery.descobrir(chamar_modelo: Callable[[str], str]) -> tuple[list[Oportunidade], list[str]]` — `chamar_modelo` recebe o prompt e devolve o texto da resposta; falha devolve lista vazia e a mensagem de erro
  - `newsletter.discovery.cliente_gemini(api_key: str) -> Callable[[str], str]` — fábrica do chamador real, com grounding de Google Search ativado

- [ ] **Step 1: Criar a fixture da resposta do modelo**

`tests/fixtures/resposta_gemini.json`:

```json
[
  {
    "titulo": "Programa Trainee Afirmativo 2027",
    "url": "https://exemplo.org/trainee-afirmativo",
    "categoria": "trainee",
    "prazo": "2026-09-30",
    "afirmativa": true
  },
  {
    "titulo": "Curso Gratuito de Excel",
    "url": "https://exemplo.org/excel",
    "categoria": "educacao",
    "prazo": null,
    "afirmativa": false
  },
  {
    "titulo": "Oportunidade sem link",
    "url": "",
    "categoria": "estagio",
    "prazo": null,
    "afirmativa": false
  },
  {
    "titulo": "Categoria que nao existe",
    "url": "https://exemplo.org/x",
    "categoria": "vaga_efetiva",
    "prazo": null,
    "afirmativa": false
  },
  {
    "titulo": "Prazo ilegivel",
    "url": "https://exemplo.org/y",
    "categoria": "edital",
    "prazo": "semana que vem",
    "afirmativa": false
  }
]
```

- [ ] **Step 2: Escrever o teste que falha**

`tests/test_discovery.py`:

```python
import datetime
from pathlib import Path

from newsletter.discovery import descobrir, interpretar

FIXTURES = Path(__file__).parent / "fixtures"
RESPOSTA = (FIXTURES / "resposta_gemini.json").read_text(encoding="utf-8")


def test_interpreta_item_valido():
    itens = interpretar(RESPOSTA)
    primeiro = next(i for i in itens if i.categoria == "trainee")
    assert primeiro.titulo == "Programa Trainee Afirmativo 2027"
    assert primeiro.url == "https://exemplo.org/trainee-afirmativo"
    assert primeiro.prazo == datetime.date(2026, 9, 30)
    assert primeiro.afirmativa is True
    assert primeiro.fonte == "Gemini"


def test_descarta_item_sem_url():
    """Item sem URL rastreavel e a principal defesa contra oportunidade inventada."""
    assert all(item.url for item in interpretar(RESPOSTA))
    assert not any(i.titulo == "Oportunidade sem link" for i in interpretar(RESPOSTA))


def test_descarta_categoria_desconhecida():
    assert not any(i.titulo == "Categoria que nao existe" for i in interpretar(RESPOSTA))


def test_prazo_ilegivel_vira_nulo_sem_descartar_o_item():
    item = next(i for i in interpretar(RESPOSTA) if i.titulo == "Prazo ilegivel")
    assert item.prazo is None


def test_resposta_com_cerca_de_markdown_e_aceita():
    texto = '```json\n[{"titulo":"A","url":"https://a.org","categoria":"trainee","prazo":null,"afirmativa":false}]\n```'
    assert len(interpretar(texto)) == 1


def test_resposta_invalida_devolve_lista_vazia():
    assert interpretar("desculpe, nao encontrei nada") == []


def test_descobrir_devolve_itens_e_nenhum_erro():
    itens, erros = descobrir(lambda prompt: RESPOSTA)
    assert erros == []
    assert len(itens) == 3


def test_descobrir_captura_falha_do_modelo():
    def explode(prompt):
        raise RuntimeError("cota esgotada")

    itens, erros = descobrir(explode)
    assert itens == []
    assert erros == ["cota esgotada"]


def test_prompt_pede_url_de_origem_e_json():
    from newsletter.discovery import PROMPT

    assert "URL" in PROMPT
    assert "JSON" in PROMPT
```

- [ ] **Step 3: Rodar o teste e confirmar que falha**

Run: `python -m pytest tests/test_discovery.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'newsletter.discovery'`

- [ ] **Step 4: Implementar o mínimo**

`newsletter/discovery.py`:

```python
"""Descoberta de oportunidades pelo Gemini com grounding de Google Search."""

import datetime
import json
import logging
import re
from collections.abc import Callable

from newsletter.models import CATEGORIAS, Oportunidade

log = logging.getLogger(__name__)

MODELO = "gemini-2.5-flash"

PROMPT = """Você pesquisa oportunidades para o Clube dos Libertos, uma rede de
profissionais e estudantes negros no Brasil.

Busque na web oportunidades com INSCRIÇÕES ABERTAS HOJE nestas categorias:
- trainee: programas de trainee
- estagio: programas de estágio
- edital: editais, bolsas e chamadas públicas
- educacao: cursos e programas de formação gratuitos

Priorize oportunidades afirmativas para pessoas negras, e oportunidades
nacionais ou remotas.

Responda SOMENTE com um array JSON, sem texto em volta. Cada item:
{"titulo": str, "url": str, "categoria": str, "prazo": "AAAA-MM-DD" ou null,
 "afirmativa": bool}

A URL é obrigatória e precisa ser a página real da oportunidade, obtida na
busca. Se você não tem a URL de origem, NÃO inclua o item.
"""


def cliente_gemini(api_key: str) -> Callable[[str], str]:
    """Cria o chamador real do Gemini, com Google Search ligado."""
    from google import genai
    from google.genai import types

    cliente = genai.Client(api_key=api_key)

    def chamar(prompt: str) -> str:
        resposta = cliente.models.generate_content(
            model=MODELO,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            ),
        )
        return resposta.text

    return chamar


def _sem_cerca(texto: str) -> str:
    """Remove a cerca de markdown que o modelo às vezes acrescenta."""
    return re.sub(r"^```(?:json)?|```$", "", texto.strip(), flags=re.MULTILINE).strip()


def _data(valor) -> datetime.date | None:
    if not valor:
        return None
    try:
        return datetime.date.fromisoformat(str(valor))
    except ValueError:
        return None


def interpretar(texto: str) -> list[Oportunidade]:
    """Converte a resposta do modelo em oportunidades, descartando o inválido."""
    try:
        dados = json.loads(_sem_cerca(texto))
    except json.JSONDecodeError:
        log.warning("resposta do modelo nao e JSON valido")
        return []

    if not isinstance(dados, list):
        return []

    itens = []
    for bruto in dados:
        if not isinstance(bruto, dict):
            continue
        url = (bruto.get("url") or "").strip()
        categoria = bruto.get("categoria")
        if not url or categoria not in CATEGORIAS:
            continue
        itens.append(
            Oportunidade(
                titulo=(bruto.get("titulo") or "").strip(),
                url=url,
                categoria=categoria,
                fonte="Gemini",
                prazo=_data(bruto.get("prazo")),
                afirmativa=bool(bruto.get("afirmativa")),
            )
        )
    return itens


def descobrir(
    chamar_modelo: Callable[[str], str],
) -> tuple[list[Oportunidade], list[str]]:
    """Consulta o modelo. Falha não propaga — devolve lista vazia e o erro."""
    try:
        return interpretar(chamar_modelo(PROMPT)), []
    except Exception as erro:
        log.warning("discovery falhou: %s", erro)
        return [], [str(erro)]
```

- [ ] **Step 5: Rodar o teste e confirmar que passa**

Run: `python -m pytest tests/test_discovery.py -v`
Expected: PASS, 9 testes

- [ ] **Step 6: Commit**

```bash
git add newsletter/discovery.py tests/test_discovery.py tests/fixtures/resposta_gemini.json
git commit -m "feat: descoberta de oportunidades via gemini com google search"
```

---

### Task 7: Writer — abertura e resumos

**Files:**
- Create: `newsletter/writer.py`
- Test: `tests/test_writer.py`

**Interfaces:**
- Consumes: `newsletter.models.Oportunidade`
- Produces:
  - `newsletter.writer.ABERTURA_PADRAO: str`
  - `newsletter.writer.escrever(blocos: dict[str, list[Oportunidade]], chamar_modelo) -> tuple[str, dict[str, list[Oportunidade]]]` — devolve a abertura e os blocos com `resumo` preenchido; falha do modelo devolve `ABERTURA_PADRAO` e os blocos intactos

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_writer.py`:

```python
import json

from newsletter.models import Oportunidade
from newsletter.writer import ABERTURA_PADRAO, escrever


def _op(titulo, url):
    return Oportunidade(
        titulo=titulo,
        url=url,
        categoria="trainee",
        fonte="Exemplo",
        prazo=None,
        afirmativa=False,
    )


BLOCOS = {
    "Trainees e estágios": [_op("Trainee Alfa", "https://exemplo.org/a")],
    "Editais e formações": [_op("Curso Beta", "https://exemplo.org/b")],
}


def _modelo_ok(prompt):
    return json.dumps(
        {
            "abertura": "Boa semana, Libertos!",
            "resumos": {
                "https://exemplo.org/a": "Programa para quem esta comecando.",
                "https://exemplo.org/b": "Curso gratuito e online.",
            },
        },
        ensure_ascii=False,
    )


def test_preenche_abertura_e_resumos():
    abertura, blocos = escrever(BLOCOS, _modelo_ok)
    assert abertura == "Boa semana, Libertos!"
    assert blocos["Trainees e estágios"][0].resumo == "Programa para quem esta comecando."
    assert blocos["Editais e formações"][0].resumo == "Curso gratuito e online."


def test_nao_altera_titulo_nem_url():
    _, blocos = escrever(BLOCOS, _modelo_ok)
    item = blocos["Trainees e estágios"][0]
    assert item.titulo == "Trainee Alfa"
    assert item.url == "https://exemplo.org/a"


def test_falha_do_modelo_usa_abertura_padrao_e_mantem_os_itens():
    def explode(prompt):
        raise RuntimeError("cota esgotada")

    abertura, blocos = escrever(BLOCOS, explode)
    assert abertura == ABERTURA_PADRAO
    assert blocos["Trainees e estágios"][0].titulo == "Trainee Alfa"
    assert blocos["Trainees e estágios"][0].resumo == ""


def test_resumo_ausente_para_um_item_nao_quebra_os_outros():
    def parcial(prompt):
        return json.dumps(
            {"abertura": "Oi", "resumos": {"https://exemplo.org/a": "Tem resumo."}}
        )

    _, blocos = escrever(BLOCOS, parcial)
    assert blocos["Trainees e estágios"][0].resumo == "Tem resumo."
    assert blocos["Editais e formações"][0].resumo == ""


def test_prompt_recebe_os_titulos_dos_itens_curados():
    recebidos = []

    def espiao(prompt):
        recebidos.append(prompt)
        return _modelo_ok(prompt)

    escrever(BLOCOS, espiao)
    assert "Trainee Alfa" in recebidos[0]
    assert "Curso Beta" in recebidos[0]
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `python -m pytest tests/test_writer.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'newsletter.writer'`

- [ ] **Step 3: Implementar o mínimo**

`newsletter/writer.py`:

```python
"""Redação da edição: abertura e resumo de cada item.

A IA redige, não decide o que entra — recebe apenas itens já curados.
"""

import dataclasses
import json
import logging
import re
from collections.abc import Callable

from newsletter.models import Oportunidade

log = logging.getLogger(__name__)

ABERTURA_PADRAO = (
    "Boa semana, Libertos! Seguem as oportunidades que encontramos para vocês."
)

_MODELO_PROMPT = """Você escreve a newsletter semanal do Clube dos Libertos, uma
rede de profissionais e estudantes negros no Brasil. O tom é acolhedor, direto e
sem jargão corporativo.

Escreva:
1. Uma abertura de no máximo 2 frases, sobre o conjunto das oportunidades desta semana.
2. Um resumo de 2 a 3 linhas para cada oportunidade, dizendo para quem serve e o
   que a pessoa ganha. Não repita o título e não invente informação que não está aqui.

Oportunidades desta semana:
{itens}

Responda SOMENTE com JSON, sem texto em volta:
{{"abertura": str, "resumos": {{"<url>": "<resumo>"}}}}
"""


def _sem_cerca(texto: str) -> str:
    return re.sub(r"^```(?:json)?|```$", "", texto.strip(), flags=re.MULTILINE).strip()


def _descrever(blocos: dict[str, list[Oportunidade]]) -> str:
    linhas = []
    for bloco, itens in blocos.items():
        for op in itens:
            marca = " [afirmativa]" if op.afirmativa else ""
            linhas.append(f"- [{bloco}]{marca} {op.titulo} — {op.url}")
    return "\n".join(linhas)


def escrever(
    blocos: dict[str, list[Oportunidade]],
    chamar_modelo: Callable[[str], str],
) -> tuple[str, dict[str, list[Oportunidade]]]:
    """Devolve a abertura e os blocos com resumo preenchido.

    Se o modelo falhar, a edição sai com a abertura padrão e sem resumo — melhor
    uma edição enxuta que nenhuma edição.
    """
    prompt = _MODELO_PROMPT.format(itens=_descrever(blocos))

    try:
        dados = json.loads(_sem_cerca(chamar_modelo(prompt)))
        abertura = (dados.get("abertura") or "").strip() or ABERTURA_PADRAO
        resumos = dados.get("resumos") or {}
    except Exception as erro:
        log.warning("writer falhou, usando abertura padrao: %s", erro)
        return ABERTURA_PADRAO, blocos

    preenchidos = {
        bloco: [
            dataclasses.replace(op, resumo=(resumos.get(op.url) or "").strip())
            for op in itens
        ]
        for bloco, itens in blocos.items()
    }
    return abertura, preenchidos
```

- [ ] **Step 4: Rodar o teste e confirmar que passa**

Run: `python -m pytest tests/test_writer.py -v`
Expected: PASS, 5 testes

- [ ] **Step 5: Commit**

```bash
git add newsletter/writer.py tests/test_writer.py
git commit -m "feat: redacao de abertura e resumos com fallback"
```

---

### Task 8: Renderer — HTML do email na identidade do Clube

**Files:**
- Create: `newsletter/renderer.py`, `newsletter/templates/edicao.html.j2`, `newsletter/assets/logo.png`
- Test: `tests/test_renderer.py`

**Interfaces:**
- Consumes: `newsletter.models.Oportunidade`, todo o `newsletter.config`
- Produces: `newsletter.renderer.renderizar(abertura: str, blocos: dict[str, list[Oportunidade]], semana: str) -> str`

- [ ] **Step 1: Baixar o logo do Drive para o repositório**

A identidade visual do Clube está no Drive, na pasta `Identidade Visual`. Para o cabeçalho, use a versão **branco com símbolo amarelo**, que é a que contrasta com o fundo roxo `#5C1A88` (id do arquivo no Drive: `1GdVlroZY6WODGxS2CW8ov5alMYNQJ5c-`).

```bash
mkdir -p newsletter/assets
```

Baixe o arquivo do Drive para `newsletter/assets/logo.png` — pelo navegador, ou por script com uma credencial que tenha leitura na pasta. O arquivo tem cerca de 8 KB.

Verifique antes de seguir:

```bash
python -c "print(open('newsletter/assets/logo.png','rb').read(8))"
```
Expected: `b'\x89PNG\r\n\x1a\n'` (assinatura de PNG — se vier HTML, o download trouxe uma página de erro)

- [ ] **Step 2: Escrever o teste que falha**

`tests/test_renderer.py`:

```python
import datetime
import re

from newsletter import config
from newsletter.models import Oportunidade
from newsletter.renderer import renderizar


def _op(titulo, url, resumo="", afirmativa=False, prazo=None):
    return Oportunidade(
        titulo=titulo,
        url=url,
        categoria="trainee",
        fonte="Portal Exemplo",
        prazo=prazo,
        afirmativa=afirmativa,
        resumo=resumo,
    )


BLOCOS = {
    "Trainees e estágios": [
        _op(
            "Trainee Alfa",
            "https://exemplo.org/a",
            resumo="Para quem esta comecando.",
            afirmativa=True,
            prazo=datetime.date(2026, 9, 30),
        )
    ],
    "Editais e formações": [],
}


def _html():
    return renderizar("Boa semana!", BLOCOS, "W36")


def test_inclui_abertura_titulo_e_link():
    html = _html()
    assert "Boa semana!" in html
    assert "Trainee Alfa" in html
    assert "https://exemplo.org/a" in html
    assert "Para quem esta comecando." in html


def test_usa_a_paleta_da_marca():
    html = _html()
    assert config.ROXO in html
    assert config.AMARELO in html


def test_inclui_cta_da_base_de_talentos_e_redes_sociais():
    html = _html()
    assert config.FORM_BASE_TALENTOS_URL in html
    assert config.INSTAGRAM_URL in html
    assert config.LINKEDIN_URL in html


def test_marca_oportunidade_afirmativa():
    assert "afirmativa" in _html().lower()


def test_mostra_prazo_quando_existe():
    assert "30/09/2026" in _html()


def test_bloco_vazio_nao_aparece_com_titulo_solto():
    html = _html()
    assert "Editais e formações" not in html


def test_inclui_marcadores_dos_blocos_manuais():
    html = _html()
    assert "Vagas da semana" in html
    assert "Espaço do Clube" in html
    assert "preencha ou apague" in html.lower()


def test_toda_imagem_tem_texto_alternativo():
    html = _html()
    for tag in re.findall(r"<img[^>]*>", html):
        assert "alt=" in tag, tag


def test_largura_fixa_de_600px_para_leitura_no_celular():
    assert "600px" in _html()


def test_nao_usa_folha_de_estilo_externa():
    """Cliente de email nao carrega CSS externo: tudo tem que ser inline."""
    html = _html()
    assert "<link" not in html
    assert "@import" not in html
```

- [ ] **Step 3: Rodar o teste e confirmar que falha**

Run: `python -m pytest tests/test_renderer.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'newsletter.renderer'`

- [ ] **Step 4: Escrever o template**

`newsletter/templates/edicao.html.j2`:

```jinja
<div style="margin:0;padding:0;background-color:#f4f2f7;font-family:Luciole,Verdana,Geneva,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f2f7;">
    <tr>
      <td align="center" style="padding:24px 12px;">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="width:600px;max-width:600px;background-color:#ffffff;">

          <tr>
            <td align="center" style="background-color:{{ roxo }};padding:28px 24px;">
              <img src="{{ logo_url }}" width="220" alt="Clube dos Libertos" style="display:block;width:220px;max-width:80%;height:auto;">
              <p style="margin:16px 0 0;color:{{ amarelo }};font-size:13px;letter-spacing:2px;text-transform:uppercase;">
                Black Network &middot; Semana {{ semana }}
              </p>
            </td>
          </tr>

          <tr>
            <td style="padding:28px 24px 8px;">
              <p style="margin:0;color:{{ preto }};font-size:16px;line-height:1.6;">{{ abertura }}</p>
            </td>
          </tr>

          <tr>
            <td style="padding:8px 24px;">
              <div style="border:2px dashed {{ amarelo }};padding:14px;">
                <p style="margin:0 0 4px;color:{{ marrom }};font-size:15px;font-weight:bold;">Vagas da semana</p>
                <p style="margin:0;color:{{ marrom }};font-size:13px;">
                  Bloco manual &mdash; preencha ou apague este bloco antes de enviar.
                </p>
              </div>
            </td>
          </tr>

          {% for bloco, itens in blocos.items() %}
          {% if itens %}
          <tr>
            <td style="padding:20px 24px 4px;">
              <h2 style="margin:0;color:{{ roxo }};font-size:19px;border-bottom:3px solid {{ amarelo }};padding-bottom:6px;">
                {{ bloco }}
              </h2>
            </td>
          </tr>
          {% for item in itens %}
          <tr>
            <td style="padding:14px 24px;">
              <p style="margin:0 0 4px;">
                <a href="{{ item.url }}" style="color:{{ roxo }};font-size:17px;font-weight:bold;text-decoration:none;">{{ item.titulo }}</a>
              </p>
              {% if item.afirmativa %}
              <p style="margin:0 0 6px;">
                <span style="background-color:{{ amarelo }};color:{{ preto }};font-size:11px;font-weight:bold;padding:3px 8px;text-transform:uppercase;">Vaga afirmativa</span>
              </p>
              {% endif %}
              {% if item.resumo %}
              <p style="margin:0 0 6px;color:{{ preto }};font-size:15px;line-height:1.6;">{{ item.resumo }}</p>
              {% endif %}
              <p style="margin:0;color:{{ marrom }};font-size:13px;">
                {{ item.fonte }}{% if item.prazo %} &middot; inscrições até {{ item.prazo.strftime('%d/%m/%Y') }}{% endif %}
              </p>
            </td>
          </tr>
          {% endfor %}
          {% endif %}
          {% endfor %}

          <tr>
            <td style="padding:20px 24px;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:{{ roxo }};">
                <tr>
                  <td align="center" style="padding:24px 20px;">
                    <p style="margin:0 0 6px;color:#ffffff;font-size:18px;font-weight:bold;">Núcleo Ubuntu &mdash; Base de Talentos</p>
                    <p style="margin:0 0 16px;color:#ffffff;font-size:14px;line-height:1.6;">
                      Cadastre seu perfil para receber indicações e aparecer para as organizações parceiras do Clube.
                    </p>
                    <a href="{{ form_url }}" style="background-color:{{ amarelo }};color:{{ preto }};font-size:15px;font-weight:bold;padding:12px 26px;text-decoration:none;display:inline-block;">
                      Quero me cadastrar
                    </a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <tr>
            <td style="padding:8px 24px 20px;">
              <div style="border:2px dashed {{ amarelo }};padding:14px;">
                <p style="margin:0 0 4px;color:{{ marrom }};font-size:15px;font-weight:bold;">Espaço do Clube</p>
                <p style="margin:0;color:{{ marrom }};font-size:13px;">
                  Bloco manual &mdash; recado, evento ou conquista de membro. Preencha ou apague este bloco antes de enviar.
                </p>
              </div>
            </td>
          </tr>

          <tr>
            <td align="center" style="background-color:{{ preto }};padding:22px 24px;">
              <p style="margin:0 0 10px;">
                <a href="{{ instagram_url }}" style="color:{{ amarelo }};font-size:14px;text-decoration:none;">Instagram</a>
                <span style="color:#ffffff;">&nbsp;&middot;&nbsp;</span>
                <a href="{{ linkedin_url }}" style="color:{{ amarelo }};font-size:14px;text-decoration:none;">LinkedIn</a>
              </p>
              <p style="margin:0;color:#cccccc;font-size:12px;line-height:1.6;">
                Clube dos Libertos &mdash; Black Network<br>
                Você recebe este email porque faz parte da comunidade.<br>
                <a href="{{ unsubscribe }}" style="color:#cccccc;text-decoration:underline;">Descadastrar</a>
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</div>
```

- [ ] **Step 5: Implementar o renderer**

`newsletter/renderer.py`:

```python
"""Renderização do HTML da edição.

CSS é inline por exigência de cliente de email: nada de folha externa nem
@import, que Gmail e Outlook descartam.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from newsletter import config
from newsletter.models import Oportunidade

TEMPLATES = Path(__file__).parent / "templates"

# Tag que o Brevo troca pelo link real de descadastro no momento do envio.
UNSUBSCRIBE_BREVO = "{{ unsubscribe }}"


def renderizar(
    abertura: str, blocos: dict[str, list[Oportunidade]], semana: str
) -> str:
    """Monta o HTML completo da edição."""
    ambiente = Environment(
        loader=FileSystemLoader(TEMPLATES),
        autoescape=select_autoescape(["html", "j2"]),
    )
    template = ambiente.get_template("edicao.html.j2")
    return template.render(
        abertura=abertura,
        blocos=blocos,
        semana=semana,
        logo_url=config.LOGO_URL,
        form_url=config.FORM_BASE_TALENTOS_URL,
        instagram_url=config.INSTAGRAM_URL,
        linkedin_url=config.LINKEDIN_URL,
        roxo=config.ROXO,
        amarelo=config.AMARELO,
        marrom=config.MARROM,
        preto=config.PRETO,
        unsubscribe=UNSUBSCRIBE_BREVO,
    )
```

- [ ] **Step 6: Rodar o teste e confirmar que passa**

Run: `python -m pytest tests/test_renderer.py -v`
Expected: PASS, 10 testes

- [ ] **Step 7: Olhar o HTML com os próprios olhos**

Teste automatizado não julga estética. Gere uma amostra e abra no navegador:

```bash
python -c "
import datetime
from newsletter.models import Oportunidade
from newsletter.renderer import renderizar
op = lambda t, u, r, a=False: Oportunidade(titulo=t, url=u, categoria='trainee', fonte='Portal Exemplo', prazo=datetime.date(2026,9,30), afirmativa=a, resumo=r)
blocos = {
  'Trainees e estágios': [op('Programa Trainee Afirmativo 2027','https://exemplo.org/a','Para pessoas negras em inicio de carreira, com atuacao remota.',True), op('Estagio em Tecnologia','https://exemplo.org/b','Vagas em Fortaleza e Salvador, para quem cursa a partir do terceiro semestre.')],
  'Editais e formações': [op('Curso Gratuito de Dados','https://exemplo.org/c','Formacao online de 40 horas, com certificado.')],
}
open('amostra.html','w',encoding='utf-8').write(renderizar('Boa semana, Libertos! Tres oportunidades boas nesta edicao.', blocos, 'W36'))
print('amostra.html gerado')
"
```

Abra `amostra.html` no navegador e confira: logo visível sobre o roxo, hierarquia legível, selo de vaga afirmativa destacado, blocos manuais evidentes, botão da Base de Talentos com contraste. Ajuste o template se algo estiver feio, e rode os testes de novo. Não commite `amostra.html` (já está coberto pelo `.gitignore` se você gerar dentro de `saida/`; caso contrário, apague).

- [ ] **Step 8: Commit**

```bash
git add newsletter/renderer.py newsletter/templates/ newsletter/assets/logo.png tests/test_renderer.py
git commit -m "feat: html da edicao na identidade visual do clube"
```

---

### Task 9: Publisher e notifier — Brevo

Usamos a API REST do Brevo direto com `requests`, sem SDK: são dois endpoints, e a dependência a menos vale mais que o açúcar sintático.

**Files:**
- Create: `newsletter/publisher.py`, `newsletter/notifier.py`
- Test: `tests/test_publisher.py`

**Interfaces:**
- Consumes: `newsletter.config.REMETENTE_EMAIL`, `newsletter.config.REMETENTE_NOME`
- Produces:
  - `newsletter.publisher.criar_rascunho(html: str, assunto: str, lista_id: int, api_key: str, poster=None) -> int` — devolve o id da campanha criada; `poster` é injetável para teste
  - `newsletter.publisher.URL_CAMPANHA: str` — molde do link do painel, formatado com o id
  - `newsletter.notifier.avisar(assunto: str, corpo: str, api_key: str, poster=None) -> None`

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_publisher.py`:

```python
import pytest

from newsletter.notifier import avisar
from newsletter.publisher import criar_rascunho


class PosterFalso:
    """Substitui a chamada HTTP e guarda o que foi enviado."""

    def __init__(self, resposta=None, erro=None):
        self.resposta = resposta or {"id": 4242}
        self.erro = erro
        self.chamadas = []

    def __call__(self, url, cabecalhos, corpo):
        self.chamadas.append({"url": url, "cabecalhos": cabecalhos, "corpo": corpo})
        if self.erro:
            raise self.erro
        return self.resposta


def test_cria_campanha_e_devolve_o_id():
    poster = PosterFalso()
    assert criar_rascunho("<p>oi</p>", "Assunto", 7, "chave-x", poster) == 4242


def test_campanha_nasce_como_rascunho_e_nunca_agendada():
    """O publisher jamais dispara envio: quem envia e a pessoa que revisa."""
    poster = PosterFalso()
    criar_rascunho("<p>oi</p>", "Assunto", 7, "chave-x", poster)
    corpo = poster.chamadas[0]["corpo"]
    assert "scheduledAt" not in corpo
    assert corpo.get("inlineImageActivation") is not True


def test_envia_html_assunto_lista_e_remetente():
    poster = PosterFalso()
    criar_rascunho("<p>oi</p>", "Assunto", 7, "chave-x", poster)
    corpo = poster.chamadas[0]["corpo"]
    assert corpo["htmlContent"] == "<p>oi</p>"
    assert corpo["subject"] == "Assunto"
    assert corpo["recipients"] == {"listIds": [7]}
    assert corpo["sender"]["email"] == "clubedoslibertos@gmail.com"


def test_manda_a_chave_no_cabecalho_e_nao_no_corpo():
    poster = PosterFalso()
    criar_rascunho("<p>oi</p>", "Assunto", 7, "chave-x", poster)
    chamada = poster.chamadas[0]
    assert chamada["cabecalhos"]["api-key"] == "chave-x"
    assert "chave-x" not in str(chamada["corpo"])


def test_falha_do_brevo_propaga_para_quem_chamou():
    """Aqui a falha NAO e silenciada: o main precisa salvar o html e avisar."""
    poster = PosterFalso(erro=RuntimeError("500 do Brevo"))
    with pytest.raises(RuntimeError, match="500 do Brevo"):
        criar_rascunho("<p>oi</p>", "Assunto", 7, "chave-x", poster)


def test_aviso_vai_para_o_email_do_clube():
    poster = PosterFalso(resposta={"messageId": "abc"})
    avisar("Rascunho pronto", "3 itens nesta edicao.", "chave-x", poster)
    corpo = poster.chamadas[0]["corpo"]
    assert corpo["to"] == [{"email": "clubedoslibertos@gmail.com"}]
    assert corpo["subject"] == "Rascunho pronto"
    assert "3 itens nesta edicao." in corpo["htmlContent"]


def test_falha_do_aviso_nao_propaga():
    """Nao dar para avisar e ruim, mas nao pode derrubar uma execucao que deu certo."""
    poster = PosterFalso(erro=RuntimeError("sem rede"))
    avisar("Assunto", "Corpo", "chave-x", poster)  # nao levanta
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `python -m pytest tests/test_publisher.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'newsletter.notifier'`

- [ ] **Step 3: Implementar o mínimo**

`newsletter/publisher.py`:

```python
"""Criação da campanha em rascunho no Brevo. Nunca dispara envio."""

import logging

import requests

from newsletter.config import REMETENTE_EMAIL, REMETENTE_NOME

log = logging.getLogger(__name__)

API_CAMPANHAS = "https://api.brevo.com/v3/emailCampaigns"
URL_CAMPANHA = "https://app.brevo.com/campaign/classic/edit/{id}"
TIMEOUT = 30


def _postar(url: str, cabecalhos: dict, corpo: dict) -> dict:
    resposta = requests.post(url, headers=cabecalhos, json=corpo, timeout=TIMEOUT)
    resposta.raise_for_status()
    return resposta.json() if resposta.content else {}


def criar_rascunho(
    html: str,
    assunto: str,
    lista_id: int,
    api_key: str,
    poster=None,
) -> int:
    """Cria a campanha como rascunho e devolve o id.

    Falha propaga de propósito: quem orquestra precisa salvar o HTML e avisar,
    em vez de perder a edição em silêncio.
    """
    postar = poster or _postar
    corpo = {
        "name": assunto,
        "subject": assunto,
        "sender": {"name": REMETENTE_NOME, "email": REMETENTE_EMAIL},
        "htmlContent": html,
        "recipients": {"listIds": [lista_id]},
    }
    resposta = postar(API_CAMPANHAS, {"api-key": api_key, "accept": "application/json"}, corpo)
    campanha_id = resposta["id"]
    log.info("campanha rascunho criada: %s", URL_CAMPANHA.format(id=campanha_id))
    return campanha_id
```

`newsletter/notifier.py`:

```python
"""Aviso de execução por email transacional do Brevo.

Mesmo canal para sucesso e para falha, de modo que silêncio signifique sempre
"o job não rodou".
"""

import logging

from newsletter.config import REMETENTE_EMAIL, REMETENTE_NOME
from newsletter.publisher import _postar

log = logging.getLogger(__name__)

API_TRANSACIONAL = "https://api.brevo.com/v3/smtp/email"


def avisar(assunto: str, corpo: str, api_key: str, poster=None) -> None:
    """Envia o aviso. Falhar em avisar não derruba a execução."""
    postar = poster or _postar
    try:
        postar(
            API_TRANSACIONAL,
            {"api-key": api_key, "accept": "application/json"},
            {
                "sender": {"name": REMETENTE_NOME, "email": REMETENTE_EMAIL},
                "to": [{"email": REMETENTE_EMAIL}],
                "subject": assunto,
                "htmlContent": f"<pre style='font-family:monospace'>{corpo}</pre>",
            },
        )
    except Exception as erro:
        log.warning("nao foi possivel enviar o aviso: %s", erro)
```

- [ ] **Step 4: Rodar o teste e confirmar que passa**

Run: `python -m pytest tests/test_publisher.py -v`
Expected: PASS, 7 testes

- [ ] **Step 5: Commit**

```bash
git add newsletter/publisher.py newsletter/notifier.py tests/test_publisher.py
git commit -m "feat: campanha rascunho no brevo e aviso de execucao"
```

---

### Task 10: Main — orquestração e política de falha

**Files:**
- Create: `newsletter/main.py`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: todos os módulos anteriores
- Produces:
  - `newsletter.main.semana_iso(hoje: datetime.date) -> str` — devolve `"W36"`
  - `newsletter.main.montar_assunto(blocos, semana) -> str`
  - `newsletter.main.EdicaoVazia` — exceção
  - `newsletter.main.executar(dependencias: dict) -> dict` — orquestra tudo e devolve o relatório da execução
  - `newsletter.main.main() -> int` — monta as dependências reais a partir do ambiente e chama `executar`

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_main.py`:

```python
import datetime
import json

import pytest

from newsletter.main import EdicaoVazia, executar, montar_assunto, semana_iso
from newsletter.models import Oportunidade

HOJE = datetime.date(2026, 8, 31)


def _op(titulo, url, categoria="trainee"):
    return Oportunidade(
        titulo=titulo,
        url=url,
        categoria=categoria,
        fonte="Exemplo",
        prazo=None,
        afirmativa=False,
    )


def _deps(tmp_path, **sobrescritas):
    avisos = []
    base = {
        "hoje": HOJE,
        "caminho_historico": tmp_path / "history.json",
        "coletar": lambda: ([_op("Trainee Alfa", "https://exemplo.org/a")], []),
        "descobrir": lambda: ([_op("Curso Beta", "https://exemplo.org/b", "educacao")], []),
        "verificar_link": lambda url: True,
        "escrever": lambda blocos: ("Boa semana!", blocos),
        "publicar": lambda html, assunto: 4242,
        "avisar": lambda assunto, corpo: avisos.append((assunto, corpo)),
        "salvar_html": lambda html: None,
    }
    base.update(sobrescritas)
    return base, avisos


def test_semana_iso_usa_o_padrao_do_obsidian():
    assert semana_iso(datetime.date(2026, 8, 31)) == "W36"


def test_assunto_cita_a_semana_e_a_quantidade():
    blocos = {"Trainees e estágios": [_op("A", "https://a.org")], "Editais e formações": []}
    assunto = montar_assunto(blocos, "W36")
    assert "W36" in assunto
    assert "1" in assunto


def test_execucao_feliz_publica_e_registra_historico(tmp_path):
    deps, avisos = _deps(tmp_path)
    relatorio = executar(deps)

    assert relatorio["campanha_id"] == 4242
    assert relatorio["total"] == 2
    dados = json.loads((tmp_path / "history.json").read_text(encoding="utf-8"))
    assert len(dados["itens"]) == 2
    assert len(avisos) == 1


def test_falha_das_fontes_fixas_segue_com_o_discovery(tmp_path):
    deps, _ = _deps(tmp_path, coletar=lambda: ([], ["Fonte Morta"]))
    relatorio = executar(deps)
    assert relatorio["total"] == 1
    assert relatorio["fontes_com_falha"] == ["Fonte Morta"]


def test_falha_do_gemini_segue_com_as_fontes_fixas(tmp_path):
    deps, _ = _deps(tmp_path, descobrir=lambda: ([], ["cota esgotada"]))
    relatorio = executar(deps)
    assert relatorio["total"] == 1
    assert relatorio["erros_discovery"] == ["cota esgotada"]


def test_zero_itens_aborta_sem_publicar(tmp_path):
    publicou = []
    deps, avisos = _deps(
        tmp_path,
        coletar=lambda: ([], []),
        descobrir=lambda: ([], []),
        publicar=lambda html, assunto: publicou.append(True),
    )
    with pytest.raises(EdicaoVazia):
        executar(deps)
    assert publicou == []
    assert len(avisos) == 1, "falha tambem precisa avisar"


def test_historico_nao_e_gravado_quando_a_publicacao_falha(tmp_path):
    """Gravar historico antes de publicar sumiria com a oportunidade na semana seguinte."""

    def explode(html, assunto):
        raise RuntimeError("500 do Brevo")

    deps, avisos = _deps(tmp_path, publicar=explode)
    with pytest.raises(RuntimeError):
        executar(deps)
    assert not (tmp_path / "history.json").exists()
    assert len(avisos) == 1


def test_html_e_salvo_quando_o_brevo_falha(tmp_path):
    salvos = []

    def explode(html, assunto):
        raise RuntimeError("500 do Brevo")

    deps, _ = _deps(
        tmp_path, publicar=explode, salvar_html=lambda html: salvos.append(html)
    )
    with pytest.raises(RuntimeError):
        executar(deps)
    assert len(salvos) == 1
    assert "Boa semana!" in salvos[0]


def test_item_ja_publicado_nao_volta(tmp_path):
    """Rodar duas vezes na mesma semana nao republica nada: tudo ja esta no historico,
    logo a segunda execucao aborta como edicao vazia."""
    deps, _ = _deps(tmp_path)
    executar(deps)
    with pytest.raises(EdicaoVazia):
        executar(deps)
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `python -m pytest tests/test_main.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'newsletter.main'`

- [ ] **Step 3: Implementar o mínimo**

`newsletter/main.py`:

```python
"""Orquestração do pipeline semanal.

Toda dependência externa entra pelo dicionário `dependencias`, o que deixa o
fluxo inteiro testável sem rede.
"""

import datetime
import logging
import os
import sys
from pathlib import Path

import requests

from newsletter import collector, curator, discovery, history, notifier, publisher, renderer, writer

log = logging.getLogger(__name__)

RAIZ = Path(__file__).parent.parent
CAMINHO_HISTORICO = RAIZ / "history.json"
CAMINHO_SAIDA = RAIZ / "saida" / "edicao.html"


class EdicaoVazia(Exception):
    """Nenhum item sobrou após a curadoria — não se cria rascunho vazio."""


def semana_iso(hoje: datetime.date) -> str:
    return f"W{hoje.isocalendar().week:02d}"


def montar_assunto(blocos: dict, semana: str) -> str:
    total = sum(len(itens) for itens in blocos.values())
    return f"Oportunidades da semana {semana} — {total} para você conferir"


def _verificar_link(url: str) -> bool:
    """Link vivo responde. HEAD primeiro; alguns servidores só aceitam GET."""
    try:
        resposta = requests.head(url, timeout=15, allow_redirects=True)
        if resposta.status_code >= 400:
            resposta = requests.get(url, timeout=15, allow_redirects=True)
        return resposta.status_code < 400
    except Exception:
        return False


def executar(dependencias: dict) -> dict:
    """Roda o pipeline. Devolve o relatório da execução."""
    hoje = dependencias["hoje"]
    caminho_historico = dependencias["caminho_historico"]
    avisar = dependencias["avisar"]
    semana = semana_iso(hoje)

    fixas, fontes_com_falha = dependencias["coletar"]()
    achadas, erros_discovery = dependencias["descobrir"]()
    log.info("coletadas %d das fontes fixas, %d do discovery", len(fixas), len(achadas))

    blocos = curator.curar(
        [*fixas, *achadas],
        history.carregar(caminho_historico),
        hoje,
        dependencias["verificar_link"],
    )
    total = sum(len(itens) for itens in blocos.values())

    relatorio = {
        "semana": semana,
        "total": total,
        "por_bloco": {bloco: len(itens) for bloco, itens in blocos.items()},
        "fontes_com_falha": fontes_com_falha,
        "erros_discovery": erros_discovery,
    }

    if total == 0:
        relatorio["abortou"] = True
        avisar(
            f"[Newsletter {semana}] nenhuma oportunidade nova",
            f"Nada sobrou apos a curadoria.\n\n{relatorio}",
        )
        raise EdicaoVazia(f"semana {semana} sem itens")

    abertura, blocos = dependencias["escrever"](blocos)
    html = renderer.renderizar(abertura, blocos, semana)
    assunto = montar_assunto(blocos, semana)

    try:
        campanha_id = dependencias["publicar"](html, assunto)
    except Exception as erro:
        dependencias["salvar_html"](html)
        avisar(
            f"[Newsletter {semana}] falha ao criar o rascunho",
            f"O HTML foi salvo para nao perder a edicao.\nErro: {erro}\n\n{relatorio}",
        )
        raise

    # O histórico só é gravado depois de publicar: gravar antes sumiria com a
    # oportunidade na semana seguinte se a publicação falhasse.
    publicados = [op for itens in blocos.values() for op in itens]
    history.registrar(caminho_historico, publicados, hoje)

    relatorio["campanha_id"] = campanha_id
    relatorio["url_campanha"] = publisher.URL_CAMPANHA.format(id=campanha_id)
    avisar(
        f"[Newsletter {semana}] rascunho pronto para revisao",
        f"{relatorio['url_campanha']}\n\n{relatorio}",
    )
    return relatorio


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    gemini_key = os.environ["GEMINI_API_KEY"]
    brevo_key = os.environ["BREVO_API_KEY"]
    lista_id = int(os.environ["BREVO_LIST_ID"])

    chamar_modelo = discovery.cliente_gemini(gemini_key)

    def salvar_html(html: str) -> None:
        CAMINHO_SAIDA.parent.mkdir(parents=True, exist_ok=True)
        CAMINHO_SAIDA.write_text(html, encoding="utf-8")
        log.info("html salvo em %s", CAMINHO_SAIDA)

    dependencias = {
        "hoje": datetime.date.today(),
        "caminho_historico": CAMINHO_HISTORICO,
        "coletar": lambda: collector.coletar(
            collector.carregar_fontes(), collector.buscar_http
        ),
        "descobrir": lambda: discovery.descobrir(chamar_modelo),
        "verificar_link": _verificar_link,
        "escrever": lambda blocos: writer.escrever(blocos, chamar_modelo),
        "publicar": lambda html, assunto: publisher.criar_rascunho(
            html, assunto, lista_id, brevo_key
        ),
        "avisar": lambda assunto, corpo: notifier.avisar(assunto, corpo, brevo_key),
        "salvar_html": salvar_html,
    }

    try:
        executar(dependencias)
    except EdicaoVazia:
        log.warning("edicao vazia — nenhum rascunho criado")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Rodar o teste e confirmar que passa**

Run: `python -m pytest tests/test_main.py -v`
Expected: PASS, 9 testes

- [ ] **Step 5: Rodar a suíte inteira**

Run: `python -m pytest tests/ -v`
Expected: PASS, todos os testes de todas as tarefas

- [ ] **Step 6: Commit**

```bash
git add newsletter/main.py tests/test_main.py
git commit -m "feat: orquestracao do pipeline com politica de falha explicita"
```

---

### Task 11: GitHub Actions, README e primeira execução real

**Files:**
- Create: `.github/workflows/newsletter.yml`, `README.md`, `history.json`
- Modify: nenhum

**Interfaces:**
- Consumes: `newsletter.main.main`
- Produces: workflow semanal e documentação operacional

- [ ] **Step 1: Criar o histórico vazio**

`history.json`:

```json
{
  "itens": []
}
```

- [ ] **Step 2: Escrever o workflow**

`.github/workflows/newsletter.yml`:

```yaml
name: Newsletter semanal

on:
  schedule:
    # 10:00 UTC = 07:00 em Brasilia, toda segunda-feira.
    - cron: "0 10 * * 1"
  workflow_dispatch:

permissions:
  contents: write

jobs:
  edicao:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          # Mesma versao da maquina de desenvolvimento, para o CI nao divergir.
          python-version: "3.14"

      - name: Instalar dependencias
        run: pip install -r requirements.txt

      - name: Rodar os testes
        run: python -m pytest tests/ -q

      - name: Montar a edicao e criar o rascunho
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          BREVO_API_KEY: ${{ secrets.BREVO_API_KEY }}
          BREVO_LIST_ID: ${{ secrets.BREVO_LIST_ID }}
        run: python -m newsletter.main

      - name: Guardar o html quando o Brevo falha
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: edicao-html
          path: saida/
          if-no-files-found: ignore

      - name: Commitar o historico atualizado
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add history.json
          git diff --staged --quiet || git commit -m "chore: historico da edicao semanal"
          git push
```

> A suíte roda antes da edição de propósito: se uma mudança quebrou o pipeline, é melhor descobrir sem gastar cota do Gemini.

- [ ] **Step 3: Escrever o README**

`README.md`:

```markdown
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
   ordena por relevância (afirmativas primeiro) e corta em 5 itens por bloco
4. `writer` redige a abertura e os resumos
5. `renderer` monta o HTML
6. `publisher` cria a campanha **rascunho** no Brevo
7. Chega um email em clubedoslibertos@gmail.com com o link da campanha

Quem revisa preenche ou apaga os blocos manuais ("Vagas da semana" e "Espaço do
Clube") e clica em Enviar. **O pipeline nunca envia sozinho.**

## Rodar localmente

```bash
pip install -r requirements.txt
python -m pytest tests/ -q

export GEMINI_API_KEY=...
export BREVO_API_KEY=...
export BREVO_LIST_ID=...
python -m newsletter.main
```

## Segredos

Configurados em Settings → Secrets and variables → Actions:

| Segredo | Onde obter |
|---|---|
| `GEMINI_API_KEY` | aistudio.google.com — **em projeto sem billing ativo**, senão a cota do free tier vira zero |
| `BREVO_API_KEY` | Brevo → SMTP & API → API keys |
| `BREVO_LIST_ID` | Brevo → Contacts → a lista de membros; o id aparece na URL |

## Manutenção

- **Adicionar fonte:** editar `newsletter/sources.yml`. Verifique antes que a
  fonte responde e é parseável — o histórico de avaliação está em
  `docs/fontes-avaliadas.md`.
- **Fonte parou de funcionar:** o log da execução no Actions nomeia a fonte que
  falhou. Fonte quebrada não derruba a edição.
- **Lista de contatos:** gerida direto no Brevo, não neste repositório.

## Documentos

- Design: `docs/superpowers/specs/2026-08-25-newsletter-clube-dos-libertos-design.md`
- Plano de implementação: `docs/superpowers/plans/2026-08-25-newsletter-fase-1.md`
```

- [ ] **Step 4: Commit e push**

```bash
git add .github/ README.md history.json
git commit -m "feat: workflow semanal, readme e historico inicial"
git push
```

- [ ] **Step 5: Cadastrar os segredos**

No GitHub, em Settings → Secrets and variables → Actions, criar `GEMINI_API_KEY`, `BREVO_API_KEY` e `BREVO_LIST_ID`. A chave do Gemini precisa ter sido gerada em projeto **sem billing ativo**.

Antes de rodar, confirme que a lista existe no Brevo com pelo menos um contato de teste (o próprio `clubedoslibertos@gmail.com`), e que o remetente está verificado em Senders.

- [ ] **Step 6: Primeira execução real**

Disparar manualmente pelo Actions (`workflow_dispatch`) e verificar, nesta ordem:

1. O job termina com sucesso
2. Chegou o email de aviso em `clubedoslibertos@gmail.com`
3. A campanha aparece **como rascunho** no Brevo — nada foi enviado
4. O HTML no painel do Brevo está com o logo visível, os links funcionando e os blocos manuais marcados
5. O `history.json` recebeu commit com os itens da edição

Mande um teste para si mesmo pelo próprio Brevo e abra no celular antes de enviar para a lista.

- [ ] **Step 7: Enviar a primeira edição**

Revisar, preencher ou apagar os blocos manuais, e enviar. A partir daí o cron assume.

---

## Self-Review

**Cobertura da spec:**

| Seção da spec | Tarefa |
|---|---|
| 4.1 `sources.yml` | Task 5 |
| 4.2 `collector` | Task 4 |
| 4.3 `discovery` | Task 6 |
| 4.4 `curator` | Task 3 |
| 4.5 `writer` | Task 7 |
| 4.6 `renderer` | Task 8 |
| 4.7 `publisher` + notificação | Task 9 |
| 4.8 `history.json` | Task 2, Task 11 |
| 5 Fluxo semanal | Task 10, Task 11 |
| 6 Tratamento de erros | Task 4 (fonte), Task 6 (Gemini), Task 7 (writer), Task 10 (edição vazia, Brevo) |
| 7 Configuração e segredos | Task 1, Task 11 |
| 8 Testes | todas as tarefas |
| Blocos manuais | Task 8 |
| Reconciliação de blocos | Task 1 (`bloco_de`), Task 8 (template) |

Nenhuma seção da spec ficou sem tarefa.

**Consistência de tipos:** `Oportunidade` é criada em Task 1 e consumida sem alteração de assinatura em todas as demais. `chave` (Task 2) é usada por `curator` (Task 3) e `history` (Task 2). `curar` devolve `dict[str, list[Oportunidade]]`, que é exatamente o que `escrever` (Task 7) e `renderizar` (Task 8) consomem. `_postar` é definido em `publisher` (Task 9) e reaproveitado por `notifier` na mesma tarefa.

**Ponto de atenção deixado explícito:** Task 5 pode reduzir `CATEGORIAS` se alguma categoria não tiver fonte fixa aprovada. O plano manda ajustar `models.py` e o teste correspondente em vez de inventar URL — inventar fonte é pior que ficar sem ela, porque a falha só aparece em produção.
