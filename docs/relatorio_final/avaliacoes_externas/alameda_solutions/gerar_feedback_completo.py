from pathlib import Path
from lxml import etree as E
import zipfile,copy
src=(Path(__file__).resolve().parent/'modelo_termo.docx');out=(Path(__file__).resolve().parent/'Registro_feedback_Thiago_Alameda_Solutions.docx');W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
groups=[('Aplicação: entrada, escolhas e continuidade da navegação',[
('Entrada por QR Code e localização','Identificar o embarque e evitar redigitação desnecessária da origem.','Reconhecimento em vez de memorização; redução de esforço.'),
('Busca e seleção de origem e destino','Aprimorar a busca, selecionar paradas ou coordenadas por toque prolongado e evitar seleção acidental durante arrasto ou gesto com dois dedos.','Prevenção de erros e adequação ao uso móvel.'),
('Alteração do embarque','Conservar o destino ao mudar a origem e reenquadrar o mapa para manter o contexto da consulta.','Continuidade da tarefa e controle do usuário.'),
('Cancelamento de viagem','Explicar as consequências, permitir desistir da ação e preservar embarque e favoritos ao confirmar.','Prevenção de erros e possibilidade de recuperação.'),
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
('Apresentação audiovisual: personagens, voz e composição',[
('Resíduos atrás dos avatares','Remover fundos remanescentes, inclusive em cenas sem mapa, e assegurar recorte transparente.','Legibilidade e ausência de interferência visual.'),
('Altura e posição dos personagens','Normalizar a altura, manter centro horizontal comum e margem direita definida pelo personagem mais largo; evitar saltos de posição.','Consistência visual.'),
('Representação de Leonardo e Nathalia','Substituir Johnny Bravo exclusivamente por Edward Elric; substituir Botan por Frieren, incluindo as vozes solicitadas.','Coerência entre identidade visual e sonora.'),
('Ruído nas vozes e apresentações','Revisar as apresentações de Freeza e Leonardo e a voz metálica do Edward, usando a nova referência indicada.','Inteligibilidade e conforto auditivo.'),
('Identificação de Procópio e trecho mudo','Usar Procópio na apresentação falada e corrigir o trecho de Caio/Naruto sem áudio.','Compreensão da identificação e continuidade sonora.'),
('Participação real de André','Substituir somente André pela gravação enviada, selecionar a última tomada válida das frases repetidas e adequar as telas ao ritmo da fala.','Sincronização entre explicação e demonstração.'),
('Recorte e iluminação da imagem real','Remover o fundo verde, normalizar a imagem, alinhar o nome ao centro visual e corrigir diferenças de iluminação.','Uniformidade e foco no apresentador.'),
('Fundos ao longo de todo o vídeo','Revisar fundos atrasados, retângulos claros e blocos sólidos nas transições, além dos exemplos inicialmente apontados.','Continuidade visual e redução de distrações.')]),
('Apresentação audiovisual: mapas, texto e encerramento',[
('Cena com lâmpada apagada','Reduzir os marcadores na demonstração em que sua exibição poluía o mapa.','Hierarquia visual e atenção ao conteúdo relevante.'),
('Comparação Google Maps e Moovit','Aproximar o enquadramento e uniformizar o tamanho dos painéis, preservando percursos e identificação das fontes.','Comparabilidade e leitura.'),
('Tela seguinte à comparação','Aplicar zoom e recorte análogos e retirar as ferramentas de navegação da composição solicitada.','Consistência entre telas consecutivas.'),
('Trechos considerados desnecessários','Retirar as frases sobre ainda verificar os sinais com passageiros e ainda precisar de avaliação com passageiros nos pontos indicados do roteiro.','Concisão da apresentação; a edição não substitui evidências de avaliação.'),
('Legendas sem sobreposição','Evitar cobrir os personagens e organizar as frases para não iniciar uma nova sentença no fim do bloco anterior.','Legibilidade e segmentação do discurso.'),
('Legendas externas e fala real','Manter VTT separado para o vídeo principal, evitar duplicação por legenda incorporada e atualizar o texto conforme a fala efetivamente gravada.','Acessibilidade e correspondência entre áudio e texto.'),
('Encerramento abrupto','Preservar o final de “Obrigado pela atenção” e manter tempo adicional antes de encerrar o filme.','Ritmo e percepção de conclusão.'),
('Distribuição das participações','Considerar o pedido de levantamento do tempo de fala de cada participante na revisão da apresentação.','Equilíbrio da comunicação; não se registra aqui uma medição não anexada.')]),
('Materiais de apoio à gravação e documentação',[
('Guia para leitura','Preparar vídeo com fundo branco, nome do participante e texto de apoio, mantendo o áudio de referência.','Orientação durante a gravação.'),
('Posição e tamanho do texto','Criar versão com texto próximo à câmera e outra de leitura ampliada para o segundo celular, em orientação horizontal.','Legibilidade e adequação ao contexto de gravação.'),
('Ritmo de fala e pausas','Usar destaque amarelo claro, mostrar o texto dois segundos antes da fala e mantê-lo por mais dois segundos ao terminar.','Antecipação e acompanhamento do ritmo.'),
('Contagem e treino de repetição','Considerar as versões solicitadas com espera inicial de 15 e 30 segundos, avisos sonoros e pausa para repetir cada frase.','Preparação e orientação temporal; são variantes de apoio.'),
('Revisão posterior do guia','Considerar a retirada de bips, apresentações completas com o nome e os intervalos entre falas, respeitando as especificações de cada versão.','Controle da carga de atenção; pedidos sucessivos não são cumulativos quando incompatíveis.'),
('Acesso e controle do celular','Considerar a preferência pelo Chromium e os testes de WebADB/Tango para controle por mouse.','Apoio operacional; os problemas de compatibilidade relatados não constituem melhoria comprovada do PaP.'),
('Autorizações e feedback','Identificar Alameda Solutions e Thiago, registrar as duas datas de feedback e disponibilizar documentos editáveis e PDFs para assinatura.','Rastreabilidade da avaliação e clareza documental.')])]
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
 p('O inventário anexo reúne os pedidos disponíveis na conversa e os registros do projeto. A aplicação, a apresentação audiovisual e os materiais de apoio estão identificados separadamente. A inclusão no inventário não atribui todos os itens à avaliação de 21/10 nem comprova, por si só, a conclusão de cada pedido.')
 p('PARECER DE THIAGO — PARA CONFERÊNCIA E ASSINATURA',True)
 p('No primeiro feedback, em 21/10/2026, avaliei as melhorias realizadas até aquela data. Na atualização de 25/10/2026, considerei as modificações posteriores, levantadas internamente pelo grupo e a partir das navegações de usuários. Considero que as melhorias efetivamente avaliadas foram devidamente implementadas e contribuíram para melhorar a qualidade da experiência de uso.')
 p('Sob a perspectiva de Interação Humano-Computador (IHC), o resultado é qualitativamente favorável à clareza das informações, à visibilidade do estado, ao controle da navegação, à prevenção de erros e à redução de esforço. Os ajustes audiovisuais contribuem para a compreensão da demonstração; não substituem a avaliação do uso da aplicação.')
 p('As respostas do anexo detalham os ajustes e sua relação com IHC para conferência do avaliador. Não representam transcrição literal de falas nem resultados quantitativos de testes.')
 p('Versão do protótipo e materiais efetivamente avaliados: ___________________')
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
 p('Fim do inventário. Itens de apoio operacional e variantes de gravação não devem ser apresentados como funcionalidades da aplicação.')
 if sect is not None:body.append(sect)
 with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as dst:
  for item in z.infolist():dst.writestr(item,E.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True) if item.filename=='word/document.xml' else z.read(item.filename))
print(n,'itens',out)
