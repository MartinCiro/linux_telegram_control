# controller/SpeechToCommand.py - Versión simplificada que usa CommandRegistry
import speech_recognition as sr
from pathlib import Path
from typing import Optional, Dict
from controller.Log import Log
from controller.utils.file import FileUtils
from pydub import AudioSegment
from controller.CommandRegistry import CommandRegistry, Command

class SpeechToCommand:
    """
    Convierte AUDIOS (archivos) a comandos de texto.
    Utiliza CommandRegistry para la gestión de comandos.
    """
    
    def __init__(self, config):
        """
        Args:
            config: Instancia de Config
            commands_config_path: Ruta opcional a JSON con comandos personalizados
        """
        self.config = config
        self.log = Log()
        self.recognizer = sr.Recognizer()
        
        # Inicializar registro de comandos
        self.command_registry = CommandRegistry(config)
        
        # Cache de archivos temporales (para limpieza automática)
        self._temp_files = set()
    
    def _convert_to_wav(self, input_path: str) -> Optional[str]:
        """
        Convierte cualquier formato de audio a WAV para SpeechRecognition
        
        Args:
            input_path: Ruta del archivo original
        
        Returns:
            Ruta del archivo WAV temporal o None si falla
        """
        try:
            input_path_obj = Path(input_path)
            output_path = input_path_obj.with_suffix('.wav')
            
            self.config.log.comentario("INFO", f"🔄 Convirtiendo {input_path_obj.suffix} a WAV...")
            
            # Cargar audio con pydub (soporta OGG, MP3, etc.)
            audio = AudioSegment.from_file(str(input_path_obj))
            
            # Exportar como WAV mono (mejor para reconocimiento)
            audio = audio.set_channels(1).set_frame_rate(16000)
            audio.export(str(output_path), format='wav')
            
            self._temp_files.add(str(output_path))
            self.config.log.comentario("INFO", f"✅ Conversión exitosa: {output_path}")
            return str(output_path)
            
        except Exception as e:
            self.config.log.error(f"❌ Error en conversión: {e}")
            return None
    
    def transcribe_audio_file(self, audio_file_path: str, language: str = "es-ES") -> Optional[str]:
        """
        Transcribe un archivo de audio a texto.
        Soporta: WAV, MP3, OGG, FLAC, M4A, etc.
        
        Args:
            audio_file_path: Ruta al archivo de audio
            language: Código de idioma (default: es-ES)
        
        Returns:
            Texto transcrito o None si falla
        """
        temp_wav = None
        
        try:
            # Verificar que el archivo existe
            if not FileUtils.exists(audio_file_path):
                self.config.log.error(f"Archivo no encontrado: {audio_file_path}")
                return None
            
            self.config.log.comentario("INFO", f"📁 Procesando archivo: {audio_file_path}")
            
            # Si no es WAV, convertir
            if not audio_file_path.lower().endswith('.wav'):
                temp_wav = self._convert_to_wav(audio_file_path)
                if not temp_wav:
                    return None
                process_path = temp_wav
            else:
                process_path = audio_file_path
            
            # Procesar con SpeechRecognition
            with sr.AudioFile(process_path) as source:
                # Ajustar para ruido ambiente (opcional)
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio_data = self.recognizer.record(source)
                
                # Usar Google Speech Recognition
                text = self.recognizer.recognize_google(audio_data, language=language)
                
            self.config.log.comentario("INFO", f"📝 Transcripción: '{text}'")
            return text.lower()
            
        except sr.UnknownValueError:
            self.config.log.comentario("WARNING", "❓ No se pudo entender el audio")
            return None
        except sr.RequestError as e:
            self.config.log.error(f"🔌 Error con el servicio de reconocimiento: {e}")
            return None
        except Exception as e:
            self.config.log.error(f"💥 Error al procesar archivo: {e}")
            return None
            
        finally:
            self._cleanup_temp_files(temp_wav)
    
    def text_to_command(self, text: str) -> Optional[str]:
        """
        Convierte texto a comando utilizando CommandRegistry.
        
        Args:
            text: Texto transcrito
        
        Returns:
            Comando a ejecutar (ej: "/saluda") o None
        """
        if not text:
            return None
        
        # Buscar comando en el registro
        command = self.command_registry.get_command_by_text(text)
        
        if command is not None:
            # Extraer parámetros si es necesario
            params = self.command_registry.extract_parameters(text, command)
            
            # Construir comando final
            final_command = command.action
            if params:
                # Formatear parámetros (ej: /volume 75)
                param_str = " ".join(str(v) for v in params.values())
                final_command = f"{command.action} {param_str}"
            
            self.config.log.comentario("INFO", f"✅ Comando detectado: '{final_command}'")
            return final_command
        
        msg = self.command_registry.get_missing_command_message(text)
        self.config.log.comentario("INFO", msg)
        return msg
    
    def process_audio_to_command(self, audio_file_path: str) -> Optional[str]:
        """
        Proceso completo: archivo de audio → texto → comando
        
        Args:
            audio_file_path: Ruta al archivo de audio
        
        Returns:
            Comando a ejecutar o None
        """
        text = self.transcribe_audio_file(audio_file_path)
        if not text:
            return None
        self.config.log.comentario("INFO", f"✅ Texto recibido: '{text}'")
        return self.text_to_command(text)
    
    def process_audio_bytes(self, audio_bytes: bytes, format: str = 'ogg') -> Optional[str]:
        """
        Procesa audio desde bytes (útil para descargas de Telegram)
        
        Args:
            audio_bytes: Datos del audio en bytes
            format: Formato del audio ('wav', 'mp3', 'ogg')
        
        Returns:
            Comando a ejecutar o None
        """
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix=f'.{format}', delete=False) as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_path = tmp_file.name
        
        try:
            self._temp_files.add(tmp_path)
            result = self.process_audio_to_command(tmp_path)
            return result
        finally:
            self._cleanup_temp_files(tmp_path)
    
    def _cleanup_temp_files(self, *paths):
        """Limpia archivos temporales"""
        for path in paths:
            if path and Path(path).exists():
                try:
                    Path(path).unlink(missing_ok=True)
                    self._temp_files.discard(path)
                except Exception as e:
                    self.config.log.comentario("DEBUG", f"Error limpiando {path}: {e}")
        
        # Limpiar todos los temporales acumulados
        for temp_path in list(self._temp_files):
            try:
                Path(temp_path).unlink(missing_ok=True)
                self._temp_files.discard(temp_path)
            except Exception:
                pass
    
    def get_available_commands(self) -> Dict[str, Command]:
        """Retorna todos los comandos disponibles"""
        return self.command_registry.get_all_commands()
    
    def get_help_text(self) -> str:
        """Retorna texto de ayuda formateado"""
        return self.command_registry.get_help_text()