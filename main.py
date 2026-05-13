from sys import exit
from asyncio import sleep as asy_sleep, run as run_asy
from traceback import print_exc
from playwright.async_api import async_playwright

from controller.Config import Config
from controller.YoutubePlayer import YoutubePlayer
from os import path as os_path
from random import uniform

async def ensure_first_tab(context, config):
    """
    Asegura que la primera pestaña esté activa y limpia.
    Retorna la página de la primera pestaña.
    """
    if len(context.pages) == 0:
        # No hay páginas, crear una nueva
        page = await context.new_page()
        config.log.comentario("INFO", "📑 Creada nueva pestaña principal")
    else:
        # Usar la primera pestaña existente
        page = context.pages[0]
        config.log.comentario("INFO", f"📑 Usando pestaña principal (Total: {len(context.pages)} pestañas)")
        
        # Si hay más pestañas, cerrarlas opcionalmente
        if len(context.pages) > 1:
            config.log.comentario("INFO", f"🧹 Cerrando {len(context.pages)-1} pestañas adicionales")
            for i in range(len(context.pages) - 1, 0, -1):
                await context.pages[i].close()
    
    # Asegurar que la página esté activa
    await page.bring_to_front()
    return page

async def init_browser(config: Config):
    """Inicializa Playwright con técnicas avanzadas de stealth."""
    
    playwright = await async_playwright().start()
    user_data_dir = os_path.expanduser("~/.config/BraveSoftware/Brave-Browser-Playwright")
    if not os_path.exists(user_data_dir):
        os_path.makedirs(user_data_dir, exist_ok=True)
    
    brave_exec = config.get_chrome_path()
    if not brave_exec:
        config.log.comentario("ERROR", "No se encontró la ruta de Brave.")
        return None
    
    # Configuración optimizada de argumentos
    launch_options = {
        'headless': config.headless.lower() == 'true',
        'executable_path': brave_exec,
        'args': [
            # Sandbox y rendimiento
            '--disable-dev-shm-usage',
            
            # Anti-detección de automatización (Chromium/Playwright)
            '--disable-blink-features=AutomationControlled',
            '--disable-features=IsolateOrigins,site-per-process,AutomationControlled',
            
            # Ventana y viewport consistente
            '--window-size=1920,1080',
            '--viewport-size=1920,1080',
            
            # Limpieza de huellas de automatización
            '--disable-infobars',
            '--disable-extensions',
            '--disable-component-update',
            '--no-first-run',
            '--disable-default-apps',
            '--disable-sync',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            '--disable-ipc-flooding-protection',
            
            # Configuración de medios y autoplay
            '--autoplay-policy=no-user-gesture-required',
            '--enable-features=MediaRouter',
            
            # Idioma y regionalización
            '--lang=es-ES',
            '--accept-lang=es-ES,es,en-US,en',
            
            # Brave-specific: desactivar shields para evitar conflictos con fingerprinting
            '--disable-brave-component-updates',
        ],
        'ignore_default_args': ['--enable-automation'], 
    }
    
    # Crear contexto
    context = await playwright.chromium.launch_persistent_context(
        user_data_dir=user_data_dir,
        **launch_options
    )

    stealth_script = """
        // 1. Eliminar webdriver de forma segura para Playwright
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
            configurable: true
        });
        
        // 2. Simular window.chrome real (estructura mínima que esperan los detectores)
        if (!window.navigator.chrome) {
            window.navigator.chrome = {
                runtime: {},
                loadTimes: function() { return {}; },
                csi: function() { return {}; },
                connection: function() { return { type: 'wifi', downlink: 10, rtt: 50 }; }
            };
        }
        
        // 3. Plugins realistas con Prototype correcto
        const mockPlugins = {
            length: 3,
            item: function(index) { return this[index] || null; },
            namedItem: function(name) { return this[name] || null; },
            refresh: function() { return []; },
            0: {
                name: 'Chrome PDF Plugin',
                filename: 'internal-pdf-viewer',
                description: 'Portable Document Format',
                version: '1.0.0.0',
                length: 0,
                item: function() { return null; },
                namedItem: function() { return null; }
            },
            1: {
                name: 'Chrome PDF Viewer',
                filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
                description: 'Portable Document Format',
                version: '1.0.0.0',
                length: 0,
                item: function() { return null; },
                namedItem: function() { return null; }
            },
            2: {
                name: 'Native Client',
                filename: 'internal-nacl-plugin',
                description: '',
                version: '1.0.0.0',
                length: 0,
                item: function() { return null; },
                namedItem: function() { return null; }
            }
        };
        Object.setPrototypeOf(mockPlugins, PluginArray.prototype);
        Object.defineProperty(navigator, 'plugins', {
            get: () => mockPlugins,
            configurable: true
        });
        
        // 4. Idiomas coherentes con el locale del sistema
        Object.defineProperty(navigator, 'languages', {
            get: () => ['es-ES', 'es', 'en-US', 'en'],
            configurable: true
        });
        Object.defineProperty(navigator, 'language', {
            get: () => 'es-ES',
            configurable: true
        });
        
        // 5. Parchear Function.toString para evitar detección de código inyectado
        const nativeToString = Function.prototype.toString;
        const nativeHasOwnProperty = Object.prototype.hasOwnProperty;
        
        Function.prototype.toString = function() {
            if (nativeHasOwnProperty.call(this, 'name') && this.name === 'get webdriver') {
                return 'function get webdriver() { [native code] }';
            }
            return nativeToString.call(this);
        };
        
        // 6. Permisos silenciosos (evita prompts que delatan automatización)
        const originalQuery = window.navigator.permissions?.query;
        if (originalQuery) {
            window.navigator.permissions.query = function(parameters) {
                if (parameters.name === 'notifications') {
                    return Promise.resolve({
                        state: Notification.permission || 'default',
                        onchange: null,
                        addEventListener: function() {},
                        removeEventListener: function() {},
                        dispatchEvent: function() { return false; }
                    });
                }
                return originalQuery.apply(this, arguments);
            };
        }
        
        // 7. Screen y hardware coherentes con viewport 1920x1080
        Object.defineProperty(screen, 'width', { get: () => 1920, configurable: true });
        Object.defineProperty(screen, 'height', { get: () => 1080, configurable: true });
        Object.defineProperty(screen, 'availWidth', { get: () => 1920, configurable: true });
        Object.defineProperty(screen, 'availHeight', { get: () => 1080, configurable: true });
        Object.defineProperty(screen, 'colorDepth', { get: () => 24, configurable: true });
        Object.defineProperty(screen, 'pixelDepth', { get: () => 24, configurable: true });
        
        // 8. Hardware concurrency y deviceMemory realistas para un i5/Ryzen moderno
        Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8, configurable: true });
        Object.defineProperty(navigator, 'deviceMemory', { get: () => 8, configurable: true });
        
        // 9. Eliminar propiedades de Playwright que puedan delatar
        delete window.__playwright;
        delete window.__pw_manual;
        delete window.__PW_inspect;
    """

    await context.add_init_script(stealth_script)
    
    await context.set_extra_http_headers({
        'Accept-Language': 'es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7',
        'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Brave";v="122"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Linux"'
    })

    page = context.pages[0] if context.pages else await context.new_page()
    page = await ensure_first_tab(context, config) if context.pages else await context.new_page()
    
    config.log.comentario("INFO", "🌐 Navegador Brave iniciado con stealth mejorado.")
    
    return playwright, context.browser, page 

async def play_youtube(config: Config, page, query: str = None) -> int:
    """Wrapper que retorna código de salida (0=éxito, 1=error)"""
    yt_query = query or config.youtube_query
    
    yt = YoutubePlayer(config, page)
    success = await yt.search_and_play(yt_query)
    
    # ✅ Mantener abierto si se configura
    if config.headless:
        input("⏸️ Presiona Enter para cerrar...")
    
    return 0 if success else 1

# 🔹 Búsqueda interactiva: usuario elige el video
async def play_youtube_interactive(config: Config, page) -> bool:    
    yt = YoutubePlayer(config, page)
    
    # 1. Buscar y mostrar resultados
    query = config.youtube_query
    results = await yt.search(query)
    # print(results) # Lista de obj
    if not results:
        print("❌ No se encontraron resultados")
        return False
    
    print(f"\n📋 Resultados para '{query}':")
    for r in results:
        print(f"   {r['index']}. {r['title'][:60]}{'...' if len(r['title']) > 60 else ''}")
    
    # 2. Pedir selección al usuario
    try:
        choice = input("\n👉 Elige un número (1-5) o 'q' para salir: ").strip()
        if choice.lower() == 'q':
            return False
        
        idx = int(choice) - 1
        if 0 <= idx < len(results):
            # 1️⃣ Navegar al video (SOLO domcontentloaded)
            await page.goto(results[idx]["url"], wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_selector('video', timeout=10000)
            await asy_sleep(1.5)  # Tiempo para que YouTube inicialice su player interno
            
            print(f"✅ Reproduciendo: {results[idx]['title']}")
            return True
        else:
            print("❌ Opción inválida")
            return False
    except ValueError:
        print("❌ Entrada inválida")
        return False
    
async def main():
    try:
        config = Config()
        playwright, browser, page = await init_browser(config)
        
        print("🎵 YouTube Player Interactivo - Escribe 'q' para salir en cualquier momento\n")

        while True:
            success = await play_youtube_interactive(config, page)
            if not success:
                break  

            print("🎵 Video reproduciéndose...")
            
            await page.wait_for_load_state("domcontentloaded")
            await asy_sleep(uniform(0.3, 0.7))

            volume_button = page.locator(f"xpath={config.youtube_dict['icon_volumen']}")
            await asy_sleep(uniform(0.5, 0.1))

            button_count = await volume_button.count()

            if button_count > 0:
                await page.keyboard.press('M')

            input("⏸️ Presiona Enter para buscar otro video o salir..." if config.headless.lower() == 'false' else "⏸️ [HEADLESS] Presiona Enter para continuar...")

            next_action = input("🔁 ¿Buscar otro video? (Enter=Sí / q=Salir): ").strip()
            if next_action.lower() == 'q':
                break

        return 0

    except KeyboardInterrupt:
        print("\n⚠️ Interrumpido por usuario")
        return 130
    except Exception as e:
        print(f"\n💥 Error crítico: {e}")
        print_exc()
        return 1
    finally:
        if 'browser' in locals() and browser:
            await browser.close()
        if 'playwright' in locals() and playwright:
            await playwright.stop()
        print("✅ Recursos liberados")

def run():
    exit_code = run_asy(main())
    exit(exit_code)

if __name__ == "__main__":
    run()