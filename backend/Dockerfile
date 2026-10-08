# Imagem de DESENVOLVIMENTO do backend.
# A imagem de produção (gunicorn, sem dependências de teste) será criada na Etapa 20.
FROM python:3.14-slim

# Não gera arquivos .pyc e mostra os logs na hora (sem buffer).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Copiar só os requirements primeiro aproveita o cache do Docker:
# as dependências só são reinstaladas quando esses arquivos mudam.
COPY requirements.txt requirements-dev.txt ./
RUN pip install -r requirements-dev.txt

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py runserver 0.0.0.0:8000"]
