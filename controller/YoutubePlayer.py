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

    def __init__(self, config, page):
        """
        Args:
            config: Instancia de Config
            page: Playwright page (inyectada desde main)
            logger: Logger opcional (si config.log no existe)
        """
        self.config = config
        self.page = page

    async def _accept_cookies_if_needed(self):
        """Cierra banner de cookies si aparece (no fatal si falla)"""
        try:
            locator = self.page.locator(f'xpath={YoutubePlayer.XPATH_COOKIE_ACCEPT}')
            if await locator.count() > 0:
                await locator.click(timeout=3000, delay=50)
                await asy_slp(uniform(0.3, 0.7))
                self.config.log.comentario("DEBUG", "🍪 Banner de cookies cerrado")
        except Exception:
            pass  # No es crítico
        
    async def search(self, query: str = None, limit: int = 5) -> list:
        """
        Busca en YouTube y retorna lista con título, URL y thumbnail para usar en Telegram.
        Args:
            query: Término de búsqueda
            limit: Número máximo de resultados (default 5)
        Returns:
            Lista de diccionarios con: index, title, url, thumbnail, channel
        """
        try:
            yt_query = query or getattr(self.config, 'youtube_query', 'lofi hip hop radio')
            self.config.log.comentario("INFO", f"🔍 Buscando (con thumbnails): {yt_query}")
            
            # Navegar y buscar
            await self.page.goto("https://www.youtube.com", wait_until="domcontentloaded", timeout=30000)
            await asy_slp(uniform(0.5, 1.2))
            await self._accept_cookies_if_needed()
            
            search_box = self.page.locator(f'xpath={YoutubePlayer.XPATH_SEARCH_BOX}')
            await search_box.fill(yt_query, timeout=5000)
            await asy_slp(uniform(0.2, 0.4))
            await search_box.press("Enter", delay=50)
            
            # Esperar resultados
            await self.page.wait_for_selector('ytd-video-renderer', timeout=10000)
            await asy_slp(uniform(0.8, 1.5))
            
            results = []
            for i in range(limit):
                try:
                    # Usar xpath más específico para evitar duplicados
                    video_element = self.page.locator(f'xpath=(//ytd-video-renderer)[{i+1}]')
                    if await video_element.count() == 0:
                        continue
                    
                    # ✅ Título (específico, solo el enlace principal)
                    title_element = video_element.locator('xpath=.//a[@id="video-title"]')
                    title = await title_element.get_attribute('title') or await title_element.text_content()
                    href = await title_element.get_attribute('href')
                    
                    # ✅ Thumbnail - usando el selector más específico
                    thumbnail_selectors = [
                        'xpath=.//img[@id="img" and @src]',
                        'xpath=.//img[contains(@src, "ytimg.com")]',
                        'xpath=.//ytd-thumbnail//img'
                    ]
                    
                    thumbnail = None
                    for selector in thumbnail_selectors:
                        img_element = video_element.locator(selector)
                        if await img_element.count() > 0:
                            thumbnail = await img_element.first.get_attribute('src')
                            if thumbnail:
                                break
                    
                    # ✅ Canal - USAR .first PARA EVITAR STRICT MODE
                    # Opción 1: El texto del canal (segundo enlace)
                    channel_element = video_element.locator('xpath=.//div[@id="channel-info"]//a').last
                    if await channel_element.count() > 0:
                        channel = await channel_element.text_content()
                    else:
                        # Fallback: buscar el enlace que NO tenga "channel-thumbnail"
                        channel_element = video_element.locator('xpath=.//a[contains(@href, "/@") or contains(@href, "/channel/")][not(@id="channel-thumbnail")]').first
                        channel = await channel_element.text_content() if await channel_element.count() > 0 else None
                    
                    # ✅ Extraer video ID para generar thumbnail manual si es necesario
                    video_id = None
                    if href and 'v=' in href:
                        video_id = href.split('v=')[1].split('&')[0]
                    
                    # Si no se encontró thumbnail, generar manualmente
                    if not thumbnail and video_id:
                        thumbnail = f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
                    
                    if title and href:
                        results.append({
                            "index": i + 1,
                            "title": title.strip(),
                            "url": f"https://youtube.com{href}" if href.startswith('/watch') else href,
                            "thumbnail": thumbnail,
                            "channel": channel.strip() if channel else None,
                            "video_id": video_id
                        })
                        self.config.log.comentario("DEBUG", f"✅ Video {i+1}: {title[:50]}...")
                        
                except Exception as e:
                    self.config.log.comentario("DEBUG", f"No se pudo extraer video {i+1}: {str(e)[:100]}")
                    continue
            
            self.config.log.comentario("SUCCESS", f"✅ {len(results)} resultados encontrados con thumbnails")
            return results
            
        except Exception as e:
            self.config.log.error(f"❌ Error en búsqueda con thumbnails: {e}", "Search with thumbnails")
            return []