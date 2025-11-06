import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import ttkbootstrap as tb
from frontend.login_gui import LoginWindow

def main():
    root = tb.Window(themename="darkly")
    LoginWindow(root)
    root.mainloop()

if __name__ == "__main__":
    main()
