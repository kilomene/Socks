@echo off
title SOCKS5 Chrome Protector
echo [*] Using Python 3.10...
C:\Users\User\AppData\Local\Programs\Python\Python310\python.exe -m pip install -r requirements.txt --quiet
echo [*] Launching...
C:\Users\User\AppData\Local\Programs\Python\Python310\python.exe main.py
pause
