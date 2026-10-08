# Autenticação e permissões

## Estratégia: JWT (SimpleJWT)

| Token | Validade | Para que serve |
|---|---|---|
| `access` | 15 min | Enviado em toda requisição: `Authorization: Bearer <access>` |
| `refresh` | 1 dia | Só serve para obter um novo `access` em `/auth/token/refresh/` |

- **Rotação:** cada uso do `refresh` devolve um `refresh` novo e invalida o antigo.
- **Logout:** o `refresh` vai para uma *blacklist* no banco e não pode mais ser usado.
- **Limite de tentativas:** login limitado por IP (`LOGIN_THROTTLE_RATE`, padrão `10/min`).
- **Senhas:** sempre com hash (PBKDF2); validadas quanto à força.

**Vantagens:** funciona bem com React e Django em origens diferentes, sem configurar cookies/CSRF entre sites; fácil de usar no Swagger, curl e Postman.

**Limitações:** um `access` vazado vale até expirar (por isso dura só 15 min); tokens acessíveis por JavaScript são alvo de XSS (mitigação: access em memória no frontend, React escapa HTML; melhoria futura: refresh em cookie `HttpOnly`).

## Endpoints

| Método | Rota | Quem | Descrição |
|---|---|---|---|
| POST | `/api/v1/auth/token/` | público | Login → `access` + `refresh` |
| POST | `/api/v1/auth/token/refresh/` | público | Renova o `access` |
| POST | `/api/v1/auth/logout/` | logado | Invalida o `refresh` (204) |
| GET/PATCH | `/api/v1/auth/me/` | logado | Dados próprios; só o nome é editável |
| POST | `/api/v1/auth/me/change-password/` | logado | Troca de senha (exige a atual) |
| GET/POST | `/api/v1/users/` | admin | Lista/cria usuários |
| GET/PATCH | `/api/v1/users/{id}/` | admin | Detalhe/edição (sem DELETE: desative com `is_active=false`) |
| GET/POST | `/api/v1/tickets/` | logado | Lista os chamados visíveis / abre chamado |
| GET/PATCH | `/api/v1/tickets/{id}/` | logado | Detalhe / edição conforme permissões |
| POST | `/api/v1/tickets/{id}/assign/` | técnico, admin | `{"assignee_id": 3}` |
| POST | `/api/v1/tickets/{id}/status/` | logado | `{"status": "RESOLVED"}` — valida a transição |
| GET/POST | `/api/v1/tickets/{id}/comments/` | logado | `{"body": "...", "is_internal": false}` |
| GET | `/api/v1/tickets/{id}/history/` | logado | Histórico de alterações |
| GET | `/api/v1/users/technicians/` | técnico, admin | Técnicos ativos |

Parâmetros de `GET /api/v1/tickets/`: `status` e `priority` (aceitam vários), `category`, `requester`,
`assignee`, `unassigned=true`, `created_after`/`created_before` (AAAA-MM-DD), `search` (título,
descrição ou número), `ordering` (`created_at`, `updated_at`, `priority`, `status`, `id`; prefixo `-`
para decrescente), `page` e `page_size` (máx. 100).

Documentação interativa: http://localhost:8000/api/docs/ (clique em **Authorize** e cole o `access`).

## Matriz de permissões

| Ação | Solicitante | Técnico | Administrador |
|---|---|---|---|
| Ver chamados | só os próprios (alheio → **404**) | todos | todos |
| Abrir chamado | ✅ (vira o solicitante) | ✅ | ✅ |
| Editar título/descrição/categoria | próprio, só com status Aberto | se for o responsável | ✅ |
| Editar prioridade | ❌ (só na criação) | se for o responsável | ✅ |
| Editar status/responsável/solicitante via PATCH | ❌ (400) | ❌ (400) | ❌ (400) |
| Atribuir técnico (`/assign/`) | ❌ (403) | só assumir para si, se sem responsável | ✅ qualquer técnico ativo |
| Iniciar / aguardar / resolver (`/status/`) | ❌ (403) | se for o responsável | ✅ |
| Cancelar (se Aberto) / fechar ou reabrir (se Resolvido) | próprio chamado | ❌ (403) | ✅ |
| Comentar | próprio chamado | ✅ (inclusive nota interna) | ✅ (inclusive nota interna) |
| Ver notas internas | ❌ (ocultas) | ✅ | ✅ |
| Ver histórico | próprio chamado | ✅ | ✅ |
| Qualquer escrita em chamado Fechado/Cancelado | ❌ (403) | ❌ (403) | ❌ (403) |
| Alterar o próprio perfil (`role`) | ❌ (400) | ❌ (400) | ❌ não pode se rebaixar |
| Gerenciar usuários | ❌ (403) | ❌ (403) | ✅ (não pode se desativar) |

Campos que o cliente não pode alterar são **recusados com 400** (em vez de ignorados em silêncio).

### Códigos de resposta

- `400` dados inválidos ou campo proibido
- `401` sem token, token inválido/expirado ou login incorreto
- `403` autenticado, mas sem permissão
- `404` não existe **ou** o usuário não pode vê-lo
- `429` excesso de tentativas de login

## Criando o primeiro administrador

Dentro de `backend/`, com o ambiente virtual ativo:

```bash
python manage.py createsuperuser
```

O comando pede e-mail, nome, sobrenome e senha (com validação de força). O superusuário nasce com perfil **ADMIN**.

## Cadastrando usuários de teste

**Opção 1 — pela API (recomendado, testa o fluxo real).** Faça login como admin e crie os usuários:

```bash
curl -X POST http://localhost:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email": "SEU_EMAIL_ADMIN", "password": "SUA_SENHA"}'
```

```bash
curl -X POST http://localhost:8000/api/v1/users/ \
  -H "Authorization: Bearer ACCESS_DO_ADMIN" \
  -H "Content-Type: application/json" \
  -d '{"email": "tecnico@helpdesk.local", "first_name": "Tiago", "last_name": "Tecnico", "role": "TECHNICIAN", "password": "Tecnico-teste-123"}'
```

Repita com `"role": "REQUESTER"` para criar um solicitante.

**Opção 2 — pelo Django Admin:** http://localhost:8000/admin/ → Usuários → Adicionar.

**Opção 3 — pelo Swagger:** http://localhost:8000/api/docs/ → `POST /auth/token/` → Authorize → `POST /users/`.

> Use contas de teste apenas no ambiente local. Em produção, crie usuários reais com senhas fortes.

## Exemplos de requisições e respostas

Login:

```http
POST /api/v1/auth/token/
{"email": "solicitante@helpdesk.local", "password": "..."}

200 OK
{"refresh": "eyJhbGciOi...", "access": "eyJhbGciOi..."}
```

Login inválido:

```http
401 Unauthorized
{"detail": "E-mail ou senha inválidos."}
```

Solicitante tentando se promover:

```http
PATCH /api/v1/auth/me/
Authorization: Bearer <access do solicitante>
{"role": "ADMIN"}

400 Bad Request
{"role": ["Este campo não pode ser alterado."]}
```

Solicitante tentando ver chamado de outra pessoa:

```http
GET /api/v1/tickets/2/

404 Not Found
{"detail": "Não encontrado."}
```

Técnico tentando editar chamado que não é dele:

```http
PATCH /api/v1/tickets/1/
{"title": "Mudado pelo técnico"}

403 Forbidden
{"detail": "Você não tem permissão para alterar este chamado."}
```

Refresh após logout:

```http
POST /api/v1/auth/token/refresh/
{"refresh": "<refresh já invalidado>"}

401 Unauthorized
{"detail": "Token is blacklisted", "code": "token_not_valid"}
```
