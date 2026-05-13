from typing import Dict, Optional, List

from dotenv import load_dotenv
from os import getenv, path as os_path, remove
from dataclasses import dataclass
from controller.utils.file import FileUtils
from controller.Log import Log

@dataclass
class Command:
    """Define un comando y su acción"""
    trigger_words: List[str]
    action: str
    description: str
    parameters: Optional[Dict] = None 

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
        self.telegram_token: str = getenv("TELEGRAM_TOKEN")
        self.telegram_chat: str = getenv("TELEGRAM_CHAT")
        self.log = Log()

        self._commands_cache: Optional[Dict[str, Command]] = None
    
    @property
    def youtube_query(self) -> str:

        value = FileUtils.get_config_value(
            self.config_json, 
            "youtube.default_query"
        )
        if value is not None:
            return value
         
        return getenv("YOUTUBE_QUERY", "lofi hip hop radio")
    
    @property
    def commands(self) -> Dict[str, Command]:
        """
        Carga los comandos desde config.json o usa los defaults.
        La propiedad se cachea para evitar múltiples lecturas.
        """
        if self._commands_cache is not None:
            return self._commands_cache
        
        # Obtener comandos por defecto
        default_commands = self._get_default_commands()
        
        # Intentar cargar desde config.json usando FileUtils
        self._commands_cache = FileUtils.load_commands_from_json(
            json_path=self.config_json,
            command_class=Command,
            default_commands=default_commands
        )
        
        if self._commands_cache:
            self.log.comentario("INFO", f"✅ Cargados {len(self._commands_cache)} comandos")
        else:
            self._commands_cache = default_commands
            self.log.comentario("INFO", "📝 Usando comandos por defecto")
        
        return self._commands_cache

    @property
    def speech_arg(self) -> str:

        value = FileUtils.get_config_value(
            self.config_json, 
            "speech.commands"
        )
        if value is not None:
            return value
         
        return self._get_default_commands()
    
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

    def _get_default_commands(self) -> Dict[str, Command]:
        """Comandos por defecto del sistema (fallback)"""
        return {
            "saluda": Command(
                trigger_words=["saluda", "saludar", "hola", "dime hola"],
                action="/saluda",
                description="Saluda al bot"
            ),
            "reproduce": Command(
                trigger_words=["reproduce", "pon", "toca", "play", "reproducir", "pon música"],
                action="/play",
                description="Reproduce música (ej: 'reproduce lofi')"
            )
        }
    
    def _get_default_xpath(self) -> Dict[str, Command]:
        """Xpath por defecto del sistema (fallback)"""
        return {
            "icon_volumen": "//button[@class='ytp-volume-icon ytp-button' and (starts-with(@data-tooltip-title, 'Unmute') or @data-tooltip-title='Unmute (m)')]",
            "input_search": "//input[@name='search_query']",
            "first_video": "//ytd-video-renderer",
            "btn_acp_cookies": "//button[contains(., 'Aceptar') or contains(., 'Accept') or contains(., 'Aceptar todas')]"
        }
    
    @property
    def youtube_dict(self) -> str:
        value = FileUtils.get_config_value(
            self.config_json, 
            "youtube.xpath"
        )
        return self._get_default_xpath() if value is None or not isinstance(value, dict) or len(value) == 0 else value