# Publicar o Fiscalia

O piloto usa PostgreSQL no Neon Free e um serviço web no Render Free. Use um banco vazio para o primeiro deploy. A configuração de produção recusa SQLite e conexões PostgreSQL que não verificam o certificado e o hostname do servidor.

## Preparar o PostgreSQL

1. Crie um projeto gratuito no Neon, com uma região próxima à do serviço web. Crie um banco exclusivo do Fiscalia. Use a URL direta para migrações, backup e restauração.
2. Separe o papel que cria e migra tabelas do papel usado pelo portal. Configure as senhas pelo painel ou pelo comando interativo `\password` do `psql`. Mantenha a URL de migração com o operador. No Render, guarde como `DATABASE_URL` somente a URL do papel do portal, sem privilégios de administração da instância.
3. Na URL de produção, use `sslmode=verify-full` e preserve `channel_binding=require` do Neon. O Django usa a cadeia de confiança do Certifi por padrão e aceita `sslrootcert` para uma CA fornecida pelo operador. O padrão de produção encerra a conexão ao fim de cada requisição. Ajuste `DB_CONN_MAX_AGE` somente após medir uso e limites da instância.
4. Com `DJANGO_SETTINGS_MODULE=config.production` e a URL do papel de migração fornecida pelo ambiente, execute `python manage.py migrate --noinput` e `python manage.py migrate --check`. Confira os requisitos de `SECRET_KEY` e `ALLOWED_HOSTS` em [Segurança](SECURITY.md).
5. Como dono das tabelas, conceda ao papel do portal acesso de leitura e escrita às tabelas da aplicação e uso das sequências. Conceda apenas leitura a `django_migrations`. Repita a verificação após criar tabelas em novas versões. No ambiente publicado, confira que `SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()` retorna `true`.

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
