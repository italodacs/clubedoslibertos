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

# Quantos itens de cada categoria entram na edição. Revisado pela Presidência em
# 26/08/2026. O corte é por categoria, não por bloco: "Trainees e estágios"
# reúne duas categorias, e sem cota separada uma delas ocuparia as vagas da
# outra. Edição cheia = 21 itens.
LIMITES_POR_CATEGORIA = {
    "trainee": 6,
    "estagio": 5,
    "educacao": 5,
    "edital": 5,
}

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
