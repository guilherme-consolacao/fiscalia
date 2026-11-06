# Publicar o Fiscalia

O piloto usa PostgreSQL no Neon Free e um serviço web no Render Free. Use um banco vazio para o primeiro deploy. A configuração de produção recusa SQLite e conexões PostgreSQL que não verificam o certificado e o hostname do servidor.

## Preparar o PostgreSQL

1. O piloto usa um projeto Neon Free em AWS São Paulo (`aws-sa-east-1`), com PostgreSQL 17 e banco exclusivo `fiscalia`. Use a URL direta para migrações, backup e restauração.
2. Separe o papel que cria e migra tabelas do papel usado pelo portal. Configure as senhas pelo painel ou pelo comando interativo `\password` do `psql`. Mantenha a URL de migração com o operador. No Render, guarde como `DATABASE_URL` somente a URL do papel do portal, sem privilégios de administração da instância.
3. Na URL de produção, use `sslmode=verify-full` e preserve `channel_binding=require` do Neon. O Django usa a cadeia de confiança do Certifi por padrão e aceita `sslrootcert` para uma CA fornecida pelo operador. O padrão de produção encerra a conexão ao fim de cada requisição. Ajuste `DB_CONN_MAX_AGE` somente após medir uso e limites da instância.
4. Em um terminal de operação com as dependências de `requirements-production.txt`, defina `DJANGO_SETTINGS_MODULE=config.production` e forneça a URL do papel de migração pelo ambiente. Execute `python manage.py migrate --noinput` e `python manage.py migrate --check`. Confira os requisitos de `SECRET_KEY` e `ALLOWED_HOSTS` em [Segurança](SECURITY.md).
5. Como dono das tabelas, conceda ao papel do portal acesso de leitura e escrita às tabelas da aplicação e uso das sequências. Conceda apenas leitura a `django_migrations`. Repita a verificação após criar tabelas em novas versões. Confira o TLS no cliente com `psycopg.Connection.pgconn.ssl_in_use` e o parâmetro `sslmode=verify-full`. No Neon, `pg_stat_ssl` descreve o trecho interno do proxy e pode retornar `false` mesmo com a conexão do cliente protegida.

Exemplo para um banco dedicado, com o papel `fiscalia_runtime` já criado e sem permissões administrativas:

```sql
GRANT CONNECT ON DATABASE fiscalia TO fiscalia_runtime;
GRANT USAGE ON SCHEMA public TO fiscalia_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO fiscalia_runtime;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO fiscalia_runtime;
REVOKE INSERT, UPDATE, DELETE ON django_migrations FROM fiscalia_runtime;
```

## Backup e restauração

Antes de uma migração com dados reais, faça uma cópia e ensaie a restauração em outro banco. Use clientes PostgreSQL da mesma versão principal do servidor ou compatíveis. Os serviços `fiscalia-origem` e `fiscalia-restauracao` abaixo são entradas privadas do cliente PostgreSQL, com TLS e credenciais fornecidas fora do repositório. O destino deve estar vazio.

```bash
pg_dump --dbname="service=fiscalia-origem" --format=custom --no-owner --no-acl --file fiscalia.dump
pg_restore --dbname="service=fiscalia-restauracao" --exit-on-error --no-owner --no-acl fiscalia.dump
```

Guarde o arquivo em armazenamento protegido e mantenha uma cópia antes de mudanças de esquema. Compare contas, vínculos, fontes, informativos e preferências por equipe. Teste login e isolamento no banco restaurado antes de apontar o serviço para ele. Reaplique os privilégios do papel do portal no destino. No piloto, faça backup antes de mudanças de dados e mantenha cópias periódicas conforme o volume e o prazo de recuperação acordado. Confira a janela de recuperação incluída no painel do Neon.

Trocar `DATABASE_URL` cria uma conexão com outro banco. A transferência de um acervo SQLite existente exige autorização sobre os dados, migração ensaiada e conferência de integridade por equipe. Preserve o SQLite de origem até validar a transferência.

## Publicar no Render

1. Envie a versão para a `main` no GitHub. No Render, crie um Blueprint usando o `render.yaml` da `main`. O plano `free` constrói o `Dockerfile` na nuvem. A imagem final roda como usuário sem privilégios e escuta a porta definida pelo Render.
2. Forneça `SECRET_KEY`, uma chave exclusiva com pelo menos 50 caracteres, e `DATABASE_URL`, a URL do papel do portal. Gere a chave em um terminal privado com `python -c "import secrets; print(secrets.token_urlsafe(64))"`. Mantenha `NEWS_AI_ENABLED=False` no piloto.
3. O inicializador usa o hostname fornecido pelo Render. Se configurar outro domínio, liste os hosts exatos em `ALLOWED_HOSTS` e suas origens HTTPS em `CSRF_TRUSTED_ORIGINS`. O Blueprint ativa o reconhecimento de HTTPS do proxy do Render. Valide na URL real que não há loop de redirecionamento e que os cookies de sessão e CSRF são `Secure`.
4. A inicialização verifica os controles de produção e a aplicação das migrações antes de subir. Depois coleta CSS, JavaScript e imagens com WhiteNoise. O endpoint `/saude/` confirma que o processo Django responde. A verificação de acesso ao banco ocorre durante a inicialização.
5. Antes de divulgar, confirme que a borda do Render substitui `CF-Connecting-IP` enviado pelo cliente e que a aplicação recebe endereços distintos em duas origens. Só depois habilite `TRUST_RENDER_CLIENT_IP=True`. Com a opção desligada, o limitador usa `REMOTE_ADDR`. Em um proxy compartilhado, várias pessoas podem cair no mesmo limite por origem. O bloqueio por conta permanece independente.
6. Valide cadastro, login, troca de equipe, isolamento, arquivos estáticos, coleta RSS e Libras no endereço HTTPS. Reinicie o serviço e confirme a persistência. Registre a URL e a versão nos cards após essa validação.

O deploy automático fica desativado. Para atualizar, revise o plano de migrações, faça o backup quando houver alterações de esquema e aplique as migrações com o papel apropriado. Depois dispare o deploy manual do commit. Ao voltar para uma versão anterior, confirme a compatibilidade do esquema. Use a restauração em outro banco quando precisar voltar dados ou esquema.

## Retomar coleta após reinício

No plano gratuito, o serviço pode hibernar ou reiniciar. Uma coleta em andamento pode ficar pendente ou marcada como em execução. Após confirmar que a coleta anterior foi interrompida, use um terminal autorizado com as variáveis de produção, selecione a equipe correta e execute:

```bash
python manage.py process_news_jobs --workspace ID_DA_EQUIPE --recover-stale
```

O comando retoma jobs pendentes da equipe selecionada e encerra jobs em execução sem atualização há mais de 30 minutos. Depois disso, uma pessoa com permissão pode solicitar nova coleta no portal. O processo em segundo plano do piloto não substitui um worker independente com fila durável.
