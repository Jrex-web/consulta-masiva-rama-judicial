# ⚖️ Consulta Masiva de Procesos - Rama Judicial (CPNU)

Herramienta automatizada en **Python** con interfaz web en **Streamlit** para consultar de forma masiva actuaciones judiciales en el portal de Consulta de Procesos Nacional Unificada (CPNU) de la Rama Judicial de Colombia y exportar los resultados organizados a Excel (`.xlsx`).

## ✨ Características Principales
* **Automatización de Navegador:** Manejo inteligente de SPA (Single-Page Application) con **Playwright** utilizando Google Chrome o Microsoft Edge instalados en el sistema.
* **Soporte de Múltiples Registros y Privacidad:** Detecta y cierra automáticamente alertas de radicados duplicados y omite registros marcados como `[ PROCESO PRIVADO ]`.
* **Dos Modos de Entrada:** Permite pegar una lista de radicados (23 dígitos) o cargar un archivo Excel (`.xlsx`) con la columna `Radicado`.
* **Exportación Segura a Excel:** Genera un libro `.xlsx` con **una hoja por cada proceso** conservando los 23 dígitos íntegros sin pérdida de precisión numérica.
* **Empaquetable como `.exe`:** Incluye lanzador (`run_app.py`) listo para compilar con PyInstaller y ejecutarse en equipos Windows sin Python.

## 🏗️ Arquitectura del Proyecto
* `backend.py`: Contiene las tres clases principales bajo el principio de responsabilidad única:
  * `RamaJudicialScraper`: Navegación web y extracción de tablas HTML.
  * `ProcesoBatchProcessor`: Orquestación de lotes y estructuración en `pandas.DataFrame`.
  * `ExcelExporter`: Generación de libros Excel multi-hoja.
* `app.py`: Interfaz gráfica web construida con **Streamlit**.
* `run_app.py`: Punto de entrada para empaquetado autónomo con **PyInstaller**.

## 🚀 Instalación y Uso Local

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com
   cd consulta-rama-judicial
   ```

2. **Crear y activar el entorno virtual (Windows):**
   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Ejecutar la aplicación:**
   ```bash
   streamlit run app.py
   ```

## 📦 Compilar como Ejecutable Independiente (Windows)
Para generar una carpeta portable con `.exe` sin ventana de consola:
```powershell
pyinstaller --noconfirm --clean --onedir --windowed --add-data "app.py;." --add-data "backend.py;." --collect-all streamlit --collect-all playwright --collect-all openpyxl --collect-all numpy --collect-all pandas --copy-metadata streamlit run_app.py
```

## 📋 Buenas Prácticas de Uso
* Los números de radicación deben tener exactamente **23 dígitos** sin puntos, guiones ni espacios.
* Si cargas un archivo `.xlsx`, asegúrate de que la celda `A1` tenga el encabezado **`Radicado`** y que la columna esté en **formato Texto** para conservar los ceros a la izquierda.
