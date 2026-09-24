# Requisitos implementados

| Requisito do PI2 | Implementação |
|---|---|
| Python/Django + React | API Django; componentes React e mapa Leaflet |
| Base OSM de Mauá | Recorte local com origem/licença e links por objeto |
| Complementar lacunas para demonstração | Rede DEMO independente, documentada e reproduzível |
| Acesso sem conhecer linha, ponto ou endereço | QR identifica a origem pela URL; dispensa instalação e GPS |
| Gerar material de demonstração | QR em SVG e cartão imprimível por parada |
| Próximos ônibus de várias linhas | Quadro consolidado e veículos no mesmo mapa |
| Destino no mapa | Todas as paradas selecionáveis, incluindo destinos com troca |
| Destino em outro local | Clique livre, endereço ou localização com paradas próximas |
| Filtrar automaticamente | Alternativas e veículos determinados pelo destino |
| Dijkstra | Eventos temporais, espera, sentido, embarques e reconstrução |
| Viagens posteriores | Ônibus posteriores são examinados, incluindo expressos |
| Baldeações | Tempo mínimo, limite configurável e instruções por trecho |
| Previsão/duração | Horário de embarque, chegada, espera, viagem e caminhada |
| Detalhes e acompanhamento | Sequência de paradas e viagem fixa durante simulação |
| Dados mockados | Horários e posições derivados do mesmo cenário |
| Apresentação repetível | Estado e relógio global configurados na administração Django |
| Favoritos e preferências web | Casa/Trabalho/Escola, locais livres, remoção e persistência local |
| Interface dos mockups | Sete telas móveis, cabeçalho Meu Ponto, cartões, abas e navegação inferior |
| Trajetos viários | Geometrias OSM/OSRM locais e veículos percorrendo as ruas |
| Administração separada | Login, permissões e controle persistente da simulação |
| Registro da avaliação | Formulário, SQLite e exportação pelo servidor |
| Robustez | Erros de API, QR inválido, ausência de conexão e armazenamento bloqueado |
| Verificação | Testes de domínio, APIs e navegador com Django real |

## Fora desta etapa

Por orientação expressa do usuário, **Android, APK e PWA não foram implementados**.
Favoritos nesta etapa pertencem à aplicação web e ficam no navegador, sem conta
ou sincronização entre aparelhos.

Integração com dados operacionais reais, validação de itinerários, instalação
de adesivos nos pontos, apresentação efetiva a Osmar e publicação em servidor
externo dependem de dados ou ações externas. A aplicação entrega os instrumentos
para demonstrar e registrar a avaliação; não afirma que essa avaliação ocorreu.

O relatório parcial continua sendo o documento de concepção fornecido pelo
grupo. Este inventário registra o que foi implementado no código, sem reescrever
retroativamente resultados de campo nem transformar simulações em dados reais.
