# --- MÓDULO 4: ASISTENTE IA OPTIMIZADO Y PROTEGIDO ---
elif menu == "🤖 Asistente IA":
    st.header("🤖 Asistente Inteligente")
    st.write("Analizo la información familiar para responder tus dudas.")
    
    # Usamos un formulario para evitar que la app llame a la API con cada letra que escribes
    with st.form(key="formulario_ia"):
        pregunta = st.text_input("¿Qué deseas consultar o planificar?")
        boton_enviar = st.form_submit_button(label="Consultar a la IA")
    
    if boton_enviar and pregunta:
        if not client_ia:
            st.error("API Key de Gemini no configurada.")
        else:
            citas_ctx = supabase.table("citas_medicas").select("*").execute().data
            tareas_ctx = supabase.table("tareas").select("*").eq("completada", False).execute().data
            chat_ctx = supabase.table("chat_familiar").select("*").order("creado_en", desc=True).limit(15).execute().data
            
            contexto = f"""
            Eres el asistente inteligente de este hogar. Tienes acceso a:
            - Agenda de recordatorios y eventos: {citas_ctx}
            - Tareas domésticas pendientes: {tareas_ctx}
            - Últimos mensajes del chat: {chat_ctx}
            
            Ayuda a quien consulta de forma clara, directa y familiar.
            """
            
            with st.spinner("Buscando en los registros domésticos..."):
                try:
                    # Llamada protegida al modelo gemini-2.0-flash
                    response = client_ia.models.generate_content(
                        model='gemini-2.0-flash', 
                        contents=[contexto, pregunta]
                    )
                    st.chat_message("assistant").write(response.text)
                except Exception as e:
                    # Si se agota la cuota gratuita, evitamos que la app se caiga en rojo
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                        st.warning("⚠️ La IA está recibiendo muchas preguntas seguidas. Por favor, espera unos 10 segundos antes de volver a consultar.")
                    else:
                        st.error(f"Hubo un inconveniente al conectar con la IA: {e}")