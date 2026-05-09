from html import escape

class Template:

    def __init__(self, config, dict):
        self.config = config
        self.data = dict

    def _safe(self, value: str) -> str:
        return escape(value or "")

    def _get_icon_class(self, icon_type: str) -> str:
        """Retorna la clase de FontAwesome para cada tipo de producto"""
        icons = {
            'cleanser': 'fa-soap',
            'toner': 'fa-spray-can',
            'serum': 'fa-droplet',
            'moisturizer': 'fa-jar',
            'sunscreen': 'fa-sun',
            'mask': 'fa-mask-face',
            'double_cleanse': 'fa-pump-soap',
            'treatment': 'fa-flask'
        }
        return icons.get(icon_type, 'fa-soap')

    def _build_step(self, number: int, title: str, description: str, icon_type: str, primary_color: str, extra_info: str = "", is_placeholder: bool = False) -> str:
        """Construye un paso con altura fija para alineación perfecta de filas"""
        if is_placeholder or (not title and not description):
            # Div vacío con la misma altura mínima para mantener la alineación de filas
            return f'<div class="min-h-[85px] w-full"></div>'

        icon_class = self._get_icon_class(icon_type)
        extra_html = f'''<div class="text-xs mt-1 font-medium" style="color: {primary_color};">
            {self._safe(extra_info)}
        </div>''' if extra_info else ""
        
        return f'''
        <div class="flex items-center gap-3 min-h-[85px] w-full py-1">
            <div class="flex-shrink-0 relative">
                <i class="fa-solid {icon_class}" style="color: {primary_color}; opacity: 0.85; font-size: 1.75rem;"></i>
                <div class="absolute -bottom-1.5 -right-1.5 w-5 h-5 rounded-full flex items-center justify-center text-white text-[10px] font-bold shadow-sm" 
                     style="background-color: {primary_color};">
                    {number}
                </div>
            </div>
            <div class="flex-1 flex flex-col justify-center">
                <h4 class="font-semibold text-gray-800 text-sm leading-tight">
                    {self._safe(title)}
                </h4>
                <p class="text-gray-600 text-xs leading-relaxed mt-0.5">
                    {self._safe(description)}
                </p>
                {extra_html}
            </div>
        </div>
        '''

    def _build_extra_section(self, title: str, items: list, primary_color: str) -> str:
        """Construye la sección Extra"""
        if not items:
            return ""
            
        items_html = ""
        for item in items:
            items_html += f'''
            <div class="flex items-start gap-2 mt-2">
                <div class="w-1.5 h-1.5 rounded-full flex-shrink-0 mt-1.5" style="background-color: {primary_color};"></div>
                <p class="text-gray-600 text-xs">{self._safe(item)}</p>
            </div>
            '''
        
        return f'''
        <div class="mt-6 pt-4 border-t border-dashed" style="border-color: {primary_color}; opacity: 0.8;">
            <p class="text-xs font-semibold mb-2 flex items-center gap-1.5" style="color: {primary_color};">
                <span>✨</span>
                <span>{self._safe(title)}</span>
            </p>
            {items_html}
        </div>
        '''

    def render(self) -> str:
        titulo = self._safe(self.data.get("titulo", ""))
        subtitle = self._safe(self.data.get("subtitle", "Controla el brillo y equilibra tu piel"))
        manana_steps = self.data.get("manana", [])
        noche_steps = self.data.get("noche", [])
        extra_manana = self.data.get("extra_manana", [])
        extra_noche = self.data.get("extra_noche", [])

        font = self.config.template.font_family
        primary = self.config.template.primary_color
        bg = self.config.template.background_color

        # 1. Calcular máximo de pasos para alinear filas
        max_steps = max(len(manana_steps), len(noche_steps), 1)
        placeholder = {"title": "", "description": "", "icon": "", "extra_info": ""}
        
        manana_padded = manana_steps + [placeholder.copy() for _ in range(max_steps - len(manana_steps))]
        noche_padded = noche_steps + [placeholder.copy() for _ in range(max_steps - len(noche_steps))]

        # 2. Construir HTML de pasos
        manana_html = ""
        for i, step in enumerate(manana_padded, 1):
            is_placeholder = not step.get("title") and not step.get("description")
            manana_html += self._build_step(
                number=i,
                title=step.get("title", ""),
                description=step.get("description", ""),
                icon_type=step.get("icon", "cleanser"),
                primary_color=primary,
                extra_info=step.get("extra_info", ""),
                is_placeholder=is_placeholder
            )

        noche_html = ""
        for i, step in enumerate(noche_padded, 1):
            is_placeholder = not step.get("title") and not step.get("description")
            noche_html += self._build_step(
                number=i,
                title=step.get("title", ""),
                description=step.get("description", ""),
                icon_type=step.get("icon", "cleanser"),
                primary_color=primary,
                extra_info=step.get("extra_info", ""),
                is_placeholder=is_placeholder
            )

        # 3. Secciones Extra (independientes y condicionales)
        has_extra_manana = bool(extra_manana)
        has_extra_noche = bool(extra_noche)
        extra_manana_html = self._build_extra_section("Extra Mañana (2 veces por semana)", extra_manana, primary) if has_extra_manana else ""
        extra_noche_html = self._build_extra_section("Extra Noche (2 veces por semana)", extra_noche, primary) if has_extra_noche else ""

        # Grid condicional para extras - CORREGIDO PARA CENTRADO
        if has_extra_manana and has_extra_noche:
            extras_html = f"""
            <div class="grid md:grid-cols-2 gap-8 md:gap-12 mt-8">
                <div>{extra_manana_html}</div>
                <div>{extra_noche_html}</div>
            </div>
            """
        elif has_extra_manana:
            extras_html = f"""
            <div class="flex justify-center mt-8">
                <div class="max-w-2xl mx-auto">{extra_manana_html}</div>
            </div>
            """
        elif has_extra_noche:
            extras_html = f"""
            <div class="flex justify-center mt-8">
                <div class="max-w-2xl mx-auto">{extra_noche_html}</div>
            </div>
            """
        else:
            extras_html = ""

        html = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <script src="https://cdn.tailwindcss.com"></script>
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
            <link href="https://fonts.googleapis.com/css2?family={font}:wght@300;400;500;600;700&display=swap" rel="stylesheet">
            <style>
                body {{ font-family: '{font}', sans-serif; }}
            </style>
        </head>

        <body class="p-4 md:p-8 min-h-screen flex items-center justify-center" style="background-color: {bg};">
            <div class="w-full max-w-4xl bg-white rounded-3xl shadow-xl overflow-hidden">
                
                <!-- Header -->
                <div class="text-center pt-8 pb-6 px-6" style="background: linear-gradient(135deg, {primary}10 0%, {primary}05 100%);">
                    <div class="inline-flex items-center gap-2 px-5 py-2 rounded-full mb-4" 
                         style="background-color: {primary}; opacity: 0.90;">
                        <span class="text-xl">💧</span>
                        <span class="font-semibold text-sm tracking-wide">RUTINA DE CUIDADO FACIAL</span>
                    </div>
                    <h1 class="text-4xl md:text-5xl font-bold mb-3" style="color: {primary};">
                        {titulo}
                    </h1>
                    <p class="text-gray-500 text-sm md:text-base font-light">
                        {subtitle} <span class="text-amber-400">✨</span>
                    </p>
                </div>

                <!-- Main Steps Grid (Siempre 2 columnas) -->
                <div class="p-6 md:p-10">
                    <div class="grid md:grid-cols-2 gap-8 md:gap-12" style="opacity: 0.85;">
                        <!-- Mañana -->
                        <div>
                            <div class="flex items-center gap-3 mb-4 pb-3 border-b-2" style="border-color: {primary};">
                                <div class="text-3xl">☀️</div>
                                <h2 class="text-2xl font-bold" style="color: {primary};">Mañana</h2>
                            </div>
                            <div class="flex flex-col gap-1">
                                {manana_html}
                            </div>
                        </div>

                        <!-- Noche -->
                        <div>
                            <div class="flex items-center gap-3 mb-4 pb-3 border-b-2" style="border-color: {primary};">
                                <div class="text-3xl">🌙</div>
                                <h2 class="text-2xl font-bold" style="color: {primary};">Noche</h2>
                            </div>
                            <div class="flex flex-col gap-1">
                                {noche_html}
                            </div>
                        </div>
                    </div>

                    <!-- Extras Section (Condicional) -->
                    {extras_html}
                </div>

                <!-- Footer -->
                <div class="h-2 w-full" style="background: linear-gradient(90deg, {primary} 0%, {primary}80 50%, {primary} 100%);"></div>
            </div>
        </body>
        </html>
        """
        return html