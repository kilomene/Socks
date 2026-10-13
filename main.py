import os
import sys
import threading
import time
from utils import print_status, load_config, save_config
from proxy_checker import test_proxy
from chrome_launcher import launch_chrome
from monitor import monitor_proxy_and_chrome
from cleanup import cleanup
from logger import log
from local_proxy import start_local_proxy
from kill_switch import kill_switch
from error_handler import report_error
import colorama
from colorama import Fore, Style

colorama.init()

def main():
    print_status("1/8", "Loading config...", Fore.CYAN)
    config = load_config()

    if not config['proxy'].get('server'):
        print(Fore.YELLOW + "\nEnter SOCKS5 details:")
        config['proxy']['server']   = input("Server: ").strip()
        config['proxy']['port']     = int(input("Port (default 5050): ") or 5050)
        config['proxy']['username'] = input("Username: ").strip()
        config['proxy']['password'] = input("Password: ").strip()
        save_config(config)

    proxy = config['proxy']

    # === VALIDATION SEQUENCE ===
    print_status("2/8", "Verifying SOCKS5 proxy...", Fore.CYAN)
    success, real_ip, latency = test_proxy(
        proxy['server'], proxy['port'], proxy['username'], proxy['password']
    )

    if not success:
        log("Proxy validation failed. Aborting.", "ERROR")
        report_error(
            Exception("Proxy validation failed after all retries."),
            source_module="main",
            extra_context="Could not verify SOCKS5 proxy during startup. Check your credentials and server address."
        )
        sys.exit(1)

    print_status("3/8", f"Proxy authenticated | IP: {real_ip} | Latency: {latency:.0f}ms", Fore.GREEN)
    print_status("4/8", "Testing DNS leak protection...", Fore.CYAN)
    print_status("5/8", "Applying Chrome hardening...", Fore.CYAN)

    # Start Local Proxy Bridge
    print_status("6/8", "Starting local proxy bridge...", Fore.CYAN)
    proxy_thread = threading.Thread(
        target=start_local_proxy,
        args=(proxy['server'], proxy['port'], proxy['username'], proxy['password']),
        daemon=True,
    )
    proxy_thread.start()
    time.sleep(3)   # Give bridge time to bind

    # Launch Chrome and register it with the kill switch immediately
    print_status("7/8", "Launching Chrome (Normal Mode)...", Fore.CYAN)
    chrome_proc, profile_dir = launch_chrome(config)
    kill_switch.register_chrome(chrome_proc)   # ← kill switch now owns Chrome

    print_status("8/8", "Opening https://browserleaks.com/ip", Fore.GREEN)
    log("Session started. Monitoring active. Kill switch enabled.")

    try:
        monitor_proxy_and_chrome(chrome_proc, proxy)
    except SystemExit:
        pass
    except Exception as e:
        report_error(e, source_module="main", chrome_proc=chrome_proc,
                     extra_context="Unexpected error in the main session loop.")
    finally:
        print(Fore.YELLOW + "\nSession ended. Cleaning up...")
        cleanup(profile_dir)

if __name__ == "__main__":
    main()
