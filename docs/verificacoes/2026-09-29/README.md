# Verificação do relatório — 29/09/2026

Código testado: `a60f290`, branch `relatorio`; alterações pendentes restritas à documentação.

| Verificação | Resultado |
| --- | --- |
| Django: `python backend/manage.py test transit` | 65 aprovados |
| JavaScript: `npm test` em `frontend/` | 10 aprovados |
| Playwright: `npm run test:e2e` em `frontend/` | 13 aprovados |

Total: 88 testes sem falhas. O Playwright compilou o frontend e iniciou o servidor com SQLite temporário, conforme `backend/e2e_server.py`. Os testes não validam coordenadas em campo nem a experiência da comunidade.

Ambiente: Python 3.14.4, Django 6.0.8, Node.js 22.22.1. O Node disponível difere do requisito 24 do projeto; o sucesso desta execução não altera o requisito declarado. Saídas preservadas em `django.txt`, `javascript.txt` e `playwright.txt`.

## Datas das fontes

`datas_fontes.csv` registra todos os documentos do manifesto `fonts/collected.json` e os arquivos locais principais. Datas locais usam America/Sao_Paulo (UTC−03); coleta e Last-Modified mantêm a representação original. Campos vazios indicam informação ausente. O levantamento não acessou novamente os provedores e não importou novos dados. Modificação local, coleta, data-base e vigência operacional são conceitos distintos.

## Atualizações informadas pelo grupo

O mockup interativo no Figma foi concluído e suas telas são idênticas às imagens já utilizadas no relatório. O cargo adotado para Osmar Junior é gerente de Transportes Públicos de Mauá. O cabeçalho do e-mail fornecido em captura mostra 02/09/2026 às 19h42. Essas informações não constituem avaliação do protótipo pelo interlocutor.

## Conferência do banco local

Consulta somente de leitura em 29/09/2026: 1.616 paradas, 172 com coordenadas, 233 linhas/variantes não demonstrativas e seis demonstrativas. Os totais coincidem com os do inventário de 24/09 descrito no relatório; isso não atesta atualização operacional.
