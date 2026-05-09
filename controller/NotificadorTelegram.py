# ===========================================================================
# Importe de clases/librerias necesarias
# ===========================================================================
from requests import exceptions, post

class NotificadorTelegram:
    """
    NotificadorTelegram
    ===================
    Clase para enviar notificaciones a Telegram.
    Recibe la configuración por inyección de dependencias.
    """
    
    def __init__(self, config):  
        """
        Constructor con inyección de configuración
        
        Args:
            config: Instancia de Config con las credenciales de Telegram
        """
        self.config = config  
        self.__asuntoNotificacion = "🔔 Alerta Bot"
        self.api_url = "https://api.telegram.org/bot"
        self.token = self.config.telegram_token
        self.chat_id = self.config.telegram_chat  
        
        if not self.token or not self.chat_id:  
            print("⚠️  Advertencia: Token o Chat ID de Telegram no configurados")
    
    def __enviar_peticion(self, metodo: str, datos: dict) -> dict:
        """
        Método privado para enviar peticiones a la API de Telegram
        
        Args:
            metodo (str): Método de la API (sendMessage, sendDocument, etc.)
            datos (dict): Datos a enviar en la petición
            
        Returns:
            dict: Respuesta de la API
        """
        if not self.token:
            raise Exception("❌ Token de Telegram no configurado")
            
        url = f"{self.api_url}{self.token}/{metodo}"
        
        try:
            response = post(url, data=datos, timeout=30)
            response.raise_for_status()
            return response.json()
        except exceptions.RequestException as e:
            raise Exception(f"❌ Error en petición a Telegram: {str(e)}")
    
    def enviar_mensaje(self, mensaje: str, formato: str = 'HTML', silencioso: bool = False):
        """
        Envía un mensaje de texto a Telegram
        
        Args:
            mensaje (str): Texto del mensaje a enviar
            formato (str): Formato del mensaje ('HTML' o 'Markdown')
            silencioso (bool): True para enviar sin notificación sonora
            
        Returns:
            dict: Respuesta de la API
        """
        if not self.chat_id:  
            raise Exception("❌ Chat ID de Telegram no configurado")
        
        datos = {
            'chat_id': self.chat_id,  
            'text': mensaje,
            'parse_mode': formato,
            'disable_notification': silencioso
        }
        
        try:
            respuesta = self.__enviar_peticion('sendMessage', datos)
            if hasattr(self.config, 'log'):
                self.config.log.comentario("SUCCESS", "✅ Mensaje de Telegram enviado")
            else:
                print("✅ Mensaje de Telegram enviado exitosamente")
            return respuesta
        except Exception as e:
            if hasattr(self.config, 'log'):
                self.config.log.error(f"Error enviando mensaje a Telegram: {str(e)}", "Telegram")
            else:
                print(f"❌ Error enviando mensaje a Telegram: {str(e)}")
            return None
    
    def enviar_documento(self, ruta_archivo: str, caption: str = None):
        """
        Envía un documento/archivo a Telegram
        
        Args:
            ruta_archivo (str): Ruta del archivo a enviar
            caption (str): Texto descriptivo del archivo
            
        Returns:
            dict: Respuesta de la API
        """
        if not self.chat_id:  
            raise Exception("❌ Chat ID de Telegram no configurado")
        
        url = f"{self.api_url}{self.token}/sendDocument"
        
        try:
            with open(ruta_archivo, 'rb') as archivo:
                files = {'document': archivo}
                datos = {'chat_id': self.chat_id}  
                
                if caption:
                    datos['caption'] = caption
                
                response = post(url, data=datos, files=files, timeout=60)
                response.raise_for_status()
                
                if hasattr(self.config, 'log'):
                    self.config.log.comentario("SUCCESS", f"✅ Documento enviado: {ruta_archivo}")
                else:
                    print(f"✅ Documento enviado a Telegram: {ruta_archivo}")
                    
                return response.json()
                
        except FileNotFoundError:
            if hasattr(self.config, 'log'):
                self.config.log.error(f"Archivo no encontrado: {ruta_archivo}", "Telegram")
            else:
                print(f"❌ Archivo no encontrado: {ruta_archivo}")
            return None
        except Exception as e:
            if hasattr(self.config, 'log'):
                self.config.log.error(f"Error enviando documento: {str(e)}", "Telegram")
            else:
                print(f"❌ Error enviando documento: {str(e)}")
            return None
    
    def enviar_foto(self, ruta_foto: str, caption: str = None):
        """
        Envía una foto a Telegram
        
        Args:
            ruta_foto (str): Ruta de la foto a enviar
            caption (str): Texto descriptivo de la foto
            
        Returns:
            dict: Respuesta de la API
        """
        if not self.chat_id:  
            raise Exception("❌ Chat ID de Telegram no configurado")
        
        url = f"{self.api_url}{self.token}/sendPhoto"
        
        try:
            with open(ruta_foto, 'rb') as foto:
                files = {'photo': foto}
                datos = {'chat_id': self.chat_id}  
                
                if caption:
                    datos['caption'] = caption
                
                response = post(url, data=datos, files=files, timeout=60)
                response.raise_for_status()
                
                if hasattr(self.config, 'log'):
                    self.config.log.comentario("SUCCESS", f"✅ Foto enviada: {ruta_foto}")
                else:
                    print(f"✅ Foto enviada a Telegram: {ruta_foto}")
                    
                return response.json()
        except Exception as e:
            if hasattr(self.config, 'log'):
                self.config.log.error(f"Error enviando foto: {str(e)}", "Telegram")
            else:
                print(f"❌ Error enviando foto: {str(e)}")
            return None
    
    def notificar_exito(self, mensaje: str):
        """Envía una notificación de éxito con emoji ✅"""
        return self.enviar_mensaje(f"✅ {mensaje}")
    
    def notificar_error(self, mensaje: str):
        """Envía una notificación de error con emoji ❌"""
        return self.enviar_mensaje(f"❌ {mensaje}")
    
    def notificar_advertencia(self, mensaje: str):
        """Envía una notificación de advertencia con emoji ⚠️"""
        return self.enviar_mensaje(f"⚠️ {mensaje}")
    
    def notificar_info(self, mensaje: str):
        """Envía una notificación informativa con emoji ℹ️"""
        return self.enviar_mensaje(f"ℹ️ {mensaje}")
    
    def notificar_proceso_completado(self, nombre_proceso: str, detalles: str = None):
        """
        Notifica que un proceso ha sido completado
        
        Args:
            nombre_proceso (str): Nombre del proceso completado
            detalles (str): Detalles adicionales del proceso
        """
        mensaje = f"✅ **{nombre_proceso}** completado exitosamente"
        if detalles:
            mensaje += f"\n📋 {detalles}"
        return self.enviar_mensaje(mensaje, formato='Markdown')
    
    def enviar_notificacion_scraper(self, urls: list, error: bool = False):
        """
        Versión adaptada del método EjecutarEnvioCorreo pero para Telegram
        
        Args:
            urls (list): Lista de URLs de los documentos
            error (bool): True si hay error, False si todo OK
        """
        if not error:
            # Nombres de los documentos
            nombres = ["Acta", "Certificado", "Notas"]
            
            # Crear mensaje con los enlaces
            mensaje = "📄 **Documentos generados:**\n\n"
            
            for i, url in enumerate(urls):
                if i < len(nombres):
                    mensaje += f"• *{nombres[i]}*: [Descargar]({url})\n"
            
            mensaje += "\n✅ Scraper completado exitosamente"
            
            self.enviar_mensaje(mensaje, formato='Markdown')
        else:
            mensaje = "❌ **Error en el scraper**\n\nAún no se ha generado certificado"
            self.enviar_mensaje(mensaje, formato='Markdown')