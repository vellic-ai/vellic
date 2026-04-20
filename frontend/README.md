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

| Command            | Description                        |
| ------------------ | ---------------------------------- |
| `npm run dev`      | Start dev server (port 5173)       |
| `npm run build`    | Type-check + Vite production build |
| `npm run typecheck`| Run TypeScript without emitting    |
| `npm run lint`     | ESLint (zero warnings)             |
| `npm run test`     | Run Vitest unit tests              |
| `npm run test:watch` | Vitest in watch mode             |

## Running tests

```bash
npm run test
```

Unit tests use Vitest + React Testing Library + MSW for API mocking.

## E2E tests

Playwright is installed. Actual test files live in `e2e/` and are authored separately (VEL-51).

```bash
npx playwright test
```

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
