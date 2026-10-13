"""
error_classifier.py
-------------------
Maps raw exceptions and source locations to:
  - A severity level  (MINOR / MAJOR / CRITICAL)
  - A plain-English explanation of WHERE and WHY the error happened

FIX (2026-05-26): Added missing timeout/proxy error patterns that were
causing all log entries to fall through to the generic "unexpected error"
fallback. Patterns are now checked case-insensitively.
"""

from enum import Enum


class ErrorSeverity(Enum):
    MINOR    = "MINOR"     # Something small went wrong; the app may keep running
    MAJOR    = "MAJOR"     # A key feature failed; user action likely needed
    CRITICAL = "CRITICAL"  # Security or session integrity at risk; app must stop


# ── WHERE did the error come from? ───────────────────────────────────────────

LOCATION_LABELS = {
    "main":                 "Startup / main entry point",
    "monitor":              "Proxy & Chrome health monitor",
    "kill_switch":          "Kill-switch (emergency shutdown system)",
    "local_proxy":          "Local proxy bridge (the tunnel between Chrome and your SOCKS5 server)",
    "proxy_checker":        "Proxy connection tester",
    "chrome_launcher":      "Chrome browser launcher",
    "cleanup":              "Cleanup / temp-file remover",
    "logger":               "Logging system",
    "utils":                "Config loader / utilities",
    "dns_leak_protection":  "DNS leak protection",
    "fingerprint_reduction":"Browser fingerprint reduction",
    "error_reporter":       "Error reporting system",
}


# ── WHAT went wrong? ─────────────────────────────────────────────────────────
# Each entry: (keyword_in_exception_text_lowercase, severity, plain_english_cause)
# Patterns are checked IN ORDER — put more specific ones first.
# All matching is done against the lowercased exception string.

ERROR_PATTERNS = [

    # ── Timeout errors (these were the source of ALL entries in the log) ─────
    # The old classifier missed these because it only checked "10060" and
    # "timed out" but not the full urllib3/requests exception names.
    ("connecttimeout",          ErrorSeverity.MINOR,
     "The connection to your SOCKS5 proxy timed out while trying to connect. "
     "The proxy server took too long to respond — this is often a temporary blip. "
     "If it keeps happening, your proxy may be overloaded or offline."),

    ("readtimeout",             ErrorSeverity.MINOR,
     "The proxy connected successfully but the response took too long to arrive. "
     "This is usually a temporary slowdown on the proxy server. "
     "The monitor will retry automatically."),

    ("connecttimeouterror",     ErrorSeverity.MINOR,
     "The SOCKS5 connection timed out during the connect phase. "
     "The proxy server did not accept the connection in time."),

    ("proxyconnectionerror",    ErrorSeverity.MINOR,
     "Could not reach the SOCKS5 proxy server. "
     "It may be temporarily offline, rate-limiting connections, or the server address is wrong. "
     "The monitor will retry automatically."),

    ("generalproxyerror",       ErrorSeverity.MINOR,
     "The SOCKS5 proxy reported a socket-level error during the connection. "
     "This is often a transient network blip. The monitor will retry."),

    ("max retries exceeded",    ErrorSeverity.MAJOR,
     "The connection to the proxy failed after the maximum number of retry attempts. "
     "The proxy server may be down or your network connection may be unstable."),

    ("sockshttp",               ErrorSeverity.MINOR,
     "A network request through the SOCKS5 proxy timed out or failed. "
     "This is often temporary — the monitor will retry automatically."),

    ("read timed out",          ErrorSeverity.MINOR,
     "The proxy connection was established but reading the response took too long. "
     "Usually a temporary slowdown. The monitor will retry."),

    ("10060",                   ErrorSeverity.MAJOR,
     "The connection to your SOCKS5 proxy timed out (Windows error 10060). "
     "The proxy server did not respond in time — it may be offline or the address is wrong."),

    # ── Other network / proxy ────────────────────────────────────────────────
    ("10054",                   ErrorSeverity.MINOR,
     "The remote server forcibly closed the connection. "
     "This is usually a normal part of browsing; a website hung up the call."),

    ("10053",                   ErrorSeverity.MINOR,
     "A network connection was cut off by your own machine. "
     "This sometimes happens when Chrome or the proxy bridge is shutting down."),

    ("connection refused",      ErrorSeverity.MAJOR,
     "Nothing is listening on the target address. "
     "Either the SOCKS5 proxy server is down, or the local proxy bridge failed to start on port 8080."),

    ("proxy validation failed", ErrorSeverity.CRITICAL,
     "The SOCKS5 proxy could not be verified. "
     "Your username, password, server address, or port may be wrong — or the proxy is down."),

    ("proxy unreachable",       ErrorSeverity.CRITICAL,
     "The proxy stopped responding while you were browsing. "
     "Chrome has been shut down to protect your real IP address from leaking."),

    ("socks5 auth",             ErrorSeverity.CRITICAL,
     "The proxy rejected your username or password. "
     "Please check your credentials in config.json."),

    ("general socks server failure", ErrorSeverity.MAJOR,
     "The SOCKS5 server reported an internal error. "
     "The proxy may be overloaded or temporarily unavailable."),

    ("name or service not known", ErrorSeverity.MAJOR,
     "A hostname could not be resolved (turned into an IP address). "
     "This may indicate a DNS leak or that the proxy does not support DNS-over-SOCKS."),

    # ── Chrome ───────────────────────────────────────────────────────────────
    ("chrome process died",     ErrorSeverity.CRITICAL,
     "The Chrome browser closed unexpectedly. "
     "The kill switch has fired to make sure no unprotected connections can be made."),

    ("chrome process terminated", ErrorSeverity.CRITICAL,
     "Chrome stopped running without warning. "
     "This can happen if Chrome crashed or was closed manually. The session has been ended for safety."),

    ("no such file or directory", ErrorSeverity.MAJOR,
     "Chrome could not be found at the path listed in config.json. "
     "Please check that Google Chrome is installed and the chrome_path setting is correct."),

    ("permission denied",       ErrorSeverity.MAJOR,
     "The program was blocked from accessing a file or folder. "
     "Try running the terminal as Administrator."),

    # ── Local proxy bridge ───────────────────────────────────────────────────
    ("local proxy failed",      ErrorSeverity.CRITICAL,
     "The local proxy bridge (port 8080) could not start. "
     "Port 8080 may already be in use by another application. "
     "Close anything using that port and try again."),

    ("local proxy crashed",     ErrorSeverity.CRITICAL,
     "The local proxy bridge stopped working mid-session. "
     "All connections have been closed to prevent your real IP from being exposed."),

    ("address already in use",  ErrorSeverity.MAJOR,
     "Port 8080 is already occupied by another program. "
     "Check for other proxies or applications running on that port and close them."),

    ("broken pipe",             ErrorSeverity.MINOR,
     "A data pipe between Chrome and the proxy broke. "
     "This usually just means the browser navigated away from a page. Not harmful."),

    ("ipv6",                    ErrorSeverity.MINOR,
     "An IPv6 address was attempted but is blocked. "
     "This is expected — IPv6 is disabled on purpose to prevent IP leaks."),

    # ── Kill switch ──────────────────────────────────────────────────────────
    ("kill switch triggered",   ErrorSeverity.CRITICAL,
     "The emergency kill switch was activated. "
     "Chrome and all network connections have been forcibly closed "
     "to stop your real IP address from being revealed."),

    ("could not kill chrome",   ErrorSeverity.MAJOR,
     "The kill switch tried to shut Chrome down but was unable to. "
     "Please close Chrome manually right away to prevent unprotected connections."),

    # ── Config / startup ─────────────────────────────────────────────────────
    ("json",                    ErrorSeverity.MAJOR,
     "The config.json file could not be read. "
     "It may be corrupted or contain a typo. "
     "Delete config.json and restart to re-enter your proxy details."),

    ("cleanup error",           ErrorSeverity.MINOR,
     "The temporary Chrome profile folder could not be fully deleted. "
     "You can remove it manually — it is safe to do so."),

    # ── DNS ──────────────────────────────────────────────────────────────────
    ("netsh",                   ErrorSeverity.MINOR,
     "Changing the system DNS settings did not work. "
     "Your DNS may not be locked to Cloudflare. "
     "Consider setting it manually in your network adapter settings."),

    # ── Fallback — must stay last ─────────────────────────────────────────────
    ("",                        ErrorSeverity.MINOR,
     "An unexpected error occurred. See the details and screenshot below for more information."),
]


def classify(exception: Exception, source_module: str = "unknown") -> dict:
    """
    Given an exception and the module it came from, return a dict with:
      severity   – ErrorSeverity enum value
      location   – plain-English location string
      cause      – plain-English cause string
      raw_error  – the original exception message
    """
    # Lowercase once; all pattern matching is case-insensitive
    error_text = str(exception).lower()

    severity = ErrorSeverity.MINOR
    cause    = ERROR_PATTERNS[-1][2]   # default to fallback

    for keyword, sev, explanation in ERROR_PATTERNS:
        if keyword and keyword in error_text:
            severity = sev
            cause    = explanation
            break

    location = LOCATION_LABELS.get(source_module, f"Module: {source_module}")

    return {
        "severity":  severity,
        "location":  location,
        "cause":     cause,
        "raw_error": str(exception),
    }
