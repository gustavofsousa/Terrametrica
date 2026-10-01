# Imagem da API + front estático na mesma origem (AD-013). A ingestão não roda aqui: a base é
# carregada localmente (`python -m terrametrica.ingestao.carregar_base`) e restaurada no banco.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TERRAMETRICA_DIR_APP=/srv/app

WORKDIR /srv
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install .
COPY app ./app

# OPS: Railway injeta PORT; bind em 0.0.0.0 senão o healthcheck não alcança o processo.
CMD ["sh", "-c", "uvicorn terrametrica.api.app:app_padrao --factory --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
