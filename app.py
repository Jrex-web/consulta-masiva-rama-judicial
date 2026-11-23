import os
import streamlit as st
import pandas as pd
from backend import RamaJudicialScraper, ProcesoBatchProcessor, ExcelExporter
import time
import threading

st.set_page_config(page_title="Consulta Rama Judicial", page_icon="⚖️", layout="wide")
st.title("⚖️ Consulta Masiva de Procesos - Rama Judicial")

# Close button
with st.sidebar:
    st.header("Control de la Aplicación")
    if st.button("🛑 Cerrar Aplicación", use_container_width=True):
        st.success("✅ Aplicación cerrada correctamente. Ya puedes cerrar esta pestaña.")
        threading.Thread(target=lambda: (time.sleep(1.5), os._exit(0)), daemon=True).start()

# Input method: Paste text OR upload Excel
input_mode = st.radio("¿Cómo deseas ingresar los radicados?", ["Pegar lista", "Subir archivo Excel"])

radicados = []
if input_mode == "Pegar lista":
    raw_text = st.text_area(
        "Pega los números de radicación (23 dígitos, uno por línea sin puntos ni comas):",
        height=150
        # placeholder="00000000000000000000000\n00000000000000000000000"
    )
    radicados = [line.strip() for line in raw_text.splitlines() if line.strip()]
else:
    uploaded_file = st.file_uploader("Sube un Excel (.xlsx) con una columna en formato texto, llamada 'Radicado' en la celda A1.", type=["xlsx"])
    if uploaded_file:
        df_input = pd.read_excel(uploaded_file, dtype=str)
        if "Radicado" in df_input.columns:
            radicados = df_input["Radicado"].dropna().str.strip().tolist()
        else:
            st.error("El archivo Excel debe tener una columna llamada 'Radicado' en formato texto.")

headless_mode = st.checkbox("Ejecutar navegador en segundo plano (sin abrir ventana)", value=False)

if st.button("Iniciar Consulta", type="primary", disabled=len(radicados) == 0):
    with st.spinner(f"Consultando {len(radicados)} proceso(s) en la Rama Judicial..."):
        scraper = RamaJudicialScraper(headless=headless_mode, slow_mo=300)
        processor = ProcesoBatchProcessor(scraper=scraper)
        df_resultado = processor.process_list(radicados)

    if df_resultado.empty:
        st.warning("No se encontraron actuaciones públicas para los radicados ingresados.")
    else:
        st.success(f"¡Consulta completada! Se extrajeron {len(df_resultado)} actuaciones. da click en el boton de abajo de la tabla, para descargar el archivo")
        # st.dataframe(df_resultado, use_container_width=True)
        df_vista = df_resultado.copy()
        df_vista["Proceso_Número"] = df_vista["Proceso_Número"].apply(lambda x: f'="{x}"')
        st.dataframe(df_vista, use_container_width=True, hide_index=True)


        exporter = ExcelExporter()
        excel_bytes = exporter.export_to_bytes(df_resultado)

        st.download_button(
            label="📥 Descargar Excel por Hojas (.xlsx)",
            data=excel_bytes,
            file_name="procesos_rama_judicial.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
