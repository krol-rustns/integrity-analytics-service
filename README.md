# Integrity Analytics Service

Microsserviço para análise de telemetria industrial, detecção de anomalias e geração de diagnósticos via gRPC.

## Pré-requisitos

Os seguintes serviços devem estar em execução:

- `petroedge-operational`: gRPC na porta `50051`.
- `operational-response-service (OPRS)`: gRPC na porta `9090`.

## Execução

Clone o repositório:

```bash
git clone https://github.com/SEU_USUARIO/integrity-analytics-service.git
cd integrity-analytics-service
```

Configure as variáveis de ambiente:

```bash
cp .env.example .env
```

Ajuste o arquivo `.env` conforme necessário e inicie o serviço.

## Docker

Para iniciar o serviço:

```bash
docker compose up -d --build
```

Para acompanhar os logs:

```bash
docker compose logs -f
```
