# Taskly App

## 🤖 See the agent in action

| Demo PR | Agent comments and results |
| --- | --- |
| **[PR #3 — Backend: sufficient tests](https://github.com/michalwilk123/taskly-app/pull/3)** | **[Read the 5/5 review](https://github.com/michalwilk123/taskly-app/pull/3#issuecomment-6351685952)** · [No additional tests needed](https://github.com/michalwilk123/taskly-app/pull/3#issuecomment-6352087517) |
| **[PR #4 — Frontend: missing tests](https://github.com/michalwilk123/taskly-app/pull/4)** | **[Read the gap assessment](https://github.com/michalwilk123/taskly-app/pull/4#issuecomment-6351715875)** · **[Generated tests and verification results](https://github.com/michalwilk123/taskly-app/pull/4#issuecomment-6351765422)** |

PR #4 intentionally retains the failing generated test that exposes an overdue-filter bug. The agent commits tests without changing production code.

**[Architecture, setup and workflow evidence → SOLUTION.md](SOLUTION.md)**

## Setup

```sh
cp .env.example .env
```

## Docker

```sh
docker compose up --build -d --wait
```

Application: http://localhost:8080. API: http://localhost:8000/docs.

```sh
docker compose down
```

## Frontend

Installation:

```sh
cd frontend
npm ci
```

Development — http://localhost:5173:

```sh
npm run dev
```

Storybook — http://localhost:6006:

```sh
npm run storybook
```

Tests:

```sh
npm test
```

Coverage — `frontend/coverage/index.html`:

```sh
npm run test:coverage
```

## Backend

Installation (from the repository root):

```sh
python3 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install -r backend/requirements.txt
```

Development — http://localhost:8000/docs:

```sh
docker compose up -d --wait postgres
cd backend
python -m uvicorn app.main:app --reload
```

Tests (in `backend`, with `.venv` activated):

```sh
python -m pytest
```

Coverage — `backend/coverage/html/index.html`:

```sh
python -m pytest --cov=app --cov-report=term-missing --cov-report=html
```
