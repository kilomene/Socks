import time
import requests
import random
from logger import log
from kill_switch import kill_switch
from error_handler import report_error
import colorama
from colorama import Fore

colorama.init()

last_status  = ""
print_count  = 0

# Split timeouts: connect phase vs read phase
HEALTH_CHECK_CONNECT_TIMEOUT = 15
HEALTH_CHECK_READ_TIMEOUT    = 20

# 3 consecutive failures before triggering kill switch
MAX_FAIL_STREAK = 3

# Multi-endpoint pool — rotate to avoid a dead endpoint masking a real failure
_IP_CHECK_ENDPOINTS = [
    "https://api.ipify.org",
    "https://ipinfo.io/ip",
    "https://icanhazip.com",
    "https://ifconfig.me",
]
_endpoint_index = 0

def _next_endpoint():
    global _endpoint_index
    ep = _IP_CHECK_ENDPOINTS[_endpoint_index % len(_IP_CHECK_ENDPOINTS)]
    _endpoint_index += 1
    return ep

# Phrases that indicate a transient timeout — logged but not reported as errors
_TRANSIENT_PHRASES = (
    "timed out", "timeout", "connecttimeout", "readtimeout",
    "proxyconnectionerror", "10060",
)


def monitor_proxy_and_chrome(chrome_proc, proxy_config):
    global last_status, print_count
    fail_streak = 0

    while True:
        try:
            # ── Chrome still alive? ──────────────────────────────────────
            if chrome_proc.poll() is not None:
                log("Chrome process terminated", "WARNING")
                kill_switch.trigger("Chrome process died unexpectedly")

            # ── Proxy health check via rotating endpoint ─────────────────
            endpoint = _next_endpoint()
            proxies = {
                'http':  (f'socks5h://{proxy_config["username"]}:{proxy_config["password"]}'
                          f'@{proxy_config["server"]}:{proxy_config["port"]}'),
                'https': (f'socks5h://{proxy_config["username"]}:{proxy_config["password"]}'
                          f'@{proxy_config["server"]}:{proxy_config["port"]}'),
            }

            r = requests.get(
                endpoint,
                proxies=proxies,
                timeout=(HEALTH_CHECK_CONNECT_TIMEOUT, HEALTH_CHECK_READ_TIMEOUT),
            )
            current_ip  = r.text.strip()
            fail_streak = 0   # reset on success

            status = f"CONNECTED | IP: {current_ip}"
            if print_count == 0 or status != last_status:
                print(f"\n{Fore.GREEN}Proxy Health        CONNECTED                     🟢")
                print(f"Chrome Process      RUNNING                       🟢")
                print(f"Current IP          {current_ip}                  ✅")
                print(f"Check endpoint      {endpoint}")
                last_status  = status
                print_count += 1

            time.sleep(6)

        except Exception as e:
            fail_streak += 1
            err_lower = str(e).lower()
            log(f"Health check failed (streak {fail_streak}/{MAX_FAIL_STREAK}) [{endpoint}]: {e}", "WARNING")

            is_transient = any(p in err_lower for p in _TRANSIENT_PHRASES)
            if not is_transient:
                report_error(
                    e,
                    source_module="monitor",
                    extra_context=f"Non-transient proxy failure {fail_streak} time(s) in a row via {endpoint}.",
                )

            if fail_streak >= MAX_FAIL_STREAK:
                kill_switch.trigger(f"Proxy unreachable after {fail_streak} consecutive checks: {e}")

            time.sleep(6)
