from typing import Optional, Dict, Any
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
        cmd = self.registry.get_command_by_text(command_text)
        if not cmd:
            return {"success": False, "message": self.registry.get_missing_command_message(command_text)}
        
        # 2️⃣ Extraer parámetros usando Registry
        params = self.registry.extract_parameters(command_text, cmd)
        
        # 3️⃣ Mapear acción -> handler
        handlers = {
            "/saluda": self._cmd_saluda,
            "/help": self._cmd_help,
            "/play": self._cmd_play,
            "/pause": self._cmd_pause,
            "/next": self._cmd_next,
            "/volume": self._cmd_volume,
            "/stop": self._cmd_stop,
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
        query = query or self.config.youtube_query
        
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
            await player.toggle_play_pause()
            return {"message": "⏸️ Pausado / Reanudado"}
        return {"message": "❌ No hay reproducción activa"}
    
    async def _cmd_next(self, params: Optional[Dict]) -> Dict:
        player = await self._ensure_player()
        if player:
            await player.page.keyboard.press('N')
            return {"message": "⏭️ Siguiente video..."}
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
    
    async def _cmd_stop(self, params: Optional[Dict]) -> Dict:
        await self.browser_manager.close()
        self.youtube_player = None
        return {"message": "🛑 Navegador cerrado y recursos liberados"}