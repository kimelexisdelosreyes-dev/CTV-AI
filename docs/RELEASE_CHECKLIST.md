# Release Checklist

## Code
- [ ] Backend compile check passes
- [ ] Backend tests pass
- [ ] Frontend lint passes
- [ ] Frontend production build passes
- [ ] No secrets committed
- [ ] `.env.example` updated

## Infrastructure
- [ ] PostgreSQL healthy
- [ ] Qdrant healthy
- [ ] Ollama responds
- [ ] Required models installed
- [ ] Alembic migration is at head

## Application
- [ ] Login succeeds
- [ ] Roles work
- [ ] Open WebUI models load
- [ ] Enterprise UI loads
- [ ] Company Brain upload and search work
- [ ] Grounded answers cite sources

## Release
- [ ] VERSION updated
- [ ] CHANGELOG updated
- [ ] Migration notes updated
- [ ] Stable commit merged into main
- [ ] Version tag pushed
- [ ] Rollback point recorded
