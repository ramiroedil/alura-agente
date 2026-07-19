from pathlib import Path

import streamlit as st
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter


# Ruta principal del proyecto
BASE_DIR = Path(__file__).resolve().parent

# Ruta del documento PDF
PDF_PATH = (
    BASE_DIR
    / "documentos"
    / "marco_teorico_agenda_digital.pdf"
)


def procesar_documento(ruta_pdf: Path):
    """
    Lee el PDF, elimina páginas vacías y divide
    el contenido en fragmentos más pequeños.
    """
    loader = PyPDFLoader(str(ruta_pdf))
    paginas = loader.load()

    paginas_con_texto = [
        pagina
        for pagina in paginas
        if pagina.page_content.strip()
    ]

    divisor = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
    )

    fragmentos = divisor.split_documents(
        paginas_con_texto
    )

    return paginas_con_texto, fragmentos


st.set_page_config(
    page_title="Alura Agente",
    page_icon="🤖",
    layout="centered",
)

st.title("🤖 Alura Agente")

st.write(
    "Procesamiento del documento: "
    "**Marco teórico de la agenda digital**"
)

if not PDF_PATH.exists():
    st.error(
        "No se encontró el PDF. Verifica que exista en:\n\n"
        f"`{PDF_PATH}`"
    )
    st.stop()

try:
    with st.spinner("Leyendo y procesando el documento..."):
        paginas, fragmentos = procesar_documento(PDF_PATH)

    total_caracteres = sum(
        len(pagina.page_content)
        for pagina in paginas
    )

    st.success("Documento procesado correctamente.")

    columna_1, columna_2, columna_3 = st.columns(3)

    with columna_1:
        st.metric(
            "Páginas con texto",
            len(paginas),
        )

    with columna_2:
        st.metric(
            "Fragmentos",
            len(fragmentos),
        )

    with columna_3:
        st.metric(
            "Caracteres",
            total_caracteres,
        )

    st.subheader("Contenido de una página")

    numero_pagina = st.selectbox(
        "Selecciona una página",
        options=range(1, len(paginas) + 1),
    )

    pagina_seleccionada = paginas[numero_pagina - 1]

    st.text_area(
        "Texto extraído",
        value=pagina_seleccionada.page_content,
        height=300,
        disabled=True,
    )

    st.subheader("Ejemplo de fragmento")

    numero_fragmento = st.selectbox(
        "Selecciona un fragmento",
        options=range(1, len(fragmentos) + 1),
    )

    fragmento_seleccionado = fragmentos[
        numero_fragmento - 1
    ]

    pagina_original = (
        fragmento_seleccionado.metadata.get("page", 0) + 1
    )

    st.caption(
        f"Fragmento obtenido de la página {pagina_original}"
    )

    st.text_area(
        "Contenido del fragmento",
        value=fragmento_seleccionado.page_content,
        height=250,
        disabled=True,
    )

except Exception as error:
    st.error(
        f"No se pudo procesar el documento: {error}"
    )