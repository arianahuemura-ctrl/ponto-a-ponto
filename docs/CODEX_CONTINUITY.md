# Continuidade baseada no repositório

Diagnóstico e procedimento estabelecidos em 02/11/2026. Ponto de entrada:
[AGENTS.md](../AGENTS.md); resumo atual: [CODEX_STATE.md](CODEX_STATE.md).

## Diagnóstico e alcance

- Foram relatados históricos JSONL maiores que 800 MB, falhas de compactação
  remota e desconexões WebSocket. Os arquivos de sessões não foram inspecionados
  nem manipulados nesta investigação; tamanho e causa dos incidentes não foram
  aferidos independentemente. Tamanho em disco não mede diretamente os tokens
  ativos enviados ao modelo.
- O repositório não tinha `AGENTS.md` local nem resumo de continuidade. Na
  inspeção havia 56 arquivos rastreados modificados e 157 não rastreados, além
  de dados ignorados pelo Git. Retomar só pelo HEAD perderia contexto de trabalho.
- Há relatórios de gerações diferentes do planejador. Ler tudo indiscriminadamente
  acrescenta volume e pode confundir uma medição histórica com o estado vigente.
- Saídas extensas de código/documentos atingiram limites de retorno durante a
  própria inspeção. Limitar apenas a saída final da ferramenta não garante que
  os trechos relevantes sobrevivam: selecionar arquivos e campos antes de imprimir
  é mais útil. Não se mediu a contribuição de cada ferramenta aos JSONL antigos.

A estratégia é manter um resumo pequeno do estado atual e instruções locais de
retomada, com referências às evidências completas. Ela reduz a dependência da
conversa anterior e o volume futuro desnecessário; não repara WebSocket,
compactação remota ou arquivos de histórico já existentes.

## Retomada e atualização

1. Leia o estado; confira branch, HEAD, status e estatística dos diffs. Não
   restaure a árvore para igualar o documento: atualize sua compreensão.
2. Leia apenas os módulos, diffs e relatórios necessários para a tarefa.
   Datas, base de dados, escopo e código testado fazem parte de cada evidência.
3. Depois de uma etapa relevante, atualize o resumo com resultado, decisão,
   pendência, teste e próximo passo. Prefira substituir estado obsoleto a
   acumular transcrições de comandos ou um diário ilimitado.
4. Se houver interrupção, recomece pelos arquivos e verifique o que de fato
   terminou. Um processo iniciado ou um arquivo parcial não comprova sucesso.
5. Versione os documentos junto às mudanças pelo fluxo habitual de revisão.
   Enquanto não houver commit, outra sessão no mesmo diretório os encontrará,
   mas um novo clone não recuperará arquivos locais, dados ignorados ou logs.
   Esta tarefa não criou commit nem alterou o histórico Git.

## Como reduzir resultados enviados ao contexto

| Necessidade | Procedimento |
| --- | --- |
| Descobrir código | `rg --files` com diretório/glob; depois `rg -n` com padrão específico. Excluir dados gerados e caches. |
| Examinar alterações | `git diff --stat`, depois `git diff -- caminho/do/arquivo`; evitar o diff integral de toda a árvore. |
| Ler documento grande | Buscar títulos/termos e abrir intervalos de linhas. Não concatenar todos os documentos. |
| Ler JSON/JSONL | Extrair campos e contagens com Python; para JSONL volumoso, processar linha a linha e imprimir só resumo/amostra limitada. |
| Executar testes | Salvar stdout/stderr em log exclusivo; exibir código de saída, totais e falhas. Abrir mais contexto do erro sob demanda. |
| Consultar conectores | Usar filtros, paginação e seleção de campos; resumir a resposta antes de repassá-la, quando a ferramenta permitir. |

Adote limites de retorno explícitos (`max_output_tokens` ou equivalente, quando
disponível) e controle também a soma dos resultados de chamadas agrupadas.
Um alvo local de 1.000–3.000 tokens por chamada costuma bastar para triagem;
não é uma configuração imposta ao cliente. Expanda quando necessário para não
ocultar evidência. Não reimprima resultados completos já resumidos.

Exemplo executado a partir da raiz, compatível com shell POSIX, para uma
**nova execução** de testes (não para tratar históricos existentes):

```sh
mkdir -p .cache/setup
log_dir=$(mktemp -d .cache/setup/codex-run.XXXXXX) || exit 1
if npm --prefix frontend test >"$log_dir/javascript.log" 2>&1; then
  command_rc=0
else
  command_rc=$?
fi
printf 'command=npm --prefix frontend test\nexit_code=%s\n' "$command_rc" >"$log_dir/result.txt"
printf 'exit_code=%s log=%s/javascript.log\n' "$command_rc" "$log_dir"
tail -n 15 "$log_dir/javascript.log"
(exit "$command_rc")
```

O diretório exclusivo evita sobrescrever logs. O código de saída é preservado;
o `tail` atua no arquivo após a execução. Em falha, leia também o bloco do erro,
não apenas as últimas linhas. Para Django, substitua o comando e registre seu
escopo real. Não use `tee` sem necessidade: ele envia novamente todo o log ao
contexto. Não aplique filtros destrutivos ou truncamento ao arquivo completo.

`.cache/setup/` já está no `.gitignore`; os logs ficam disponíveis nesta máquina,
sem poluir o status. Quando uma evidência precisar acompanhar o repositório,
prepare um resumo sem segredos/dados pessoais em `docs/verificacoes/` ou
`artifacts/benchmarks/`, indicando onde consultar o original. Não copie sessões.

## Configuração do Codex investigada, sem alterações

A [referência oficial de configuração](https://learn.chatgpt.com/docs/config-file/config-reference)
documenta `tool_output_token_limit` como orçamento em tokens para armazenar cada
resultado de ferramenta no histórico. Um valor menor pode reduzir o conteúdo
retido, mas também omitir diagnósticos; não limita o total acumulado nem reduz
retroativamente arquivos existentes. Sua aplicação depende do cliente/versão.

A mesma referência descreve `model_auto_compact_token_limit` como limiar de
compactação automática. Alterá-lo muda quando compactar; não é correção
demonstrada para falhas remotas. Diminuí-lo pode aumentar a frequência de
compactações, e aumentá-lo pode ampliar o contexto entre elas.

Na leitura seletiva de `~/.codex/config.toml`, não estavam explicitadas no nível
superior as chaves `tool_output_token_limit`, `model_auto_compact_token_limit`,
`model_context_window` ou `project_doc_max_bytes`. Isso não determina valores
efetivos: padrões, perfis e o cliente podem influenciá-los. Nenhum outro conteúdo
da configuração foi exposto; não se alteraram configurações globais ou locais.

A [documentação oficial de AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
descreve instruções por diretório e limites de tamanho. Por isso, o arquivo de
instruções aqui permanece curto e aponta para o estado, em vez de incorporar
logs. Essas regras orientam o agente; não instalam um filtro automático de saídas.

Qualquer ajuste futuro de configuração global exige primeiro apresentar chave,
escopo, justificativa, consequências e forma de reversão, obtendo autorização.
A solução desta etapa usa apenas documentação no repositório e captura local
de novas saídas. Não modifica, trunca ou exclui `~/.codex/sessions`, não limpa
arquivos de trabalho e não reescreve histórico Git.
