# RC1 Validation Checklist

- [x] Frontend TypeScript check passes.
- [x] Frontend lint passes.
- [x] Frontend tests pass: 115.
- [x] Frontend production build passes and includes `/capabilities`.
- [x] Focused capability API, governance, and manifest tests pass: 8.
- [x] Backend regression suite passes: 701.
- [x] Alembic migration head resolves to `0011`.
- [x] Registry, manifest, governance, discovery, execution, identity, and disabled-flag paths are covered by tests.
- [x] `git diff --check -- frontend backend` passes.
- [ ] Controlled authenticated environment validates browser navigation/load and real execution timing before production flag activation.
