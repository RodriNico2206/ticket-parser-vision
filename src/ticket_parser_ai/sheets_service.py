import datetime
from pathlib import Path
import gspread
from google.oauth2.service_account import Credentials
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

    def _get_next_code(self) -> int:
        """Calculate next available integer code based on column A values."""
        codes = self.sheet.col_values(1)[1:]  # Exclude header
        valid_codes = [int(c) for c in codes if c.isdigit()]
        return max(valid_codes) + 1 if valid_codes else 1

    def append_ticket_data(
        self,
        ticket: TicketData,
        default_margin: float = 0.40,
        default_category: str = "Comestibles",
    ) -> int:
        """Calculate selling price per item and append rows to Google Sheets."""
        rows_to_add = []
        current_code = self._get_next_code()

        now = datetime.datetime.now()
        entry_date = f"{now.day}/{now.month}/{now.year}"

        for item in ticket.items:
            unit_cost = float(item.unit_price) if item.unit_price else 0.0
            margin = item.profit_margin if item.profit_margin is not None else default_margin

            # Formula: selling_price = purchase_price / (1 - profit_margin)
            if margin < 1.0:
                selling_price = round(unit_cost / (1.0 - margin), 2)
            else:
                selling_price = unit_cost

            row = [
                current_code,  # Column A: Código
                item.product_name.lower(),  # Column B: Descripción
                unit_cost,  # Column C: Precio compra
                item.quantity,  # Column D: Cantidad
                f"{int(margin * 100)}%",  # Column E: Margen de ganancia
                selling_price,  # Column F: Precio venta
                entry_date,  # Column G: Fecha ingreso
                default_category,  # Column H: Categoría
            ]
            rows_to_add.append(row)
            current_code += 1

        if rows_to_add:
            self.sheet.append_rows(rows_to_add, value_input_option="USER_ENTERED")
            print(
                f"[+] Successfully appended {len(rows_to_add)} rows to worksheet '{self.sheet.title}'."
            )

        return len(rows_to_add)