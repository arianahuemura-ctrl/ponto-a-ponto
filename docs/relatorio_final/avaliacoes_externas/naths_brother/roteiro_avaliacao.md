# Roteiro de avaliação técnica externa

**Situação:** preparação; avaliação ainda não realizada. “Nath's Brother” é uma identificação provisória. Contato previsto por intermédio de Nathália Almeida Amorim.

## Preparação e registro

1. Confirmar nome oficial da empresa, CNPJ se aplicável, nome e função do avaliador, disponibilidade e modalidade acordada.
2. Registrar a data de envio e os materiais efetivamente disponibilizados: nome do PDF, data, versão e hash; revisão da aplicação e endereço temporário, se houver demonstração. Não presumir acesso ao código ou à aplicação.
3. Apresentar o escopo: necessidades levantadas em Mauá e implementação funcional com dados de São Paulo. A avaliação técnica não substitui a avaliação com passageiros nem representa a gestão municipal.
4. Para cada resposta, indicar a origem: **análise documental**, **demonstração observada** ou **teste executado pelo avaliador**. Usar “não examinado” quando necessário.
5. Em testes, registrar tarefa, versão, dispositivo/navegador, condições, resultado observado e evidência. Não usar dados pessoais reais desnecessários ou fornecer credenciais administrativas e bases de telemetria.

## Questões para análise

| Eixo | Questões propostas |
|---|---|
| Arquitetura | A organização dos componentes e a separação entre frontend e backend estão claras? Como são descritas persistência, procedência, atualização e integração dos dados? |
| Planejamento híbrido | O relatório explica a recuperação de candidatos materializados, a validação das caminhadas, a avaliação temporal, o refinamento operacional quando disponível e o retorno progressivo? Fica claro que o planejador por rodadas é fallback condicional, sem execução simultânea dos planejadores em produção? |
| Origem e destino | A identificação do embarque está compreensível? O acesso por QR Code/link abre os próximos ônibus; selecionar origem no mapa permite continuar para o destino; selecionar destino solicita alternativas. Os fluxos e seus equivalentes por clique longo estão claros? |
| Alternativas | Percursos, caminhadas, baldeações, horários programados e previsões operacionais são distinguíveis? Como indisponibilidade de dados e ausência de alternativas são comunicadas? |
| Favoritos e acompanhamento | O uso e a persistência local dos favoritos estão explicados? O acompanhamento operacional informa fonte, atualização e limitações? |
| Qualidade técnica | A estrutura da solução facilita manutenção? Quais limitações estão documentadas ou precisam ser esclarecidas? Quais dependências externas e condições de implantação merecem atenção? |
| Segurança e privacidade | O material explica categorias de dados coletados, finalidade, consentimento, recusa, retenção, acesso e exclusão? Há divergências aparentes entre aviso, documentação e comportamento observado? Registrar dúvidas sem presumir conformidade ou realizar testes invasivos. |
| Experiência do usuário | A proposta e as informações são claras? A navegação parece fácil de compreender? Quais dificuldades podem surgir? Distinguir essa apreciação técnica de evidência obtida em tarefas com passageiros. |
| Recomendações | Quais mudanças são recomendadas, por qual motivo e com qual prioridade? Que observação ou evidência sustenta cada recomendação? |

## Encerramento

Registrar respostas no registro de feedback, inclusive limitações e itens não examinados. Não preencher resultados de benchmark pendentes. Submeter a redação do parecer ao avaliador para correção e aprovação antes de assinar. Relacionar sugestões às decisões e evidências na matriz; o grupo responde pelas decisões de implementação. Confirmar como o avaliador autoriza sua identificação e a inclusão do parecer na entrega acadêmica.
