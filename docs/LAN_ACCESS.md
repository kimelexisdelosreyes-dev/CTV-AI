# CTV ONE LAN Access

Use this only on the office LAN. This is not an internet deployment and these ports must not be forwarded from the router.

## Start LAN Mode

From the repository root:

```powershell
cd B:\CTV_AI
.\scripts\start-lan.ps1
```

The script detects the active private LAN IPv4 address, starts Docker-backed internal dependencies with the existing compose file, starts the FastAPI backend on `0.0.0.0:8000`, and starts the Next.js frontend on `0.0.0.0:3001`.

Other laptops should open:

```text
http://192.168.31.42:3001
```

If DHCP changes the workstation address, run:

```powershell
Get-NetIPConfiguration
```

Use the private IPv4 address on the active Ethernet or Wi-Fi adapter with a default gateway. Ignore Docker, WSL, Hyper-V, VPN, loopback, and disconnected adapters.

## Firewall

Run these from an Administrator PowerShell. They are idempotent and only allow the Windows Private network profile.

```powershell
if (-not (Get-NetFirewallRule -DisplayName "CTV ONE Frontend LAN 3001" -ErrorAction SilentlyContinue)) {
  New-NetFirewallRule -DisplayName "CTV ONE Frontend LAN 3001" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 3001 -Profile Private
}

if (-not (Get-NetFirewallRule -DisplayName "CTV ONE Backend LAN 8000" -ErrorAction SilentlyContinue)) {
  New-NetFirewallRule -DisplayName "CTV ONE Backend LAN 8000" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000 -Profile Private
}
```

Do not open PostgreSQL, Qdrant, Redis, Ollama, Docker management, model-service, or database ports.

## Health Test

From the workstation:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
Invoke-RestMethod http://192.168.31.42:8000/api/v1/health
```

The expected response is:

```json
{"status":"healthy"}
```

## Troubleshooting

- Confirm Windows shows the office network as `Private`, not `Public`.
- Confirm the firewall rules above exist and are enabled for the Private profile.
- Confirm the frontend URL uses the workstation LAN IP, not `127.0.0.1` from another laptop.
- If login or API calls fail, check that `CORS_ALLOWED_ORIGINS` includes the exact frontend origin, such as `http://192.168.31.42:3001`.
- If the frontend loads but API calls fail, confirm `CTV_BACKEND_URL` is set for the Next.js process and points to `http://127.0.0.1:8000` on the workstation.
- If the IP changes after reboot, reserve the workstation IP in the router DHCP reservation settings.
- If laptops still cannot connect, check Wi-Fi client isolation and confirm all devices are on the same subnet, such as `192.168.31.x`.
- Do not enable router port forwarding for CTV ONE.
