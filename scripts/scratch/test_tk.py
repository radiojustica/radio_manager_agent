import tkinter as tk
import sys
print("Starting Tk...")
try:
    root = tk.Tk()
    print("Tk initialized!")
    root.withdraw()
    print("Mainloop...")
    root.after(1000, lambda: sys.exit(0))
    root.mainloop()
except Exception as e:
    print(f"FAILED: {e}")
    sys.exit(1)


