@echo off
powershell -Command "Start-Process python -ArgumentList 'deploy.py --user %USERNAME%' -Verb RunAs -Wait"
