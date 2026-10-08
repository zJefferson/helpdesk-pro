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

_Instruções serão adicionadas a partir da Etapa 1 (backend + PostgreSQL no Docker)._
