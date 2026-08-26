/**
 * Newsletter do Clube dos Libertos — envio por Apps Script.
 *
 * Fluxo:
 *   1. A rotina do app do Claude pesquisa e devolve a edição em markdown.
 *   2. Você cola no Google Doc e revisa à mão.
 *   3. Este script lê o Doc, pede ao Gemini para estruturar e redigir, monta o
 *      HTML na identidade do Clube e envia para a lista da planilha.
 *
 * Não há parser de markdown aqui de propósito: o Gemini lê o texto do Doc e
 * devolve JSON. O que o código faz, e o modelo não decide, são as validações —
 * URL que não está no Doc não vai para o email, e prazo vencido interrompe o
 * envio.
 *
 * Instalação e configuração: veja appscript/README.md no repositório.
 */

// ===========================================================================
// CONFIGURAÇÃO — preencha estes valores
// ===========================================================================

const CONFIG = {
  // Doc onde você cola a edição.
  DOC_ID: '1W5YmKrcM0DxwIFgrv_0cdw3SlArskqgzItWW1dWMecQ',

  // Planilha com a lista de emails. Aba vazia cai na primeira da planilha.
  PLANILHA_ID: '1znLhBKmn-PBChZZm8IOaDSI9Eojj5ayZGPQ3SJoEti8',
  ABA: 'db',

  // As colunas são achadas pelo cabeçalho da primeira linha: qualquer coluna
  // cujo título contenha "email", "nome" ou "status" é reconhecida, em qualquer
  // ordem. Sem cabeçalho reconhecível, cai para A = nome e B = email.

  REMETENTE_NOME: 'Clube dos Libertos',
  RESPONDER_PARA: 'clubedoslibertos@gmail.com',

  INSTAGRAM_URL: 'https://www.instagram.com/clubedoslibertos/',
  LINKEDIN_URL: 'https://www.linkedin.com/company/clube-dos-libertos-black-network/',
  FORM_BASE_TALENTOS_URL: 'https://forms.gle/TXvssihhk4QTnCJo6',
  LOGO_URL:
    'https://raw.githubusercontent.com/italodacs/clubedoslibertos/main/assets/logo.png',

  // Formulário de saída da lista. Quem responde precisa ser marcado como
  // "inativa" na coluna de status da planilha — o Form registra o pedido, mas
  // não mexe na planilha sozinho.
  SAIR_DA_LISTA_URL: 'https://forms.gle/umX8akZhxpuudF4SA',

  MODELO_GEMINI: 'gemini-3.6-flash',
};

const CORES = {
  roxo: '#5C1A88',
  amarelo: '#FFC812',
  marrom: '#4B2B20',
  preto: '#000000',
};

const BLOCOS = [
  { chave: 'trainee', titulo: 'Trainees' },
  { chave: 'estagio', titulo: 'Estágios' },
  { chave: 'educacao', titulo: 'Cursos e formações gratuitas' },
  { chave: 'edital', titulo: 'Editais, bolsas e intercâmbio' },
];

// ===========================================================================
// MENU NO DOC
// ===========================================================================

/** Cria o menu "Newsletter" ao abrir o Doc. */
function onOpen() {
  DocumentApp.getUi()
    .createMenu('Newsletter')
    .addItem('Pré-visualizar (não envia)', 'preVisualizar')
    .addItem('Enviar teste para mim', 'enviarTeste')
    .addSeparator()
    .addItem('Enviar newsletter', 'enviarNewsletter')
    .addToUi();
}

// ===========================================================================
// AÇÕES DO MENU
// ===========================================================================

/** Monta a edição e mostra o resumo, sem enviar nada. */
function preVisualizar() {
  const edicao = montarEdicao_();
  const linhas = [
    'Assunto: ' + edicao.assunto,
    '',
    'Itens por bloco:',
  ];
  BLOCOS.forEach(function (b) {
    const n = edicao.porBloco[b.chave] || 0;
    if (n > 0) linhas.push('  ' + b.titulo + ': ' + n);
  });
  linhas.push('', 'Total: ' + edicao.total + ' itens');
  linhas.push('', 'Destinatários ativos: ' + lerDestinatarios_().length);
  if (edicao.avisos.length) {
    linhas.push('', 'ATENÇÃO:');
    edicao.avisos.forEach(function (a) {
      linhas.push('  - ' + a);
    });
  }
  alerta_('Pré-visualização', linhas.join('\n'));
}

/**
 * Envia a edição para um email digitado na hora, com [TESTE] no assunto.
 *
 * Quem revisa põe o próprio endereço — não há lista de teste para manter, e
 * qualquer pessoa da coordenação consegue conferir sem mexer na planilha.
 */
function enviarTeste() {
  const ui = DocumentApp.getUi();
  const resposta = ui.prompt(
    'Enviar teste',
    'Para qual email enviar a prévia?',
    ui.ButtonSet.OK_CANCEL
  );
  if (resposta.getSelectedButton() !== ui.Button.OK) return;

  const email = resposta.getResponseText().trim();
  if (!email || email.indexOf('@') === -1 || email.indexOf(' ') !== -1) {
    throw new Error('Email inválido: ' + (email || '(vazio)'));
  }

  const edicao = montarEdicao_();
  enviarUm_({ nome: '', email: email }, edicao, '[TESTE] ' + edicao.assunto);

  alerta_(
    'Teste enviado',
    'Enviado para ' +
      email +
      '.\n\nAbra no celular antes de enviar para a lista.\n\n' +
      'O "Enviar newsletter" vai mandar exatamente este email, desde que você ' +
      'não altere o Doc no meio.'
  );
}

/**
 * Envia a newsletter para todos os destinatários ativos da planilha.
 *
 * É o botão que uma pessoa clica depois de revisar o Doc e conferir o teste.
 * Pede confirmação antes, porque não tem volta.
 */
function enviarNewsletter() {
  const edicao = montarEdicao_();
  const pessoas = lerDestinatarios_();

  if (!pessoas.length) {
    throw new Error('Nenhum destinatário ativo na planilha.');
  }

  // Cota diária do Gmail: 100 numa conta comum, 1.500 no Workspace. Melhor
  // parar antes de começar do que enviar para metade da lista.
  const restante = MailApp.getRemainingDailyQuota();
  if (restante < pessoas.length) {
    throw new Error(
      'Cota insuficiente: ' +
        restante +
        ' envios restantes hoje para ' +
        pessoas.length +
        ' destinatários. Envie amanhã ou reduza a lista.'
    );
  }

  const ui = DocumentApp.getUi();
  const resposta = ui.alert(
    'Enviar para a lista?',
    'Vai enviar "' +
      edicao.assunto +
      '" para ' +
      pessoas.length +
      ' pessoas.\n\nIsso não tem volta.',
    ui.ButtonSet.OK_CANCEL
  );
  if (resposta !== ui.Button.OK) return;

  let enviados = 0;
  const falhas = [];
  pessoas.forEach(function (pessoa) {
    try {
      enviarUm_(pessoa, edicao, edicao.assunto);
      enviados++;
    } catch (erro) {
      falhas.push(pessoa.email + ': ' + erro.message);
    }
  });

  let msg = enviados + ' de ' + pessoas.length + ' enviados.';
  if (falhas.length) msg += '\n\nFalhas:\n' + falhas.join('\n');
  alerta_('Envio concluído', msg);
}

// ===========================================================================
// MONTAGEM DA EDIÇÃO
// ===========================================================================

/**
 * Lê o Doc, pede ao Gemini para estruturar e redigir, valida e devolve tudo
 * que o envio precisa.
 */
function montarEdicao_() {
  const texto = lerDoc_();
  if (!texto.trim()) {
    throw new Error('O Doc está vazio. Cole a edição antes de enviar.');
  }

  // O Gemini redige diferente a cada chamada. Sem cache, o teste mostraria um
  // texto e a lista receberia outro — o que esvazia o sentido de testar. A
  // chave é o hash do Doc: mexer no conteúdo invalida e gera de novo.
  const cache = CacheService.getDocumentCache();
  const chave = 'edicao:' + hashDoTexto_(texto);
  const guardado = cache ? cache.get(chave) : null;
  if (guardado) {
    return reviverEdicao_(JSON.parse(guardado));
  }

  const bruto = pedirAoGemini_(texto);
  const validado = validar_(bruto, texto);

  const porBloco = {};
  validado.itens.forEach(function (item) {
    porBloco[item.categoria] = (porBloco[item.categoria] || 0) + 1;
  });

  const total = validado.itens.length;
  if (total === 0) {
    throw new Error(
      'Nenhum item sobrou depois da validação. Confira os avisos:\n' +
        validado.avisos.join('\n')
    );
  }

  const edicao = {
    abertura: validado.abertura,
    itens: validado.itens,
    porBloco: porBloco,
    total: total,
    avisos: validado.avisos,
    assunto: montarAssunto_(total),
  };

  if (cache) {
    try {
      cache.put(chave, JSON.stringify(edicao), 21600); // 6 horas
    } catch (erro) {
      // Edição grande pode não caber no cache. Não é motivo para não enviar —
      // só significa que o texto será gerado de novo na próxima ação.
      console.warn('nao guardei a edicao no cache: ' + erro.message);
    }
  }

  return edicao;
}

/** Identidade do conteúdo do Doc, para saber se ele mudou. */
function hashDoTexto_(texto) {
  const bytes = Utilities.computeDigest(
    Utilities.DigestAlgorithm.MD5,
    texto,
    Utilities.Charset.UTF_8
  );
  return bytes
    .map(function (b) {
      return ((b & 0xff) + 0x100).toString(16).slice(1);
    })
    .join('');
}

/** O JSON do cache devolve prazo como texto; aqui ele volta a ser Date. */
function reviverEdicao_(edicao) {
  edicao.itens.forEach(function (item) {
    item.prazo = item.prazo ? new Date(item.prazo) : null;
  });
  return edicao;
}

/** Texto puro do Doc da edição. */
function lerDoc_() {
  return DocumentApp.openById(CONFIG.DOC_ID).getBody().getText();
}

function montarAssunto_(total) {
  const semana = Utilities.formatDate(
    new Date(),
    Session.getScriptTimeZone(),
    'w'
  );
  return (
    'Oportunidades da semana W' + semana + ' — ' + total + ' para você conferir'
  );
}

// ===========================================================================
// GEMINI
// ===========================================================================

/**
 * Manda o markdown do Doc e recebe a edição estruturada e redigida.
 *
 * O modelo faz duas coisas: interpreta o markdown (por isso não existe parser
 * aqui) e escreve a abertura e os resumos no tom do Clube.
 */
function pedirAoGemini_(textoDoc) {
  const chave = PropertiesService.getScriptProperties().getProperty(
    'GEMINI_API_KEY'
  );
  if (!chave) {
    throw new Error(
      'Falta a GEMINI_API_KEY. Configure em Project Settings → Script properties.'
    );
  }

  const hoje = Utilities.formatDate(
    new Date(),
    Session.getScriptTimeZone(),
    'yyyy-MM-dd'
  );

  const prompt = [
    'Você escreve a newsletter semanal do Clube dos Libertos, uma rede de',
    'profissionais e estudantes negros no Brasil. O tom é acolhedor, direto e',
    'sem jargão corporativo. Hoje é ' + hoje + '.',
    '',
    'Abaixo está a edição desta semana, em markdown, curada por uma pessoa.',
    'Sua tarefa é estruturar e redigir — não é decidir o que entra, nem buscar',
    'nada novo.',
    '',
    'Para cada oportunidade do texto:',
    '- copie a URL EXATAMENTE como está. Não corrija, não complete, não invente;',
    '- escreva um resumo de 2 a 3 linhas dizendo para quem serve e o que a',
    '  pessoa ganha, usando só o que está no texto;',
    '- converta o prazo para AAAA-MM-DD. Se o texto disser que a matrícula é',
    '  sempre aberta ou não trouxer data, use null.',
    '',
    'Escreva também uma abertura de no máximo duas frases sobre o conjunto.',
    '',
    'EDIÇÃO:',
    textoDoc,
    '',
    'Responda SOMENTE com JSON, sem cerca de código e sem texto em volta:',
    '{"abertura": "...", "itens": [{"titulo": "...", "url": "...",',
    ' "categoria": "trainee|estagio|educacao|edital", "prazo": "AAAA-MM-DD" ou null,',
    ' "local": "...", "afirmativa": true|false, "resumo": "..."}]}',
  ].join('\n');

  const url =
    'https://generativelanguage.googleapis.com/v1beta/models/' +
    CONFIG.MODELO_GEMINI +
    ':generateContent?key=' +
    encodeURIComponent(chave);

  const resposta = UrlFetchApp.fetch(url, {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify({
      contents: [{ parts: [{ text: prompt }] }],
    }),
    muteHttpExceptions: true,
  });

  const codigo = resposta.getResponseCode();
  if (codigo !== 200) {
    throw new Error(
      'Gemini respondeu ' + codigo + ': ' + resposta.getContentText().slice(0, 300)
    );
  }

  const corpo = JSON.parse(resposta.getContentText());
  const texto = corpo.candidates[0].content.parts[0].text;
  return JSON.parse(limparCerca_(texto));
}

/** O modelo às vezes embrulha o JSON em ```json apesar da instrução. */
function limparCerca_(texto) {
  return texto
    .trim()
    .replace(/^```(?:json)?/i, '')
    .replace(/```$/, '')
    .trim();
}

// ===========================================================================
// VALIDAÇÃO — o que o código decide, e o modelo não
// ===========================================================================

/**
 * Duas garantias:
 *
 * 1. URL que não aparece no Doc não vai para o email. Link inventado deixa de
 *    depender de o modelo obedecer ao prompt.
 * 2. Prazo vencido não sai. Data passada no Doc é erro de curadoria, e a
 *    newsletter anunciando inscrição encerrada é pior que a newsletter atrasada.
 */
function validar_(bruto, textoDoc) {
  const avisos = [];
  const itens = [];
  const hoje = new Date();
  hoje.setHours(0, 0, 0, 0);

  (bruto.itens || []).forEach(function (item) {
    const titulo = (item.titulo || '').trim();
    const url = (item.url || '').trim();

    if (!titulo || !url) {
      avisos.push('Item sem título ou sem URL, descartado.');
      return;
    }

    if (textoDoc.indexOf(url) === -1) {
      avisos.push('URL que não está no Doc, descartada: ' + url);
      return;
    }

    const categoria = item.categoria;
    if (!BLOCOS.some(function (b) { return b.chave === categoria; })) {
      avisos.push('Categoria desconhecida em "' + titulo + '": ' + categoria);
      return;
    }

    let prazo = null;
    if (item.prazo) {
      prazo = new Date(item.prazo + 'T00:00:00');
      if (isNaN(prazo.getTime())) {
        avisos.push('Prazo ilegível em "' + titulo + '": ' + item.prazo);
        prazo = null;
      } else if (prazo < hoje) {
        avisos.push(
          'Descartado, prazo vencido em ' + item.prazo + ': ' + titulo
        );
        return;
      }
    }

    if (prazo === null && categoria !== 'educacao') {
      avisos.push('Sem prazo (só curso pode): ' + titulo);
    }

    itens.push({
      titulo: titulo,
      url: url,
      categoria: categoria,
      prazo: prazo,
      local: (item.local || '').trim(),
      afirmativa: item.afirmativa === true,
      resumo: (item.resumo || '').trim(),
    });
  });

  return {
    abertura:
      (bruto.abertura || '').trim() ||
      'Boa semana, Libertos! Seguem as oportunidades desta edição.',
    itens: itens,
    avisos: avisos,
  };
}

// ===========================================================================
// PLANILHA
// ===========================================================================

/**
 * Destinatários ativos de uma aba. Sem argumento, usa a aba principal.
 *
 * As colunas são descobertas pelo cabeçalho, não fixadas por posição: mexer na
 * ordem das colunas da planilha é a coisa mais fácil de acontecer e a mais
 * chata de descobrir depois — o sintoma seria email indo para a coluna de nome.
 */
function lerDestinatarios_(nomeDaAba) {
  const nome = nomeDaAba || CONFIG.ABA;
  const planilha = SpreadsheetApp.openById(CONFIG.PLANILHA_ID);
  const aba = nome ? planilha.getSheetByName(nome) : planilha.getSheets()[0];
  if (!aba) {
    throw new Error('Aba "' + nome + '" não encontrada na planilha.');
  }

  const ultima = aba.getLastRow();
  if (ultima < 2) return [];

  const dados = aba.getRange(1, 1, ultima, aba.getLastColumn()).getValues();
  const col = acharColunas_(dados[0]);

  const pessoas = [];
  const vistos = {};

  for (let i = 1; i < dados.length; i++) {
    const linha = dados[i];
    const email = String(linha[col.email] || '').trim();
    if (!email || email.indexOf('@') === -1) continue;

    if (col.ativo !== -1 && !estaAtivo_(linha[col.ativo])) continue;

    const chave = email.toLowerCase();
    if (vistos[chave]) continue; // ninguém recebe duas vezes
    vistos[chave] = true;

    pessoas.push({
      nome: col.nome === -1 ? '' : String(linha[col.nome] || '').trim(),
      email: email,
    });
  }

  return pessoas;
}

/**
 * Decide se a pessoa recebe, a partir da coluna de status.
 *
 * Célula **vazia conta como ativa**: ninguém deixa de receber por esquecimento
 * de preencher. O que tira da lista é valor explícito de saída — "inativa",
 * "não", "descadastrado".
 *
 * O teste é por prefixo `inativ` de propósito: "inativa" e "inativo" contam,
 * "ativa" e "ativo" não, e a comparação não depende de gênero nem de acento.
 */
function estaAtivo_(valor) {
  const v = String(valor || '').trim().toLowerCase();
  if (!v) return true;
  if (v.indexOf('inativ') !== -1) return false;
  if (v.indexOf('descadastr') !== -1 || v.indexOf('desinscr') !== -1) return false;
  return ['nao', 'não', 'no', 'false', '0', 'sair', 'removido'].indexOf(v) === -1;
}

/** Acha as colunas pelo cabeçalho. Sem cabeçalho útil, A = nome e B = email. */
function acharColunas_(cabecalho) {
  const col = { nome: -1, email: -1, ativo: -1 };

  cabecalho.forEach(function (celula, i) {
    const t = String(celula || '')
      .trim()
      .toLowerCase();
    if (col.email === -1 && (t.indexOf('email') !== -1 || t.indexOf('e-mail') !== -1)) {
      col.email = i;
    } else if (col.nome === -1 && t.indexOf('nome') !== -1) {
      col.nome = i;
    } else if (
      col.ativo === -1 &&
      (t.indexOf('status') !== -1 ||
        t.indexOf('ativo') !== -1 ||
        t.indexOf('ativa') !== -1 ||
        t.indexOf('receb') !== -1)
    ) {
      col.ativo = i;
    }
  });

  if (col.email === -1) {
    col.nome = 0;
    col.email = 1;
  }
  return col;
}

// ===========================================================================
// ENVIO
// ===========================================================================

function enviarUm_(pessoa, edicao, assunto) {
  MailApp.sendEmail({
    to: pessoa.email,
    subject: assunto,
    htmlBody: montarHtml_(edicao, pessoa.nome),
    body: montarTextoSimples_(edicao, pessoa.nome),
    name: CONFIG.REMETENTE_NOME,
    replyTo: CONFIG.RESPONDER_PARA,
  });
}

/** Primeiro nome, para a saudação. */
function primeiroNome_(nome) {
  const limpo = (nome || '').trim();
  if (!limpo) return '';
  return limpo.split(/\s+/)[0];
}

function formatarPrazo_(item) {
  if (item.prazo) {
    return (
      'inscrições até ' +
      Utilities.formatDate(item.prazo, Session.getScriptTimeZone(), 'dd/MM/yyyy')
    );
  }
  return item.categoria === 'educacao'
    ? 'matrícula sempre aberta'
    : 'prazo não informado — confira na página';
}

function escapar_(texto) {
  return String(texto || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/** HTML do email. CSS inline: cliente de email descarta folha externa. */
function montarHtml_(edicao, nome) {
  const saudacao = primeiroNome_(nome)
    ? 'Olá, ' + escapar_(primeiroNome_(nome)) + '!'
    : 'Olá!';

  let corpo = '';

  BLOCOS.forEach(function (bloco) {
    const doBloco = edicao.itens.filter(function (i) {
      return i.categoria === bloco.chave;
    });
    if (!doBloco.length) return;

    corpo +=
      '<tr><td style="padding:22px 24px 4px;">' +
      '<h2 style="margin:0;color:' +
      CORES.roxo +
      ';font-size:19px;border-bottom:3px solid ' +
      CORES.amarelo +
      ';padding-bottom:6px;">' +
      escapar_(bloco.titulo) +
      '</h2></td></tr>';

    doBloco.forEach(function (item) {
      corpo +=
        '<tr><td style="padding:14px 24px;">' +
        '<p style="margin:0 0 4px;"><a href="' +
        escapar_(item.url) +
        '" style="color:' +
        CORES.roxo +
        ';font-size:17px;font-weight:bold;text-decoration:none;">' +
        escapar_(item.titulo) +
        '</a></p>';

      if (item.afirmativa) {
        corpo +=
          '<p style="margin:0 0 6px;"><span style="background-color:' +
          CORES.amarelo +
          ';color:' +
          CORES.preto +
          ';font-size:11px;font-weight:bold;padding:3px 8px;text-transform:uppercase;">Vaga afirmativa</span></p>';
      }

      if (item.resumo) {
        corpo +=
          '<p style="margin:0 0 6px;color:' +
          CORES.preto +
          ';font-size:15px;line-height:1.6;">' +
          escapar_(item.resumo) +
          '</p>';
      }

      const detalhe = [formatarPrazo_(item)];
      if (item.local) detalhe.push(escapar_(item.local));
      corpo +=
        '<p style="margin:0;color:' +
        CORES.marrom +
        ';font-size:13px;">' +
        detalhe.join(' &middot; ') +
        '</p></td></tr>';
    });
  });

  return [
    '<div style="margin:0;padding:0;background-color:#f4f2f7;font-family:Luciole,Verdana,Geneva,sans-serif;">',
    '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f2f7;">',
    '<tr><td align="center" style="padding:24px 12px;">',
    '<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="width:600px;max-width:600px;background-color:#ffffff;">',

    // cabeçalho
    '<tr><td align="center" style="background-color:' +
      CORES.roxo +
      ';padding:28px 24px;">',
    '<img src="' +
      CONFIG.LOGO_URL +
      '" width="220" alt="Clube dos Libertos" style="display:block;width:220px;max-width:80%;height:auto;">',
    '<p style="margin:16px 0 0;color:' +
      CORES.amarelo +
      ';font-size:13px;letter-spacing:2px;text-transform:uppercase;">Black Network</p>',
    '</td></tr>',

    // abertura
    '<tr><td style="padding:28px 24px 8px;">',
    '<p style="margin:0 0 10px;color:' +
      CORES.preto +
      ';font-size:16px;font-weight:bold;">' +
      saudacao +
      '</p>',
    '<p style="margin:0;color:' +
      CORES.preto +
      ';font-size:16px;line-height:1.6;">' +
      escapar_(edicao.abertura) +
      '</p>',
    '</td></tr>',

    corpo,

    // CTA da Base de Talentos
    '<tr><td style="padding:20px 24px;">',
    '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:' +
      CORES.roxo +
      ';">',
    '<tr><td align="center" style="padding:24px 20px;">',
    '<p style="margin:0 0 6px;color:#ffffff;font-size:18px;font-weight:bold;">Núcleo Ubuntu &mdash; Base de Talentos</p>',
    '<p style="margin:0 0 16px;color:#ffffff;font-size:14px;line-height:1.6;">Cadastre seu perfil para receber indicações e aparecer para as organizações parceiras do Clube.</p>',
    '<a href="' +
      CONFIG.FORM_BASE_TALENTOS_URL +
      '" style="background-color:' +
      CORES.amarelo +
      ';color:' +
      CORES.preto +
      ';font-size:15px;font-weight:bold;padding:12px 26px;text-decoration:none;display:inline-block;">Quero me cadastrar</a>',
    '</td></tr></table></td></tr>',

    // rodapé
    '<tr><td align="center" style="background-color:' +
      CORES.preto +
      ';padding:22px 24px;">',
    '<p style="margin:0 0 10px;">',
    '<a href="' +
      CONFIG.INSTAGRAM_URL +
      '" style="color:' +
      CORES.amarelo +
      ';font-size:14px;text-decoration:none;">Instagram</a>',
    '<span style="color:#ffffff;">&nbsp;&middot;&nbsp;</span>',
    '<a href="' +
      CONFIG.LINKEDIN_URL +
      '" style="color:' +
      CORES.amarelo +
      ';font-size:14px;text-decoration:none;">LinkedIn</a>',
    '</p>',
    '<p style="margin:0;color:#cccccc;font-size:12px;line-height:1.6;">',
    'Clube dos Libertos &mdash; Black Network<br>',
    'Você recebe este email porque faz parte da comunidade.<br>',
    '<a href="' +
      CONFIG.SAIR_DA_LISTA_URL +
      '" style="color:#cccccc;text-decoration:underline;">Sair desta lista</a>',
    '</p></td></tr>',

    '</table></td></tr></table></div>',
  ].join('');
}

/** Versão em texto puro, para cliente que não renderiza HTML. */
function montarTextoSimples_(edicao, nome) {
  const linhas = [];
  const saudacao = primeiroNome_(nome) ? 'Olá, ' + primeiroNome_(nome) + '!' : 'Olá!';
  linhas.push(saudacao, '', edicao.abertura, '');

  BLOCOS.forEach(function (bloco) {
    const doBloco = edicao.itens.filter(function (i) {
      return i.categoria === bloco.chave;
    });
    if (!doBloco.length) return;
    linhas.push('== ' + bloco.titulo.toUpperCase() + ' ==', '');
    doBloco.forEach(function (item) {
      linhas.push(item.titulo);
      if (item.resumo) linhas.push(item.resumo);
      linhas.push(formatarPrazo_(item));
      linhas.push(item.url, '');
    });
  });

  linhas.push(
    'Cadastre-se na Base de Talentos: ' + CONFIG.FORM_BASE_TALENTOS_URL,
    '',
    'Clube dos Libertos — Black Network',
    'Instagram: ' + CONFIG.INSTAGRAM_URL,
    'LinkedIn: ' + CONFIG.LINKEDIN_URL
  );

  return linhas.join('\n');
}

// ===========================================================================
// UTILIDADES
// ===========================================================================

function alerta_(titulo, mensagem) {
  DocumentApp.getUi().alert(titulo, mensagem, DocumentApp.getUi().ButtonSet.OK);
}
