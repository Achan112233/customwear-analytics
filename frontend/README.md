# CustomWear Analytics Dashboard

Responsive customer intelligence dashboard for the CustomWear Analytics platform. It provides segment distribution, revenue and retention insights, searchable customer profiles, and CSV transaction imports.

## Run locally

```bash
cp .env.example .env
npm ci
npm run dev
```

Set `NEXT_PUBLIC_API_BASE_URL` to the FastAPI origin. Without it, the interface intentionally runs in demo mode.

## Verify

```bash
npm run lint
npm test
```

The test command creates a production Vinext build and validates branded server-rendered output, social metadata, accessible landmarks, core API contracts, responsive breakpoints, and reduced-motion support.

## Docker

The multi-stage image builds the production bundle and runs as an unprivileged Node user. The root `docker-compose.yml` supplies the API and site URLs as build arguments.
