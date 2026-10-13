"""
kill_switch.py — Central kill switch for SOCKS5 Chrome Protector.

When triggered, this module:
  1. Immediately kills the Chrome process
  2. Stops the local proxy bridge (stops accepting new connections)
  3. Closes every open forwarding socket so no buffered data can leak
  4. Logs the reason and exits the process

Usage:
    from kill_switch import KillSwitch
    ks = KillSwitch()
    ks.register_chrome(proc)
    ks.register_socket(sock)     # call for every socket opened in local_proxy
    ks.trigger("reason string")  # hard kill — blocks until clean
"""

import os
import sys
import threading
import socket
from logger import log
import colorama
from colorama import Fore

colorama.init()

class KillSwitch:
    def __init__(self):
        self._lock       = threading.Lock()
        self._triggered  = False
        self._chrome     = None        # subprocess.Popen
        self._proxy_srv  = None        # server socket in local_proxy
        self._sockets    = []          # all open forwarding sockets

    # ------------------------------------------------------------------ #
    #  Registration helpers (called by other modules)                      #
    # ------------------------------------------------------------------ #

    def register_chrome(self, proc):
        with self._lock:
            self._chrome = proc

    def register_proxy_server(self, srv_socket):
        with self._lock:
            self._proxy_srv = srv_socket

    def register_socket(self, sock):
        """Track every client/remote socket opened by the bridge."""
        with self._lock:
            self._sockets.append(sock)

    def unregister_socket(self, sock):
        """Remove a socket that closed normally — keeps the list lean."""
        with self._lock:
            try:
                self._sockets.remove(sock)
            except ValueError:
                pass

    # ------------------------------------------------------------------ #
    #  Trigger                                                             #
    # ------------------------------------------------------------------ #

    def trigger(self, reason: str = "unknown"):
        with self._lock:
            if self._triggered:
                return          # already firing — don't double-kill
            self._triggered = True

        print(f"\n{Fore.RED}[KILL SWITCH] TRIGGERED — {reason}{Fore.RESET}")
        log(f"Kill switch triggered: {reason}", "ERROR")

        # 1. Stop the proxy server from accepting new connections
        if self._proxy_srv:
            try:
                self._proxy_srv.close()
            except Exception:
                pass

        # 2. Slam every open forwarding socket shut
        with self._lock:
            sockets_snapshot = list(self._sockets)

        for s in sockets_snapshot:
            try:
                s.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                s.close()
            except Exception:
                pass

        # 3. Kill Chrome so it cannot make any direct connections
        if self._chrome:
            try:
                self._chrome.kill()
                self._chrome.wait(timeout=5)
                log("Chrome process killed by kill switch.")
            except Exception as e:
                log(f"Could not kill Chrome: {e}", "WARNING")

        print(f"{Fore.RED}[KILL SWITCH] All connections closed. Exiting.{Fore.RESET}")
        log("Session terminated by kill switch. All sockets closed.")
        os._exit(1)   # hard exit — no further code runs, no buffered data flushes


# Module-level singleton — import this everywhere
kill_switch = KillSwitch()
