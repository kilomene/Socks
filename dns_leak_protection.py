# dns_leak_protection.py
import subprocess
from logger import log


def apply_system_dns_protection():
    """
    Force system DNS to Cloudflare on common adapter names.
    This is a belt-and-suspenders measure; the real DNS leak protection
    is socks5h (rdns=True in PySocks), which routes all hostname
    resolution through the proxy server, never touching the local resolver.
    """
    adapters = ["Ethernet", "Wi-Fi", "Local Area Connection", "Ethernet 2"]
    for adapter in adapters:
        try:
            result = subprocess.run(
                f'netsh interface ip set dns "{adapter}" static 1.1.1.1',
                shell=True,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                log(f"System DNS forced to Cloudflare on adapter: {adapter}")
        except Exception as e:
            log(f"DNS protection skipped for '{adapter}': {e}", "WARNING")
