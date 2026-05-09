# main.py
from sys import exit
from asyncio import run as run_asy
from playwright.async_api import async_playwright

from controller.Config import Config
from controller.utils.file import FileUtils
from controller.YoutubePlayer import YoutubePlayer

async def init_browser(config: Config):
    """Inicializa Playwright y retorna (playwright, browser, context, page)"""
    
    playwright = await async_playwright().start()
    
    launch_options = {
        'headless': config.headless.lower() == 'true',
        'args': [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--window-size=1920,1080',
        ]
    }
    
    chrome_path = config.get_chrome_path()
    if chrome_path:
        config.log.comentario("INFO", f"🌐 Usando Chrome: {chrome_path}")
        launch_options['executable_path'] = chrome_path
    else:
        config.log.comentario("INFO", "🌐 Usando Chromium interno de Playwright")
    
    browser = await playwright.chromium.launch(**launch_options)
    
    # Cookies 
    cookies_path = config.get_cookies_path()
    storage_state = None
    if FileUtils.exists(cookies_path):
        storage_state = cookies_path
        config.log.comentario("INFO", f"🍪 Cargando cookies desde: {cookies_path}")
    
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        storage_state=storage_state
    )
    page = await context.new_page()
    
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

async def main():
    try:
        config = Config()
        playwright, browser, page = await init_browser(config)
        
        print("🎵 Buscando video en YouTube...")
        exit_code = await play_youtube(config, page)  
        
        return exit_code
        
    except KeyboardInterrupt:
        print("\n⚠️ Interrumpido por usuario")
        return 130
    except Exception as e:
        print(f"\n💥 Error crítico: {e}")
        import traceback; traceback.print_exc()
        return 1
    finally:
        if 'browser' in locals():
            await browser.close()
        if 'playwright' in locals():
            await playwright.stop()
        print("✅ Recursos liberados")

def run():
    exit_code = run_asy(main())
    exit(exit_code)

if __name__ == "__main__":
    run()