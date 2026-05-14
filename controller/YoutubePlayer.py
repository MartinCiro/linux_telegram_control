# controller/YoutubePlayer.py
from asyncio import sleep as asy_slp
from random import uniform

class YoutubePlayer:
    """
    YouTube Player con Playwright - Compatible con Config minimalista.
    ✅ Page inyectada, ✅ Logger flexible, ✅ Sin dependencias de config.log
    """

    def __init__(self, config, page):
        """
        Args:
            config: Instancia de Config
            page: Playwright page (inyectada desde main)
            logger: Logger opcional (si config.log no existe)
        """
        self.config = config
        self.page = page
        self.search_box = self.config.youtube_dict['input_search']
        self.xpath_first_vd = self.config.youtube_dict['first_video']
        self.xpath_cookie_acpt = self.config.youtube_dict['btn_acp_cookies']

    async def _accept_cookies_if_needed(self):
        """Cierra banner de cookies si aparece (no fatal si falla)"""
        try:
            locator = self.page.locator(f'xpath={self.xpath_cookie_acpt}')
            if await locator.count() > 0:
                await locator.click(timeout=3000, delay=50)
                await asy_slp(uniform(0.3, 0.7))
                self.config.log.comentario("DEBUG", "🍪 Banner de cookies cerrado")
        except Exception:
            pass
        
    async def search(self, query: str = None, limit: int = 5, max_retries: int = 3) -> list:
        """
        Busca en YouTube y retorna lista con título, URL y thumbnail para usar en Telegram.
        Con sistema de reintentos automáticos.
        
        Args:
            query: Término de búsqueda
            limit: Número máximo de resultados (default 5)
            max_retries: Número máximo de intentos (default 3)
        Returns:
            Lista de diccionarios con: index, title, url, thumbnail, channel
        """
        last_error = None
        
        for attempt in range(1, max_retries + 1):
            try:
                if attempt > 1:
                    self.config.log.comentario("INFO", f"🔄 Reintento {attempt}/{max_retries} para búsqueda: {query}")
                    # Espera exponencial: 1s, 2s, 4s
                    await asy_slp(2 ** (attempt - 1))
                
                yt_query = query or getattr(self.config, 'youtube_query', 'lofi hip hop radio')
                self.config.log.comentario("INFO", f"🔍 Buscando (intento {attempt}): {yt_query}")
                
                # Navegar y buscar
                await self.page.goto("https://www.youtube.com", wait_until="domcontentloaded", timeout=30000)
                await asy_slp(uniform(0.5, 1.2))
                await self._accept_cookies_if_needed()
                
                search_box = self.page.locator(f'xpath={self.search_box}')
                await search_box.fill(yt_query, timeout=5000)
                await asy_slp(uniform(0.2, 0.4))
                await search_box.press("Enter", delay=50)
                
                # Esperar resultados
                await self.page.wait_for_selector(f'{self.xpath_first_vd}', timeout=10000)
                await asy_slp(uniform(0.8, 1.5))
                
                # ✅ Thumbnail - usando el selector más específico
                thumbnail_selectors = [
                    'xpath=.//img[@id="img" and @src]',
                    'xpath=.//img[contains(@src, "ytimg.com")]',
                    'xpath=.//ytd-thumbnail//img'
                ]
                results = []
                for i in range(limit):
                    try:
                        # Usar xpath más específico para evitar duplicados
                        video_element = self.page.locator(f'xpath=({self.xpath_first_vd})[{i+1}]')
                        if await video_element.count() == 0:
                            continue
                        
                        # ✅ Título (específico, solo el enlace principal)
                        title_element = video_element.locator('xpath=.//a[@id="video-title"]')
                        title = await title_element.get_attribute('title') or await title_element.text_content()
                        href = await title_element.get_attribute('href')
                        
                        
                        thumbnail = None
                        for selector in thumbnail_selectors:
                            img_element = video_element.locator(selector)
                            if await img_element.count() > 0:
                                thumbnail = await img_element.first.get_attribute('src')
                                if thumbnail:
                                    break
                        
                        # ✅ Canal - USAR .first PARA EVITAR STRICT MODE
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
                last_error = e
                error_msg = str(e)
                
                # Verificar si es timeout
                if "Timeout" in error_msg or "timeout" in error_msg.lower():
                    self.config.log.comentario("WARNING", f"⏰ Timeout en intento {attempt}/{max_retries}")
                    
                    if attempt == max_retries:
                        self.config.log.error(f"❌ Búsqueda falló después de {max_retries} intentos: {last_error}", "Search in youtubeplayer")
                        return []
                    continue
                else:
                    # Error diferente, no reintentar
                    self.config.log.error(f"❌ Error en búsqueda: {e}", "Search")
                    return []
        
        # Si llegamos aquí, todos los intentos fallaron
        self.config.log.error(f"❌ Búsqueda falló después de {max_retries} intentos", "Search")
        return []