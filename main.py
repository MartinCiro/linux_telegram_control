from sys import exit
from asyncio import sleep as asy_sleep, run as run_asy
from traceback import print_exc
from playwright.async_api import async_playwright

from controller.Config import Config
from controller.YoutubePlayer import YoutubePlayer
from os import path as os_path
from random import uniform

async def init_browser(config: Config):
    """Inicializa Playwright y retorna (playwright, browser, context, page)"""
    
    playwright = await async_playwright().start()
    user_data_dir = os_path.expanduser("~/.config/BraveSoftware/Brave-Browser-Playwright")
    if not os_path.exists(user_data_dir):
        os_path.makedirs(user_data_dir, exist_ok=True)
    
    launch_options = {
        'headless': config.headless.lower() == 'true',
        'args': [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--window-size=1920,1080',
            '--autoplay-policy=no-user-gesture-required',
            '--brave-shields-enabled=true',
            '--brave-ad-block-enabled=true',
            '--disable-infobars',
            '--disable-extensions',
            '--window-size=1920,1080',
        ],
        'channel': 'chrome',
    }
    
    chrome_path = config.get_chrome_path()
    if chrome_path:
        config.log.comentario("INFO", f"🌐 Usando Chrome: {chrome_path}")
        launch_options['executable_path'] = chrome_path
    else:
        config.log.comentario("INFO", "🌐 Usando Chromium interno de Playwright")
    
    context = await playwright.chromium.launch_persistent_context(
        user_data_dir=user_data_dir,
        **launch_options
    )

    browser = context.browser
    page = context.pages[0] if context.pages else await context.new_page()
    await page.add_init_script("""
        delete navigator.__proto__.webdriver;
        window.navigator.chrome = { runtime: {}, loadTimes: function() {}, connection: function() {} };
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        Object.defineProperty(navigator, 'languages', { get: () => ['es-ES', 'es', 'en-US', 'en'] });
    """)

    config.log.comentario("INFO", f"🌐 Brave con perfil persistente: {user_data_dir}")
    
    return playwright, browser, page

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

        # 🔁 LOOP PRINCIPAL: permite buscar varios videos sin reiniciar el navegador
        while True:
            success = await play_youtube_interactive(config, page)
            if not success:
                break  

            print("🎵 Video reproduciéndose...")
            
            await page.wait_for_load_state("domcontentloaded")
            await asy_sleep(uniform(0.3, 0.7))
            
            await page.keyboard.press('M')
            # ✅ Corrección crítica: config.headless es string, no booleano
            if config.headless.lower() == 'false':
                input("⏸️ Presiona Enter para buscar otro video o salir...")
            else:
                input("⏸️ [HEADLESS] Presiona Enter para continuar...")

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