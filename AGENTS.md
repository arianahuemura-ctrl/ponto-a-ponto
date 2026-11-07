# Continuidade do desenvolvimento

## Ao iniciar ou retomar uma sessão

- Leia `docs/CODEX_STATE.md` antes de planejar alterações. Consulte os documentos
  específicos ali vinculados somente conforme a tarefa exigir.
- Confira branch, HEAD, `git status --short`, `git diff --stat` e os últimos
  commits (`git log -5 --oneline`). Inspecione diffs por arquivo quando necessário.
- Não presuma que a conversa anterior foi recuperada integralmente, nem que o
  documento está atualizado. Confronte-o com os arquivos e o Git; registre
  divergências e distinga fatos verificados, registros anteriores e hipóteses.
- Alterações locais e arquivos não rastreados são trabalho existente. Preserve-os;
  não faça limpeza, reset, checkout restaurador, stash ou reescrita de histórico
  como parte de uma retomada. Não crie commits automaticamente.
- Leia eventuais instruções adicionais aplicáveis ao diretório em que trabalhar.

## Decisões e evidências

- Preserve as decisões técnicas documentadas e os contratos existentes. Mudanças
  necessárias devem ter motivação, impacto e evidências registrados no estado.
- Não confunda código presente, código commitado, teste aprovado e implantação.
  Não declare funcionalidades concluídas ou testes aprovados sem evidência.
- Mantenha distintas as informações simuladas, programadas e em tempo real.
  Preserve bancos, fontes, artefatos e a separação entre fontes de transporte.
- Consulte o estado antes de executar setup, importações, materializações ou
  recargas de serviços: esses comandos podem alterar dados e consumir muito disco.
- Nunca modifique, trunque ou exclua arquivos em `~/.codex/sessions`. Não use a
  leitura integral dos JSONL como procedimento de retomada.
- Não altere configurações globais do Codex sem apresentar previamente a
  justificativa e as consequências e obter autorização para a alteração.

## Saídas de ferramentas

- Evite saídas excessivamente grandes. Prefira `rg -n` com caminhos específicos,
  `rg --files`, intervalos de `sed`, `git diff --stat` e diffs por arquivo.
- Limite o volume antes de enviá-lo à ferramenta: selecione campos de JSON,
  agregue contagens e use paginação. Não despeje bases, bundles, logs, JSONL,
  lockfiles ou diretórios inteiros no contexto. Limite também o tamanho total
  dos lotes de comandos; muitos resultados pequenos podem formar uma saída grande.
- Use limites explícitos de saída quando a ferramenta permitir. Como referência
  local, procure ficar entre 1.000 e 3.000 tokens por chamada; amplie somente
  para examinar evidência relevante. Isso é orientação, não limite automático.
- Para testes e comandos verbosos, redirecione stdout e stderr a um arquivo novo
  em diretório exclusivo sob `.cache/setup/`, já ignorado pelo Git. Informe o
  comando, código de saída, totais, falhas relevantes e caminho do log completo.
- Não use `comando | head` ou `comando | tail` para executar testes: isso pode
  interromper o produtor ou mascarar seu código de saída. Capture o resultado
  primeiro, depois leia trechos do arquivo. Nunca sobrescreva logs anteriores.
- Em erros, examine trechos delimitados e expanda conforme necessário. Um resumo
  não deve esconder falhas, testes ignorados, limites ou verificações não feitas.
- Não copie segredos, `.env`, dados pessoais de pesquisa ou logs sensíveis para
  os documentos de continuidade. Veja exemplos em `docs/CODEX_CONTINUITY.md`.

## Ao concluir uma etapa relevante

- Atualize `docs/CODEX_STATE.md` após mudanças de arquitetura ou comportamento,
  validações importantes, descoberta de impedimentos e antes de encerrar uma
  etapa com trabalho pendente. Não dependa de uma futura compactação bem-sucedida.
- Registre data, branch/commit de referência, alterações ainda sem commit,
  decisões, pendências e próximo passo concreto. Para testes, registre comando,
  escopo, resultado e evidência; marque explicitamente o que não foi executado.
- Mantenha o estado como resumo atual, substituindo informação obsoleta. Detalhes
  e logs ficam em documentos/artefatos referenciados; o Git preserva a evolução
  quando os arquivos forem commitados pelo fluxo normal do projeto.
- Valide links locais e coerência do documento. Para alterações só documentais,
  não execute importações ou testes pesados sem necessidade.
