# Use uma imagem base do Python
FROM python:3.10-slim

# Defina o diretório de trabalho
WORKDIR /app

# Instale o LibreOffice e outras dependências do sistema
# O comando apt-get update pode falhar às vezes, adicionamos retry
RUN apt-get update && \
    apt-get install -y --no-install-recommends libreoffice wget ca-certificates fonts-liberation && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copie o arquivo de requisitos
COPY requirements.txt requirements.txt

# Instale as dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copie o restante do código da aplicação
COPY . .

# Copie os arquivos de entrada explicitamente (garantia)
COPY input_files/ input_files/

# Crie o diretório de saída se não existir
RUN mkdir -p /app/output

# Exponha a porta que o Gunicorn usará
EXPOSE 8080

# Comando para rodar a aplicação com Gunicorn
# Use 0.0.0.0 para aceitar conexões externas
# Ajuste o número de workers (-w) conforme necessário (e.g., 2 * num_cores + 1)
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8080", "app:app"]
