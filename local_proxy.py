import socket
import threading
import time
import socks
from logger import log
from kill_switch import kill_switch
from error_handler import report_error

PROXY_CONNECT_TIMEOUT = 30   # seconds to wait for SOCKS5 handshake
PROXY_CONNECT_RETRIES = 3    # retry attempts before giving up
PROXY_RETRY_DELAY     = 2    # seconds between retries


def _make_socks_socket(proxy_host, proxy_port, username, password,
                       target_host, target_port):
    """
    Create a SOCKS5H socket connected to target via proxy.

    socks.SOCKS5 + rdns=True  →  equivalent to socks5h://
    DNS is resolved by the proxy server, not locally.
    Retries up to PROXY_CONNECT_RETRIES times on timeout (WinError 10060).
    """
    last_err = None
    for attempt in range(1, PROXY_CONNECT_RETRIES + 1):
        sock = socks.socksocket()
        sock.settimeout(PROXY_CONNECT_TIMEOUT)
        # rdns=True makes PySocks send the hostname to the proxy for resolution
        # instead of resolving it locally — this is the socks5h behaviour.
        sock.set_proxy(
            socks.SOCKS5,
            proxy_host,
            int(proxy_port),
            rdns=True,               # ← KEY: proxy-side DNS (socks5h)
            username=username,
            password=password,
        )
        try:
            sock.connect((target_host, target_port))
            sock.settimeout(None)    # back to blocking after connect
            return sock
        except Exception as e:
            try:
                sock.close()
            except Exception:
                pass
            last_err = e
            err_str  = str(e)
            # Only retry on timeout-class errors
            if "10060" in err_str or "timed out" in err_str.lower():
                if attempt < PROXY_CONNECT_RETRIES:
                    log(f"Bridge SOCKS5H connect timeout (attempt {attempt}/{PROXY_CONNECT_RETRIES}), "
                        f"retrying in {PROXY_RETRY_DELAY}s…", "WARNING")
                    time.sleep(PROXY_RETRY_DELAY)
                continue
            raise   # non-timeout errors fail immediately
    raise last_err


def start_local_proxy(proxy_host, proxy_port, username, password, local_port=8080):

    def handle_client(client_sock):
        remote_sock = None
        kill_switch.register_socket(client_sock)

        try:
            data = client_sock.recv(8192)
            if not data:
                return

            if data.startswith(b'CONNECT'):
                # HTTPS CONNECT tunnel
                try:
                    first_line  = data.split(b'\r\n')[0]
                    host_port   = first_line.split(b' ')[1].decode('utf-8', errors='ignore')
                    target_host, target_port = host_port.rsplit(':', 1)
                    target_port = int(target_port)
                except Exception:
                    return

                remote_sock = _make_socks_socket(
                    proxy_host, proxy_port, username, password,
                    target_host, target_port,
                )
                kill_switch.register_socket(remote_sock)
                client_sock.sendall(b'HTTP/1.1 200 Connection Established\r\n\r\n')

            else:
                # Plain HTTP fallback (e.g. health-check pings to IP endpoints)
                # Parse the Host header to route correctly instead of hard-coding ipify.
                target_host = "api.ipify.org"
                target_port = 80
                for line in data.split(b'\r\n')[1:]:
                    if line.lower().startswith(b'host:'):
                        host_val = line.split(b':', 1)[1].strip().decode('utf-8', errors='ignore')
                        if ':' in host_val:
                            target_host, p = host_val.rsplit(':', 1)
                            target_port = int(p)
                        else:
                            target_host = host_val
                        break

                remote_sock = _make_socks_socket(
                    proxy_host, proxy_port, username, password,
                    target_host, target_port,
                )
                kill_switch.register_socket(remote_sock)

            # ── Bidirectional forwarding ──────────────────────────────────
            def forward(src, dst):
                try:
                    while True:
                        buf = src.recv(8192)
                        if not buf:
                            break
                        dst.sendall(buf)
                except Exception:
                    pass

            t1 = threading.Thread(target=forward, args=(client_sock, remote_sock), daemon=True)
            t2 = threading.Thread(target=forward, args=(remote_sock, client_sock), daemon=True)
            t1.start()
            t2.start()
            t1.join()
            t2.join()

        except Exception as e:
            err = str(e)
            # Suppress normal TCP teardown noise — these are not bugs
            if any(x in err for x in [
                "IPv6", "address family",
                "Connection closed unexpectedly",
                "Connection reset by peer",
                "Broken pipe",
                "timed out",
                "104", "32", "10054", "10053", "10060",
            ]):
                pass
            else:
                log(f"Bridge error: {err[:120]}", "WARNING")
                report_error(
                    e,
                    source_module="local_proxy",
                    extra_context="Error inside the local proxy bridge while forwarding traffic.",
                )
        finally:
            for s in [client_sock, remote_sock]:
                if s:
                    kill_switch.unregister_socket(s)
                    try:
                        s.close()
                    except Exception:
                        pass

    # ── Server loop ───────────────────────────────────────────────────────
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('127.0.0.1', local_port))
        server.listen(20)

        kill_switch.register_proxy_server(server)
        log(f"✅ Local SOCKS5H proxy bridge started on http://127.0.0.1:{local_port}")

        while True:
            try:
                client, _ = server.accept()
            except OSError:
                break   # server socket closed by kill switch — clean exit
            threading.Thread(target=handle_client, args=(client,), daemon=True).start()

    except Exception as e:
        log(f"Local proxy failed to start: {e}", "ERROR")
        report_error(
            e,
            source_module="local_proxy",
            extra_context="The local proxy bridge could not start. Port 8080 may already be in use.",
        )
        kill_switch.trigger(f"Local proxy crashed: {e}")
