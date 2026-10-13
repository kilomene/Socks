# Socks

SOCKS5 proxy protector with kill switch, DNS leak protection, fingerprint
reduction, and a Chrome launcher that routes traffic through a SOCKS5 proxy.

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Copy the config template and fill in your proxy details:
   ```
   cp config.example.json config.json
   ```
   `config.json` is gitignored — your credentials never leave your machine.
3. Run:
   ```
   python main.py
   ```
   On Windows you can use `launcher.bat` instead.

## What it does

- `main.py` — entry point
- `local_proxy.py` — local SOCKS5 proxy
- `kill_switch.py` — kills connectivity if the proxy drops
- `dns_leak_protection.py` — blocks DNS leaks outside the tunnel
- `fingerprint_reduction.py` — browser fingerprint hardening
- `chrome_launcher.py` — launches Chrome through the proxy
- `proxy_checker.py` / `monitor.py` — proxy health checks and monitoring
- `cleanup.py` / `utils.py` / `logger.py` — helpers
- `error_handler/` — error classification, reporting, and screenshots

## Notes

- Run logs and screenshots stay local (excluded from git).
- Never commit `config.json` — it holds real proxy credentials.
