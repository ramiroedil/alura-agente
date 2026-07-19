import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import (
    ChatGoogleGenerativeAI,
    GoogleGenerativeAIEmbeddings,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter


# ---------------------------------------------------------
# Configuración general
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

PDF_PATH = (
    BASE_DIR
    / "documentos"
    / "manual_onboarding_desarrolladores.pdf"
)

# Leer las variables guardadas en el archivo .env
load_dotenv(BASE_DIR / ".env")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.5-flash",
)

GEMINI_EMBEDDING_MODEL = os.getenv(
    "GEMINI_EMBEDDING_MODEL",
    "gemini-embedding-2",
)


# ---------------------------------------------------------
# Leer el PDF y crear la base vectorial
# ---------------------------------------------------------

@st.cache_resource(show_spinner=False)
def crear_base_vectorial(
    ruta_pdf: str,
    fecha_modificacion: float,
):
    """
    Lee el PDF, extrae el texto, crea fragmentos,
    genera embeddings y construye la base FAISS.
    """

    # Esta variable hace que Streamlit reconstruya
    # la base cuando el PDF sea modificado.
    del fecha_modificacion

    loader = PyPDFLoader(ruta_pdf)
    paginas = loader.load()

    paginas_con_texto = [
        pagina
        for pagina in paginas
        if pagina.page_content.strip()
    ]

    if not paginas_con_texto:
        raise ValueError(
            "No se encontró texto legible en el PDF."
        )

    divisor = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
    )

    fragmentos = divisor.split_documents(
        paginas_con_texto
    )

    # Convierte cada fragmento en un vector numérico.
    embeddings = GoogleGenerativeAIEmbeddings(
        model=GEMINI_EMBEDDING_MODEL,
    )

    # Guarda los vectores para realizar búsquedas.
    base_vectorial = FAISS.from_documents(
        fragmentos,
        embeddings,
    )

    return paginas_con_texto, fragmentos, base_vectorial


# ---------------------------------------------------------
# Buscar información y generar la respuesta
# ---------------------------------------------------------

def responder_pregunta(
    pregunta: str,
    base_vectorial: FAISS,
):
    """
    Busca los fragmentos más relacionados con la pregunta
    y solicita a Gemini una respuesta basada en ellos.
    """

    documentos_encontrados = (
        base_vectorial.similarity_search(
            pregunta,
            k=3,
        )
    )

    contexto = "\n\n".join(
        (
            f"[Página "
            f"{documento.metadata.get('page', 0) + 1}]\n"
            f"{documento.page_content}"
        )
        for documento in documentos_encontrados
    )

    instrucciones = """
Eres un agente especializado en responder preguntas sobre
un documento académico.

Debes cumplir las siguientes reglas:

1. Responde únicamente utilizando el contexto proporcionado.
2. No inventes datos.
3. No utilices información externa al documento.
4. Si la respuesta no aparece, responde exactamente:
   "No encontré esa información en el documento".
5. Responde en español.
6. Explica la respuesta de manera clara y directa.
7. Cuando sea posible, menciona la página correspondiente.
"""

    modelo = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        temperature=0,
        max_retries=2,
    )

    respuesta = modelo.invoke(
        [
            SystemMessage(
                content=instrucciones
            ),
            HumanMessage(
                content=(
                    f"CONTEXTO DEL DOCUMENTO:\n\n"
                    f"{contexto}\n\n"
                    f"PREGUNTA DEL USUARIO:\n"
                    f"{pregunta}"
                )
            ),
        ]
    )

    paginas_consultadas = sorted(
        {
            documento.metadata.get("page", 0) + 1
            for documento in documentos_encontrados
        }
    )

    return (
        respuesta.text,
        paginas_consultadas,
        documentos_encontrados,
    )


# ---------------------------------------------------------
# Interfaz de Streamlit
# ---------------------------------------------------------

st.set_page_config(
    page_title="Alura Agente",
    page_icon="🤖",
    layout="centered",
)

st.title("🤖 Alura Agente")


# ---------------------------------------------------------
# Barra lateral
# ---------------------------------------------------------

with st.sidebar:
    st.header("Información del proyecto")

    st.write(
        "Este agente responde preguntas utilizando únicamente "
        "el contenido del documento seleccionado."
    )

    st.subheader("Documento utilizado")

    st.write(
    "Manual de Onboarding para Nuevos Desarrolladores "
    "de Santo Pegasus Soluciones."
)

    st.subheader("Tecnologías")

    st.markdown(
        """
- Python
- Streamlit
- LangChain
- PyPDF
- FAISS
- Google Gemini
"""
    )

    st.warning(
        "Las respuestas deben verificarse con las páginas "
        "recuperadas del documento."
    )


st.write(
    "Realiza preguntas sobre el documento "
    "**Manual de Onboarding para Nuevos Desarrolladores**."
)


# ---------------------------------------------------------
# Validaciones
# ---------------------------------------------------------

if not GOOGLE_API_KEY:
    st.error(
        "No se encontró GOOGLE_API_KEY. "
        "Crea el archivo .env y agrega tu clave de Gemini."
    )
    st.stop()


if not PDF_PATH.exists():
    st.error(
        "No se encontró el PDF en la ruta:\n\n"
        f"`{PDF_PATH}`"
    )
    st.stop()


# ---------------------------------------------------------
# Ejecución principal
# ---------------------------------------------------------

try:
    with st.spinner(
        "Procesando el PDF y creando la base de conocimiento..."
    ):
        paginas, fragmentos, base_vectorial = (
            crear_base_vectorial(
                str(PDF_PATH),
                PDF_PATH.stat().st_mtime,
            )
        )

    st.success(
        "Agente preparado correctamente."
    )

    columna_1, columna_2 = st.columns(2)

    with columna_1:
        st.metric(
            "Páginas procesadas",
            len(paginas),
        )

    with columna_2:
        st.metric(
            "Fragmentos indexados",
            len(fragmentos),
        )

    st.divider()

    # -----------------------------------------------------
    # Preguntas de ejemplo
    # -----------------------------------------------------

    st.subheader("Preguntas de ejemplo")

    st.info(
    """
- ¿Qué tecnologías utiliza el equipo de back-end?
- ¿Qué accesos debe recibir una persona durante el primer día?
- ¿Cuál es el flujo de trabajo de Git utilizado por la empresa?
- ¿Qué requisitos debe cumplir un Pull Request antes del merge?
- ¿Cuáles son los beneficios disponibles para los empleados?
"""
)
    # -----------------------------------------------------
    # Formulario
    # -----------------------------------------------------

    with st.form("formulario_pregunta"):
        pregunta = st.text_area(
            "Escribe una pregunta sobre el documento",
            placeholder=(
    "¿Qué accesos debe recibir un desarrollador "
    "durante su primer día?"
),
            height=100,
        )

        consultar = st.form_submit_button(
            "Consultar documento",
            type="primary",
        )

    # -----------------------------------------------------
    # Mostrar respuesta
    # -----------------------------------------------------

    if consultar:
        if not pregunta.strip():
            st.warning(
                "Debes escribir una pregunta."
            )
        else:
            with st.spinner(
                "Buscando información en el documento..."
            ):
                (
                    respuesta,
                    paginas_usadas,
                    documentos_usados,
                ) = responder_pregunta(
                    pregunta.strip(),
                    base_vectorial,
                )

            st.subheader("Respuesta")

            st.write(respuesta)

            st.caption(
                "Páginas recuperadas: "
                + ", ".join(
                    str(pagina)
                    for pagina in paginas_usadas
                )
            )

            with st.expander(
                "Ver fragmentos utilizados"
            ):
                for posicion, documento in enumerate(
                    documentos_usados,
                    start=1,
                ):
                    pagina = (
                        documento.metadata.get("page", 0)
                        + 1
                    )

                    st.markdown(
                        f"### Fragmento {posicion} "
                        f"— página {pagina}"
                    )

                    st.write(
                        documento.page_content
                    )

                    st.divider()

    # -----------------------------------------------------
    # Pie de página
    # -----------------------------------------------------

    st.divider()

    st.caption(
        "Proyecto desarrollado para el desafío final "
        "Alura Agente."
    )

except Exception as error:
    st.error(
        f"No se pudo ejecutar el agente: {error}"
    )