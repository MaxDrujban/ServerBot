FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    API_PORT=8010

WORKDIR /app

# Корневые сертификаты Минцифры: без них не проходят TLS-запросы к API MAX
# Файлы взяты с официального адреса https://gu-st.ru/content/Other/doc/russiantrustedca.pem
COPY certs/russian_trusted_root_ca.pem /usr/local/share/ca-certificates/russian_trusted_root_ca.crt
COPY certs/russian_trusted_sub_ca.pem /usr/local/share/ca-certificates/russian_trusted_sub_ca.crt
RUN update-ca-certificates

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# httpx берёт сертификаты не из системного хранилища, а из файла certifi,
# поэтому для MAX собираем общий набор: публичные УЦ + УЦ Минцифры
RUN CERTIFI_PATH="$(python -c 'import certifi; print(certifi.where())')" \
    && cat "$CERTIFI_PATH" \
           /usr/local/share/ca-certificates/russian_trusted_root_ca.crt \
           /usr/local/share/ca-certificates/russian_trusted_sub_ca.crt \
       > /etc/ssl/certs/max_ca_bundle.pem
ENV MAX_CA_BUNDLE=/etc/ssl/certs/max_ca_bundle.pem

COPY api ./api
COPY models ./models
COPY services ./services
COPY config.py main.py ./

EXPOSE 8010

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${API_PORT:-8010}"]