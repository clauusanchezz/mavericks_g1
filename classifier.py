from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path
import os
import json

load_dotenv()

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

def cargar_preguntas_del_txt(nombre_archivo="FAQs_Asistente_Bancario_Mavericks.txt"):
    ruta = Path(__file__).parent / nombre_archivo
    if not ruta.exists():
        raise FileNotFoundError(f"No se encuentra el archivo {nombre_archivo}")
    
    contenido = ruta.read_text(encoding="utf-8")
    bloques = contenido.split("---")
    
    guia_preguntas = []
    for bloque in bloques:
        pregunta = ""
        ruta_faq = ""
        for linea in bloque.strip().splitlines():
            if linea.startswith("PREGUNTA:"):
                pregunta = linea.replace("PREGUNTA:", "").strip()
            elif linea.startswith("RUTA:"):
                ruta_faq = linea.replace("RUTA:", "").strip()
        if pregunta:
            guia_preguntas.append(f"- {pregunta} (Ruta: {ruta_faq})")
            
    return "\n".join(guia_preguntas)

def clasificar_llamada_banco(texto_cliente, nombre_txt="FAQs_Asistente_Bancario_Mavericks.txt"):
    guia_txt = cargar_preguntas_del_txt(nombre_txt)
    
    system_prompt = f"""
    Eres el agente clasificador de consultas de un banco.
    Por motivos éticos y de privacidad, NO extraigas ni guardes datos personales o financieros del cliente.
    
    Tienes esta guía de 50 preguntas frecuentes del banco y su ruta interna:
    {guia_txt}
    
    Clasifica el mensaje del cliente estrictamente en UNA de estas 3 categorías:
    1. "HIPOTECAS": El cliente quiere hacer una simulación o cálculo numérico de su hipoteca (cuota mensual, cuánto puede permitirse según sueldo, cuánto ahorro necesita, qué pasa si cambia el plazo/interés/capital, amortizar cuota vs plazo; corresponden a las de ruta SIMULAR).
    2. "FAQS": El cliente hace una consulta informativa sobre conceptos hipotecarios (TIN/TAE, fija/variable/mixta, FEIN, gastos, notario), cuentas, comisiones, tarjetas, transferencias o Bizum que el asistente RAG puede explicar con la guía (rutas FAQ o BANCO informativas).
    3. "OTROS": Casos críticos, urgencias o solicitudes que requieren atención de una persona: pérdida/robo de tarjeta, cargos no reconocidos, SMS sospechosos (smishing), dificultades para pagar la cuota, avales, reclamaciones, cuenta bloqueada, pedir hablar con un humano o temas ajenos al banco (rutas PERSONA o URGENTE, o consultas fuera de la guía).

    Responde ÚNICAMENTE con un objeto JSON válido con este formato exacto:
    {{
      "categoria": "HIPOTECAS" | "FAQS" | "OTROS",
      "confianza": float entre 0.0 y 1.0,
      "razonamiento_breve": "explicación de 1 frase de la intención detectada"
    }}
    """

    respuesta = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": texto_cliente}
        ],
        temperature=0.0,
        response_format={"type": "json_object"}
    )
    
    return json.loads(respuesta.choices[0].message.content)