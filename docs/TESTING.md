# Testes e regressões

## Execução local

```bash
python -m pip install -r requirements-dev.txt
python manage.py test --settings=config.test_settings --noinput
```

Os testes usam SQLite temporário, credenciais fictícias de IA, relógio controlado quando necessário e respostas de provedores simuladas. O runner `feeds.tests.runner.IsolatedTestRunner` bloqueia requisições HTTP sem mock e conexões externas. Tentativas capturadas pela aplicação também fazem a suíte falhar. Sockets locais são permitidos para a comunicação interna do Python no Windows. Não é necessário configurar uma chave real de IA.

Durante a implementação, execute os módulos afetados, por exemplo:

```bash
python manage.py test feeds.tests.test_weekly_summary_service --settings=config.test_settings --noinput
```

Para a verificação final com cobertura:

```bash
python -m coverage run manage.py test --settings=config.test_settings --noinput
python -m coverage report
python manage.py makemigrations --check --dry-run
python manage.py check
python -m pip check
```

`.coveragerc` mede linhas e ramificações de `feeds`, excluindo arquivos de teste e migrations da porcentagem. As migrations continuam sendo executadas e possuem teste de migração de dados. `coverage report` falha abaixo de 85% na medida combinada. Os arquivos de resultados são ignorados pelo Git; `coverage html` é opcional para investigação local.

## Matriz funcional

| Área | Cenários exercitados |
| --- | --- |
| Contas e sessões | Cadastro válido/inválido, criação atômica do espaço, duplicidade de e-mail, rollback, login, contas e associações inativas, redirecionamento seguro, logout, expiração e limites por IP/ação |
| Espaços e permissões | Consultas fechadas sem contexto, troca autorizada de espaço, sessão adulterada, leitor/editor/administrador em cada rota, CSRF, métodos HTTP, acesso negado a IDs de outro espaço e último administrador ativo |
| Equipe | Adição de conta existente, validação, perfis, confirmação e desativação de associação sem alterar outros espaços |
| Fontes e tags | Criação, edição, exclusão, ativação, cores, normalização, duplicidade por espaço, relacionamentos, entradas inválidas e preservação do outro espaço |
| Informativos | Busca, filtros, datas, ordenação, leitura individual/em lote, acompanhamento, notificações e preferências pessoais, escopo dos endpoints JSON e escape de conteúdo |
| Domínio persistido | Restrições de unicidade, deduplicação por fonte, cascatas, contexto restaurado após exceção e isolamento de contextos concorrentes |
| RSS e HTTP | Feed e HTML, normalização, dados incompletos, deduplicação, falha parcial, URLs internas/credenciais/IPv6/DNS, redirecionamentos, prazo total, limite de corpo, resposta HTTP e stream |
| Análises de IA | Payload, lotes, score/tags/datas, saídas inválidas e extremas, erros de configuração/provedor/cota, falhas parciais e continuidade da importação |
| Resumo semanal | Semana no fuso local, isolamento, configuração, payload limitado, respostas inválidas, 429/503, falha persistida, reaproveitamento, recuperação, revisão e rejeição de worker antigo |
| Jobs e comandos | Reivindicação única, contexto do worker, progresso limitado, falha sem exposição de detalhes, job inexistente, bootstrap idempotente, backfill e recuperação restritos ao espaço explícito |
| Interface | Filtros recolhidos/ativos, resumo sem duplicação, conteúdo complementar disponível, nomes acessíveis, conta distinta da equipe, opções restritas a associações ativas, identidade preservada na troca e versão nas URLs de estilos; reflow e interação complementados pelo navegador |

Os módulos originais de `feeds/tests/` permanecem na suíte. Os arquivos `test_*_contracts.py`, `test_weekly_summary_service.py`, `test_jobs_and_commands.py` e `test_http_boundaries.py` ampliam os cenários usando dois espaços e dados independentes em `scenarios.py`.

## Resultado da revisão de 19/10/2026

- 217 testes passaram, incluindo a revisão de identidade de conta/equipe; nenhuma chamada paga de IA ou acesso HTTP externo foi realizado pela suíte.
- Cobertura: 2.746 de 3.001 linhas (91,5%), 630 de 798 ramificações (78,9%) e 88,9% na medida combinada. A medição inicial era 78,6% combinada, com 138 testes.
- `makemigrations --check --dry-run`, `check`, verificação de produção com parâmetros locais de validação e `pip check` passaram.
- Regressões corrigidas: consultas ao status de um resumo com falha reiniciavam a geração repetidamente; um resumo abandonado em execução não era recuperado; score infinito do provedor causava exceção; menu oculto após reduzir o desktop continuava acessível.

Um resumo com falha aguarda 15 minutos antes de uma nova tentativa automática. Uma execução sem término por 5 minutos pode ser retomada em uma consulta posterior. A recuperação incrementa a revisão para que o worker anterior não sobrescreva o resultado novo. A invalidação após alteração do acervo continua permitindo nova geração. A interface informa o estado de falha sem uma sequência de tentativas a cada polling.

## Validação no segundo Chrome

Foram usados dados sintéticos em um espaço local identificado como **[TESTE] Densidade e regressões**, com títulos longos, 18 informativos, múltiplas fontes/tags e oito membros. As fontes de exemplo ficam desativadas. Os dados locais não fazem parte do repositório.

Dashboard, informativos, fontes, tags, equipe, progresso, entrada e cadastro foram medidos nas larguras CSS de 320, 390, 768, 1024 e 1440 px: nenhuma página apresentou rolagem horizontal. A tabela de equipe conserva sua rolagem interna. O cabeçalho desktop passou de aproximadamente 113 para 57 px na primeira revisão de densidade; após a separação entre conta e equipe, ocupa cerca de 69 px no desktop e 65 px em 320/390 px. Os títulos de página passaram de 30 para 24 px. O formulário de edição de acesso também foi conferido em tela pequena.

Interações verificadas: criar/editar/desativar fonte, abrir/cancelar exclusão, criar/editar tag e cor, pesquisar, filtrar por status, marcar leitura, acompanhar, selecionar/aplicar ação em lote, concluir coleta sem fontes ativas, navegar pelo menu, bloquear envio de alteração de acesso sem confirmação e usar Tab/Shift+Tab/Escape com retorno de foco no modal. A exclusão efetiva é exercitada no banco temporário dos testes. A transição desktop/celular foi revista com o estado de acessibilidade do menu. O console da sessão de regressão ficou sem erros e avisos.

A revisão de identidade conferiu os painéis **Equipe atual** e **Minha conta** abertos nas cinco larguras, sem cortes laterais. Foram verificados ícone de pessoas no menu lateral, nome/e-mail/papel da conta, troca de equipe por clique e Tab/Enter preservando a pessoa conectada e alterando o acervo, fechamento por Escape com retorno de foco, clique externo e apenas um painel aberto por vez. Dois testes adicionais cobrem conta/equipe, vínculo inativo ou de outro usuário, papel diferente após a troca e equipe única. O cabeçalho não usa mais select ou botão separado para confirmar a troca.

A extensão manteve a captura nativa em 1280 px. Para medir outras larguras no mesmo Chrome, foi usada uma moldura temporária com o portal real por proxy exclusivamente em loopback. A moldura preservou os fluxos e foi encerrada após a validação; as proteções contra enquadramento da aplicação permanecem ativas. A largura útil pode ser 15 px menor por causa da barra de rolagem. As telas públicas foram solicitadas sem cookie nessa prévia para preservar a sessão de trabalho. Isso verifica reflow CSS e interações, sem substituir testes em aparelhos físicos, zoom nativo, motores de outros navegadores ou leitor de tela real.

## Revisão de cadastro e equipe em 01/11/2026

O cadastro separa **Sua conta pessoal** de **Sua equipe inicial**. Os rótulos e as instruções explicam o login individual, a primeira equipe privada e a inclusão em outras equipes pelo mesmo e-mail. Gerenciar equipe reúne nome/e-mail da conta, marca **Você**, identifica a equipe atual e diferencia papel, acesso ao vínculo e conta desativada. A edição esclarece o efeito limitado à equipe atual.

A suíte completa passou com **219 testes**, sem chamadas pagas de IA. Os dois testes adicionais verificam cadastro seguido de inclusão em outra equipe sem alterar identidade ou senha e a distinção entre conta inativa e participação desativada na lista. `makemigrations --check --dry-run` não encontrou alterações.

Os fluxos funcionais conferidos foram cadastro inválido com confirmação de senha diferente, cadastro válido com equipe privada, rejeição de conta inexistente, inclusão de conta de teste existente, descrição dos papéis e desativação de um vínculo. Após corrigir a seleção do perfil do Chrome, foram reconferidos no segundo perfil o cadastro, o login individual, a listagem e a edição de acesso. Cadastro e listagem foram medidos nesse perfil em 320, 390, 768 e 1440 px sem rolagem horizontal da página; a tabela mantém rolagem própria. A edição de acesso foi conferida em 320 px. A extensão exigiu reconexão e substituição de abas durante a validação. Foram usados apenas dados sintéticos locais; não foram adicionadas dependências, migrações ou convites por e-mail.

## Proteção contra força bruta em 05/11/2026

A suíte SQLite executou 226 testes, com um caso de concorrência reservado ao PostgreSQL. Os 23 testes de segurança e autenticação também passaram em PostgreSQL 17 descartável, inclusive o caso com oito requisições simultâneas e apenas cinco verificações de senha para a mesma conta. Foram exercitados o desbloqueio, reinício da contagem após sucesso, troca de caixa e IP, limite por origem, CSRF, acesso pelo Django Admin e rejeição de entidades XML em uma fonte sem interromper a coleta das demais.

No segundo Chrome, uma conta criada em SQLite descartável recebeu quatro respostas de credenciais inválidas. A quinta falha e o envio seguinte com a senha correta receberam `429`, exibindo a mensagem de espera. O relógio simulado nos testes automatizados verifica a expiração exata sem esperar 15 minutos. A suíte continua sem chamadas pagas de IA.

## Limites e próxima liberação

Cobertura não prova ausência de defeitos nem corresponde a todas as combinações de entradas. O contrato da API de IA foi simulado; um smoke test pago deve ser pequeno e deliberado ao habilitar o serviço. O VLibras depende de rede e serviço externo; sua validação e tratamento de indisponibilidade estão registrados em [SECURITY.md](SECURITY.md).

PostgreSQL, concorrência real entre processos, worker durável, implantação, restauração e limites operacionais permanecem nas tarefas de INFRA. Repetir os testes de integração e os checks no ambiente publicado com sua configuração real. A análise de segurança e os requisitos de publicação estão em [SECURITY.md](SECURITY.md).
