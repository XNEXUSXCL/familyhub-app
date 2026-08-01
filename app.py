import streamlit as st
import os
import datetime
import time
from dotenv import load_dotenv
from supabase import create_client, Client
from google import genai
from streamlit_calendar import calendar

# Cargar variables de entorno
load_dotenv()

# Inicializar Supabase e IA
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

try:
    client_ia = genai.Client()
except Exception:
    client_ia = None

# Configuración móvil
st.set_page_config(page_title="FamilyHub", page_icon="🏠", layout="centered")

st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .block-container { padding-top: 1rem; padding-bottom: 1rem; padding-left: 0.8rem; padding-right: 0.8rem; }
        .stButton>button { width: 100%; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- FUNCIÓN AUXILIAR PARA SUBIR ARCHIVOS ---
def subir_archivo_a_supabase(uploaded_file):
    if uploaded_file is not None:
        try:
            extension = uploaded_file.name.split(".")[-1]
            nombre_unico = f"{int(datetime.datetime.now().timestamp())}_{uploaded_file.name}"
            file_bytes = uploaded_file.read()
            
            supabase.storage.from_("archivos_familia").upload(
                path=nombre_unico,
                file=file_bytes,
                file_options={"content-type": uploaded_file.type}
            )
            
            url_publica = supabase.storage.from_("archivos_familia").get_public_url(nombre_unico)
            return url_publica, uploaded_file.name, uploaded_file.type
        except Exception as e:
            st.error(f"Error al subir archivo: {e}")
            return None, None, None
    return None, None, None

# --- CONTROL DE ACCESO ---
try:
    perfiles_db = supabase.table("perfiles_familia").select("*").order("nombre").execute().data
    lista_nombres = [p["nombre"] for p in perfiles_db]
except Exception:
    lista_nombres = []

if "usuario_activo" not in st.session_state:
    st.session_state.usuario_activo = None

if st.session_state.usuario_activo is None:
    st.title("🏠 Bienvenido a FamilyHub")
    tab1, tab2 = st.tabs(["🔑 Ingresar", "👤 Crear Perfil"])
    with tab1:
        if lista_nombres:
            usuario_sel = st.selectbox("Selecciona tu nombre:", lista_nombres)
            if st.button("Entrar a la App"):
                st.session_state.usuario_activo = usuario_sel
                st.rerun()
        else:
            st.info("Aún no hay perfiles creados.")
    with tab2:
        nuevo_nombre = st.text_input("Nombre / Apodo")
        fecha_nac = st.date_input("Fecha de Nacimiento", min_value=datetime.date(1950, 1, 1))
        num_tel = st.text_input("Número de Teléfono")
        correo_inst = st.text_input("Correo Electrónico")
        if st.button("Registrar Perfil"):
            if nuevo_nombre and nuevo_nombre not in lista_nombres:
                supabase.table("perfiles_familia").insert({"nombre": nuevo_nombre, "fecha_nacimiento": str(fecha_nac), "telefono": num_tel, "correo": correo_inst}).execute()
                st.session_state.usuario_activo = nuevo_nombre
                st.rerun()
    st.stop()

st.title("🏠 FamilyHub")

st.sidebar.title("Menú Principal")
st.sidebar.write(f"👤 Usuario: **{st.session_state.usuario_activo}**")
if st.sidebar.button("🔒 Cerrar Sesión"):
    st.session_state.usuario_activo = None
    st.rerun()

menu = st.sidebar.radio("Navegación", ["📅 Recordatorios", "✅ Tareas", "💬 Chat", "🤖 Asistente IA"])

# --- MÓDULO 1: RECORDATORIOS Y CALENDARIO CON CONTROL DE WHATSAPP ---
if menu == "📅 Recordatorios":
    st.header("📅 Calendario y Recordatorios")
    
    with st.expander("➕ Crear Nuevo Recordatorio"):
        titulo_evento = st.text_input("¿Qué evento o recordatorio es?")
        descripcion_evento = st.text_area("Detalles adicionales / Notas")
        
        archivo_adjunto_cal = st.file_uploader("Adjuntar información (Recetas médicas, invitaciones, pdfs)", key="file_cal")
        
        fecha_evento = st.date_input("Fecha", min_value=datetime.date.today())
        hora_evento = st.time_input("Hora")
        
        if st.button("Guardar Recordatorio"):
            if titulo_evento:
                url_archivo = "No"
                if archivo_adjunto_cal:
                    url_res, _, _ = subir_archivo_a_supabase(archivo_adjunto_cal)
                    if url_res:
                        url_archivo = url_res
                
                detalles_finales = f"{descripcion_evento}\n\n📎 Adjunto: {url_archivo}" if url_archivo != "No" else descripcion_evento
                
                data = {
                    "paciente": titulo_evento,
                    "doctor": detalles_finales if detalles_finales else "Sin descripción", 
                    "fecha": str(fecha_evento), 
                    "hora": str(hora_evento),
                    "notificacion_enviada": False  # Nueva marca para control de WhatsApp
                }
                supabase.table("citas_medicas").insert(data).execute()
                st.success("¡Recordatorio guardado! La alerta de WhatsApp quedó programada.")
                st.rerun()

    eventos_db = supabase.table("citas_medicas").select("*").execute().data
    calendar_events = [{"title": ev['paciente'], "start": f"{ev['fecha']}T{ev['hora']}"} for ev in eventos_db]
    calendar(events=calendar_events, options={"headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth,listWeek"}, "initialView": "dayGridMonth", "locale": "es"}, key="calendar_familiar")
    
    st.subheader("Lista de Próximos Eventos")
    citas_ordenadas = supabase.table("citas_medicas").select("*").order("fecha").execute().data
    for c in citas_ordenadas:
        with st.container(border=True):
            st.markdown(f"🔔 **{c['paciente']}**")
            st.code(f"📅 {c['fecha']} a las {c['hora'][:5]}")
            
            texto_desc = c['doctor']
            if "📎 Adjunto: " in texto_desc:
                partes = texto_desc.split("📎 Adjunto: ")
                st.write(partes[0])
                st.link_button("📂 Ver Documento Adjunto", partes[1])
            else:
                st.write(texto_desc)

# --- MÓDULO 2: TAREAS ---
elif menu == "✅ Tareas":
    st.header("✅ Tareas de la Casa")
    with st.expander("➕ Asignar nueva tarea"):
        desc = st.text_input("¿Qué hay que hacer?")
        asignado = st.selectbox("Asignar a:", ["Todos"] + lista_nombres)
        fecha_limite = st.date_input("Fecha límite")
        if st.button("Asignar Tarea"):
            if desc:
                supabase.table("tareas").insert({"descripcion": desc, "asignado_a": asignado, "fecha_limite": str(fecha_limite), "completada": False}).execute()
                st.success("Tarea asignada.")
                st.rerun()

    tareas = supabase.table("tareas").select("*").order("creado_en", desc=True).execute().data
    st.subheader("Pendientes")
    for t in [t for t in tareas if not t["completada"]]:
        col1, col2 = st.columns([0.75, 0.25])
        with col1: st.write(f"📌 **{t['descripcion']}**\n\n_Responsable: {t['asignado_a']}_ | Vence: {t['fecha_limite']}")
        with col2:
            if st.button("Listo", key=f"t_{t['id']}"):
                supabase.table("tareas").update({"completada": True}).eq("id", t["id"]).execute()
                st.rerun()
        st.divider()

# --- MÓDULO 3: CHAT FAMILIAR MULTIMEDIA ---
elif menu == "💬 Chat":
    st.header("💬 Sala de Chat")
    
    with st.expander("📸 Enviar Foto, Video, Audio o Documento"):
        archivo_chat = st.file_uploader("Elige un archivo de tu galería o cámara", key="file_chat_input")
        if st.button("Enviar archivo al chat"):
            if archivo_chat:
                with st.spinner("Subiendo archivo..."):
                    url_file, name_file, type_file = subir_archivo_a_supabase(archivo_chat)
                    if url_file:
                        contenido_mensaje = f"MEDIA_FILE|{type_file}|{url_file}|{name_file}"
                        supabase.table("chat_familiar").insert({"autor": st.session_state.usuario_activo, "mensaje": contenido_mensaje}).execute()
                        st.success("¡Archivo enviado!")
                        st.rerun()

    mensajes = supabase.table("chat_familiar").select("*").order("creado_en", desc=False).limit(50).execute().data
    
    for m in mensajes:
        es_propio = m["autor"] == st.session_state.usuario_activo
        with st.chat_message("user" if es_propio else "assistant"):
            st.write(f"**{m['autor']}:**")
            
            if str(m["mensaje"]).startswith("MEDIA_FILE|"):
                _, tipo, url_adjunta, nombre_adjunto = m["mensaje"].split("|")
                
                if tipo.startswith("image/"):
                    st.image(url_adjunta, caption=nombre_adjunto, use_container_width=True)
                elif tipo.startswith("video/"):
                    st.video(url_adjunta)
                elif tipo.startswith("audio/"):
                    st.audio(url_adjunta)
                else:
                    st.link_button(f"📄 Descargar {nombre_adjunto}", url_adjunta)
            else:
                st.write(m["mensaje"])

    nuevo_msg = st.chat_input("Escribe un mensaje de texto...")
    if nuevo_msg:
        supabase.table("chat_familiar").insert({"autor": st.session_state.usuario_activo, "mensaje": nuevo_msg}).execute()
        st.rerun()

# --- MÓDULO 4: ASISTENTE IA ---
elif menu == "🤖 Asistente IA":
    st.header("🤖 Asistente Inteligente")
    st.write("Analizo la información familiar para responder tus dudas.")
    
    with st.form(key="formulario_ia"):
        pregunta = st.text_input("¿Qué deseas consultar o planificar?")
        boton_enviar = st.form_submit_button(label="Consultar a la IA")
    
    if boton_enviar and pregunta:
        if not client_ia:
            st.error("API Key de Gemini no configurada.")
        else:
            citas_db = supabase.table("citas_medicas").select("paciente,fecha,hora").order("fecha").limit(5).execute().data
            tareas_db = supabase.table("tareas").select("descripcion,asignado_a").eq("completada", False).limit(5).execute().data
            
            contexto = f"Eres el asistente del hogar de la familia de Alan. Agenda: {citas_db}. Tareas: {tareas_db}. Responde conciso."
            
            respuesta_texto = None
            
            with st.spinner("Conectando con la Inteligencia Artificial..."):
                for intento in range(3):
                    try:
                        response = client_ia.models.generate_content(
                            model='gemini-2.0-flash', 
                            contents=[contexto, pregunta]
                        )
                        respuesta_texto = response.text
                        break
                    except Exception as e:
                        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                            time.sleep(3)
                        else:
                            st.error(f"Error de conexión: {e}")
                            break
            
            if respuesta_texto:
                st.chat_message("assistant").write(respuesta_texto)
            else:
                st.info("💡 La API Key de AI Studio está saturada temporalmente. Aquí tienes los datos directos:")
                st.markdown("### 📅 Próximos Eventos")
                if citas_db:
                    for c in citas_db: st.write(f"• **{c['paciente']}** - {c['fecha']} a las {c['hora'][:5]}")
                st.markdown("### ✅ Tareas Pendientes")
                if tareas_db:
                    for t in tareas_db: st.write(f"• {t['descripcion']} ({t['asignado_a']})")