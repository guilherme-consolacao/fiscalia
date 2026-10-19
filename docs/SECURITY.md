# Segurança e preparação para publicação

## Revisão de 19/10/2026

Foram revisados autenticação, autorização, isolamento entre espaços, preferências individuais, entradas JSON/datas, CSRF, coleta de URLs externas, execução de jobs, cabeçalhos, dependências e exposição de erros. As correções incluem consultas fechadas sem contexto, restrição do Django Admin ao superusuário, limite persistente de tentativas, proteção contra requisições à rede interna e remoção de mensagens inesperadas detalhadas das respostas.

`requirements.txt` contém versões fixadas. Django foi atualizado para 5.2.18, idna para 3.15, sqlparse para 0.6.0 e urllib3 para 2.8.0 após a auditoria de dependências. A última execução de `pip-audit`, em 19/10/2026, não encontrou vulnerabilidades conhecidas nas dependências declaradas. Isso é uma fotografia das bases consultadas, não garantia de ausência de vulnerabilidades desconhecidas.

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

## Configuração de produção

Defina `DJANGO_SETTINGS_MODULE=config.production` no processo WSGI/ASGI e nos comandos do ambiente. Essa entrada força `APP_ENV=production`, `DEBUG=False` e recusa chave fraca ou hosts vazios/curinga. Forneça uma `SECRET_KEY` aleatória exclusiva com pelo menos 50 caracteres por secret manager ou variável de ambiente.

```env
DJANGO_SETTINGS_MODULE=config.production
APP_ENV=production
DEBUG=False
SECRET_KEY=<segredo-aleatorio-do-ambiente>
ALLOWED_HOSTS=portal.seu-dominio.example
CSRF_TRUSTED_ORIGINS=https://portal.seu-dominio.example
DATABASE_URL=postgresql://<usuario>:<senha>@<host>:5432/<banco>
NEWS_AI_ENABLED=False
TRUST_PROXY_SSL_HEADER=False
```

Em produção, HTTPS é obrigatório: cookies Secure/HttpOnly/SameSite, redirecionamento TLS, HSTS, `nosniff`, proteção contra enquadramento e política de conteúdo são habilitados. HSTS inclui subdomínios; valide todos os subdomínios antes de usar essa política no domínio real.

Se o TLS termina em proxy reverso, habilite `TRUST_PROXY_SSL_HEADER=True` somente depois de garantir que ele elimina `X-Forwarded-Proto` fornecido pelo cliente e define o valor correto. O servidor também deve fornecer `REMOTE_ADDR` real e confiável; o limitador não confia diretamente em `X-Forwarded-For`. Um proxy sem essa configuração concentra todos os usuários no mesmo limite por IP.

Use `python manage.py check --deploy --settings=config.production` com as variáveis reais, execute migrações e `collectstatic`, e configure um servidor de aplicação de produção. `runserver` e `config.test_settings` não atendem à publicação.

## Itens da INFRA, fora desta entrega

Publicação e migração PostgreSQL permanecem no Trello por orientação do solicitante. Antes de liberar acesso externo:

1. Validar migrações e concorrência no PostgreSQL real, transferir dados com contagem e integridade por espaço e ensaiar restauração/rollback. Trocar a URL não importa o banco SQLite.
2. Configurar HTTPS, processo WSGI/ASGI, estáticos, worker/agendamento durável, backup, retenção, restauração e observabilidade sem segredos.
3. Aplicar limites no proxy e no banco: conexões, requisições, tempo, fontes/jobs por espaço e orçamento de IA. O limite de autenticação da aplicação não substitui proteção contra abuso distribuído; threads locais não garantem entrega após reinício.
4. Validar cookies, cabeçalhos, isolamento, coleta, VLibras e permissões no domínio publicado. Repetir auditoria de dependências antes de cada liberação e manter atualizações.
5. Usar credenciais novas do ambiente de produção. Rotacionar a chave OpenAI compartilhada durante a configuração e manter limite de gastos no provedor. Habilitar IA apenas após confirmar orçamento e política de envio de conteúdo.

Não há declaração de risco zero nem de publicação já validada: configuração de rede, persistência e serviços externos só podem ser comprovadas no ambiente implantado.
