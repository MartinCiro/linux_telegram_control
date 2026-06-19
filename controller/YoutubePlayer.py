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
        if not query or not query.strip():
            self.config.log.comentario("WARNING", "⚠️ Búsqueda sin query válida, abortando")
            return []
        
        last_error = None
        
        for attempt in range(1, max_retries + 1):
            try:
                if attempt > 1:
                    self.config.log.comentario("INFO", f"🔄 Reintento {attempt}/{max_retries} para búsqueda: {query}")
                    # Espera exponencial: 1s, 2s, 4s
                    await asy_slp(2 ** (attempt - 1))
                
                yt_query = query  # ✅ SIN FALLBACK a "Dora la exploradora"
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

    async def play_video(self, url: str, max_retries: int = 3) -> bool:
        """
        Navega a una URL de video y espera que se reproduzca.
        Sin input() — apto para entorno headless/Telegram.
        """
        for attempt in range(max_retries):
            try:
                await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await asy_slp(2)  # Esperar inicialización de YouTube player
                
                # Verificar que el video esté presente
                await self.page.wait_for_selector('video', timeout=10000)
                
                # Intentar play (YouTube a veces requiere interacción)
                is_paused = await self.page.evaluate("""
                    () => {
                        const video = document.querySelector('video');
                        return video ? video.paused : true;
                    }
                """)

                # Solo presionar play si está pausado
                if is_paused:
                    await self.page.keyboard.press(' ')
                
                # Verificar que no haya error de reproducción
                error = self.page.locator('.ytp-error')
                if await error.count() > 0:
                    error_msg = await error.first.text_content()
                    self.config.log.error(f"❌ Error de YouTube: {error_msg}")
                    return False
                
                return True
                
            except Exception as e:
                self.config.log.comentario("WARNING", f"Intento {attempt+1} fallido: {e}")
                if attempt == max_retries - 1:
                    return False
                await asy_slp(2 ** attempt)  # Espera exponencial
        
        return False
    
    async def next_video(self) -> bool:
        """
        Reproduce el siguiente video en la cola/reproducción automática.
        Hace click en el botón "Siguiente" de YouTube.
        
        Returns:
            bool: True si se ejecutó correctamente, False si falló
        """
        try:
            # ✅ Localizar el botón "Siguiente" usando múltiples selectores
            next_button_selectors = [
                '(//a[contains(@class, "ytp-next-button") or contains(@aria-keyshortcuts, "SHIFT+n")])[1]',  # Selector principal de YouTube
                '//a[@aria-keyshortcuts="SHIFT+n"]',  # Selector por título
                'button[title="Siguiente"]',  # Selector en español
                'button[data-title-no-tooltip="Next"]',  # Selector alternativo
                'button[data-title-no-tooltip="Siguiente"]'  # Selector alternativo en español
            ]
            next_button = None
            for selector in next_button_selectors:
                locator = self.page.locator(selector)
                if await locator.count() > 0:
                    next_button = locator.first
                    self.config.log.comentario("DEBUG", f"✅ Botón siguiente encontrado con selector: {selector}")
                    break
            
            if not next_button:
                self.config.log.comentario("WARNING", "⚠️ No se encontró el botón 'Siguiente'")
                return False
            
            # ✅ Hacer click en el botón
            await next_button.click(timeout=3000)
            self.config.log.comentario("INFO", "⏭️ Click en botón 'Siguiente' ejecutado")
            
            # ✅ Esperar a que cargue el nuevo video
            await asy_slp(2)
            
            # ✅ Verificar que el video se está reproduciendo
            video_selector = self.page.locator('video')
            if await video_selector.count() == 0:
                self.config.log.comentario("WARNING", "⚠️ No se detectó video después de presionar siguiente")
                return False
            
            # Verificar que no haya error
            error = self.page.locator('.ytp-error')
            if await error.count() > 0:
                error_msg = await error.first.text_content()
                self.config.log.error(f"❌ Error después de siguiente: {error_msg}")
                return False
            
            self.config.log.comentario("SUCCESS", "✅ Siguiente video reproducido correctamente")
            return True
            
        except Exception as e:
            self.config.log.error(f"❌ Error en next_video: {e}")
            return False
        
    async def prev_video(self) -> bool:
        """
        Reproduce el anterior video en la cola/reproducción automática.
        Hace click en el botón "Anterior" de YouTube.
        
        Returns:
            bool: True si se ejecutó correctamente, False si falló
        """
        try:
            # ✅ Localizar el botón "Anterior" usando múltiples selectores
            prev_button_selectors = [
                '(//a[contains(@class, "ytp-prev-button") or contains(@aria-keyshortcuts, "SHIFT+p")])[1]',  # Selector principal de YouTube
                '//a[@aria-keyshortcuts="SHIFT+n"]',  # Selector por título
                'button[title="Anterior"]',  # Selector en español
                'button[data-title-no-tooltip="Prev"]',  # Selector alternativo
                'button[data-title-no-tooltip="Anterior"]'  # Selector alternativo en español
            ]
            prev_button = None
            for selector in prev_button_selectors:
                locator = self.page.locator(selector)
                if await locator.count() > 0:
                    prev_button = locator.first
                    self.config.log.comentario("DEBUG", f"✅ Botón anterior encontrado con selector: {selector}")
                    break
            
            if not prev_button:
                self.config.log.comentario("WARNING", "⚠️ No se encontró el botón 'Anterior'")
                return False
            
            # ✅ Hacer click en el botón
            await prev_button.click(timeout=3000)
            self.config.log.comentario("INFO", "⏭️ Click en botón 'Anterior' ejecutado")
            
            # ✅ Esperar a que cargue el nuevo video
            await asy_slp(2)
            
            # ✅ Verificar que el video se está reproduciendo
            video_selector = self.page.locator('video')
            if await video_selector.count() == 0:
                self.config.log.comentario("WARNING", "⚠️ No se detectó video después de presionar anterior")
                return False
            
            # Verificar que no haya error
            error = self.page.locator('.ytp-error')
            if await error.count() > 0:
                error_msg = await error.first.text_content()
                self.config.log.error(f"❌ Error después de anterior: {error_msg}")
                return False
            
            self.config.log.comentario("SUCCESS", "✅ Anterior video reproducido correctamente")
            return True
            
        except Exception as e:
            self.config.log.error(f"❌ Error en next_video: {e}")
            return False
        
    async def pause_video(self) -> bool:
        """
        Pausa el video en reproducción.
        Hace click en el botón "Pausar" de YouTube.
        
        Returns:
            bool: True si se ejecutó correctamente, False si falló
        """
        try:
            # ✅ Localizar el botón "Pausa" usando múltiples selectores
            pause_button_selectors = [
                '(//button[contains(@class, "ytp-play-button") or contains(@aria-keyshortcuts, "k")])[1]',  # Selector principal de YouTube
                '//button[@aria-keyshortcuts="k"]',  # Selector por título
            ]
            pause_button = None
            for selector in pause_button_selectors:
                locator = self.page.locator(selector)
                if await locator.count() > 0:
                    pause_button = locator.first
                    self.config.log.comentario("DEBUG", f"✅ Botón anterior encontrado con selector: {selector}")
                    break
            
            if not pause_button:
                self.config.log.comentario("WARNING", "⚠️ No se encontró el botón 'Pausa'")
                return False
            
            # ✅ Hacer click en el botón
            await pause_button.click(timeout=3000)
            self.config.log.comentario("INFO", "⏭️ Click en botón 'Pausa' ejecutado")
            
            # ✅ Esperar a que cargue el nuevo video
            await asy_slp(2)
            
            # ✅ Verificar que el video se está reproduciendo
            video_selector = self.page.locator('video')
            if await video_selector.count() == 0:
                self.config.log.comentario("WARNING", "⚠️ No se detectó video después de presionar pausa")
                return False
            
            # Verificar que no haya error
            error = self.page.locator('.ytp-error')
            if await error.count() > 0:
                error_msg = await error.first.text_content()
                self.config.log.error(f"❌ Error después de pausa: {error_msg}")
                return False
            
            self.config.log.comentario("SUCCESS", "✅ Pausa video reproducido correctamente")
            return True
            
        except Exception as e:
            self.config.log.error(f"❌ Error en pausa de video: {e}")
            return False
        
    async def resume_video(self) -> bool:
        """
        Reanuda la reproducción del video pausado.
        Hace click en el botón "Play" de YouTube.
        
        Returns:
            bool: True si se ejecutó correctamente, False si falló
        """
        try:
            # Verificar primero si ya está reproduciéndose
            is_paused = await self.page.evaluate("""
                () => {
                    const video = document.querySelector('video');
                    return video ? video.paused : true;
                }
            """)
            
            if not is_paused:
                self.config.log.comentario("INFO", "ℹ️ El video ya se está reproduciendo")
                return True
            
            resume_button_selectors = [
                'button.ytp-play-button',
                'button[aria-keyshortcuts="k"]',
                'button[aria-label*="Play"]',
                'button[aria-label*="Reproducir"]'
            ]
            
            resume_button = None
            for selector in resume_button_selectors:
                locator = self.page.locator(selector)
                if await locator.count() > 0:
                    resume_button = locator.first
                    self.config.log.comentario("DEBUG", f"✅ Botón play encontrado con selector: {selector}")
                    break
            
            if not resume_button:
                self.config.log.comentario("WARNING", "⚠️ No se encontró el botón 'Play'")
                return False
            
            await resume_button.click(timeout=3000)
            self.config.log.comentario("INFO", "▶️ Click en botón 'Play' ejecutado")
            
            await asy_slp(0.5)
            
            # Verificar que efectivamente se reanudó
            is_paused_now = await self.page.evaluate("""
                () => {
                    const video = document.querySelector('video');
                    return video ? video.paused : true;
                }
            """)
            
            if is_paused_now:
                self.config.log.comentario("WARNING", "⚠️ El video no se reanudó correctamente")
                return False
            
            self.config.log.comentario("SUCCESS", "✅ Video reanudado correctamente")
            return True
            
        except Exception as e:
            self.config.log.error(f"❌ Error en resume_video: {e}")
            return False
        
    async def full_screen_video(self) -> bool:
        """
        Reproduce el video en la cola/reproducción automática en pantalla completa.
        Hace click en el botón "full_screen" de YouTube.
        
        Returns:
            bool: True si se ejecutó correctamente, False si falló
        """
        try:
            # ✅ Localizar el botón "full screen" usando múltiples selectores
            full_screen_button_selectors = [
                '(//button[contains(@class, "ytp-fullscreen-button") or contains(@aria-keyshortcuts, "f")])[1]',  # Selector principal de YouTube
                '//button[@aria-keyshortcuts="f"]',  # Selector por título
            ]
            full_screen_button = None
            for selector in full_screen_button_selectors:
                locator = self.page.locator(selector)
                if await locator.count() > 0:
                    full_screen_button = locator.first
                    self.config.log.comentario("DEBUG", f"✅ Botón full screen encontrado con selector: {selector}")
                    break
            
            if not full_screen_button:
                self.config.log.comentario("WARNING", "⚠️ No se encontró el botón 'full screen'")
                return False
            
            # ✅ Hacer click en el botón
            await full_screen_button.click(timeout=3000)
            self.config.log.comentario("INFO", "⏭️ Click en botón 'full screen' ejecutado")
            
            # ✅ Esperar a que cargue el nuevo video
            await asy_slp(2)
            
            # ✅ Verificar que el video se está reproduciendo
            video_selector = self.page.locator('video')
            if await video_selector.count() == 0:
                self.config.log.comentario("WARNING", "⚠️ No se detectó video después de presionar full screen")
                return False
            
            # Verificar que no haya error
            error = self.page.locator('.ytp-error')
            if await error.count() > 0:
                error_msg = await error.first.text_content()
                self.config.log.error(f"❌ Error después de click full screen: {error_msg}")
                return False
            
            self.config.log.comentario("SUCCESS", "✅ Full screen de video reproducido correctamente")
            return True
            
        except Exception as e:
            self.config.log.error(f"❌ Error en full screen: {e}")
            return False