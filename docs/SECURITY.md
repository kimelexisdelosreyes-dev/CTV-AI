# Security Notes

- Replace the default PostgreSQL password before broader deployment.
- Replace `JWT_SECRET_KEY` with a long random secret.
- Never commit `.env`.
- JWT payloads are signed, not encrypted. Do not place passwords or confidential data in tokens.
- PostgreSQL and Qdrant are bound to localhost in the development Compose configuration.
- Add HTTPS before exposing authentication beyond a trusted private LAN.
