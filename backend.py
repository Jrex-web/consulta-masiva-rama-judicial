import sys
import asyncio
import io
import pandas as pd
from playwright.sync_api import sync_playwright, Page


class RamaJudicialScraper:
    """Handles browser navigation and HTML extraction for a single radicado."""

    BASE_URL = "https://consultaprocesos.ramajudicial.gov.co/"

    def __init__(self, headless: bool = False, slow_mo: int = 400):
        self.headless = headless
        self.slow_mo = slow_mo
        self._playwright = None
        self._browser = None
        self.page: Page | None = None

    def start(self) -> None:
        """Launches system Chrome (or Edge fallback) and opens the CPNU portal."""
        if sys.platform.startswith("win"):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        self._playwright = sync_playwright().start()
        try:
            # Uses Google Chrome already installed on the target PC
            self._browser = self._playwright.chromium.launch(
                channel="chrome", headless=self.headless, slow_mo=self.slow_mo
            )
        except Exception:
            # Fallback to Microsoft Edge (pre-installed on all Windows 10/11 PCs)
            self._browser = self._playwright.chromium.launch(
                channel="msedge", headless=self.headless, slow_mo=self.slow_mo
            )

        self.page = self._browser.new_page()
        self.page.goto(self.BASE_URL, wait_until="networkidle")

    def close(self) -> None:
        """Safely closes the browser and Playwright session."""
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    def fetch_actuaciones(self, radicado: str) -> list[dict]:
        """Queries a single radicado, handles duplicate/private records, and extracts actuaciones."""
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")

        # 1. Select search options and input the 23-digit radicado
        self.page.get_by_text("Número de Radicación").first.click()
        self.page.get_by_text("Todos los Procesos").first.click()

        input_field = self.page.locator("input[maxlength='23']:visible").first
        if not input_field.is_visible():
            input_field = self.page.locator("input[type='text']:visible").first

        input_field.fill("")
        input_field.fill(radicado)
        self.page.get_by_role("button", name="Consultar").click()

        # 2. Wait for summary table or "no results" dialog to appear
        result_area = self.page.locator("table:visible, .v-dialog--active").first
        result_area.wait_for(state="visible", timeout=20000)
        self.page.wait_for_timeout(1000)

        # 3. Dismiss any popup dialog (e.g., "varios registros" or "no se encontraron resultados")
        volver_btn = self.page.get_by_role("button", name="VOLVER")
        if volver_btn.is_visible():
            print(" -> Aviso del portal detectado. Cerrando popup...")
            volver_btn.click()
            self.page.wait_for_timeout(500)

        # Verify that a summary table actually rendered (in case the radicado had 0 results)
        summary_table = self.page.locator("table:visible").first
        if not summary_table.is_visible():
            print(f" -> No se encontró tabla de resultados para {radicado}.")
            return []

        # 4. Find all rows in the summary table and click the public (non-private) one(s)
        total_rows = summary_table.locator("tbody tr").count()
        extracted_rows = []

        for i in range(total_rows):
            # Re-locate the summary table and row on each iteration to avoid stale DOM references
            current_table = self.page.locator("table:visible").first
            current_row = current_table.locator("tbody tr").nth(i)
            row_text = current_row.inner_text()

            if "PROCESO PRIVADO" in row_text.upper():
                print(f" -> Fila {i + 1} es PROCESO PRIVADO, omitiendo...")
                continue

            radicado_link = (
                current_row.locator("button, a, span.blue--text, td:nth-child(2)")
                .get_by_text(radicado)
                .first
            )
            if not radicado_link.is_visible():
                continue

            radicado_link.click()

            # 5. Switch to the ACTUACIONES tab
            actuaciones_tab = self.page.get_by_role("tab", name="ACTUACIONES")
            actuaciones_tab.wait_for(state="visible", timeout=15000)
            actuaciones_tab.click()

            # 6. Extract rows from the Actuaciones table
            self.page.wait_for_timeout(1500)
            actuaciones_table = self.page.locator("table:visible").last
            actuaciones_table.locator("tbody tr").first.wait_for(
                state="visible", timeout=15000
            )

            rows = actuaciones_table.locator("tbody tr").all()
            for row in rows:
                cells = [cell.inner_text().strip() for cell in row.locator("td").all()]
                if len(cells) >= 6:
                    extracted_rows.append(
                        {
                            "Proceso_Número": radicado,
                            "Fecha_Actuación": cells[0],
                            "Anotación": cells[2],
                            "Fecha_Inicia_Termino": cells[3],
                            "Fecha_Finaliza_Termino": cells[4],
                            "Fecha_Registro": cells[5],
                        }
                    )

            # If there are more public rows for this same radicado, return to the summary list
            if i < total_rows - 1:
                regresar_btn = self.page.get_by_role("button", name="Regresar al listado")
                if regresar_btn.is_visible():
                    regresar_btn.click()
                    self.page.wait_for_timeout(1000)

        return extracted_rows

    def return_to_search(self) -> None:
        """Clicks 'Regresar al listado' or resets to the index page."""
        if not self.page:
            return

        regresar_btn = self.page.get_by_role("button", name="Regresar al listado")
        if regresar_btn.is_visible():
            regresar_btn.click()
            self.page.wait_for_timeout(1000)
        else:
            self.page.goto(self.BASE_URL, wait_until="networkidle")


class ProcesoBatchProcessor:
    """Collaborates with RamaJudicialScraper to process multiple radicados into a DataFrame."""

    COLUMNS = [
        "Registro_Número",
        "Proceso_Número",
        "Fecha_Actuación",
        "Anotación",
        "Fecha_Inicia_Termino",
        "Fecha_Finaliza_Termino",
        "Fecha_Registro",
    ]

    def __init__(self, scraper: RamaJudicialScraper):
        self.scraper = scraper

    def process_list(self, radicados: list[str]) -> pd.DataFrame:
        """Iterates over a list of radicados and compiles a structured pandas DataFrame."""
        all_records = []
        self.scraper.start()

        try:
            for radicado in radicados:
                # Clean whitespace and ensure 23-digit format
                radicado_clean = str(radicado).strip()
                if not radicado_clean:
                    continue

                print(f"Consultando proceso: {radicado_clean}...")
                try:
                    raw_rows = self.scraper.fetch_actuaciones(radicado_clean)

                    for idx, record in enumerate(raw_rows, start=1):
                        record["Registro_Número"] = idx
                        all_records.append(record)

                    print(f" -> {len(raw_rows)} actuaciones extraídas.")
                    self.scraper.return_to_search()

                except Exception as e:
                    print(f"Error consultando {radicado_clean}: {e}")
                    self.scraper.return_to_search()
        finally:
            self.scraper.close()

        return pd.DataFrame(all_records, columns=self.COLUMNS)


class ExcelExporter:
    """Exports the compiled DataFrame to Excel worksheets."""

    def __init__(self, file_path: str = "procesos_rama_judicial.xlsx"):
        self.file_path = file_path

    def export_by_process_sheets(self, df: pd.DataFrame) -> None:
        """Creates one worksheet per Process_Number inside the same Excel file."""
        if df.empty:
            print("No hay datos para exportar.")
            return

        with pd.ExcelWriter(self.file_path, engine="openpyxl") as writer:
            for process_num, group_df in df.groupby("Proceso_Número"):
                sheet_name = str(process_num)[:31]
                group_df.to_excel(writer, sheet_name=sheet_name, index=False)
        print(f"Archivo guardado con una hoja por proceso en: {self.file_path}")

    def export_to_bytes(self, df: pd.DataFrame) -> bytes:
        """Returns the multi-sheet Excel workbook as bytes for web download."""
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            for process_num, group_df in df.groupby("Proceso_Número"):
                sheet_name = str(process_num)[:31]
                group_df.to_excel(writer, sheet_name=sheet_name, index=False)
        return output.getvalue()
    
    
    