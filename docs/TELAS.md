# Telas de referência e implementação

As imagens mockup1.png a mockup8.png do relatório PI2 orientam a interface.
A aplicação reproduz a estrutura visual: marca “Meu Ponto”, azul principal,
fundo branco, cartões de linhas com códigos coloridos, abas e navegação inferior.
A moldura de telefone e a barra de status fictícia das imagens não fazem parte
da página web; o próprio dispositivo fornece essa área.

| Referência | Tela / acesso |
|---|---|
| Mockup 1 | Mais → QR Code deste ponto → Imprimir sinalização |
| Mockup 2 | Início; entrada por URL do QR identifica automaticamente o ponto |
| Mockup 3 | Ver linhas deste ponto / Horários |
| Mockup 4 | Buscar destino no mapa → selecionar local → Confirmar destino |
| Mockup 5 | Linhas que atendem origem e destino |
| Mockup 6 | Ver essas linhas no mapa |
| Mockup 7 | Detalhes da linha → Horários |
| Mockup 8 | Detalhes → Mapa da linha / Itinerário |

Códigos de linha, nomes de locais e previsões são dados, não texto fixo de imagem.
A aplicação usa valores consistentes com o cenário e exibe baldeações quando
necessárias. Os nomes MAU-001 e os códigos de linha são identificadores locais
ilustrativos; os IDs OSM originais ficam preservados.

## Separação da administração

A navegação do passageiro contém somente Início, Horários, Favoritos e Mais.
O estado da simulação é informado discretamente, sem ações para ligá-la,
desligá-la, pausar o relógio ou trocar de cenário.

A página separada /admin/ usa autenticação e permissões do Django. O controle
é persistente, global e lido no servidor. Desligar a simulação retira os dados
operacionais; não os substitui por previsões reais inexistentes.

## Geometria e mapas

Os percursos são polilinhas viárias locais derivadas do OSM via OSRM. As curvas
das ruas ficam destacadas, com contorno branco e cores das linhas. A posição
dos veículos é interpolada por distância ao longo da mesma geometria.
Ausência de geometria não gera uma linha reta substituta.

Testes de navegador produzem capturas das sete telas em test-results. Os tiles
do mapa são bloqueados nesses testes para deixá-los independentes da internet;
na utilização normal, o fundo vem do OpenStreetMap com atribuição visível.
