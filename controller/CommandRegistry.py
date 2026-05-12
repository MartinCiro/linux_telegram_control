# controller/commands/CommandRegistry.py
from typing import Dict, Optional
from re import findall
from controller.Config import Command, Config

class CommandRegistry:
    """
    Registro central de comandos disponibles.
    Los comandos son inyectados desde Config (que ya los carga de JSON o defaults).
    """
    
    def __init__(self, config: Config):  # ← Recibir instancia como parámetro
        """
        Args:
            config: Instancia de Config (ya tiene config.commands cargado)
        """
        self.config = config  # ← Asignar la instancia recibida
        # Los comandos vienen directamente de config.commands
        self.commands: Dict[str, Command] = self.config.commands
    
    def get_command_by_text(self, text: str) -> Optional[Command]:
        """
        Encuentra qué comando coincide con el texto.
        
        Args:
            text: Texto a analizar
            
        Returns:
            Command si hay coincidencia, None si no
        """
        if not text:
            return None
        
        text_lower = text.lower()
        
        for cmd in self.commands.values():
            for trigger in cmd.trigger_words:
                if trigger in text_lower:
                    return cmd
        
        return None
    
    def get_command_by_action(self, action: str) -> Optional[Command]:
        """Obtiene un comando por su acción"""
        for cmd in self.commands.values():
            if cmd.action == action:
                return cmd
        return None
    
    def extract_parameters(self, text: str, command: Command) -> Optional[Dict]:
        """
        Extrae parámetros del texto según la definición del comando.
        
        Ejemplo: "volumen 75" → {"value": 75}
        """
        if not command.parameters:
            return None
        
        params = {}
        
        if command.parameters.get("type") == "integer":
            # Buscar números en el texto
            numbers = findall(r'\d+', text)
            if numbers:
                params["value"] = int(numbers[0])
                
                # Validar rango
                if "min" in command.parameters:
                    params["value"] = max(params["value"], command.parameters["min"])
                if "max" in command.parameters:
                    params["value"] = min(params["value"], command.parameters["max"])
        
        return params if params else None
    
    def get_all_commands(self) -> Dict[str, Command]:
        """Retorna todos los comandos registrados"""
        return self.commands.copy()
    
    def get_help_text(self) -> str:
        """Genera texto de ayuda con todos los comandos"""
        help_lines = ["🎙️ **Comandos disponibles:**\n"]
        
        for cmd in self.commands.values():
            triggers = ", ".join(cmd.trigger_words[:3])
            help_lines.append(f"🗣️ *{triggers}* → `{cmd.action}`")
            if cmd.description:
                help_lines.append(f"   _{cmd.description}_")
            help_lines.append("")  # Línea en blanco entre comandos
        
        return "\n".join(help_lines)
    
    def reload_commands(self):
        """Recarga los comandos desde Config (útil si cambió el JSON en tiempo real)"""
        self.commands = self.config.commands
        if self.config.log:
            self.config.log.comentario("INFO", "🔄 Comandos recargados desde configuración")

    def command_exists(self, command_name: str) -> bool:
        """Verifica si un comando existe por su nombre"""
        return command_name in self.commands

    def get_missing_command_message(self, text: str) -> str:
        """Genera mensaje cuando no se reconoce el comando"""
        return f"❌ El comando '{text}' no está configurado. Comandos disponibles: {', '.join(self.commands.keys())}"