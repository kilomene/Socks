import json
import os
import colorama
from colorama import Fore, Style

colorama.init(autoreset=True)

def load_config():
    if not os.path.exists('config.json'):
        return {
            "proxy": {"server": "", "port": 1080, "username": "", "password": ""},
            "chrome_path": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            "test_url": "https://browserleaks.com/ip"
        }
    with open('config.json', 'r') as f:
        return json.load(f)

def save_config(config):
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=4)
    print(Fore.YELLOW + "[WARNING] Proxy password saved in plain text in config.json")

def print_status(step, status, color=Fore.WHITE):
    print(f"{Fore.CYAN}[{step}]{Style.RESET_ALL} {color}{status}{Style.RESET_ALL}")