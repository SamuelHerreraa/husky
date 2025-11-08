# frontend/main.py
import sys, os

# añade la carpeta donde está el exe / script a sys.path
base_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(base_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import ttkbootstrap as tb
from frontend.login_gui import LoginWindow


def main():
    root = tb.Window(themename="darkly")
    LoginWindow(root)
    root.mainloop()

if __name__ == "__main__":
    main()
