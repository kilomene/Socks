import requests
import time
import random
from logger import log
from error_handler import report_error

# Multi-endpoint IP check pool — rotated to avoid single-point failure
_IP_CHECK_ENDPOINTS = [
    "https://api.ipify.org",
    "https://ipinfo.io/ip",
    "https://icanhazip.com",
    "https://ifconfig.me",
]

_endpoint_index = 0

def _next_endpoint():
    """Round-robin through IP check endpoints."""
    global _endpoint_index
    ep = _IP_CHECK_ENDPOINTS[_endpoint_index % len(_IP_CHECK_ENDPOINTS)]
    _endpoint_index += 1
    return ep


def test_proxy(server, port, username, password, retries=3):
    """
    Verify SOCKS5 proxy is reachable and returns a routed IP.

    Uses socks5h so DNS resolves through the proxy (no local DNS leak).
    Rotates across multiple IP-check endpoints so a single endpoint
    outage does not cause false proxy failures.
    """
    for attempt in range(retries):
        endpoint = _next_endpoint()
        proxies = {
            'http':  f'socks5h://{username}:{password}@{server}:{port}',
            'https': f'socks5h://{username}:{password}@{server}:{port}',
        }
        try:
            start = time.time()
            r = requests.get(
                endpoint,
                proxies=proxies,
                timeout=(15, 20),   # (connect, read) split timeout
            )
            latency   = (time.time() - start) * 1000
            proxy_ip  = r.text.strip()

            log(f"Proxy OK via {endpoint} | IP: {proxy_ip} | Latency: {latency:.0f}ms")
            return True, proxy_ip, latency

        except Exception as e:
            log(f"Proxy test attempt {attempt+1}/{retries} failed [{endpoint}]: {e}", "WARNING")
            report_error(
                e,
                source_module="proxy_checker",
                extra_context=f"Attempt {attempt+1} of {retries} using endpoint {endpoint}.",
            )
            if attempt < retries - 1:
                time.sleep(2)

    log("Proxy validation failed after all retries.", "ERROR")
    return False, None, None
