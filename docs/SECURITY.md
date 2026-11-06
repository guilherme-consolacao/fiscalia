# Segurança e preparação para publicação

## Revisão de 19/10/2026

Foram revisados autenticação, autorização, isolamento entre espaços, preferências individuais, entradas JSON/datas, CSRF, coleta de URLs externas, execução de jobs, cabeçalhos, dependências e exposição de erros. As correções incluem consultas fechadas sem contexto, restrição do Django Admin ao superusuário, limite persistente de tentativas, proteção contra requisições à rede interna e remoção de mensagens inesperadas detalhadas das respostas.

`requirements.txt` contém versões fixadas. Django foi atualizado para 5.2.18, idna para 3.15, sqlparse para 0.6.0 e urllib3 para 2.8.0 após a auditoria de dependências de 19/10/2026.

Os ícones Lucide são servidos localmente; licença, versão e SHA-256 estão em `static/vendor/lucide/`. O VLibras é opcional e carrega JavaScript externo somente após acionamento. Sua política de conteúdo permite as origens oficiais e o caminho da versão 7.12.2 no CDN. Revisar os redirecionamentos e a CSP quando o serviço atualizar. Estilos inline permanecem permitidos para o comportamento visual existente e para o widget; scripts inline arbitrários não são permitidos.

## Evidências de validação

- 217 testes Django passaram, incluindo regressões, isolamento, papéis, preferências individuais, URLs/redirecionamentos inseguros, CSRF, tentativas de login, identidade preservada na troca de equipe e migração de acervo de `0015` até a versão atual. A [matriz de testes](TESTING.md) registra a cobertura e as revisões de densidade, responsividade e identificação de conta/equipe.
- Testes de IA usam chave fictícia e respostas simuladas, incluindo erros HTTP, limite de uso e parsing. Nenhuma chamada paga foi necessária para a suíte.
- Validação manual no segundo Chrome: cadastro/login, fontes, modal por teclado/Escape/retorno de foco, contraste e reflow em quadros de 390/320 px, carregamento e ocultação do VLibras e continuidade do portal quando o script externo falha.
- A validação de layout não equivale a certificação WCAG. Não foi executada uma sessão completa com leitor de tela real.
- Após restaurar a janela do segundo Chrome e colocá-la em primeiro plano, o avatar 3D inicializou. O clique em um texto iniciou a tradução, o controle mudou para Pausar e foi possível pausar a reprodução. A falha inicial e a tentativa novamente também foram observadas no widget oficial em página mínima; o teste final de tradução foi realizado dentro do portal.
- `check --deploy --settings=config.production`, `makemigrations --check --dry-run` e `pip check` passaram. O primeiro foi executado com configuração local de validação e não substitui a verificação dos hosts, TLS e proxy reais.

Comandos reproduzíveis:

```bash
python manage.py test --settings=config.test_settings
python manage.py makemigrations --check --dry-run
python manage.py check
python -m pip install pip-audit==2.10.1
python -m pip_audit -r requirements.txt
```

## Proteção do login e revisão de 05/11/2026

- Cinco falhas para o mesmo identificador, dentro de 15 minutos, iniciam um bloqueio de 15 minutos a partir da quinta falha. Durante o bloqueio, a senha não é verificada, a resposta é `429` com `Retry-After` e novas tentativas não prolongam a espera. Um login bem-sucedido zera as falhas antes do bloqueio.
- Portal e Django Admin compartilham o contador por identificador normalizado. Tentativas com conta desconhecida recebem o mesmo tratamento. A barreira adicional permite dez envios de credenciais por origem a cada 15 minutos, somando os dois formulários de login. O cadastro mantém seu limite independente. Requisições rejeitadas por CSRF não consomem tentativas.
- A aplicação persiste os contadores no banco com chaves derivadas por HMAC, sem armazenar IP, identificador ou senha em claro. A autenticação é serializada por conta no PostgreSQL. A aplicação registra o início do bloqueio sem dados da conta. A espera temporária limita o impacto de bloqueios intencionais contra contas conhecidas. A barreira de origem depende do IP fornecido por um proxy confiável, a validar na INFRA.
- `pip-audit` encontrou o aviso crítico [GHSA-6q48-6c7w-9gw2](https://github.com/certifi/python-certifi/security/advisories/GHSA-6q48-6c7w-9gw2) no Certifi. Após atualizar para 2026.10.23 e incluir o `defusedxml`, a nova consulta não encontrou vulnerabilidades conhecidas nas dependências declaradas. O `defusedxml` impede a expansão de entidades nos documentos XML das fontes e a coleta segue para as demais fontes após rejeitar um documento.
- O Bandit 1.9.4 apontou o parser de XML, corrigido nesta revisão. O alerta `B113` restante foi conferido manualmente. O resumo semanal passa um timeout inteiro explícito de `NEWS_AI_TIMEOUT_SECONDS` para `requests.post`. A execução de `check --deploy` também passou em configuração local.

A [matriz de testes](TESTING.md) registra a validação no PostgreSQL, no SQLite e no segundo Chrome. A política de bloqueio segue as recomendações de [autenticação da OWASP](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html#login-throttling).

## Configuração de produção

Defina `DJANGO_SETTINGS_MODULE=config.production` no processo WSGI/ASGI e nos comandos do ambiente. Essa entrada força `APP_ENV=production`, `DEBUG=False` e recusa chave fraca ou hosts vazios/curinga. Forneça uma `SECRET_KEY` aleatória exclusiva com pelo menos 50 caracteres por secret manager ou variável de ambiente.

```env
DJANGO_SETTINGS_MODULE=config.production
APP_ENV=production
DEBUG=False
SECRET_KEY=<segredo-aleatorio-do-ambiente>
ALLOWED_HOSTS=portal.seu-dominio.example
CSRF_TRUSTED_ORIGINS=https://portal.seu-dominio.example
DATABASE_URL=postgresql://<usuario>:<senha>@<host>:5432/<banco>?sslmode=verify-full&channel_binding=require
NEWS_AI_ENABLED=False
TRUST_PROXY_SSL_HEADER=False
```

Em produção, HTTPS é obrigatório: cookies Secure/HttpOnly/SameSite, redirecionamento TLS, HSTS, `nosniff`, proteção contra enquadramento e política de conteúdo são habilitados. HSTS inclui subdomínios; valide todos os subdomínios antes de usar essa política no domínio real.

Se o TLS termina em proxy reverso, habilite `TRUST_PROXY_SSL_HEADER=True` somente depois de garantir que ele elimina `X-Forwarded-Proto` fornecido pelo cliente e define o valor correto. O servidor também deve fornecer `REMOTE_ADDR` real e confiável; o limitador não confia diretamente em `X-Forwarded-For`. Um proxy sem essa configuração concentra todos os usuários no mesmo limite por IP.

Use `python manage.py check --deploy --settings=config.production` com as variáveis reais, execute migrações e `collectstatic`, e configure um servidor de aplicação de produção. `runserver` e `config.test_settings` não atendem à publicação.

## Itens da INFRA, fora desta entrega

O procedimento de preparação do PostgreSQL e o ensaio de restauração estão no [guia de publicação](DEPLOYMENT.md). Antes de liberar acesso externo:

1. Validar migrações e concorrência no PostgreSQL real, transferir dados com contagem e integridade por espaço e ensaiar restauração/rollback. Trocar a URL não importa o banco SQLite.
2. Configurar HTTPS, processo WSGI/ASGI, estáticos, worker/agendamento durável, backup, retenção, restauração e observabilidade sem segredos.
3. Aplicar limites no proxy e no banco: conexões, requisições, tempo, fontes/jobs por espaço e orçamento de IA. O limite de autenticação da aplicação não substitui proteção contra abuso distribuído; threads locais não garantem entrega após reinício.
4. Validar cookies, cabeçalhos, isolamento, coleta, VLibras e permissões no domínio publicado. Repetir auditoria de dependências antes de cada liberação e manter atualizações.
5. Usar credenciais novas do ambiente de produção. Rotacionar a chave OpenAI compartilhada durante a configuração e manter limite de gastos no provedor. Habilitar IA apenas após confirmar orçamento e política de envio de conteúdo.

Não há declaração de risco zero nem de publicação já validada: configuração de rede, persistência e serviços externos só podem ser comprovadas no ambiente implantado.
