FROM python:3.13-slim
WORKDIR /app
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY
COPY requirements.txt .
RUN HTTP_PROXY="${HTTP_PROXY}" HTTPS_PROXY="${HTTPS_PROXY}" NO_PROXY="${NO_PROXY}" pip install --no-cache-dir -r requirements.txt
COPY app ./app
CMD ["sh", "-c", "python -m app.migrations && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
