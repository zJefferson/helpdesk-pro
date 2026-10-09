# Auditoria técnica — HelpDesk Pro

Data: 08/10/2026. Escopo: backend (Django/DRF), frontend (React), banco, Docker e documentação.
Regra seguida: nenhuma funcionalidade nova, apenas correções de defeitos e de segurança.

## 1. Problemas encontrados (por prioridade)

Legenda: ✅ corrigido · ⏳ pendente (registrado no checklist) · ℹ️ decisão consciente

### Alta

| # | Problema | Impacto | Como foi confirmado | Status |
|---|---|---|---|---|
| A1 | **Limite de tentativas de login burlável** via cabeçalho `X-Forwarded-For` (o DRF confiava no valor enviado pelo cliente) | Força bruta ilimitada contra senhas, trocando o cabeçalho a cada tentativa | Teste enviando 13 tentativas com IPs falsos: nunca recebia 429 | ✅ `NUM_PROXIES=0` por padrão (usa o IP da conexão) |
| A2 | **API aceitava formulários HTML** (`x-www-form-urlencoded`/`multipart`) | "Login CSRF": um site malicioso podia logar a vítima na conta do atacante e induzi-la a registrar dados lá | Teste: POST de formulário em `/auth/session/login/` retornava 200 e criava o cookie | ✅ API só aceita JSON (415 para formulários) |
| A3 | **Troca de senha não encerrava sessões** | Invasor com um refresh token roubado continuava entrando por até 1 dia após a vítima trocar a senha | Teste: refresh emitido antes da troca continuava válido | ✅ Troca de senha coloca todos os refresh do usuário na blacklist |

### Média

| # | Problema | Impacto | Status |
|---|---|---|---|
| M1 | **Django Admin permitia editar status/responsável, criar e editar chamados e comentários** sem passar pelas regras | Transições inválidas, histórico incompleto, comentários "imutáveis" alteráveis | ✅ Chamados, comentários e histórico somente leitura no admin |
| M2 | **Faltavam configurações de produção** (`check --deploy`: HTTPS, cookies `Secure`, HSTS) | Cookies e sessão expostos em HTTP; sem redirecionamento para HTTPS | ✅ Ativadas quando `DEBUG=False` (2 avisos de HSTS ficaram — ver ℹ️ abaixo) |
| M3 | **Docker nunca foi executado** (engine parado por problema de BIOS no ambiente de desenvolvimento) | Não há garantia de que `docker compose up` funcione | ⏳ Só validado estaticamente (`docker compose config`) |
| M4 | **Limite de tentativas usa cache em memória por processo** (LocMemCache) | Com vários workers do gunicorn, cada um tem seu próprio contador (limite efetivo multiplicado) | ⏳ Usar cache compartilhado (banco ou Redis) no deploy |
| M5 | **Documentação não citava os endpoints de sessão** nem as novas variáveis | Quem usa a API não sabe como o navegador autentica | ✅ `docs/AUTENTICACAO.md`, `.env.example` e README atualizados |
| M6 | **Vite no Docker não percebe alterações** em Windows/macOS (eventos de arquivo não chegam ao container) | Recarregamento automático não funcionaria | ✅ Polling ativado no compose (não testado — ver M3) |

### Baixa / cosmética

| # | Problema | Impacto | Status |
|---|---|---|---|
| B1 | Após logout voluntário, o próximo login abria a **última página do usuário anterior** | Confuso; num computador compartilhado, outra pessoa caía na tela de quem saiu | ✅ Estado de autenticação guarda o motivo (logout × sessão expirada) |
| B2 | Página da lista que deixou de existir (ex.: chamados encerrados) ficava presa em erro 404 | Usuário precisava limpar a URL | ✅ Volta para a página 1 |
| B3 | Comentar não atualizava a data "Atualizado em" na tela | Informação desatualizada até recarregar | ✅ |
| B4 | Texto de confirmação "Confirmar: cancelado?" | Pouco claro | ✅ "Sim, cancelar o chamado" |
| B5 | Mensagem "Token is blacklisted" em inglês (vem da biblioteca) | Cosmético; o frontend não exibe | ⏳ |
| B6 | Usuários ADMIN criados pela API não têm `is_staff` (sem acesso ao Django Admin) | Inconsistência entre admin da API e do Django | ℹ️ Documentar; o `createsuperuser` cria admins com acesso |
| B7 | Frontend sem ESLint e sem medição de cobertura | Menos garantias automáticas de qualidade no React | ⏳ |
| B8 | Corrida rara: dois cadastros simultâneos do mesmo e-mail → erro 500 (o banco barra o segundo) | Mensagem genérica em vez de 400; dado continua íntegro | ⏳ |

### ℹ️ Decisões conscientes (não são defeitos)

- **HSTS sem `includeSubDomains` e sem `preload`** (2 avisos restantes do `check --deploy`): ativar sem controlar todos os subdomínios pode deixá-los inacessíveis por meses. Decidir no deploy.
- **Access token vale até 15 min após troca de senha ou logout**: limitação do JWT sem estado; mitigada pela curta duração.
- **Limite de login por IP**: usuários atrás do mesmo IP (rede corporativa) compartilham o limite (10/min, configurável).

## 2. O que foi verificado e está correto

- **Organização:** views finas → serializers (formato) → services (regras + histórico em transação) → selectors (visibilidade). Regras de transição em uma única tabela.
- **Autorização:** visibilidade aplicada no queryset (404 para recurso alheio); permissões por campo; campos protegidos recusados com 400; o frontend só esconde botões com base em `permissions` calculado pelo backend.
- **Tokens:** assinatura adulterada, `alg: none`, token expirado, refresh usado como access e usuário desativado → todos 401 (testados).
- **Banco:** listagens com `select_related`; contagem de consultas constante testada (lista, comentários, dashboard).
- **Frontend:** access token só em memória; refresh em cookie `HttpOnly`/`SameSite=Strict`; nenhum `localStorage`; nenhum `dangerouslySetInnerHTML`; build sem segredos.
- **API:** schema OpenAPI válido sem avisos (`spectacular --validate --fail-on-warn`).

## 3. Comandos executados e resultados (reais)

| Comando | Resultado |
|---|---|
| `ruff check .` / `ruff format --check .` | Sem problemas · 58 arquivos formatados |
| `pytest --cov` | **276 passed** · cobertura 98% (linhas não cobertas: bloco de produção do `settings.py`, exercitado pelo `check --deploy`) |
| `manage.py makemigrations --check --dry-run` | No changes detected |
| `manage.py spectacular --validate --fail-on-warn` | exit 0 |
| `manage.py check --deploy` (DEBUG=False) | Antes: 4 avisos · Depois: 2 avisos (HSTS, decisão consciente) |
| `npx tsc --noEmit` | exit 0 |
| `npx vitest run` | **35 passed** (7 arquivos) |
| `npm run build` | OK · 145 KB gzip |
| `docker compose config --quiet` | exit 0 (validação estática apenas) |
| `docker compose up` | **NÃO executado** — engine do Docker parado |

Testes de segurança novos: os de A1, A2 e A3 **falharam antes da correção** e passam depois. O teste de B1 falha se o comportamento antigo for reintroduzido (verificado).

## 4. Checklist de qualidade para a primeira versão publicável (v1.0)

### Segurança
- [x] Senhas com hash e validação de força
- [x] Todas as permissões verificadas no backend (testes de acesso indevido para os 3 perfis)
- [x] Refresh token em cookie `HttpOnly` + `SameSite=Strict`; access só em memória
- [x] Limite de tentativas de login que não pode ser burlado por cabeçalho
- [x] API somente JSON (proteção CSRF)
- [x] Troca de senha encerra sessões
- [x] Configurações de produção ativadas com `DEBUG=False`
- [ ] `SECRET_KEY` forte e exclusiva de produção, fora do repositório
- [ ] `ALLOWED_HOSTS` e `NUM_PROXIES` configurados para o servidor real
- [ ] Cache compartilhado para o limite de tentativas (M4)
- [ ] Proteção contra força bruta no `/admin/` (ou restringir acesso a ele)
- [ ] Decidir HSTS `includeSubDomains`/`preload`
- [ ] `check --deploy` sem avisos não justificados

### Qualidade e testes
- [x] Backend: testes de regras, permissões, filtros, paginação e consultas (276)
- [x] Frontend: testes de login, sessão, listagem, formulário e detalhes (35)
- [ ] ESLint no frontend e medição de cobertura (B7)
- [ ] CI (GitHub Actions) rodando lint, testes e build a cada push
- [ ] Teste ponta a ponta (ex.: Playwright) do fluxo principal

### Infraestrutura
- [ ] `docker compose up` executado e validado (M3)
- [ ] Dockerfile de produção (gunicorn, sem dependências de teste, usuário não-root)
- [ ] Frontend compilado servido por Nginx na mesma origem da API
- [ ] Banco gerenciado com backup automático
- [ ] Migrations aplicadas no deploy; logs de erro centralizados

### Produto e documentação
- [x] README com instruções de execução
- [x] Documentação da API (Swagger) e de autenticação
- [ ] Categorias padrão e comando de dados de demonstração (`seed_demo`)
- [ ] Telas administrativas no React (usuários e categorias) ou orientação clara de uso do Django Admin
- [ ] Capturas de tela e link do deploy no README
