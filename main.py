import streamlit as st
from pathlib import Path
from classifier import clasificar_llamada_banco, client

# 1. Control de navegación en memoria de Streamlit
if "vista_actual" not in st.session_state:
    st.session_state.vista_actual = "HOME"

# Función RAG integrada para contestar automáticamente usando el .txt
def responder_con_rag(consulta_cliente, nombre_txt="FAQs_Asistente_Bancario_Mavericks.txt"):
    # Si tu compañero del RAG sube su archivo (ej. rag_agent.py), podéis importarlo aquí.
    # Mientras tanto, este bloque contesta automáticamente leyendo el .txt oficial del equipo:
    ruta = Path(__file__).parent / nombre_txt
    contexto_faqs = ruta.read_text(encoding="utf-8")
    
    prompt_rag = f"""
    Eres el asistente virtual de información bancaria del equipo Mavericks.
    Responde a la duda del cliente basándote ÚNICAMENTE en la siguiente base de conocimiento oficial:
    
    {contexto_faqs}
    
    Reglas:
    - Da una respuesta clara, amable y precisa basada en el campo RESPUESTA del documento.
    - Menciona la fuente oficial si aparece en FUENTES.
    - No inventes condiciones comerciales ni pidas claves o datos confidenciales.
    """
    
    respuesta = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {"role": "system", "content": prompt_rag},
            {"role": "user", "content": consulta_cliente}
        ],
        temperature=0.1
    )
    return respuesta.choices[0].message.content


# =========================================================
# RAMA 1: REDIRECCIÓN AL SIMULADOR DE HIPOTECAS
# =========================================================
if st.session_state.vista_actual == "HIPOTECAS":
    # Cargamos y ejecutamos mortage_simulator.py de tu compañero
    ruta_simulador = Path(__file__).parent / "mortage_simulator.py"
    codigo_simulador = ruta_simulador.read_text(encoding="utf-8")
    exec(codigo_simulador, globals())
    
    st.divider()
    if st.button("⬅️ Volver al Asistente Principal"):
        st.session_state.vista_actual = "HOME"
        st.rerun()


# =========================================================
# PANTALLA PRINCIPAL: CLASIFICADOR + RAG + HUMANO
# =========================================================
else:
    st.set_page_config(
        page_title="Contact Center Bancario - Mavericks",
        layout="centered"
    )

    st.title("🏦 Asistente Bancario Inteligente")
    st.write("Cuéntanos en qué podemos ayudarte y te atenderemos al instante.")

    consulta_usuario = st.text_area(
        "Escribe tu consulta aquí:",
        placeholder="Ej: Quiero calcular la cuota de una hipoteca / ¿Qué diferencia hay entre TIN y TAE? / He perdido mi tarjeta...",
        height=110
    )

    if st.button("Enviar consulta", type="primary", use_container_width=True):
        if not consulta_usuario.strip():
            st.warning("Por favor, escribe tu consulta antes de continuar.")
        else:
            with st.spinner("Analizando tu consulta..."):
                decision = clasificar_llamada_banco(consulta_usuario)
                categoria = decision.get("categoria")

            # --- ACCIÓN 1: HIPOTECAS -> Redirige a mortage_simulator.py ---
            if categoria == "HIPOTECAS":
                st.session_state.vista_actual = "HIPOTECAS"
                st.rerun()

            # --- ACCIÓN 2: FAQS -> Contesta automáticamente con el RAG ---
            elif categoria == "FAQS":
                st.success("✅ **Consulta informativa detectada (Agente RAG)**")
                with st.spinner("Consultando la base de conocimiento del banco..."):
                    respuesta_automatica = responder_con_rag(consulta_usuario)
                
                with st.container(border=True):
                    st.markdown("### Respuesta del Asistente:")
                    st.write(respuesta_automatica)
                    st.caption(f"Confianza del clasificador: {decision.get('confianza', 0)*100:.0f}%")

            # --- ACCIÓN 3: OTROS -> Deriva a un Agente Humano ---
            else:
                st.warning("👤 **Derivación a un Gestor Especializado**")
                with st.container(border=True):
                    st.write(
                        "Tu consulta requiere atención personalizada o urgente por parte de un "
                        "profesional de nuestra entidad para garantizar tu seguridad."
                    )
                    st.info(f"**Resumen de traspaso para el agente:** {decision.get('razonamiento_breve')}")
                    st.caption("Estado: Preparando transferencia a agente disponible (sin almacenar datos sensibles).")