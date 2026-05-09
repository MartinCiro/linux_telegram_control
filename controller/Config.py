from typing import Optional

from dotenv import load_dotenv
from os import getenv, path as os_path, remove
from dataclasses import dataclass
from controller.utils.file import FileUtils
from controller.Log import Log

@dataclass
class RenderConfig:
    width: int
    height: int
    output_dir: str


@dataclass
class TemplateConfig:
    font_family: str
    primary_color: str
    background_color: str


class Config:
    """
    Configuración simple y enfocada para generación de imágenes HTML → PNG
    (Single Responsibility)
    """

    def __init__(self):
        load_dotenv()
        self.headless = getenv("HEADLESS", "true")
        self.chrome_path: str = getenv("CHROME_PATH", "")
        self.cookies_base_path: str = getenv("COOKIES_PATH", "./cookies")
        self.config_json: str = getenv("CONFIG_JSON", "./config.json")
        self.log = Log()

    @property
    def youtube_query(self) -> str:

        value = FileUtils.get_config_value(
            self.config_json, 
            "youtube.default_query"
        )
        if value is not None:
            return value
         
        return getenv("YOUTUBE_QUERY", "lofi hip hop radio")
    
    def get_chrome_paths(self) -> list:
        """
        Retorna lista de paths válidos para Chrome/Chromium.
        Prioriza: 1) CHROME_PATH de .env → 2) FileUtils.find_chrome_paths()
        """
        paths = []
        
        # 1️⃣ Si se especificó en .env y es ejecutable, usar ese primero
        if self.chrome_path and FileUtils.is_executable(self.chrome_path):
            paths.append(self.chrome_path)
        
        # 2️⃣ Fallback: buscar en rutas comunes del SO vía FileUtils
        paths.extend(FileUtils.find_chrome_paths())
        
        return paths  # Ya vienen filtrados por exists + is_executable
    
    def get_chrome_path(self) -> Optional[str]:
        """Retorna el primer path válido de Chrome o None"""
        paths = self.get_chrome_paths()
        return paths[0] if paths else None
    
    def get_cookies_path(self) -> str:
        """
        Retorna la ruta del archivo de storage state para Playwright.
        Compatible con context.storage_state(path=...)
        """
        return os_path.join(self.cookies_base_path, "youtube_state.json")
    
    def cookies_exist(self) -> bool:
        """Verifica si ya existe un estado de sesión guardado"""
        return FileUtils.exists(self.get_cookies_path())
    
    def clear_cookies(self):
        """Elimina el archivo de cookies para forzar sesión limpia"""
        cookies_path = self.get_cookies_path()
        if os_path.exists(cookies_path):
            try:
                remove(cookies_path)
            except Exception:
                pass
