# controller/YoutubePlayer.py
from asyncio import sleep as asy_slp
import logging
from random import uniform
from logging import getLogger

class YoutubePlayer:
    """
    YouTube Player con Playwright - Compatible con Config minimalista.
    ✅ Page inyectada, ✅ Logger flexible, ✅ Sin dependencias de config.log
    """
    
    # 🎯 XPaths (ajustables si YouTube cambia su DOM)
    XPATH_SEARCH_BOX = "//input[@name='search_query']"
    XPATH_FIRST_VIDEO = "//ytd-video-renderer//a[@id='video-title'][1]"
    XPATH_COOKIE_ACCEPT = "//button[contains(., 'Aceptar') or contains(., 'Accept') or contains(., 'Aceptar todas')]"

    def __init__(self, config, page, logger=None):
        """
        Args:
            config: Instancia de Config
            page: Playwright page (inyectada desde main)
            logger: Logger opcional (si config.log no existe)
        """
        self.config = config
        self.page = page
        # 🔹 Logger flexible: usa el pasado, o config.log, o logging estándar
        self.log = logger or getattr(config, 'log', None) or getLogger(__name__)

    def _log(self, level: str, message: str, context: str = None):
        """
        Wrapper para logging compatible con múltiples estilos.
        Soporta: config.log.comentario(), config.log.proceso(), o logging estándar.
        """
        msg = f"[YOUTUBE] {message}" if not context else f"[YOUTUBE:{context}] {message}"
        
        # 🔹 Intentar usar tu Log personalizado si existe
        if hasattr(self.log, 'comentario'):
            # Tu estilo: log.comentario("LEVEL", "msg")
            if level in ("INFO", "DEBUG", "SUCCESS"):
                self.log.comentario(level, msg)
            elif level == "ERROR":
                self.log.error(msg, context or "YOUTUBE")
            elif level == "PROCESO":
                self.log.proceso(msg)
            elif level == "INICIO":
                self.log.inicio_proceso(msg)
            elif level == "FIN":
                self.log.fin_proceso(msg)
        else:
            # 🔹 Fallback a logging estándar de Python
            log_method = getattr(self.log, level.lower(), logging.info)
            log_method(msg)

    async def _accept_cookies_if_needed(self):
        """Cierra banner de cookies si aparece (no fatal si falla)"""
        try:
            locator = self.page.locator(f'xpath={YoutubePlayer.XPATH_COOKIE_ACCEPT}')
            if await locator.count() > 0:
                await locator.click(timeout=3000, delay=50)
                await asy_slp(uniform(0.3, 0.7))
                self._log("DEBUG", "🍪 Banner de cookies cerrado")
        except Exception:
            pass  # No es crítico

    async def search_and_play(self, query: str = None) -> bool:
        """
        Busca un término en YouTube y reproduce el primer resultado.
        Args:
            query: Término de búsqueda (ej: "lofi hip hop radio")
                   Si es None, usa config.youtube_query
        Returns:
            bool: True si éxito, False si error
        """
        try:
            # 🔹 Leer query: parámetro > config property > default
            yt_query = query or getattr(self.config, 'youtube_query')
            self._log("INICIO", f"YOUTUBE: '{yt_query}'")
            
            # 1. Navegar a YouTube
            await self.page.goto(
                "https://www.youtube.com",
                wait_until="domcontentloaded",
                timeout=30000  # ✅ Hardcodeado seguro, o usa getattr(self.config, 'timeout', 30) * 1000
            )
            await self.page.wait_for_load_state("networkidle")
            await asy_slp(uniform(0.5, 1.2))
            
            # 2. Aceptar cookies si es necesario
            await self._accept_cookies_if_needed()
            
            # 3. Escribir en la barra de búsqueda
            self._log("PROCESO", f"🔍 Buscando: {yt_query}")
            search_box = self.page.locator(f'xpath={YoutubePlayer.XPATH_SEARCH_BOX}')
            await search_box.fill(yt_query, timeout=5000)
            await asy_slp(uniform(0.2, 0.4))
            await search_box.press("Enter", delay=50)
            await self.page.wait_for_load_state("networkidle")
            await asy_slp(uniform(0.8, 1.5))
            
            # 4. Click en primer video
            self._log("PROCESO", "▶️ Seleccionando primer resultado")
            first_video = self.page.locator(f'xpath={YoutubePlayer.XPATH_FIRST_VIDEO}')
            
            # Esperar que sea visible y clickeable
            await first_video.wait_for(state="visible", timeout=10000)
            await first_video.click(delay=50)
            
            await self.page.wait_for_load_state("domcontentloaded")
            await asy_slp(uniform(1.0, 2.0))
            
            self._log("SUCCESS", "✅ Video reproduciéndose")
            self._log("FIN", f"YOUTUBE: '{yt_query}'")
            return True
            
        except Exception as e:
            self._log("ERROR", f"❌ Error en YouTube: {e}", "PLAY")
            return False
        
    async def search(self, query: str = None) -> list:
        """
        Busca en YouTube y retorna lista de títulos de los primeros resultados.
        ✅ Sin networkidle, ✅ Espera a elementos reales, ✅ Compatible con hover/mouse
        """
        try:
            yt_query = query or getattr(self.config, 'youtube_query', 'lofi hip hop radio')
            self._log("INFO", f"🔍 Buscando: {yt_query}")
            
            # 1️⃣ Navegar a YouTube (solo domcontentloaded)
            await self.page.goto("https://www.youtube.com", wait_until="domcontentloaded", timeout=30000)
            
            # ❌ ELIMINADO: await self.page.wait_for_load_state("networkidle")
            await asy_slp(uniform(0.5, 1.2))
            await self._accept_cookies_if_needed()
            
            # 2️⃣ Escribir búsqueda
            search_box = self.page.locator(f'xpath={YoutubePlayer.XPATH_SEARCH_BOX}')
            await search_box.fill(yt_query, timeout=5000)
            await asy_slp(uniform(0.2, 0.4))
            await search_box.press("Enter", delay=50)
            
            # ❌ ELIMINADO: await self.page.wait_for_load_state("networkidle")
            # ✅ Esperar a que los resultados se rendericen (elemento real)
            await self.page.wait_for_selector('ytd-video-renderer', timeout=10000)
            await asy_slp(uniform(0.8, 1.5))  # Tiempo para que YouTube cargue thumbnails/títulos
            
            # 3️⃣ Extraer primeros 5 resultados
            results = []
            for i in range(5):  # Limitar a 5
                try:
                    title_locator = self.page.locator(f'xpath=(//ytd-video-renderer//a[@id="video-title"])[{i+1}]')
                    
                    # Verificar que el elemento existe antes de extraer
                    if await title_locator.count() == 0:
                        continue
                        
                    title = await title_locator.text_content()
                    href = await title_locator.get_attribute('href')
                    
                    if title and href:
                        results.append({
                            "index": i + 1,
                            "title": title.strip(),
                            "url": f"https://youtube.com{href}" if href.startswith('/watch') else href
                        })
                except Exception:
                    continue  # Saltar si un resultado falla, continuar con los demás
            
            self._log("SUCCESS", f"✅ {len(results)} resultados encontrados")
            return results
            
        except Exception as e:
            self._log("ERROR", f"❌ Error buscando: {e}", "SEARCH")
            return []