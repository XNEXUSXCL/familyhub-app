import streamlit as st
import os
import datetime
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

# Estilos CSS
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
            padding-left: 0.8rem;
            padding-right: 0.8rem;
        }
        .stButton>button {
            width: 100%;
            border-radius: 10px;
        }
    </style>
""", unsafe_allow_html=True)

# --- SISTEMA DE PERFILES Y LOGIN ---
# Consultar los perfiles creados en la base de datos
try:
    perfiles_db = supabase.table("perfiles_familia").select("*").order("nombre").execute().data
    lista_nombres = [p["nombre"] for p in perfiles_db]
except Exception:
    lista_nombres = []

if "usuario_activo" not in st.session_state:
    st.session_state.usuario_activo = None

# Si no hay ningún usuario seleccionado, mostramos la pantalla de acceso/registro
if st.session_state.usuario_activo is None:
    st.title("🏠 Bienvenido a FamilyHub")
    st.write("Por favor, selecciona tu perfil o crea uno nuevo para ingresar.")
    
    tab1, tab2 = st.tabs(["🔑 Ingresar", "👤 Crear Perfil"])
    
    with tab1:
        if lista_nombres:
            usuario_sel = st.selectbox("Selecciona tu nombre:", lista_nombres)
            if st.button("Entrar a la App"):
                st.session_state.usuario_activo = usuario_sel
                st.rerun()
        else:
            st.info("Aún no hay perfiles creados. ¡Sé el primero en el registro!")
            
    with tab2:
        st.subheader("📝 Formulario de Registro")
        nuevo_nombre = st.text_input("Nombre / Apodo")
        fecha_nac = st.date_input("Fecha de Nacimiento", min_value=datetime.date(1950, 1, 1))
        num_tel = st.text_input("Número de Teléfono", placeholder="+569...")
        correo_inst = st.text_input("Correo Electrónico")
        
        if st.button("Registrar Perfil"):
            if nuevo_nombre:
                if nuevo_nombre in lista_nombres:
                    st.error("Este nombre ya está registrado.")
                else:
                    nuevo_perfil = {
                        "nombre": nuevo_nombre,
                        "fecha_nacimiento": str(fecha_nac),
                        "telefono": num_tel,
                        "correo": correo_inst
                    }
                    supabase.table("perfiles_familia").insert(nuevo_perfil).execute()
                    st.success(f"¡Perfil de {nuevo_nombre} creado con éxito!")
                    st.session_state.usuario_activo = nuevo_nombre
                    st.rerun()
            else:
                st.error("El campo 'Nombre' es obligatorio.")
    st.stop() # Frena la carga del resto de la app hasta que se identifique

# --- SI YA ESTÁ LOGUEADO, CARGA LA APP COMPLETA ---
st.title("🏠 FamilyHub")

# Barra de navegación lateral
st.sidebar.title("Menú Principal")
st.sidebar.write(f"👤 Usuario: **{st.session_state.usuario_activo}**")
if st.sidebar.button("🔒 Cerrar Sesión / Cambiar Perfil"):
    st.session_state.usuario_activo = None
    st.rerun()

menu = st.sidebar.radio("Navegación", ["📅 Recordatorios y Calendario", "✅ Tareas", "💬 Chat", "🤖 Asistente IA"])

# --- MÓDULO 1: RECORDATORIOS Y CALENDARIO ---
if menu == "📅 Recordatorios y Calendario":
    st.header("📅 Calendario y Recordatorios")
    
    with st.expander("➕ Crear Nuevo Recordatorio"):
        titulo_evento = st.text_input("¿Qué evento o recordatorio es?", placeholder="Ej: Cumpleaños, Dentista Alansito, Taller Antonia")
        descripcion_evento = st.text_area("Detalles adicionales")
        fecha_evento = st.date_input("Fecha", min_value=datetime.date.today())
        hora_evento = st.time_input("Hora")
        
        if st.button("Guardar Recordatorio"):
            if titulo_evento:
                data = {
                    "paciente": titulo_evento,
                    "doctor": descripcion_evento if descripcion_evento else "Sin descripción", 
                    "fecha": str(fecha_evento), 
                    "hora": str(hora_evento)
                }
                supabase.table("citas_medicas").insert(data).execute()
                st.success("¡Recordatorio guardado!")
                st.rerun()

    eventos_db = supabase.table("citas_medicas").select("*").execute().data
    calendar_events = []
    for ev in eventos_db:
        calendar_events.append({
            "title": ev['paciente'],
            "start": f"{ev['fecha']}T{ev['hora']}",
            "description": ev['doctor']
        })

    calendar_options = {
        "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth,listWeek"},
        "initialView": "dayGridMonth",
        "locale": "es"
    }
    
    st.subheader("Vista Mensual / Semanal")
    calendar(events=calendar_events, options=calendar_options, key="calendar_familiar")
    
    st.subheader("Lista de Próximos Eventos")
    citas_ordenadas = supabase.table("citas_medicas").select("*").order("fecha").execute().data
    for c in citas_ordenadas:
        with st.container(border=True):
            st.markdown(f"🔔 **{c['paciente']}**")
            if c['doctor'] != "Sin descripción":
                st.caption(f"📝 {c['doctor']}")
            st.code(f"📅 {c['fecha']} a las {c['hora'][:5]}")

# --- MÓDULO 2: TAREAS ---
elif menu == "✅ Tareas":
    st.header("✅ Tareas de la Casa")
    
    with st.expander("➕ Asignar nueva tarea"):
        desc = st.text_input("¿Qué hay que hacer?")
        # Opciones de asignación dinámicas basadas en los perfiles reales
        opciones_asignacion = ["Todos"] + lista_nombres
        asignado = st.selectbox("Asignar a:", opciones_asignacion)
        fecha_limite = st.date_input("Fecha límite")
        
        if st.button("Asignar Tarea"):
            if desc:
                data = {"descripcion": desc, "asignado_a": asignado, "fecha_limite": str(fecha_limite), "completada": False}
                supabase.table("tareas").insert(data).execute()
                st.success("Tarea asignada.")
                st.rerun()

    tareas = supabase.table("tareas").select("*").order("creado_en", desc=True).execute().data
    
    st.subheader("Pendientes")
    pendientes = [t for t in tareas if not t["completada"]]
    if not pendientes:
        st.write("🎉 ¡No hay tareas pendientes!")
    for t in pendientes:
        col1, col2 = st.columns([0.75, 0.25])
        with col1:
            st.write(f"📌 **{t['descripcion']}**\n\n_Responsable: {t['asignado_a']}_ | Vence: {t['fecha_limite']}")
        with col2:
            if st.button("Listo", key=f"t_{t['id']}"):
                supabase.table("tareas").update({"completada": True}).eq("id", t["id"]).execute()
                st.rerun()
        st.divider()

# --- MÓDULO 3: CHAT FAMILIAR ---
elif menu == "💬 Chat":
    st.header("💬 Sala de Chat")
    mensajes = supabase.table("chat_familiar").select("*").order("creado_en", desc=False).limit(50).execute().data
    
    for m in mensajes:
        # Si el autor del mensaje es el usuario actual, se muestra a la derecha
        es_propio = m["autor"] == st.session_state.usuario_activo
        with st.chat_message("user" if es_propio else "assistant"):
            st.write(f"**{m['autor']}**: {m['mensaje']}")

    nuevo_msg = st.chat_input("Escribe un mensaje para la familia...")
    if nuevo_msg:
        data = {"autor": st.session_state.usuario_activo, "mensaje": nuevo_msg}
        supabase.table("chat_familiar").insert(data).execute()
        st.rerun()

# --- MÓDULO 4: ASISTENTE IA ---
elif menu == "🤖 Asistente IA":
    st.header("🤖 Asistente Inteligente")
    st.write("Analizo la información familiar para responder tus dudas.")
    
    pregunta = st.text_input("¿Qué deseas consultar o planificar?")
    
    if pregunta:
        if not client_ia:
            st.error("API Key de Gemini no configurada.")
        else:
            citas_ctx = supabase.table("citas_medicas").select("*").execute().data
            tareas_ctx = supabase.table("tareas").select("*").eq("completada", False).execute().data
            chat_ctx = supabase.table("chat_familiar").select("*").order("creado_en", desc=True).limit(15).execute().data
            perfiles_ctx = lista_nombres
            
            contexto = f"""
            Eres el asistente inteligente de este hogar. Tienes acceso a:
            - Miembros de la familia registrados: {perfiles_ctx}
            - Agenda de recordatorios y eventos: {citas_ctx}
            - Tareas domésticas pendientes: {tareas_ctx}
            - Últimos mensajes del chat: {chat_ctx}
            
            Ayuda a quien consulta de forma clara y familiar.
            """
            
            with st.spinner("Buscando en los registros domésticos..."):
                response = client_ia.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[contexto, pregunta]
                )
                st.chat_message("assistant").write(response.text)