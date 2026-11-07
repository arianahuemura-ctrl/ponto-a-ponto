from pathlib import Path
from lxml import etree as E
import zipfile,copy
src=(Path(__file__).resolve().parent/'modelo_termo.docx');out=(Path(__file__).resolve().parent/'Registro_feedback_Thiago_Alameda_Solutions.docx');W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
groups=[('Aplicação: entrada, escolhas e continuidade da navegação',[
('Entrada por QR Code e localização','Identificar o embarque e evitar redigitação desnecessária da origem.','Reconhecimento em vez de memorização; redução de esforço.'),
('Busca e seleção de origem e destino','Aprimorar a busca, selecionar paradas ou coordenadas por toque prolongado e evitar seleção acidental durante arrasto ou gesto com dois dedos.','Prevenção de erros e adequação ao uso móvel.'),
('Alteração do embarque','Conservar o destino ao mudar a origem e reenquadrar o mapa para manter o contexto da consulta.','Continuidade da tarefa e controle do usuário.'),
('Cancelamento de viagem','Explicar as consequências, permitir desistir da ação e ao confirmar, remover trajeto, embarque e destino, preservando favoritos e enquadramento do mapa.','Prevenção de erros e possibilidade de recuperação.'),
('Favoritos','Facilitar salvar, reconhecer, reutilizar e remover destinos, com confirmação nas ações destrutivas.','Reconhecimento e redução de operações repetidas.'),
('Cálculo e atualização das alternativas','Mostrar andamento do cálculo, apresentar resultados progressivos e preservar a escolha e o enquadramento durante atualizações.','Visibilidade do estado e estabilidade da interação.'),
('Recálculo sob controle do usuário','Oferecer recálculo manual e evitar reiniciar a busca de rotas automaticamente a cada atualização de GPS.','Controle e previsibilidade.'),
('Uso móvel e tela cheia','Revisar seleção de pontos, controles móveis, renderização e funcionamento em tela cheia.','Consistência entre dispositivos e facilidade de operação.')]),
('Aplicação: leitura do mapa e informações de transporte',[
('Poluição visual dos pontos','Usar o controle da lâmpada para reduzir a quantidade de marcadores quando não forem necessários à tarefa.','Hierarquia visual e redução de sobrecarga.'),
('Recentrar, ampliar e pesquisar','Manter controles reconhecíveis para recuperar a posição e ajustar a leitura do mapa.','Orientação espacial e autonomia.'),
('Leitura dos trechos da viagem','Distinguir ônibus e caminhada e permitir alternar entre viagem completa e etapas.','Correspondência com a tarefa e compreensão do percurso.'),
('Antes e depois do embarque','Diferenciar o trecho anterior em lilás tracejado e o posterior em azul contínuo.','Redundância entre cor e traçado para facilitar interpretação.'),
('Sentido, retornos e extremidades da linha','Usar setas e indicações de início e fim; explicitar divergência entre fim do traçado e última parada cadastrada.','Prevenção de interpretações incorretas.'),
('Indisponibilidade de posição de ônibus','Conservar o itinerário estático e informar a ausência de posição ou previsão, sem inventar dados.','Feedback claro sobre limites da informação.'),
('Frequência e previsão de chegada','Distinguir intervalo entre veículos de contagem regressiva para chegada e organizar faixas de mesma frequência.','Clareza semântica e prevenção de confusão.')]),
('Aplicação: participação na pesquisa e confiabilidade',[
('Gravar ou interromper em uma única ação','Simplificar o comando de participação e apresentar símbolo e texto indicando o estado atual.','Visibilidade do estado e menor ambiguidade.'),
('Transporte independente da gravação','Permitir uso da aplicação mesmo com recusa ou indisponibilidade da pesquisa.','Liberdade de escolha e continuidade da tarefa.'),
('Tela em branco no acesso público','Tratar a falha de carregamento relatada e restabelecer a apresentação da interface.','Disponibilidade e recuperação de falhas.'),
('Gravação indisponível','Tratar a falha de inicialização, informar o problema e permitir nova tentativa sem impedir o uso do transporte.','Mensagens compreensíveis e recuperação.'),
('Interrupção, privacidade e feedback','Explicitar o que é capturado, interromper a captura quando solicitado e distinguir interrupção de exclusão de dados já enviados.','Transparência e controle do participante.'),
('Navegações de usuários como insumo','Considerar dificuldades observadas nas navegações e a lista interna de ajustes na revisão do protótipo.','Avaliação orientada às tarefas e ao contexto de uso.')]),
('Relatório: clareza, consistência e evidências',[
('Coerência entre relatório e aplicativo','Revisar as descrições das funcionalidades e dos fluxos para corresponder ao comportamento da versão avaliada.','Consistência da documentação e compreensão das tarefas do usuário.'),
('Legibilidade dos diagramas','Organizar os diagramas de arquitetura, estados, sequência e fluxos, com rótulos legíveis e relações explícitas.','Redução do esforço de interpretação e clareza dos modelos de interação.'),
('Explicação dos percursos e sentidos','Documentar a leitura de trechos, sentidos e retornos, distinguindo traçado cadastrado e informações em tempo real.','Clareza conceitual e prevenção de interpretações incorretas.'),
('Evidências e limites dos resultados','Distinguir funcionalidades implementadas, observações qualitativas, testes internos e medições ainda pendentes, sem apresentar projeções como resultados.','Rastreabilidade da avaliação e interpretação adequada dos resultados de IHC.'),
('Documentação da participação na pesquisa','Descrever consulta sem participação, estados da gravação, interrupção, retenção e solicitação de exclusão de forma compatível com a aplicação.','Transparência, liberdade de escolha e compreensão do controle disponível ao usuário.')])]

with zipfile.ZipFile(src) as z:
 root=E.fromstring(z.read('word/document.xml'));body=root.find(W+'body');sect=copy.deepcopy(body.find(W+'sectPr'))
 for c in list(body):body.remove(c)
 def p(text,bold=False,page=False):
  q=E.SubElement(body,W+'p');pr=E.SubElement(q,W+'pPr');sp=E.SubElement(pr,W+'spacing');sp.set(W+'after','100')
  if page:E.SubElement(pr,W+'pageBreakBefore')
  r=E.SubElement(q,W+'r');rp=E.SubElement(r,W+'rPr');sz=E.SubElement(rp,W+'sz');sz.set(W+'val','21');ft=E.SubElement(rp,W+'rFonts');ft.set(W+'ascii','Arial');ft.set(W+'hAnsi','Arial')
  if bold:E.SubElement(rp,W+'b')
  E.SubElement(r,W+'t').text=text
 p('REGISTRO DE FEEDBACK E ATUALIZAÇÃO — PONTO A PONTO',True)
 p('Thiago Almeida Amorim — Alameda Solutions',True)
 p('CNPJ: 60.184.290/0001-00 | Cargo/função: __________________________')
 p('Projeto Integrador — Grupo 17 — Univesp')
 p('Projeto: Sistema de acesso a informações do transporte público por QR Code em pontos de ônibus.')
 p('CRONOLOGIA INFORMADA',True)
 p('21/10/2026 — Primeiro feedback, referente às modificações realizadas até 21/10/2026.')
 p('25/10/2026 — Atualização do feedback, abrangendo as modificações e solicitações consolidadas até 25/10/2026.')
 p('O escopo da avaliação compreende exclusivamente o aplicativo Ponto a Ponto e o relatório acadêmico. O anexo consolida os ajustes desses dois materiais para conferência do avaliador. A inclusão no inventário não atribui todos os itens à avaliação de 21/10 nem comprova, por si só, a conclusão de cada pedido.')
 p('PARECER DE THIAGO — PARA CONFERÊNCIA E ASSINATURA',True)
 p('No primeiro feedback, em 21/10/2026, avaliei as melhorias realizadas até aquela data. Na atualização de 25/10/2026, considerei as modificações posteriores do aplicativo e do relatório, levantadas internamente pelo grupo e a partir das navegações de usuários. Considero que as melhorias efetivamente avaliadas foram devidamente implementadas e contribuíram para melhorar a qualidade da experiência de uso.')
 p('Sob a perspectiva de Interação Humano-Computador (IHC), o resultado é qualitativamente favorável à clareza das informações, à visibilidade do estado, ao controle da navegação, à prevenção de erros e à redução de esforço. No relatório, a avaliação considera a clareza da descrição, a consistência com o aplicativo e a apresentação das evidências e limitações.')
 p('As respostas do anexo detalham os ajustes e sua relação com IHC para conferência do avaliador. Não representam transcrição literal de falas nem resultados quantitativos de testes.')
 p('Referências da atualização de 25/10/2026: aplicativo 85417bc; relatório c18556c. Identificação completa e limites no anexo de versões.')
 p('________________________________________________________________')
 p('Ressalvas / itens do inventário não avaliados: ___________________________')
 p('________________________________________________________________')
 p('Divulgação identificada no relatório e na apresentação acadêmica: (  ) Autorizo (  ) Não autorizo')
 p('Local: ________________________ Data da assinatura: ____/____/________')
 p('')
 p('____________________________________________________________')
 p('Thiago Almeida Amorim — assinatura')
 n=0
 for title,items in groups:
  p('ANEXO — '+title.upper(),True,True)
  p('Atualização consolidada em 25/10/2026. Respostas e relação com IHC para conferência do avaliador.')
  for name,change,result in items:
   n+=1;p(f'{n:02d}. {name}',True);p('Pedido / resposta ao ajuste: '+change);p('Resultado relacionado à IHC: '+result)
 p('ANEXO — VERSÕES E CONFERÊNCIA DOCUMENTAL',True,True)
 p('Repositório: https://github.com/arianahuemura-ctrl/ponto-a-ponto')
 p('Aplicativo — branch feat/busca-bidirecional',True)
 p('Commit: 85417bccfb3b72ff287c5e2105840654e5b95ca1')
 p('Relatório — branch relatorio',True)
 p('Commit: c18556cb4a3f3bc733d9eab040f0d7f0755595b3')
 p('Documento principal: docs/relatorio_final/relatorio_final_pi2_v2.tex. A revisão de conteúdo está em 135e097d0b5413e61102beb02dd2b40048989886, incorporada ao commit de referência acima.')
 p('Esses commits fixam as versões disponíveis para a atualização de 25/10/2026. Sua correspondência aos materiais examinados é confirmada pelo avaliador abaixo. Não são atribuídos retroativamente ao primeiro feedback de 21/10/2026, cujo commit não foi identificado nos registros consultados.')
 p('Confirmo que as referências acima correspondem às versões que examinei: (  ) Sim (  ) Corrigir conforme indicação abaixo.')
 p('Correção de versão / material: _______________________________________')
 p('CONFERÊNCIA DOS ITENS',True)
 p('01–08: fluxos em SaoPaulo.jsx, CancelTripDialog.jsx e BoardDialog.jsx; seleção e favoritos. No item 04, o cancelamento remove embarque e destino, conforme código e relatório.')
 p('09–15: controles e legenda em SaoPaulo.jsx/SaoPauloMap.jsx; itinerários em backend/transit/sptrans/tracking.py; previsão e frequência em BoardDialog.jsx.')
 p('16–20: participação e estados em UsabilityConsent.jsx, usability.js e research.py. A presença desses mecanismos não garante disponibilidade permanente do serviço público; o item 18 deve ser confirmado no ambiente de acesso avaliado.')
 p('21: as navegações e os pedidos do grupo constituem insumos informados pelo grupo; sua ocorrência não é comprovada apenas pelo código.')
 p('22–26: relatório principal, diagramas e registros de revisão. A revisão de código é distinta da avaliação qualitativa de Thiago. Diagramas e efeitos sobre a experiência exigem apreciação do avaliador.')
 p('Ressalva documental: o relatório no commit de referência ainda emprega a identificação provisória Nath’s Brother na seção de avaliação externa. A identificação correta neste parecer é Alameda Solutions; essa denominação deverá ser harmonizada na próxima revisão do relatório.')
 p('CONFIRMAÇÃO DO ALCANCE DO PARECER',True)
 p('Itens que examinei: (  ) Todos os 26 itens (  ) Somente os itens: _____________')
 p('Conclusão qualitativa de IHC: (  ) Confirmo (  ) Confirmo com ressalvas (  ) Solicito revisão.')
 p('Ressalvas / ajustes à conclusão: _____________________________________')
 p('________________________________________________________________')
 p('Visto do avaliador: _____________________ Data: ____/____/________')

 if sect is not None:body.append(sect)
 with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as dst:
  for item in z.infolist():dst.writestr(item,E.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True) if item.filename=='word/document.xml' else z.read(item.filename))
print(n,'itens',out)
