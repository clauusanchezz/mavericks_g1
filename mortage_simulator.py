
import base64
from pathlib import Path

import streamlit as st


# ==================================================
# 1. CONFIGURACIÓN
# ==================================================

st.set_page_config(
    page_title="Simulador de Hipotecas",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ==================================================
# 2. CÁLCULO DE LA HIPOTECA
# ==================================================

def calcular_hipoteca(importe, interes_anual, años):
    """
    Calcula la cuota mensual de una hipoteca a tipo fijo.

    importe: cantidad del préstamo en euros
    interes_anual: tipo de interés anual en porcentaje
    años: duración del préstamo en años
    """

    if importe <= 0:
        raise ValueError("El importe debe ser positivo.")

    if interes_anual < 0:
        raise ValueError("El interés no puede ser negativo.")

    if años <= 0:
        raise ValueError("La duración debe ser positiva.")

    interes_mensual = interes_anual / 100 / 12
    numero_cuotas = años * 12

    if interes_mensual == 0:
        cuota_mensual = importe / numero_cuotas
    else:
        cuota_mensual = (
            importe
            * interes_mensual
            / (
                1
                - (1 + interes_mensual) ** (-numero_cuotas)
            )
        )

    total_pagado = cuota_mensual * numero_cuotas
    intereses_totales = total_pagado - importe

    return {
        "cuota_mensual": cuota_mensual,
        "total_pagado": total_pagado,
        "intereses_totales": intereses_totales,
    }


# ==================================================
# 3. CARGA DE LA IMAGEN DE FONDO
# ==================================================

RUTA_FONDO = (
    Path(__file__).parent
    / "assets"
    / "foto_familiar.jpeg"
)


def cargar_fondo(ruta):
    """Carga la imagen y la convierte a formato Base64."""

    if not ruta.exists():
        return None

    with open(ruta, "rb") as archivo:
        imagen = base64.b64encode(
            archivo.read()
        ).decode("utf-8")

    extension = ruta.suffix.lower()

    formatos = {
        ".jpg": "jpeg",
        ".jpeg": "jpeg",
        ".png": "png",
        ".webp": "webp",
    }

    formato = formatos.get(extension)

    if formato is None:
        return None

    return f"data:image/{formato};base64,{imagen}"


fondo = cargar_fondo(RUTA_FONDO)

if fondo:
    fondo_css = f"""
        background-image:
            linear-gradient(
                rgba(255, 255, 255, 0.78),
                rgba(255, 255, 255, 0.78)
            ),
            url("{fondo}");
    """
else:
    fondo_css = """
        background:
            linear-gradient(
                135deg,
                #edf3f8,
                #ffffff
            );
    """


# ==================================================
# 4. ESTILOS VISUALES
# ==================================================

st.markdown(
    f"""
    <style>
    /* Fondo de la aplicación */
    [data-testid="stAppViewContainer"] {{
        {fondo_css}
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}

    /* Cabecera transparente */
    [data-testid="stHeader"] {{
        background: transparent;
    }}

    /* Ocultar menú y pie */
    #MainMenu,
    footer {{
        visibility: hidden;
    }}

    /* Contenedor principal */
    .block-container {{
        max-width: 1000px;
        padding-top: 3rem;
        padding-bottom: 3rem;
    }}

    /* Tarjeta principal */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background: rgba(255, 255, 255, 0.94);
        border: 1px solid rgba(255, 255, 255, 0.85);
        border-radius: 18px;
        padding: 1.8rem 2rem;
        box-shadow: 0 8px 32px rgba(30, 50, 70, 0.10);
    }}

    /* Títulos */
    h1, h2, h3 {{
        color: #20364f;
    }}

    h1 {{
        font-size: 2.25rem;
        font-weight: 700;
    }}

    h2 {{
        font-size: 1.5rem;
        font-weight: 600;
    }}

    h3 {{
        font-size: 1.15rem;
        font-weight: 600;
    }}

    /* Etiquetas */
    [data-testid="stWidgetLabel"] p {{
        color: #35465b;
        font-weight: 500;
    }}

    /* Campos de entrada */
    div[data-baseweb="input"],
    div[data-baseweb="select"] > div {{
        background-color: rgba(255, 255, 255, 0.95);
        border-radius: 8px;
        border-color: #d8e1e9;
    }}

    /* Deslizador */
    [data-testid="stSlider"] {{
        padding-top: 0.5rem;
        padding-bottom: 0.5rem;
    }}

    /* Botón principal */
    div.stButton > button[kind="primary"] {{
        background-color: #285d89;
        color: white;
        border: none;
        border-radius: 8px;
        min-height: 3rem;
        font-weight: 600;
        width: 100%;
        transition: background-color 0.2s ease;
    }}

    div.stButton > button[kind="primary"]:hover {{
        background-color: #1d4568;
        border: none;
    }}

    /* Tarjetas de resultados */
    [data-testid="stMetric"] {{
        background: rgba(240, 246, 251, 0.90);
        border: 1px solid #e0eaf2;
        border-radius: 10px;
        padding: 1rem;
    }}

    /* Aviso de privacidad */
    .privacy-notice {{
        display: flex;
        align-items: flex-start;
        gap: 12px;
        background: rgba(237, 245, 250, 0.85);
        border: 1px solid #d8e6f0;
        border-radius: 10px;
        padding: 14px 16px;
        margin: 18px 0 22px 0;
        color: #35465b;
    }}

    .privacy-icon {{
        font-size: 20px;
        line-height: 1.4;
    }}

    .privacy-notice strong {{
        display: block;
        color: #20364f;
        font-size: 14px;
        margin-bottom: 4px;
    }}

    .privacy-notice p {{
        font-size: 13px;
        line-height: 1.5;
        margin: 0;
        color: #526579;
    }}

    /* Pantallas pequeñas */
    @media (max-width: 700px) {{
        .block-container {{
            padding: 1rem;
        }}

        div[data-testid="stVerticalBlockBorderWrapper"] {{
            padding: 1rem;
        }}

        h1 {{
            font-size: 1.8rem;
        }}
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ==================================================
# 5. INTERFAZ DEL SIMULADOR
# ==================================================

with st.container(border=True):

    st.title("Simulador de Hipotecas")

    st.write(
        "Introduce tus datos para calcular "
        "una estimación de tu hipoteca."
    )

    # Aviso de privacidad
    st.markdown(
        """
        <div class="privacy-notice">
            <span class="privacy-icon"></span>
            <div>
                <strong>Tu privacidad es importante</strong>
                <p>
                    La información facilitada se utilizará
                    para realizar esta simulación hipotecaria.
                    Trataremos tus datos de forma confidencial.
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    # ----------------------------------------------
    # Datos de la vivienda
    # ----------------------------------------------

    st.subheader("Datos de la vivienda")

    col1, col2 = st.columns(2)

    with col1:
        precio_vivienda = st.number_input(
            "¿Cuál es el precio de la vivienda? (€)",
            min_value=10000,
            max_value=5000000,
            value=250000,
            step=5000,
        )

    with col2:
        ahorro = st.number_input(
            "¿Cuál es el máximo ahorro que puedes aportar? (€)",
            min_value=0,
            max_value=5000000,
            value=50000,
            step=1000,
        )

    # ----------------------------------------------
    # Situación personal y económica
    # ----------------------------------------------

    st.subheader("Situación personal y económica")

    col3, col4 = st.columns(2)

    with col3:
        situacion_laboral = st.selectbox(
            "¿Cuál es tu situación laboral?",
            [
                "Contrato indefinido",
                "Contrato temporal",
                "Funcionario/a",
                "Autónomo/a",
                "Desempleado/a",
                "Estudiante",
                "Jubilado/a",
                "Otra situación",
            ],
        )

    with col4:
        ingresos_familiares = st.number_input(
            "Ingresos netos mensuales de la unidad familiar (€)",
            min_value=0,
            max_value=100000,
            value=3000,
            step=100,
        )

    # ----------------------------------------------
    # Condiciones de la hipoteca
    # ----------------------------------------------

    st.subheader("Condiciones de la hipoteca")

    col5, col6 = st.columns(2)

    with col5:
        años = st.slider(
            "Duración de la hipoteca (años)",
            min_value=5,
            max_value=40,
            value=25,
        )

    with col6:
        interes_anual = st.number_input(
            "Tipo de interés anual (%)",
            min_value=0.0,
            max_value=20.0,
            value=3.0,
            step=0.1,
        )

    st.write("")

    calcular = st.button(
        "Calcular hipoteca",
        type="primary",
        use_container_width=True,
    )

    # ----------------------------------------------
    # Resultados
    # ----------------------------------------------

    if calcular:

        if ahorro >= precio_vivienda:
            st.error(
                "El ahorro debe ser inferior "
                "al precio de la vivienda."
            )

        elif ingresos_familiares <= 0:
            st.error(
                "Introduce unos ingresos familiares "
                "mensuales válidos."
            )

        else:
            importe_hipoteca = precio_vivienda - ahorro

            resultados = calcular_hipoteca(
                importe=importe_hipoteca,
                interes_anual=interes_anual,
                años=años,
            )

            cuota = resultados["cuota_mensual"]

            st.divider()
            st.subheader("Resultados de la simulación")

            col7, col8 = st.columns(2)

            with col7:
                st.metric(
                    "Importe estimado del préstamo",
                    f"{importe_hipoteca:,.2f} €",
                )

                st.metric(
                    "Cuota mensual estimada",
                    f"{cuota:,.2f} €",
                )

            with col8:
                st.metric(
                    "Intereses totales",
                    f"{resultados['intereses_totales']:,.2f} €",
                )

                st.metric(
                    "Total pagado al banco",
                    f"{resultados['total_pagado']:,.2f} €",
                )

            porcentaje = (
                cuota / ingresos_familiares
            ) * 100

            st.write(
                f"La cuota representa el **{porcentaje:.1f}%** "
                "de los ingresos netos mensuales "
                "de la unidad familiar."
            )

            st.caption(
                f"Situación laboral indicada: {situacion_laboral}"
            )

            st.info(
                "Esta simulación es orientativa y no constituye "
                "una oferta bancaria. No incluye impuestos, gastos "
                "de compraventa, comisiones ni seguros. El ahorro "
                "se resta íntegramente del precio para estimar "
                "el préstamo; la financiación real dependerá "
                "de la evaluación bancaria."
            )
