# Metl Coding Agent - Testing

## Backend Tests (pytest)

### Run agent API tests
```bash
cd apps/agent-api
pytest tests/ -v
```

### Run with coverage
```bash
cd apps/agent-api
pytest tests/ --cov=src --cov-report=term-missing
```

## Frontend Tests (Playwright/Vitest)

### Run E2E tests
```bash
cd apps/dashboard
pnpm test:e2e
```

## Docker Compose

### Start all services
```bash
docker-compose up -d
```

### Run tests against local services
```bash
docker-compose -f docker-compose.test.yml up --build
```

## Test Environment
- POSTGRES_TEST_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/metl_test
- REDIS_TEST_URL: redis://localhost:6379/1
- Use test containers for integration tests