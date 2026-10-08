# HelpDesk Pro

Sistema de gestão de chamados de suporte técnico de TI, desenvolvido como projeto de portfólio full stack.

> 🚧 **Em desenvolvimento.** O planejamento está concluído e a implementação segue as etapas descritas em [docs/PLANEJAMENTO.md](docs/PLANEJAMENTO.md).

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
| Testes | pytest, pytest-django, factory_boy, Vitest, React Testing Library, MSW |
| Ambiente | Docker, Docker Compose, GitHub Actions |

## Documentação

- [Planejamento completo](docs/PLANEJAMENTO.md): requisitos, regras de negócio, modelo de dados, arquitetura, endpoints e plano de implementação.

## Como rodar

Primeiro, copie o arquivo de variáveis de ambiente e ajuste se necessário:

```bash
cp .env.example .env
```

### Opção 1 — Docker (recomendado)

Requer [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```bash
docker compose up --build
```

Rodar os testes dentro do container:

```bash
docker compose exec backend pytest
```

### Opção 2 — Sem Docker

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

### Verificando

Acesse http://localhost:8000/api/health/ — a resposta deve ser `{"status": "ok", "database": "ok"}`.

### Acessando o Django Admin

Crie seu próprio administrador (o login é pelo e-mail):

```bash
python manage.py createsuperuser
```

Depois acesse http://localhost:8000/admin/.
