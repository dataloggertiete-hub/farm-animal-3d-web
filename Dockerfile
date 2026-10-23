# Dockerfile para Farm Animal 3D Web Generator
# -------------------------------------------
# Build: docker build -t farm-animal-3d-web .
# Run:   docker run -p 5000:5000 farm-animal-3d-web

FROM python:3.12-slim

WORKDIR /app

# Instalar dependências
COPY farm_animal_web/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar aplicação
COPY farm_animal_web/ .

# Porta exposta
EXPOSE 5000

# Comando de inicialização
CMD ["python", "app.py"]