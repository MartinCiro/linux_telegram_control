# main.py - Bot de Telegram que escucha audios (CORREGIDO)
from pathlib import Path
from sys import exit
from asyncio import run as run_asy, sleep
from traceback import print_exc

# Importar la librería correcta
from telegram.ext import Application, MessageHandler, filters
from telegram import Update
from telegram.ext import ContextTypes

from controller.Config import Config
from controller.NotificadorTelegram import NotificadorTelegram
from tempfile import NamedTemporaryFile

# Variable global para el notificador
notificador = None

async def handle_telegram_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador para mensajes de audio en Telegram"""
    global notificador
    
    # Verificar si es un mensaje de audio
    if not update.message.audio:
        await update.message.reply_text("❌ Envíame un archivo de audio")
        return
    
    # Informar que se está procesando
    await update.message.reply_text("🎤 Recibido audio. Procesando comando...")
    
    # Obtener el audio
    audio_file = await update.message.audio.get_file()
    
    # Descargar a archivo temporal
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as tmp:
        await audio_file.download_to_drive(tmp.name)
        audio_path = tmp.name
    
    try:
        # Procesar el audio usando el notificador existente
        command = await notificador.handle_audio_message(audio_path)
        
        if not command:
            await update.message.reply_text("❌ No entendí el comando en el audio")
        else:
            await update.message.reply_text(f"✅ Comando procesado: `{command}`", parse_mode='Markdown')
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error al procesar audio: {str(e)}")
        print(f"Error: {e}")
        
    finally:
        # Limpiar archivo temporal
        Path(audio_path).unlink(missing_ok=True)

async def handle_telegram_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador para mensajes de voz (nota de voz) en Telegram"""
    global notificador
    
    if not update.message.voice:
        await update.message.reply_text("❌ Envíame una nota de voz")
        return
    
    await update.message.reply_text("🎤 Recibida nota de voz. Procesando...")
    
    # Obtener la nota de voz
    voice_file = await update.message.voice.get_file()
    
    # Descargar a archivo temporal
    
    with NamedTemporaryFile(suffix='.ogg', delete=False) as tmp:
        await voice_file.download_to_drive(tmp.name)
        audio_path = tmp.name
    
    try:
        # Procesar el audio
        command = await notificador.handle_audio_message(audio_path)
        
        await update.message.reply_text(
            "❌ No entendí el comando en la nota de voz" if not command 
            else f"✅ Comando procesado: `{command}`",
            parse_mode='Markdown' if command else None
        )
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        
    finally:
        Path(audio_path).unlink(missing_ok=True)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    await update.message.reply_text(
        "🎵 ¡Bienvenido al Bot de Comandos por Voz!\n\n"
        "📤 Envíame un **audio** o **nota de voz** y lo convertiré en comandos.\n\n"
        "**Comandos disponibles:**\n"
        "• 'saluda' → /saluda\n"
        "• 'reproduce música' → /play\n"
        "• 'siguiente canción' → /next\n"
        "• 'pausa' → /pause\n"
        "• 'volumen 50' → /volume 50\n"
        "• 'ayuda' → /help\n\n"
        "🎙️ ¡Pruébalo ahora!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /help"""
    await update.message.reply_text(
        "🎙️ **Guía de Comandos por Voz**\n\n"
        "**Ejemplos de lo que puedes decir:**\n"
        "• \"saluda\" → /saluda\n"
        "• \"reproduce lofi\" → /play\n"
        "• \"siguiente\" → /next\n"
        "• \"pausa la música\" → /pause\n"
        "• \"sube volumen a 70\" → /volume 70\n\n"
        "📤 Envía un audio o nota de voz con estos comandos."
    )

async def main():
    global notificador
    
    try:
        config = Config()
        
        print("🤖 Bot de Telegram - Comandos por Voz")
        print("=" * 40)
        
        # Verificar que el token existe
        if not config.telegram_token:
            print("❌ ERROR: TELEGRAM_TOKEN no está configurado en .env")
            return 1
        
        # Inicializar el notificador
        notificador = NotificadorTelegram(config)
        
        # Crear aplicación de Telegram
        application = Application.builder().token(config.telegram_token).build()
        
        # Agregar handlers
        application.add_handler(MessageHandler(filters.AUDIO, handle_telegram_audio))
        application.add_handler(MessageHandler(filters.VOICE, handle_telegram_voice))
        application.add_handler(MessageHandler(filters.COMMAND & filters.Regex('^/start$'), start_command))
        application.add_handler(MessageHandler(filters.COMMAND & filters.Regex('^/help$'), help_command))
        
        print("✅ Bot iniciado correctamente")
        print("📱 Busca tu bot en Telegram y envía un audio o nota de voz")
        print("Press Ctrl+C para salir\n")
        
        # Iniciar el bot (método simplificado para python-telegram-bot 20.x)
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        # Mantener el bot corriendo
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
        print("\n✅ Programa finalizado")

def run():
    exit_code = run_asy(main())
    exit(exit_code)

if __name__ == "__main__":
    run()