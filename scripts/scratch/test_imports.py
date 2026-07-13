import sys
try:
    import tkinter as tk
    import uvicorn
    from fastapi import FastAPI
    import apscheduler
    import pystray
    from PIL import Image
    import psutil
    print("OK: Imports successful")
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)


