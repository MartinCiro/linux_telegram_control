from tkinter import Tk
from typing import Tuple

class ScreenUtils:
    """Versión simple usando tkinter (incluido en Python)"""
    
    @staticmethod
    def get_screen_size() -> Tuple[int, int]:
        """Obtiene el tamaño de la pantalla usando tkinter"""
        try:
            root = Tk()
            root.withdraw()  # Ocultar la ventana
            width = root.winfo_screenwidth()
            height = root.winfo_screenheight()
            root.destroy()
            return width, height
        except Exception as e:
            print(f"Error obteniendo tamaño de pantalla: {e}")
            return 1920, 1080 
    
    @staticmethod
    def get_screen_width() -> int:
        return ScreenUtils.get_screen_size()[0]
    
    @staticmethod
    def get_screen_height() -> int:
        return ScreenUtils.get_screen_size()[1]
