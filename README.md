# Newsletter do Clube dos Libertos

Newsletter semanal com oportunidades de trainee, estágio, editais, bolsas e
cursos gratuitos, na identidade visual do Clube.

Projeto voluntário do Clube dos Libertos — Black Network.

## Como funciona

```
app do Claude  →  Google Doc  →  Apps Script  →  emails
  (pesquisa)      (você revisa)   (Gemini escreve)
```

1. Uma rotina semanal no app do Claude pesquisa as oportunidades e devolve a
   edição em markdown. O prompt está em
   [`docs/prompt-pesquisa-semanal.md`](docs/prompt-pesquisa-semanal.md)
2. Você cola no Google Doc da edição e **revisa à mão** — é aqui que a curadoria
   acontece
3. No menu **Newsletter** do próprio Doc: pré-visualizar → enviar teste → enviar
   para a lista

O código está em [`appscript/Codigo.gs`](appscript/Codigo.gs). A instalação e a
operação estão em [`appscript/README.md`](appscript/README.md).

## Por que assim

A primeira versão era um pipeline Python que fazia tudo sozinho: varria portais
de vagas, buscava na web, classificava com IA, montava o email e criava rascunho
no Brevo pelo GitHub Actions. Funcionava — mas quase todo o esforço ia para
segurar a fragilidade das fontes: seletor de CSS que quebra, site que virou
aplicação JavaScript, curso sem data de inscrição, vídeo se passando por edital,
programa de 2025 ainda publicado.

A curadoria humana na entrada elimina essa categoria inteira de problema, e o
resultado é melhor. O que ficou de máquina é o que máquina faz bem: redigir com
consistência, montar HTML de email e enviar para a lista.

O custo é honesto: **alguém precisa fazer a pesquisa toda semana.** Sem isso não
sai edição. O histórico do git guarda o pipeline antigo, se um dia fizer sentido
voltar.

## Duas garantias que não dependem da IA

O Gemini interpreta o markdown do Doc e escreve os textos. Duas coisas ficam
fora do alcance dele, por código:

- **URL que não está no Doc não vai para o email.** Link inventado deixa de
  depender de o modelo obedecer ao prompt.
- **Prazo vencido não sai.** Melhor o item cair do que a newsletter anunciar
  inscrição encerrada.

## Limites

- **100 destinatários por dia** numa conta Gmail comum (1.500 no Workspace). O
  script confere antes de começar e aborta se a lista não couber.
- **Descadastro é manual:** quem pede para sair precisa ser marcado na planilha.
- **Sem métrica de abertura.**

## Identidade visual

Paleta do Manual de Marca — roxo `#5C1A88`, amarelo `#FFC812`, marrom `#4B2B20`
— e o logo em [`assets/logo.png`](assets/logo.png), servido pelo próprio
repositório. Todos os pares de cor passam contraste WCAG AA.

## Histórico de decisões

O [design da fase 1](docs/superpowers/specs/2026-08-25-newsletter-clube-dos-libertos-design.md)
e o [plano de implementação](docs/superpowers/plans/2026-08-25-newsletter-fase-1.md)
descrevem o pipeline automatizado. **São documentos históricos** — a arquitetura
mudou em 26/08/2026 para o fluxo acima.
