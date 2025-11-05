import tkinter as tk
from tkinter import ttk

def main():
    # Crear la ventana principal
    root = tk.Tk()
    root.title("Husky")
    root.geometry("400x300")  # Tamaño de la ventana: 400x300 píxeles
    
    # Crear un label con el texto "husky"
    label = tk.Label(root, text="husky", font=("Arial", 24, "bold"))
    
    # Centrar el label en la ventana
    label.pack(expand=True)  # Esto lo expande para centrar vertical y horizontalmente
    
    # Iniciar el bucle principal de la GUI
    root.mainloop()

if __name__ == "__main__":
    main()