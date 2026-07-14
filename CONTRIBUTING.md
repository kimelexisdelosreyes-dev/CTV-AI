# Contributing to CTV ONE

## Branches

- `main`: stable tagged releases
- `develop`: integration branch
- `feature/*`: new capabilities
- `fix/*`: normal fixes
- `hotfix/*`: urgent stable-release fixes
- `docs/*`: documentation
- `chore/*`: tooling and maintenance

## Workflow

```powershell
git checkout develop
git pull
git checkout -b feature/example
```

After work:

```powershell
git add .
git commit -m "feat(module): describe the change"
git push -u origin feature/example
```

## Commit prefixes

`feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`, `build`, `ci`

## Required checks

```powershell
cd B:\CTV_AIackend
python -m compileall app
python -m pytest

cd B:\CTV_AIrontend\enterprise-ui
npm run lint
npm run build
```

Database schema changes require a new Alembic migration with upgrade and downgrade paths.
