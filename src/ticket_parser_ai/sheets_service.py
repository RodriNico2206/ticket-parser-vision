import datetime
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials
from thefuzz import fuzz, process

from ticket_parser_ai.models import TicketData

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


class GoogleSheetsService:
    def __init__(
        self,
        credentials_path: Path = Path("credentials.json"),
        spreadsheet_name: str = "Control_inventario",
        worksheet_name: str = "Datos",
    ):
        """Initialize Google Sheets client using service account credentials."""
        if not credentials_path.exists():
            raise FileNotFoundError(
                f"Credentials file not found at: {credentials_path}"
            )

        self.creds = Credentials.from_service_account_file(
            credentials_path, scopes=SCOPES
        )
        self.client = gspread.authorize(self.creds)
        self.spreadsheet = self.client.open(spreadsheet_name)
        self.sheet = self.spreadsheet.worksheet(worksheet_name)

    def _get_catalog_and_max_code(self) -> tuple[dict, int]:
        """
        Reads existing sheet records by position (Col A = Code, Col B = Description)
        and returns:
        1. A mapping dictionary: { "descripcion_limpia": {"code": "23", "official_name": "tutuca bolsita"} }
        2. The highest integer code found in Column A (for auto-incrementing new items).
        """
        # get_all_values() obtiene las celdas por posición evitando errores de encabezados vacíos o duplicados
        all_rows = self.sheet.get_all_values()
        catalog = {}
        max_code = 0

        # Omitimos la Fila 1 (encabezados) con [1:]
        rows_data = all_rows[1:] if len(all_rows) > 1 else []

        for row in rows_data:
            # Columna A (índice 0): Código | Columna B (índice 1): Descripción
            raw_code = str(row[0]).strip() if len(row) > 0 else ""
            official_name = str(row[1]).strip() if len(row) > 1 else ""

            if official_name and raw_code:
                clean_key = official_name.lower()
                catalog[clean_key] = {
                    "code": raw_code,
                    "official_name": official_name,
                }

            if raw_code.isdigit():
                max_code = max(max_code, int(raw_code))

        return catalog, max_code

    def append_ticket_data(
        self,
        ticket: TicketData,
        default_margin: float = 0.40,
        default_category: str = "Comestibles",
        similarity_threshold: int = 80,
    ) -> int:
        """Calculate selling price, match existing product codes/names, and append rows."""
        catalog, max_code = self._get_catalog_and_max_code()
        rows_to_add = []

        now = datetime.datetime.now()
        entry_date = f"{now.day}/{now.month}/{now.year}"

        for item in ticket.items:
            # Defensive casting for unit_price
            try:
                unit_cost = float(item.unit_price) if item.unit_price is not None else 0.0
            except (ValueError, TypeError):
                unit_cost = 0.0

            # Defensive casting for profit_margin
            try:
                margin = (
                    float(item.profit_margin)
                    if item.profit_margin is not None
                    else default_margin
                )
            except (ValueError, TypeError):
                margin = default_margin

            category = item.category or default_category
            raw_item_name = (item.product_name or "").strip()
            extracted_name_lower = raw_item_name.lower()

            # Default values if no match is found
            assigned_code = None
            assigned_description = raw_item_name.lower()

            # Fuzzy match against existing catalog descriptions
            if catalog and extracted_name_lower:
                match_result = process.extractOne(
                    extracted_name_lower,
                    catalog.keys(),
                    scorer=fuzz.token_set_ratio,
                )

                if match_result and match_result[1] >= similarity_threshold:
                    matched_key = match_result[0]
                    assigned_code = catalog[matched_key]["code"]
                    assigned_description = catalog[matched_key]["official_name"]

            # Generate new incremental code if product is not in catalog
            if not assigned_code:
                max_code += 1
                assigned_code = str(max_code)

            # Formula: selling_price = purchase_price / (1 - profit_margin)
            if margin < 1.0:
                selling_price = round(unit_cost / (1.0 - margin), 2)
            else:
                selling_price = unit_cost

            row = [
                assigned_code,  # Column A: Código
                assigned_description,  # Column B: Descripción
                unit_cost,  # Column C: Precio compra
                item.quantity,  # Column D: Cantidad
                f"{int(margin * 100)}%",  # Column E: Margen de ganancia
                selling_price,  # Column F: Precio venta
                entry_date,  # Column G: Fecha ingreso
                category,  # Column H: Categoría
            ]
            rows_to_add.append(row)

        if rows_to_add:
            self.sheet.append_rows(rows_to_add, value_input_option="USER_ENTERED")
            print(
                f"[+] Successfully appended {len(rows_to_add)} rows to worksheet '{self.sheet.title}'."
            )

        return len(rows_to_add)