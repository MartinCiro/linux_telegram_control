# controller/CommandExecutor.py
from re import findall
from typing import Optional, Dict, Any
from subprocess import run as run_subprocess
from asyncio import sleep as asy_slp, create_task

from controller.YoutubePlayer import YoutubePlayer
from controller.CommandRegistry import CommandRegistry
from controller.Log import Log

class CommandExecutor:
    """
    Orquestador central. 
    Usa CommandRegistry para PARSEAR y ROUTEAR, 
    y servicios internos para EJECUTAR.
    """
    
    def __init__(self, config, browser_manager):
        self.config = config
        self.browser_manager = browser_manager
        self.log = Log()
        
        # 👇 Reutilizamos CommandRegistry para parsing y validación
        self.registry = CommandRegistry(config)
        self.youtube_player: Optional[YoutubePlayer] = None

    async def _ensure_player(self) -> Optional[YoutubePlayer]:
        if self.youtube_player:
            try:
                if self.youtube_player.page.is_closed():
                    self.config.log.comentario("WARNING", "⚠️ Página del player cerrada, reinstanciando...")
                    self.youtube_player = None  # Invalidar caché
                else:
                    return self.youtube_player  # ✅ Vivo, reutilizar
            except Exception as e:
                self.config.log.comentario("WARNING", f"⚠️ Error validando player: {e}")
                self.youtube_player = None
        
        # ✅ 2. Inicializar desde cero
        success, page = await self.browser_manager.initialize(self.config)
        if success and page:
            self.youtube_player = YoutubePlayer(self.config, page)
            return self.youtube_player
        
        return None

    async def toggle_play_pause(self):
        player = await self._ensure_player()
        if player:
            await player.page.keyboard.press(' ')

    async def set_volume(self, level: int):
        player = await self._ensure_player()
        if player:
            current = getattr(player, '_vol', 50)
            diff = level - current
            key = 'ArrowUp' if diff > 0 else 'ArrowDown'
            for _ in range(abs(diff) // 5):
                await player.page.keyboard.press(key)
            player._vol = level

    async def execute(self, command_text: str) -> Dict[str, Any]:
        """
        Punto de entrada único.
        Recibe el string crudo (ej: "/play lofi study")
        y delega al handler correspondiente.
        """
        # 1️⃣ Identificar comando usando Registry
        # 1️⃣ Extraer la acción del comando parseado
        parts = command_text.split(maxsplit=1)
        action = parts[0]  # "/pause", "/play", "/volume"
        param_str = parts[1].strip() if len(parts) > 1 else None  # "lofi", "50", None

        # 2️⃣ Buscar comando por ACTION (no por trigger word)
        cmd = self.registry.get_command_by_action(action)
        if not cmd:
            return {"success": False, "message": f"❌ Acción '{action}' no está configurada"}

        # 3️⃣ Construir parámetros basados en el tipo definido en el comando
        params = None
        if param_str and cmd.parameters:
            param_type = cmd.parameters.get("type")
            
            if param_type == "query":
                # Parámetro de texto libre (ej: "/play lofi" → {"query": "lofi"})
                params = {"query": param_str}
                
            elif param_type == "integer":
                # Parámetro numérico (ej: "/volume 50" → {"value": 50})
                numbers = findall(r'\d+', param_str)
                if numbers:
                    value = int(numbers[0])
                    if "min" in cmd.parameters:
                        value = max(value, cmd.parameters["min"])
                    if "max" in cmd.parameters:
                        value = min(value, cmd.parameters["max"])
                    params = {"value": value}
        
        # 3️⃣ Mapear acción -> handler
        handlers = {
            "/saluda": self._cmd_saluda,
            "/help": self._cmd_help,
            "/play": self._cmd_play,
            "/pause": self._cmd_pause,
            "/resume": self._cmd_resume,
            "/next": self._cmd_next,
            "/prev": self._cmd_prev,
            "/fullscreen": self._cmd_fullscreen,
            "/volume": self._cmd_volume,
            "/stop": self._cmd_stop,
            "/shutdown": self._cmd_shutdown,
        }
        
        handler = handlers.get(cmd.action)
        if not handler:
            return {"success": False, "message": f"❌ Acción '{cmd.action}' sin implementación"}
        
        # 4️⃣ Ejecutar
        try:
            self.log.comentario("INFO", f"⚡ Ejecutando: {cmd.action} | params: {params}")
            result = await handler(params)
            return {"success": True, "message": result.get("message", "✅ OK"), "data": result.get("data")}
        except Exception as e:
            self.log.error(f"💥 Error en {cmd.action}: {e}")
            return {"success": False, "message": f"❌ Error interno: {str(e)}"}

    # ─────────────────────────────────────────────────────
    # Handlers (lógica de negocio pura)
    # ─────────────────────────────────────────────────────

    async def _cmd_saluda(self, params: Optional[Dict]) -> Dict:
        return {"message": "¡Hola! 👋 ¿En qué puedo ayudarte?"}

    async def _cmd_help(self, params: Optional[Dict]) -> Dict:
        return {"message": self.registry.get_help_text()}

    async def _cmd_play(self, params: Optional[Dict]) -> Dict:
        query = params.get("query") if params else None
        
        # ✅ VALIDACIÓN TEMPRANA: si no hay query, NO abrir el navegador
        if not query or not query.strip():
            return {"message": "❌ Debes decir qué quieres reproducir (ej: 'reproduce lofi')"}
        
        player = await self._ensure_player()
        if not player:
            return {"message": "❌ No pude inicializar el navegador"}
        
        results = await player.search(query, limit=1)
        if not results:
            return {"message": f"❌ No encontré resultados para '{query}'"}
        
        success = await player.play_video(results[0]["url"])
        if success:
            title = results[0]["title"]
            return {"message": f"✅ Reproduciendo: {title[:50]}...", "data": results[0]}
        
        return {"message": "❌ No pude reproducir el video"}

    async def _cmd_pause(self, params: Optional[Dict]) -> Dict:
        player = await self._ensure_player()
        if player:
            success = await player.pause_video()
            if success:
                return {"message": "⏸️ Video pausado"}
            return {"message": "❌ No pude pausar el video"}
        return {"message": "❌ No hay reproducción activa"}
    
    async def _cmd_shutdown(self, params: Optional[Dict]) -> Dict:
        """
        Apaga el ordenador de forma segura.
        Primero cierra el navegador, luego programa el apagado.
        """
        try:
            # 1️⃣ Cerrar el navegador si está abierto
            if self.youtube_player:
                self.config.log.comentario("INFO", "🛑 Cerrando navegador antes de apagar...")
                await self.browser_manager.close()
                self.youtube_player = None
            
            # 2️⃣ Programar apagado con delay para dar tiempo a enviar mensaje a Telegram
            async def delayed_shutdown():
                await asy_slp(3)  # 3 segundos para que Telegram envíe el mensaje
                self.config.log.comentario("INFO", "💻 Apagando sistema...")
                try:
                    # Intentar múltiples métodos de apagado (Linux)
                    result = run_subprocess(
                        ["systemctl", "poweroff"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode != 0:
                        # Fallback a shutdown
                        run_subprocess(["shutdown", "-h", "now"], timeout=5)
                except Exception as e:
                    self.config.log.error(f"❌ Error al apagar: {e}")
                    # Último recurso
                    run_subprocess(["poweroff"], timeout=5)
            
            # 3️⃣ Crear tarea en background (no bloquea el retorno del mensaje)
            create_task(delayed_shutdown())
            
            self.config.log.comentario("SUCCESS", "✅ Sistema se apagará en 3 segundos")
            return {"message": "💻 Apagando el sistema en 3 segundos... ¡Hasta luego! 👋"}
            
        except Exception as e:
            self.config.log.error(f"❌ Error en shutdown: {e}")
            return {"message": f"❌ Error al preparar el apagado: {str(e)}"}
    
    async def _cmd_resume(self, params: Optional[Dict]) -> Dict:
        player = await self._ensure_player()
        if player:
            success = await player.resume_video()
            if success:
                return {"message": "▶️ Reproducción reanudada"}
            return {"message": "❌ No pude reanudar el video"}
        return {"message": "❌ No hay reproducción activa"}

    async def _cmd_next(self, params: Optional[Dict]) -> Dict:
        player = await self._ensure_player()
        if player:
            success = await player.next_video()
            if success:
                return {"message": "⏭️ Siguiente video..."}
            return {"message": "❌ No pude ir al siguiente video"}
        return {"message": "❌ No hay reproducción activa"}
    
    async def _cmd_prev(self, params: Optional[Dict]) -> Dict:
        player = await self._ensure_player()
        if player:
            success = await player.prev_video()
            if success:
                return {"message": "⏮️ Video anterior..."}
            return {"message": "❌ No pude ir al video anterior"}
        return {"message": "❌ No hay reproducción activa"}

    async def _cmd_volume(self, params: Optional[Dict]) -> Dict:
        value = params.get("value") if params else None
        
        if value is None:
            return {"message": "🔊 Usa: 'volumen 50', 'sube volumen', etc."}
        
        player = await self._ensure_player()
        if player:
            await player.set_volume(value)
            return {"message": f"🔊 Volumen ajustado a {value}%"}
        
        return {"message": "❌ No hay reproducción activa"}
    
    async def _cmd_fullscreen(self, params: Optional[Dict]) -> Dict:
        player = await self._ensure_player()
        if player:
            success = await player.full_screen_video()
            if success:
                return {"message": "🖥️ Pantalla completa activada"}
            return {"message": "❌ No pude activar pantalla completa"}
        return {"message": "❌ No hay reproducción activa"}

    async def _cmd_stop(self, params: Optional[Dict]) -> Dict:
        await self.browser_manager.close()
        self.youtube_player = None
        return {"message": "🛑 Navegador cerrado y recursos liberados"}