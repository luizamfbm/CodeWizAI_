# Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Copiar requirements primeiro para melhor cache
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o resto do código
COPY . /app

# Expor as portas que podem ser usadas
EXPOSE 8501 8502

# Não definir CMD aqui, deixar o docker-compose definir