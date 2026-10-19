# Arquitetura do Fiscalia

## Mapa e limites da análise

A análise inicial com Graphify está versionada em [GRAPH_REPORT.md](../graphify-out/GRAPH_REPORT.md), [grafo interativo](../graphify-out/graph.html) e [grafo JSON](../graphify-out/graph.json). Foram analisados 95 arquivos: o resultado consolidado possui 596 nós, 1.212 arestas e 56 comunidades. Os principais pontos de conexão são notícias, análise de IA, coleta, resumos e seus testes.

O grafo representa o estado anterior à adaptação SaaS. Este documento descreve o funcionamento final. A extração semântica complementou a AST para documentação e imagens. O [relatório de saúde](../graphify-out/HEALTH.txt) registra 216 referências sem destino, uma autorreferência e 22 relações direcionais colapsadas; o grafo auxilia a navegação e não prova correção do código. O contador de tokens do gerador não estava disponível: os zeros do relatório não representam consumo real zero.

## Requisição e isolamento

1. Django autentica a sessão. `WorkspaceMiddleware` seleciona uma associação ativa que pertence à conta, usando a escolha salva na sessão ou a primeira associação válida.
2. A requisição recebe `workspace` e `membership`. O contexto de execução guarda o espaço e o usuário em `ContextVar`, com restauração ao terminar a requisição.
3. `WorkspaceManager` limita consultas ao espaço atual; sem contexto retorna conjunto vazio. `PersonalManager` acrescenta o usuário para leitura, acompanhamento e lembretes.
4. As views validam o papel no servidor. Esconder botões é apenas a representação visual da mesma permissão.
5. Respostas autenticadas usam `Cache-Control: private, no-store`.

`all_objects` é uma saída deliberada para operações confiáveis: migrações, bootstrap e descoberta inicial do espaço de um job. Não o utilize em views ou consultas derivadas de identificadores recebidos do navegador. Modelos e IDs acessados nas páginas precisam continuar passando pelo escopo.

## Dados

`Workspace` representa um grupo. `Membership` liga conta e grupo, com unicidade por par e papel leitor/editor/administrador. O usuário Django representa a identidade global; ser administrador de grupo não concede `is_staff` ou `is_superuser`.

Fontes, tags, notícias, análises, jobs e resumos pertencem ao espaço. A URL da fonte e o nome da tag são únicos dentro dele. A notícia não pode referenciar fonte de outro espaço. Categorias de fonte são catálogo global. `NewsItemRead`, `NewsItemFollow` e `NewsItemReminderNotification` mantêm preferências individuais. Contagens e filtros usam essas relações individuais.

As migrações `0016` e `0017` preservam o acervo, introduzem as relações de acesso e garantem uma coleta ativa por espaço. `0018` guarda contadores de tentativas de autenticação. Não altere migrações aplicadas; crie uma nova para evoluções futuras.

## Coleta e IA

O botão de atualização cria ou reutiliza um job ativo. O worker reivindica atomicamente um job pendente, estabelece o contexto do espaço e fecha conexões ao terminar. A interface acompanha etapas e progresso. O comando `process_news_jobs` permite retomar pendências de um espaço após falha do processo.

`safe_http` valida HTTP/HTTPS, portas e endereços públicos, verifica todas as respostas DNS e conecta ao IP validado, preservando Host, SNI e verificação TLS. Redirecionamentos passam pela mesma validação. Limites de redirecionamento, tamanho descomprimido, leitura e quantidade de entradas reduzem consumo abusivo. Resolução DNS ainda depende dos limites do sistema operacional.

O RSS é importado mesmo com IA desativada ou indisponível. A extração da matéria usa a mesma proteção de rede. Análises e resumos são compartilhados somente dentro do espaço; preferências de usuário não são enviadas ao provedor. Falhas conhecidas recebem mensagens úteis; falhas inesperadas são registradas no servidor e apresentadas de forma genérica.

## Estrutura mantida

- `feeds/models/`, `forms/`, `views/`, `admin/` e `tests/`: módulos por domínio ou página.
- `feeds/services/`: coleta, acesso HTTP, IA, resumos, preferências e controle de tentativas.
- `feeds/tenancy.py`, `permissions.py`, `middleware.py`: contexto e regras transversais de acesso.
- `templates/pages/`, `templates/layouts/`: telas e elementos comuns.
- `static/css/components/`, `layouts/`, `pages/` e `static/js/pages/`: padrões existentes de apresentação e interação.
- `static/vendor/lucide/`: versão local com licença e hash de origem, sem script remoto mutável para os ícones.

## Evolução de infraestrutura

O código recebe `DATABASE_URL`, usa migrações Django e inclui o driver PostgreSQL. Desenvolvimento e testes locais usam SQLite. PostgreSQL, migração dos dados reais, concorrência com múltiplos processos, backups/restauração, HTTPS, estáticos e execução durável da coleta ainda exigem implantação e validação na tarefa de INFRA. Alterar apenas a URL não transfere o conteúdo do SQLite.
