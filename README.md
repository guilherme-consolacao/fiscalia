# Fiscalia

Portal informativo que centraliza feeds RSS sobre informações fiscais, com contas, equipes e espaços de trabalho isolados.

Cada cadastro cria um espaço privado. Administradores podem adicionar contas existentes à equipe pelo e-mail; somente membros ativos compartilham fontes, tags, notícias e análises daquele espaço. Leitura, acompanhamento e notificações são individuais.

No cabeçalho, **Equipe atual** identifica o acervo em uso. Clique para ver suas equipes e escolha outra: a troca muda o acervo sem trocar a conta conectada. **Minha conta**, com avatar e nome, mostra nome completo, e-mail, equipe atual, seu papel nessa equipe e a opção **Sair da conta**. Cada pessoa usa o próprio login; uma mesma conta pode participar de várias equipes, inclusive com papéis diferentes. “Equipe” na interface corresponde ao espaço de trabalho (`Workspace`) no código. O item **Gerenciar equipe**, com o ícone de pessoas, aparece para administradores da equipe atual.

| Ação | Leitor | Editor | Administrador do espaço |
| --- | --- | --- | --- |
| Consultar notícias, filtros, análises e resumos | Sim | Sim | Sim |
| Marcar leitura, acompanhar e dispensar lembretes pessoais | Sim | Sim | Sim |
| Gerenciar fontes/tags, coletar RSS e gerar resumo | Não | Sim | Sim |
| Adicionar contas existentes, alterar perfis e desativar associações | Não | Não | Sim |

O último administrador ativo não pode ser removido. Desativar a associação revoga o acesso ao espaço, preservando o acesso da pessoa aos outros grupos. O Django Admin é reservado ao superusuário da plataforma.

Veja [arquitetura e análise Graphify](docs/ARCHITECTURE.md) e [segurança, validações e preparação para publicação](docs/SECURITY.md).

## Tecnologias
- Python 3.11+ (validação local: Python 3.14)
- Django 5.2.18 LTS
- django-environ (Gerenciamento de variáveis de ambiente)

## Como rodar o projeto

### 1. Clonar o repositório
```bash
git clone https://github.com/guilherme-consolacao/fiscalia.git
cd fiscalia
```

### 2. Criar e ativar o ambiente virtual (opcional, mas recomendado)
```bash
python -m venv .venv
# No Windows:
.\.venv\Scripts\activate
# No Linux/macOS:
source .venv/bin/activate
```

### 3. Instalar as dependências
```bash
pip install -r requirements.txt
```

### 4. Configurar as variáveis de ambiente
Crie um arquivo `.env` na raiz do projeto (use o `.env.example` como base se disponível, ou crie um novo):
```env
DEBUG=True
APP_ENV=development
SECRET_KEY=substitua-por-uma-chave-aleatoria
ALLOWED_HOSTS=127.0.0.1,localhost
DATABASE_URL=sqlite:///db.sqlite3
NEWS_AI_ENABLED=False
NEWS_AI_PROVIDER=openai
NEWS_AI_MODEL=gpt-4o-mini
NEWS_AI_TIMEOUT_SECONDS=45
NEWS_AI_PIPELINE_VERSION=v1
NEWS_AI_BATCH_SIZE=5
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_ORG_ID=
OPENAI_PROJECT=
```

Gere a chave com `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`. Nunca versione `.env`, bancos locais ou credenciais. A IA fica desativada por padrão.

### 5. Executar as migrações iniciais
```bash
python manage.py migrate
```

Abra `/cadastrar/` para criar a primeira conta e seu espaço privado. A migração `0016` preserva o acervo existente em **Acervo legado** (ID 1) e associa usuários antigos ativos; novas contas não recebem acesso automático a esse acervo. Para conceder administração de um espaço a uma conta existente pelo terminal do operador:

```bash
python manage.py grant_workspace_admin --username usuario-existente --workspace 1
```

Faça backup antes de migrar uma base existente. A migração de acervo e preferências é coberta por teste automatizado. SQLite atende ao desenvolvimento; a migração e validação operacional em PostgreSQL permanecem na tarefa de INFRA.

### Cadastro e participação em equipes

Em **Criar conta**, cada pessoa informa seu próprio nome, e-mail e senha. O formulário separa **Sua conta pessoal** de **Sua equipe inicial**: o cadastro sempre cria uma equipe privada inicial, administrada pela pessoa. Depois, a mesma conta pode participar de outras equipes sem novo cadastro nem senha compartilhada.

Para incluir alguém, o administrador seleciona a equipe no cabeçalho e abre **Gerenciar equipe**. Em **Adicionar conta existente**, informa o e-mail já cadastrado pela pessoa e escolhe o **Papel nesta equipe**. Se a pessoa ainda não tiver conta, ela deve se cadastrar primeiro. A inclusão é imediata e não envia convite por e-mail; a equipe fica disponível em **Equipe atual** no próximo acesso ou ao recarregar a página.

A lista reúne nome e e-mail de cada conta, marca **Você** e mostra papel e acesso naquela equipe. **Editar acesso** altera apenas essa participação. **Acesso desativado** bloqueia a equipe atual; **Conta desativada** indica que a conta inteira está inativa. A senha, os papéis e os vínculos nas demais equipes não são editados nessa tela. As permissões continuam sendo verificadas no servidor.

### IA opcional nos informativos
- Para ativar a análise por IA durante o botão `Atualizar`, defina `NEWS_AI_ENABLED=True`.
- `NEWS_AI_BATCH_SIZE` controla quantas notícias são enviadas por chamada ao provider. O padrão é `5`.
- A V1 usa provider `openai` e exige `OPENAI_API_KEY`.
- Se a IA estiver desabilitada ou configurada incorretamente, os informativos continuam sendo importados normalmente.
- Para reprocessar informativos antigos com a versão atual do pipeline de IA, use:
```bash
python manage.py backfill_news_analysis --workspace 1 --limit 5
```

O backfill exige um espaço explícito. `--limit 0` processa todas as pendências desse espaço e pode consumir a API. Faça primeiro uma execução pequena. O conteúdo das matérias é enviado ao provedor quando a IA está habilitada; contas e senhas não entram no prompt.

O botão de atualização inicia uma coleta por espaço e reutiliza uma execução já ativa. Jobs rodam no contexto do espaço, sem bloquear a requisição HTTP. Um processo interrompido pode ser recuperado pelo operador:

```bash
python manage.py process_news_jobs --workspace 1 --recover-stale
```

Esse comando encerra execuções sem progresso há mais de 30 minutos e executa jobs pendentes. O agendamento e o processo durável de produção serão configurados na tarefa de INFRA; threads locais não substituem essa operação.

### 6. Iniciar o servidor de desenvolvimento
```bash
python manage.py runserver
```
O projeto estará disponível em `http://127.0.0.1:8000/`.

### Acessibilidade e Libras

As páginas incluem acesso direto ao conteúdo, foco visível, nomes acessíveis, avisos de estado e modais com contenção e retorno de foco. Menu e formulários se adaptam a telas menores; a tabela de equipe possui sua própria rolagem quando necessário.

O layout usa espaçamentos compactos, títulos de página de 24 px e barra lateral de 244 px no desktop. Em telas pequenas, o cabeçalho mantém menu, equipe e conta lado a lado e acompanha a rolagem. Os painéis de equipe/conta adaptam a largura, fecham com Escape ou clique externo e podem ser usados por teclado. Os filtros adicionais dos informativos ficam em **Fonte, status, relevância e vigência**; o painel permanece aberto quando há um desses filtros aplicado. O resumo original fica em **Resumo da fonte** quando difere do resumo da análise, evitando repetir o mesmo texto no card.

Os arquivos CSS e o script global incluem `APP_VERSION` na URL. Atualize essa variável a cada versão publicada para invalidar o cache desses arquivos; a entrega e o cache dos estáticos importados devem ser configurados na INFRA.

O botão **Ativar VLibras**, ao final das páginas autenticadas, carrega o serviço oficial somente sob demanda. É possível ocultá-lo e reativá-lo por teclado. A tradução é automática e depende do serviço externo, da rede e do suporte gráfico do navegador. A indisponibilidade é informada sem impedir o uso do portal. Consulte a [documentação oficial](https://www.vlibras.gov.br/doc/widget/installation/webpageintegration.html).

## Estrutura do Projeto
- `config/`: Configurações principais do Django.
- `feeds/`: App principal para gestão de fontes e itens RSS.
- `feeds/urls.py`: URLs públicas e nomes internos de rotas do app principal.
- `feeds/views/`: Views separadas por página.
- `feeds/models/`: Models separados por domínio.
- `feeds/admin/`: Configurações do Django Admin separadas por domínio.
- `feeds/tests/`: Testes separados por domínio ou página.
- `feeds/data/`: Dados temporários e catálogos usados até a criação dos models.
- `static/`: Arquivos estáticos (CSS, JS, Imagens).
- `static/css/components/`: Estilos reutilizáveis, como botões, formulários, mensagens e modais.
- `static/css/layouts/`: Estilos da estrutura principal da aplicação.
- `static/css/pages/`: Estilos específicos de cada página.
- `static/js/app.js`: Comportamentos globais.
- `static/js/pages/`: Scripts específicos de cada página.
- `templates/`: Templates HTML globais.
- `templates/layouts/`: Partes estruturais do layout, como sidebar.
- `templates/pages/`: Templates organizados por página.

## Padrões do Projeto

### URLs, rotas e views
- URL pública é o caminho que aparece no navegador. Exemplo: `/fontes/`.
- Nome da rota é o identificador interno usado em `{% url %}`, `reverse()` e `redirect()`. Exemplo: `feeds:sources`.
- View, ou handler, é a função que responde à requisição. Exemplo: `sources.index`.
- Em `path('fontes/', sources.index, name='sources')`, `fontes/` é a URL pública, `sources.index` é a view e `sources` é o nome interno da rota.

### Convenções
- Use inglês para nomes internos: arquivos, pastas, módulos, funções, variáveis, classes e IDs no HTML/CSS e nomes internos de rotas.
- Use português para textos exibidos ao usuário: títulos, botões, labels, mensagens e itens do menu.
- URLs públicas podem ser em português quando fizer sentido para o usuário final.
- Cada página deve ter seu módulo em `feeds/views/`. Exemplo: `feeds/views/sources.py`.
- Use `index` como view principal da página. Exemplo: `sources.index`.
- Ações da mesma página ficam no mesmo módulo. Exemplo: `create_source`, `update_source`, `delete_source`.
- Cada domínio persistido deve ter seu módulo em `feeds/models/`. Exemplo: `feeds/models/source.py`.
- Reexporte os models em `feeds/models/__init__.py` para manter imports como `from feeds.models import Source`.
- Configurações do admin também devem ficar por domínio em `feeds/admin/`. Exemplo: `feeds/admin/source.py`.
- Testes devem ficar em `feeds/tests/`, agrupados por domínio ou página. Exemplo: `feeds/tests/test_sources.py`.
- Dados temporários ou mockados devem ficar em `feeds/data/`. Exemplo: `feeds/data/sources.py`.
- O template principal da página fica em `templates/pages/<page>/index.html`.
- Use `templates/pages/<page>/partials/` para partes da página, como modais, formulários e blocos reaproveitados.
- Layouts globais ficam em `templates/layouts/`, como `sidebar.html`.
- CSS global entra em `static/css/base.css`; CSS de página entra em `static/css/pages/`.
- JS global entra em `static/js/app.js`; JS de página entra em `static/js/pages/`.
- Evite criar abstrações globais antes da necessidade. Se é usado por uma página só, deixe perto dela.

## Checklist para novas páginas
1. Crie `feeds/views/<page>.py`.
2. Crie a view principal `index`.
3. Cadastre a URL pública e o nome interno da rota em `feeds/urls.py`.
4. Coloque dados temporários em `feeds/data/<page>.py`, se houver.
5. Crie `templates/pages/<page>/index.html`.
6. Crie `templates/pages/<page>/partials/` se precisar de modais ou blocos reaproveitados.
7. Crie CSS/JS em `static/css/pages/` e `static/js/pages/`, se necessário.
8. Inclua CSS e JS usando os blocos `styles` e `scripts`.
9. Se aparecer na sidebar, adicione o link em `templates/layouts/sidebar.html`.
10. Rode `python manage.py check`.

## Como Contribuir

Se você deseja contribuir com o projeto, siga os passos abaixo para criar uma nova branch e abrir um Pull Request:

1. Atualize sua branch principal para garantir que está com o código mais recente:
   ```bash
   git checkout main
   git pull origin main
   ```

2. Crie uma nova branch para a sua feature ou correção:
   ```bash
   git checkout -b minha-nova-feature
   ```

3. Faça as suas alterações e salve os commits:
   ```bash
   git add .
   git commit -m "feat: adiciona nova funcionalidade X"
   ```

4. Envie a sua branch para o repositório remoto:
   ```bash
   git push origin minha-nova-feature
   ```

5. Acesse o repositório no GitHub e abra um **Pull Request** da sua branch para a branch principal, descrevendo detalhadamente as mudanças e o contexto da sua contribuição.

## Como validar alterações e identificar regressões

Depois de implementar uma mudança, rode os testes para verificar se houve regressão no comportamento existente.

Para executar a suíte completa:

```bash
python manage.py test --settings=config.test_settings
```

Para rodar apenas um arquivo de testes:

```bash
python manage.py test feeds.tests.test_news --settings=config.test_settings
```

Para rodar um teste específico:

```bash
python manage.py test feeds.tests.test_news.NewsViewTests.test_refresh_news_skips_failed_item_without_interrupting_other_news --settings=config.test_settings
```

Se quiser uma saída mais detalhada durante a execução, use:

```bash
python manage.py test --settings=config.test_settings -v 2
```

As configurações de teste usam banco SQLite temporário, chave de IA fictícia, respostas HTTP simuladas e hash rápido somente nos testes. Não use `config.test_settings` para servir o portal.

O runner bloqueia HTTP e conexões externas sem simulação, inclusive quando a aplicação captura a exceção, para evitar consumo acidental de IA. Instale `requirements-dev.txt` para medir a cobertura. Consulte a [matriz de testes e validação visual](docs/TESTING.md) para os comandos, cenários e limites da última revisão.
