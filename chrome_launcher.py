import subprocess
import os
import tempfile
from logger import log
from error_handler import report_error

CHROME_FLAGS = [
    "--disable-quic",
    "--disable-background-networking",
    "--disable-sync",
    "--disable-translate",
    "--disable-features=IsolateOrigins,site-per-process,PreloadMedia,MediaPreload,HistoryRequireGuestSession",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-plugins",
    "--disable-extensions",
    "--disable-default-apps",
    "--disable-component-update",
    "--disable-crash-reporter",
    "--disable-metrics",
    "--log-level=3",
    "--disable-webrtc",
    "--webrtc-ip-handling-policy=disable_non_proxied_udp",
    "--force-webrtc-ip-handling-policy",
    "--disable-gpu",
    "--ignore-certificate-errors",
    "--disable-history",
    "--disable-bookmarks",
    "--disable-session-crashed-bubble",
    "--disable-infobars",
    "--disable-prompt-on-repost",
]

def launch_chrome(config):
    # Temporary isolated profile - deleted after session
    profile_dir = tempfile.mkdtemp(dir=os.getcwd(), prefix="Chrome_Temp_")
    
    cmd = [
        config.get('chrome_path', r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        "--proxy-server=http://127.0.0.1:8080",
        f"--user-data-dir={profile_dir}",
        "--host-resolver-rules=MAP * ~NOTFOUND , EXCLUDE 127.0.0.1",
        "--proxy-bypass-list=<-loopback>;localhost;127.0.0.1",
        "--disable-ipv6",
        config.get('test_url', "https://browserleaks.com/ip")
    ]
    
    cmd.extend(CHROME_FLAGS)
    
    log(f"Launching hardened Chrome with TEMPORARY profile (No history, No bookmarks)")
    log(f"Temp profile: {profile_dir}")

    try:
        proc = subprocess.Popen(cmd)
        return proc, profile_dir
    except Exception as e:
        report_error(e, source_module="chrome_launcher",
                     extra_context=(
                         "Chrome could not be launched. "
                         "Make sure Google Chrome is installed and the chrome_path in config.json is correct."
                     ))
        raise