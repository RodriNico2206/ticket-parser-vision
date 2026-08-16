from pathlib import Path
from tempfile import NamedTemporaryFile
from fastapi import FastAPI, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ticket_parser_ai.models import TicketData
from ticket_parser_ai.sheets_service import GoogleSheetsService
from ticket_parser_ai.vision_service import VisionTicketParser

app = FastAPI(title="Ticket Parser AI")

# Mount static files directory for frontend assets
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


class SaveSheetsRequest(BaseModel):
    ticket: TicketData


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Prevent 404 logs for browser favicon requests."""
    return Response(status_code=204)


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serve the main HTML web page."""
    index_path = static_dir / "index.html"
    if not index_path.exists():
        raise HTTPException(
            status_code=404, detail="Index HTML file not found."
        )
    return index_path.read_text(encoding="utf-8")


@app.post("/api/parse")
async def parse_ticket(
    file: UploadFile = File(...),
    provider: str = Form("openrouter"),
):
    """Parse uploaded receipt image using Vision LLM API."""
    suffix = Path(file.filename).suffix or ".jpg"
    with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        contents = await file.read()
        tmp.write(contents)
        tmp_path = Path(tmp.name)

    try:
        parser = VisionTicketParser(provider=provider)
        ticket_data = parser.extract_ticket_data(tmp_path)
        return ticket_data.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


@app.post("/api/save-sheets")
async def save_sheets(data: SaveSheetsRequest):
    """Save extracted ticket data to Google Sheets spreadsheet."""
    try:
        creds_file = Path("credentials.json")
        sheets_service = GoogleSheetsService(
            credentials_path=creds_file,
            spreadsheet_name="Control_inventario1",
            worksheet_name="Datos",
        )
        rows_added = sheets_service.append_ticket_data(
            ticket=data.ticket
        )
        return {"status": "success", "rows_added": rows_added}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))