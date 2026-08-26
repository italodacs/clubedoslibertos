# Envio por Apps Script

O envio da newsletter roda dentro da conta Google do Clube, com Apps Script
ligado ao Doc da edição. Não há servidor, credencial em repositório nem serviço
externo de email.

## Fluxo semanal

1. A rotina do app do Claude pesquisa e devolve a edição em markdown
2. Você cola no [Doc da edição](https://docs.google.com/document/d/1W5YmKrcM0DxwIFgrv_0cdw3SlArskqgzItWW1dWMecQ/edit) e **revisa à mão**
3. No menu **Newsletter** do próprio Doc: pré-visualizar → enviar teste → enviar para a lista

O menu tem três itens, na ordem em que devem ser usados:

| Item | O que faz |
|---|---|
| **1. Pré-visualizar** | Monta a edição, mostra quantos itens por bloco, quantos destinatários e todos os avisos da validação. Não envia nada |
| **2. Enviar teste para mim** | Manda a edição só para você, com `[TESTE]` no assunto |
| **3. Enviar para a lista** | Envia para todos os ativos da planilha, com confirmação antes |

## Instalação

1. Abra o Doc da edição → **Extensões → Apps Script**
2. Apague o conteúdo do `Código.gs` e cole o [`Codigo.gs`](Codigo.gs) deste diretório
3. Em **Configurações do projeto → Propriedades do script**, crie:
   - `GEMINI_API_KEY` — a chave do aistudio.google.com
4. Salve e rode `preVisualizar` uma vez pelo editor, para autorizar os acessos
   (Documentos, Planilhas, Gmail e requisições externas)
5. Recarregue o Doc — o menu **Newsletter** aparece

Nenhum ID precisa ser preenchido: o Doc e a planilha já estão no `CONFIG`.

## A planilha

Aba .

As colunas são descobertas pelo **cabeçalho da primeira linha**, em qualquer
ordem. Qualquer coluna cujo título contenha:

- `email` ou `e-mail` → endereço
- `nome` → usado na saudação ("Olá, Ana!")
- `ativo` ou `receb` → controle de quem recebe

Na coluna de controle, célula **vazia conta como ativo**: quem sai é marcado
explicitamente com `não`. Assim ninguém deixa de receber por esquecimento de
preencher.

Sem cabeçalho reconhecível, o script cai para coluna A = nome e B = email.
Email repetido recebe uma vez só.

## O que o código garante, e o modelo não decide

O Gemini interpreta o markdown e escreve os textos. Duas coisas ficam fora do
alcance dele:

- **URL que não está no Doc não vai para o email.** Se o modelo devolver um link
  que você não colou, ele é descartado e aparece nos avisos. Link inventado
  deixa de depender de o modelo obedecer ao prompt.
- **Prazo vencido não sai.** Data no passado descarta o item, mesmo que esteja
  no Doc — é erro de curadoria, e é melhor o item cair do que a newsletter
  anunciar inscrição encerrada.

Curso pode não ter prazo (matrícula sempre aberta). Vaga, estágio e edital sem
prazo entram, mas com aviso na pré-visualização.

## Limites que valem saber

- **Cota de envio do Gmail:** ~100 destinatários por dia em conta comum, ~1.500
  no Workspace. O script confere antes de começar e aborta se não couber — pior
  que não enviar é enviar para metade da lista.
- **Descadastro é manual.** Diferente de um serviço de newsletter, aqui quem
  pede para sair precisa ser marcado na planilha por alguém. Com a comunidade
  pequena funciona; passando de algumas dezenas, vale trocar o `mailto:` do
  rodapé por um Google Form que registre o pedido.
- **Sem métrica de abertura.** O Gmail não informa quem abriu.

## Identidade visual

O HTML usa a paleta do Manual de Marca — roxo `#5C1A88`, amarelo `#FFC812`,
marrom `#4B2B20` — e o logo branco com símbolo amarelo, servido pelo próprio
repositório. Todos os pares de cor passam contraste WCAG AA. O email tem versão
em texto puro além do HTML, para cliente que não renderiza.
