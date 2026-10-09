# HelpDesk Pro

Sistema de gestão de chamados de suporte técnico de TI, desenvolvido como projeto de portfólio full stack.

> 🚧 **Em desenvolvimento.** Backend e frontend do MVP implementados; CI e deploy em andamento. Etapas em [docs/PLANEJAMENTO.md](docs/PLANEJAMENTO.md).

## Funcionalidades (MVP)

- Autenticação com JWT e três perfis: **administrador**, **técnico** e **solicitante**
- Abertura, consulta, edição e acompanhamento de chamados
- Categorias, prioridades e fluxo de status
- Atribuição de chamados a técnicos
- Comentários (com notas internas) e histórico de alterações
- Dashboard com indicadores
- Busca, filtros, ordenação e paginação
- API REST documentada com OpenAPI/Swagger
- Testes automatizados de regras de negócio e permissões

## Tecnologias

| Camada | Tecnologias |
|---|---|
| Backend | Python, Django, Django REST Framework, SimpleJWT, drf-spectacular |
| Banco de dados | PostgreSQL |
| Frontend | React, TypeScript, Vite, Tailwind CSS, TanStack Query |
| Testes | pytest, pytest-django, Vitest, React Testing Library, MSW |
| Ambiente | Docker, Docker Compose, GitHub Actions |

## Documentação

- [Planejamento completo](docs/PLANEJAMENTO.md): requisitos, regras de negócio, modelo de dados, arquitetura, endpoints e plano de implementação.
- [Autenticação e permissões](docs/AUTENTICACAO.md): estratégia JWT, matriz de permissões, como criar o primeiro admin e usuários de teste, exemplos de requisições.
- Swagger (com o servidor rodando): http://localhost:8000/api/docs/

## Como rodar

Primeiro, copie o arquivo de variáveis de ambiente e ajuste se necessário:

```bash
cp .env.example .env
```

### Opção 1 — Docker

Requer [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```bash
docker compose up --build
```

Sobe o PostgreSQL, o backend (http://localhost:8000) e o frontend (http://localhost:5173).
Rodar os testes dentro dos containers:

```bash
docker compose exec backend pytest
```

```bash
docker compose exec frontend npm test
```

### Opção 2 — Sem Docker

São dois terminais: um para o backend e outro para o frontend.

#### Backend (terminal 1)

Requer Python 3.14 e PostgreSQL 16 instalados, com um usuário e banco `helpdesk`
(senha `helpdesk`, com permissão `CREATEDB` para os testes):

```sql
CREATE ROLE helpdesk WITH LOGIN PASSWORD 'helpdesk' CREATEDB;
CREATE DATABASE helpdesk OWNER helpdesk;
```

Depois, dentro de `backend/`:

```bash
python -m venv .venv
.venv\Scripts\activate        # Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt
python manage.py migrate
python manage.py runserver
```

Testes e lint:

```bash
pytest --cov
ruff check .
```

Acesse http://localhost:8000/api/health/ — a resposta deve ser `{"status": "ok", "database": "ok"}`.

#### Frontend (terminal 2)

Requer Node.js 24. Dentro de `frontend/`:

```bash
npm install
npm run dev
```

Acesse **http://localhost:5173**. O Vite repassa as chamadas `/api` para o Django em
`localhost:8000` (proxy), então o backend precisa estar rodando.

Testes, verificação de tipos e build de produção:

```bash
npm test
npm run typecheck
npm run build
```

### Como o frontend se autentica

- O login usa `/api/v1/auth/session/login/`: o **access token** (15 min) volta no corpo e fica
  **só em memória**; o **refresh token** vai num cookie `HttpOnly` + `SameSite=Strict`, que o
  JavaScript não consegue ler.
- Ao recarregar a página, o app chama `/auth/session/refresh/` e recupera a sessão pelo cookie.
- Nenhum token é guardado em `localStorage`. O perfil do usuário vem sempre de `/auth/me/` e
  serve só para decidir o que mostrar; quem autoriza cada ação é o backend.

### Acessando o Django Admin

Crie seu próprio administrador (o login é pelo e-mail). Para cadastrar usuários de teste,
veja [docs/AUTENTICACAO.md](docs/AUTENTICACAO.md#cadastrando-usuários-de-teste).

```bash
python manage.py createsuperuser
```

Depois acesse http://localhost:8000/admin/.
