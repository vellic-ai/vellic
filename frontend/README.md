# Vellic Frontend

SPA built with Vite + React 19 + TypeScript + Tailwind CSS v4 + shadcn/ui.

## Setup

```bash
npm install
```

## Dev server

```bash
npm run dev         # http://localhost:5173
```

Vite proxies `/admin/*` and `/health` to the FastAPI backend at `http://localhost:8001`.

## Available scripts

| Command               | Description                                              |
| --------------------- | -------------------------------------------------------- |
| `npm run dev`         | Start dev server (port 5173)                             |
| `npm run build`       | Type-check + Vite production build                       |
| `npm run typecheck`   | Run TypeScript without emitting                          |
| `npm run lint`        | ESLint (zero warnings)                                   |
| `npm run test`        | Run Vitest unit tests (no backend required)              |
| `npm run test:watch`  | Vitest in watch mode                                     |
| `npm run test:e2e`    | Run Playwright smoke tests (requires full stack)         |
| `npm run test:e2e:ui` | Playwright interactive UI mode                           |
| `npm run gen:api`     | Regenerate OpenAPI types from a running admin server     |

## Running tests

### Unit tests (no backend needed)

```bash
npm run test
```

Unit tests use Vitest + React Testing Library. All API calls are mocked with MSW handlers in `src/api/msw/handlers.ts`.

### E2E tests (full stack required)

```bash
# Easiest — uses docker for infra, local processes for admin + frontend:
../scripts/e2e-local.sh

# Or run manually against an already-running stack:
E2E_BASE_URL=http://localhost:5173 \
E2E_API_BASE=http://localhost:8001 \
npm run test:e2e
```

E2E tests live in `e2e/` and require Postgres, Redis, and the admin service running with `VELLIC_ADMIN_V2=1`.

## API client

Typed HTTP client lives in `src/api/`:

```
src/api/
  client.ts          # openapi-fetch instance + error middleware (401→logout, 403/5xx→toast)
  schema.d.ts        # openapi-typescript types generated from admin's OpenAPI spec
  index.ts           # public re-exports
  hooks/
    auth.ts          # useAuthStatus, useLogin, useLogout, useSetup, useChangePassword
    deliveries.ts    # useDeliveries, useReplayDelivery
    jobs.ts          # useJobs
    repos.ts         # useRepos, useCreateRepo, useUpdateRepo, useToggleRepo, useDeleteRepo
    settings.ts      # useLLMSettings, useWebhookSettings, useSave*, useTest*, useRotate*
    stats.ts         # useStats
  msw/handlers.ts    # MSW mock handlers (used in unit tests and dev without backend)
```

### Regenerating types

When the admin API changes, regenerate `schema.d.ts` against a running server:

```bash
# Admin must be running on port 8001
npm run gen:api
```

This runs `openapi-typescript http://localhost:8001/openapi.json -o src/api/schema.d.ts`.

### Auth

The admin uses cookie-based session auth. The client sets `credentials: "include"` on every request so cookies are sent automatically. No manual token management required.

## Design tokens

Dark-theme CSS variables are sourced from `../admin/design/v0.1/tokens.css` and
imported via `src/styles/globals.css`. Do not edit tokens there — edit the source file.

## Stack

- **Build**: Vite 6
- **Framework**: React 19 + TypeScript 5 (strict)
- **Routing**: React Router v7
- **Styling**: Tailwind CSS v4 + shadcn/ui (Radix primitives)
- **Server state**: TanStack Query v5
- **Unit tests**: Vitest + React Testing Library
- **E2E**: Playwright (configured, tests in VEL-51)
- **Mock**: MSW v2
