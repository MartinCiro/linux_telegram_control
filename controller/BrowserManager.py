# controller/BrowserManager.py
"""
Gestor de navegador Brave con anti-detección y bloqueo de anuncios.
Singleton pattern para mantener una sola instancia del navegador.
"""

from os import name as os_name, path as os_path
from playwright.async_api import async_playwright, BrowserContext, Browser, Page, Playwright
from typing import Optional, Tuple
from controller.utils.screen_utils import ScreenUtils


class BrowserManager:
    """
    Gestiona el ciclo de vida de Playwright/Brave.
    ✅ Valida estado interno
    ✅ Auto-recupera si se cierra/crasha
    ✅ Devuelve siempre una página lista para usar
    """
    
    def __init__(self):
        self._playwright = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._initialized = False
        self.config = None 
    
    async def initialize(self, config) -> Tuple[bool, Optional[Page]]:
        """
        Inicializa el navegador Brave con anti-detección
        
        Args:
            config: Instancia de Config
            
        Returns:
            Tuple[bool, Optional[Page]]: (éxito, página)
        """
        self.config = config

        screen_w, screen_h = ScreenUtils.get_screen_size()
        if self._is_alive():
            if not self._page or self._page.is_closed():
                self._page = await self._context.new_page() 
                config.log.comentario("INFO", "📑 Nueva página creada en contexto existente")
            
            await self._page.bring_to_front()
            await self._page.set_viewport_size({'width': screen_w, 'height': screen_h})
            return True, self._page
        
        config.log.comentario("INFO", "🔄 Inicializando navegador Brave...")
        await self._cleanup()
        
        try:
            self._playwright = await async_playwright().start()
            user_data_dir = os_path.expanduser(config.user_browser_directory)
            if not os_path.exists(user_data_dir):
                os_path.makedirs(user_data_dir, exist_ok=True)
            
            brave_exec = config.get_chrome_path()
            if not brave_exec:
                config.log.comentario("ERROR", "❌ No se encontró la ruta de Brave Browser")
                return False, None
            
            # Configuración de lanzamiento con anti-detección
            launch_options = {
                'headless': config.headless.lower() == 'true', # Usa 'new' si es posible en tu versión de Playwright
                'executable_path': brave_exec,
                'args': [
                    # --- Anti-Detección Fundamental ---
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=IsolateOrigins,site-per-process,TranslateUI,PrivacySandboxFirstPartySets',
                    
                    # --- Huella Digital y Rendimiento ---
                    '--disable-dev-shm-usage',
                    '--force-color-profile=srgb',
                    '--disable-accelerated-2d-canvas', # A veces necesario para evitar detección de GPU
                    '--no-first-run',
                    '--no-default-browser-check',
                    
                    # --- Limpieza de Interfaz ---
                    '--disable-infobars',
                    '--disable-background-networking', # Evita pings de fondo de Brave/Google
                    '--disable-sync',
                    
                    # --- Idioma y Regionalización ---
                    '--lang=es-ES',
                    '--accept-lang=es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7',
                    
                    # --- Brave Específico (Opcional) ---
                    # '--disable-brave-component-updates', # ¡Cuidado! Rompe actualizaciones de Shields
                    '--start-maximized',
                ],
                'ignore_default_args': [
                    '--enable-automation', 
                    '--disable-extensions', # ¡Importante! No deshabilitar extensiones si usas uBlock en el perfil
                ],
            }
            
            # Crear contexto persistente
            self._context = await self._playwright.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                no_viewport=True,
                **launch_options
            )
            
            # Script stealth
            stealth_script = """
                // Eliminar webdriver - Método más compatible
                delete Object.getPrototypeOf(navigator).webdriver;
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                    configurable: true
                });
                
                // Simular chrome.runtime (Brave lo tiene nativo)
                if (!window.chrome) {
                    window.chrome = {
                        runtime: {
                            id: 'fake-id',
                            connect: () => {},
                            sendMessage: () => {}
                        }
                    };
                }
                
                // Plugins realistas (NO sobrescribir si ya existen)
                if (!navigator.plugins || navigator.plugins.length === 0) {
                    const plugins = {
                        0: { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                        1: { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                        2: { name: 'Native Client', filename: 'internal-nacl-plugin' },
                        length: 3
                    };
                    Object.setPrototypeOf(plugins, PluginArray.prototype);
                    Object.defineProperty(navigator, 'plugins', { get: () => plugins });
                }
                
                // Idioma consistente
                Object.defineProperty(navigator, 'languages', { get: () => ['es-ES', 'es', 'en'] });
                
                // Hardware moderno
                Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
                Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
                
                // Limpiar rastros de Playwright
                delete window.__playwright;
                delete window.__pw_manual;
            """
            
            await self._context.add_init_script(stealth_script)
            
            # Headers HTTP realistas
            await self._context.set_extra_http_headers({
                'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
                'Sec-Ch-Ua': '"Brave";v="122", "Not:A-Brand";v="24", "Chromium";v="122"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"' if os_name == 'nt' else '"Linux"',
            })
            
            # Obtener o crear página
            self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()
            #await self._page.set_viewport_size({'width': screen_w, 'height': screen_h})
            
            # Asegurar una sola pestaña
            self._page = await self._ensure_first_tab()
            
            self._initialized = True
            config.log.comentario("SUCCESS", "🌐 Brave Browser iniciado con anti-detección y bloqueo de anuncios")
            return True, self._page
            
        except Exception as e:
            config.log.error(str(e), "Inicializando el navegador")
            await self._cleanup() 
            return False, None
    
    async def _ensure_first_tab(self):
        """Asegura que solo haya una pestaña activa"""
        if len(self._context.pages) == 0:
            page = await self._context.new_page()
            self.config.log.comentario("INFO", "📑 Creada nueva pestaña principal")
        else:
            page = self._context.pages[0]
            
            # Cerrar pestañas adicionales
            if len(self._context.pages) > 1:
                self.config.log.comentario("INFO", f"🧹 Cerrando {len(self._context.pages)-1} pestañas adicionales")
                for i in range(len(self._context.pages) - 1, 0, -1):
                    await self._context.pages[i].close()
        
        await page.bring_to_front()
        return page
    
    async def get_page(self) -> Optional[Page]:
        """Retorna la página actual del navegador"""
        if not self._initialized or not self._page or self._page.is_closed():
            return None
        return self._page
    
    async def close(self):
        """Cierra explícitamente todos los recursos"""
        await self._cleanup()
    
    def is_initialized(self) -> bool:
        return self._initialized and self._page and not self._page.is_closed()
    
    def _is_alive(self) -> bool:
        alive = False
        try:
            alive = (self._playwright and 
                    self._context and 
                    not self._context.browser.is_closed() and
                    (not self._page or not self._page.is_closed()))
        except Exception as e:
            if self.config:
                self.config.log.comentario("DEBUG", f"🔍 _is_alive() error: {e}")
        if self.config:
            self.config.log.comentario("DEBUG", f"🔍 _is_alive() = {alive}")
        return alive
    
    async def _cleanup(self):
        """Limpia recursos huérfanos antes de reiniciar"""
        try:
            # ✅ Usar atributos con guión bajo
            if self._page and not self._page.is_closed():
                await self._page.close()
            if self._context and not self._context.browser.is_closed():
                await self._context.close()
            if self._playwright:
                await self._playwright.stop()
            
            # ✅ Verificar que config exista antes de loguear
            if hasattr(self, 'config') and self.config:
                self.config.log.comentario("INFO", "🛑 Navegador cerrado")
        except Exception as e:
            if hasattr(self, 'config') and self.config:
                self.config.log.comentario("WARNING", f"⚠️ Error en cleanup: {e}")
        finally:
            # ✅ Resetear atributos con guión bajo
            self._playwright = None
            self._context = None
            self._page = None
            self._initialized = False