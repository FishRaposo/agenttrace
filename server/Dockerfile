FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
# shared-core is the workspace's shared library (installed from its public git repo).
RUN pip install --no-cache-dir \
    "git+https://github.com/FishRaposo/operator-shared-core.git" \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

# Make entrypoint executable
RUN chmod +x docker-entrypoint.sh

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=5)"

ENTRYPOINT ["./docker-entrypoint.sh"]
