from sys import exit
from asyncio import sleep, run as run_asy
from traceback import print_exc
from tempfile import NamedTemporaryFile
from pathlib import Path

from telegram.ext import Application, MessageHandler, CommandHandler, filters
from telegram import Update
from telegram.ext import ContextTypes

from controller.Config import Config
from controller.NotificadorTelegram import NotificadorTelegram
from controller.BrowserManager import BrowserManager

# Variable global
notificador = None

async def handle_telegram_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador para mensajes de audio en Telegram"""
    global notificador
    
    if not update.message.audio:
        await update.message.reply_text("❌ Envíame un archivo de audio")
        return
    
    await update.message.reply_text("🎤 Recibido audio. Procesando comando...")
    
    audio_file = await update.message.audio.get_file()
    
    with NamedTemporaryFile(suffix='.ogg', delete=False) as tmp:
        await audio_file.download_to_drive(tmp.name) 
        audio_path = tmp.name
    
    try:
        command = await notificador.handle_audio_message(audio_path)
        
        if not command:
            await update.message.reply_text("❌ No entendí el comando en el audio")
        else:
            pass
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error al procesar audio: {str(e)}")
        print(f"Error: {e}")
    finally:
        Path(audio_path).unlink(missing_ok=True)  

async def handle_telegram_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador para notas de voz"""
    global notificador
    
    if not update.message.voice:
        await update.message.reply_text("❌ Envíame una nota de voz")
        return
    
    await update.message.reply_text("🎤 Recibida nota de voz. Procesando...")
    
    voice_file = await update.message.voice.get_file()
    
    with NamedTemporaryFile(suffix='.ogg', delete=False) as tmp:
        await voice_file.download_to_drive(tmp.name)  
        audio_path = tmp.name
    
    try:
        command = await notificador.handle_audio_message(audio_path)
        
        if not command:
            await update.message.reply_text("❌ No entendí el comando en la nota de voz")
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
    finally:
        Path(audio_path).unlink(missing_ok=True)  # ✅ FIX

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    await update.message.reply_text(
        "🎵 **Bot de YouTube + Brave**\n\n"
        "✅ **Anti-detección activada**\n"
        "✅ **Bloqueo de anuncios activo** (Brave Shields)\n\n"
        "📤 **Envíame un audio o nota de voz** con comandos como:\n"
        "• 'reproduce lofi hip hop'\n"
        "• 'pausa'\n"
        "• 'siguiente'\n"
        "• 'volumen 70'\n\n"
        "🎙️ ¡Pruébalo ahora!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /help"""
    global notificador
    if notificador:
        # ✅ Delegamos al orquestador interno
        result = await notificador.execute_command("/help")
        await update.message.reply_text(result.get("message", "❌ Error al obtener ayuda"), parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ Bot no inicializado correctamente")

async def main():
    global notificador
    
    try:
        config = Config()
        
        print("=" * 50)
        print("🤖 Bot de Telegram + Brave Browser con anti-detección")
        print("=" * 50)
        print("✅ Bloqueo de anuncios: ACTIVADO (Brave Shields)")
        print("✅ Anti-detección: ACTIVADA")
        print("=" * 50)
        
        if not config.telegram_token:
            print("❌ ERROR: TELEGRAM_TOKEN no está configurado en .env")
            return 1
        
        # ✅ 1. Instanciar BrowserManager y inyectarlo en NotificadorTelegram
        browser_manager = BrowserManager()
        notificador = NotificadorTelegram(config, browser_manager)
        
        # Crear aplicación de Telegram
        application = Application.builder().token(config.telegram_token).build()
        
        # ✅ 2. Usar CommandHandler para comandos de texto (más limpio que MessageHandler + Regex)
        application.add_handler(MessageHandler(filters.AUDIO, handle_telegram_audio))
        application.add_handler(MessageHandler(filters.VOICE, handle_telegram_voice))
        application.add_handler(CommandHandler('start', start_command))
        application.add_handler(CommandHandler('help', help_command))
        
        print("✅ Bot de Telegram iniciado correctamente")
        print("📱 Busca tu bot en Telegram y envía un audio o nota de voz")
        print("🛡️ Brave se iniciará automáticamente cuando recibas un comando de música")
        print("Press Ctrl+C para salir\n")
        
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        try:
            while True:
                await sleep(1)
        except KeyboardInterrupt:
            print("\n⚠️ Deteniendo bot...")
            await application.updater.stop()
            await application.stop()
            await application.shutdown()
        
    except Exception as e:
        print(f"\n💥 Error crítico: {e}")
        print_exc()
        return 1
    finally:
        if notificador:
            await notificador.close_browser()
        print("\n✅ Programa finalizado")

def run():
    exit_code = run_asy(main())
    exit(exit_code)

if __name__ == "__main__":
    run()