from json import load, dump
from platform import system as platform_system
from os import makedirs, path as os_path, access, X_OK, listdir
from typing import Dict, Any
from dataclasses import is_dataclass, asdict

class FileUtils:

    @staticmethod
    def ensure_dir(path: str):
        """Crea directorio si no existe"""
        makedirs(path, exist_ok=True)

    @staticmethod
    def read_json(path: str):
        """Lee JSON de forma segura"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return load(f)
        except Exception:
            return None

    @staticmethod
    def write_json(path: str, data, indent=4):
        """Escribe JSON con formato"""
        with open(path, "w", encoding="utf-8") as f:
            dump(data, f, ensure_ascii=False, indent=indent)

    @staticmethod
    def exists(path: str) -> bool:
        """Verifica si un path existe"""
        return os_path.exists(path)

    @staticmethod
    def is_executable(path: str) -> bool:
        """Verifica si un archivo es ejecutable (multi-plataforma)"""
        if not os_path.isfile(path):
            return False
        # Windows: confiamos en la extensión .exe
        if platform_system().startswith("win"):
            return path.lower().endswith(('.exe', '.cmd', '.bat'))
        # Unix: verificar permisos de ejecución
        return access(path, X_OK)

    @staticmethod
    def find_chrome_paths() -> list:
        """
        Retorna lista de paths posibles para Chrome/Chromium según SO.
        Prioriza rutas comunes, sin hardcodear en Config.
        """
        paths = []
        
        if platform_system().startswith("win"):
            bases = [
                os_path.expandvars(r"%ProgramFiles%\Google\Chrome\Application"),
                os_path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application"),
                os_path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application"),
            ]
            for base in bases:
                if os_path.exists(base):
                    for sub in listdir(base):
                        candidate = os_path.join(base, sub, "chrome.exe")
                        if FileUtils.is_executable(candidate):
                            paths.append(candidate)
        
        elif platform_system().startswith("darwin"):
            paths.extend([
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Chromium.app/Contents/MacOS/Chromium",
            ])
        
        else:  # Linux
            paths.extend([
                "/usr/bin/google-chrome",
                "/usr/bin/google-chrome-stable",
                "/usr/bin/chromium",
                "/usr/bin/chromium-browser",
                "/snap/bin/chromium",
                "/snap/bin/google-chrome",
                "/usr/bin/brave-browser"
            ])
        
        # Filtrar solo los que existen y son ejecutables
        return [p for p in paths if FileUtils.exists(p) and FileUtils.is_executable(p)]

    # 🔹 Si quieres usar get_routes, necesita contexto. Alternativa simple:
    @staticmethod
    def resolve_path(key: str, base: str = None, config: dict = None) -> str:
        """
        Resuelve rutas relativas/absolutas desde configuración.
        Ejemplo: resolve_path("chrome", base="/usr/bin", config={"chrome": "google-chrome"})
        """
        if config and key in config:
            value = config[key]
            if os_path.isabs(value):
                return value
            return os_path.join(base or ".", value)
        return ""
    
    @staticmethod
    def get_config_value(path: str, key: str, default=None):
        """
        Lee un valor desde un archivo JSON usando notación de puntos para claves anidadas.
        
        Ejemplos:
        - get_config_value("./config.json", "path_browser") → "/usr/bin/brave_browser"
        - get_config_value("./config.json", "youtube.default_query") → "dora la exploradora"
        - get_config_value("./config.json", "youtube.inexistente", "fallback") → "fallback"
        
        Args:
            path: Ruta al archivo JSON
            key: Clave simple o anidada con puntos (ej: "padre.hijo.valor")
            default: Valor a retornar si la clave no existe
            
        Returns:
            El valor encontrado o el default especificado
        """
        data = FileUtils.read_json(path)
        if data is None:
            return default
        
        # 🔹 Soportar claves anidadas con notación de puntos
        keys = key.split(".")
        value = data
        
        try:
            for k in keys:
                if isinstance(value, dict):
                    value = value[k]
                else:
                    return default  
            return value
        except (KeyError, TypeError):
            return default
        
    @staticmethod
    def transform_json_to_commands(commands_data: dict, command_class) -> Dict[str, Any]:
        """
        Transforma un diccionario del JSON en objetos Command.
        
        Args:
            commands_data: Diccionario con datos de comandos del JSON
            command_class: Clase Command a instanciar (para evitar import circular)
        
        Returns:
            Diccionario con nombre_comando: objeto_command
        
        Ejemplo:
            commands = FileUtils.transform_json_to_commands(data, Command)
        """
        commands = {}
        
        if not commands_data or not isinstance(commands_data, dict):
            return commands
        
        for cmd_name, cmd_data in commands_data.items():
            try:
                # Validar datos mínimos requeridos
                if not cmd_data.get("trigger_words"):
                    continue
                
                commands[cmd_name] = command_class(
                    trigger_words=cmd_data.get("trigger_words", []),
                    action=cmd_data.get("action", f"/{cmd_name}"),
                    description=cmd_data.get("description", f"Comando {cmd_name}"),
                    parameters=cmd_data.get("parameters")
                )
            except Exception as e:
                # Logging podría ser opcional aquí
                print(f"Error cargando comando {cmd_name}: {e}")
        
        return commands
    
    @staticmethod
    def transform_commands_to_json(commands: dict) -> dict:
        """
        Transforma objetos Command a diccionario para guardar en JSON.
        
        Args:
            commands: Diccionario de comandos (nombre: objeto Command)
        
        Returns:
            Diccionario listo para serializar a JSON
        """
        export_data = {}
        
        for cmd_name, cmd in commands.items():
            if is_dataclass(cmd):
                # Convertir dataclass a dict
                cmd_dict = asdict(cmd)
            elif isinstance(cmd, dict):
                cmd_dict = cmd
            else:
                # Intentar acceder a atributos
                cmd_dict = {
                    "trigger_words": getattr(cmd, "trigger_words", []),
                    "action": getattr(cmd, "action", ""),
                    "description": getattr(cmd, "description", ""),
                    "parameters": getattr(cmd, "parameters", None)
                }
            
            export_data[cmd_name] = cmd_dict
        
        return export_data
    
    @staticmethod
    def load_commands_from_json(json_path: str, command_class, default_commands: dict = None) -> Dict[str, Any]:
        """
        Carga comandos desde un archivo JSON, con fallback a comandos por defecto.
        
        Args:
            json_path: Ruta al archivo JSON
            command_class: Clase Command a instanciar
            default_commands: Comandos por defecto si no hay archivo o está vacío
        
        Returns:
            Diccionario de comandos cargados
        """
        # Leer el JSON completo
        data = FileUtils.read_json(json_path)
        
        # Extraer comandos usando get_config_value anidado
        commands_data = FileUtils.get_config_value(json_path, "speech.commands")
        
        if commands_data:
            # Transformar usando el método anterior
            return FileUtils.transform_json_to_commands(commands_data, command_class)
        
        # Fallback a comandos por defecto
        return default_commands or {}