import logging
import os
from datetime import datetime
import colorama
from colorama import Fore

colorama.init(autoreset=True)

os.makedirs('logs', exist_ok=True)

logging.basicConfig(
    filename=f'logs/protector_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)

def log(message, level="INFO"):
    if level == "ERROR":
        logging.error(message)
        print(Fore.RED + f"[ERROR] {message}")
    elif level == "WARNING":
        logging.warning(message)
        print(Fore.YELLOW + f"[WARN] {message}")
    else:
        logging.info(message)
        print(Fore.GREEN + f"[INFO] {message}")