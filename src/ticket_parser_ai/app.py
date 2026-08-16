from pathlib import Path
from tempfile import NamedTemporaryFile
import pandas as pd
import streamlit as st

from ticket_parser_ai.models import TicketData, TicketItem
from ticket_parser_ai.sheets_service import GoogleSheetsService
from ticket_parser_ai.vision_service import VisionTicketParser

# Page configuration
st.set_page_config(page_title="Ticket Parser AI", page_icon="🧾", layout="wide")

st.title("🧾 Ticket Parser AI")
st.markdown(
    "Upload a purchase receipt image to extract structured data and log it into Google Sheets."
)

# Sidebar LLM settings
st.sidebar.header("LLM Settings")
provider = st.sidebar.selectbox(
    "Select API Provider",
    options=["openrouter", "groq"],
    index=0,
)

# Sidebar Google Sheets settings
st.sidebar.header("Google Sheets Settings")
default_margin = st.sidebar.slider(
    "Default Profit Margin (%)",
    min_value=10,
    max_value=100,
    value=40,
    step=5,
)

category = st.sidebar.selectbox(
    "Default Category",
    options=[
        "Comestibles",
        "Libreria",
        "Bebidas",
        "Utensilios",
        "Panaderia",
    ],
    index=0,
)

uploaded_file = st.file_uploader(
    "Choose a receipt image...", type=["jpg", "jpeg", "png"]
)

if uploaded_file is not None:
    with NamedTemporaryFile(
        delete=False, suffix=Path(uploaded_file.name).suffix
    ) as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = Path(tmp_file.name)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Receipt Image")
        st.image(uploaded_file, use_container_width=True)

    with col2:
        st.subheader("Extracted Data")

        if st.button("Parse Receipt", type="primary"):
            with st.spinner("Analyzing image with Vision Model..."):
                try:
                    parser = VisionTicketParser(provider=provider)
                    ticket = parser.extract_ticket_data(tmp_path)
                    
                    # Set default margin for extracted items
                    for item in ticket.items:
                        item.profit_margin = default_margin / 100.0

                    st.session_state["ticket_data"] = ticket
                    st.success("Analysis Completed!")
                except Exception as e:
                    st.error(f"Error processing ticket: {e}")
                finally:
                    if tmp_path.exists():
                        tmp_path.unlink()

        if "ticket_data" in st.session_state:
            ticket_data: TicketData = st.session_state["ticket_data"]

            st.metric(label="Store", value=ticket_data.store_name or "N/A")
            st.metric(
                label="Total Amount",
                value=(
                    f"${ticket_data.total_amount:,.2f}"
                    if ticket_data.total_amount
                    else "N/A"
                ),
            )

            st.subheader("Items List (Adjust Margins Individualy)")
            
            # Convert items to DataFrame for interactive editing
            df_items = pd.DataFrame([item.model_dump() for item in ticket_data.items])
            df_items["profit_margin"] = df_items["profit_margin"].apply(lambda x: int(x * 100) if x else default_margin)
            
            edited_df = st.data_editor(
                df_items,
                column_config={
                    "product_name": "Product",
                    "quantity": "Qty",
                    "unit_price": "Unit Cost ($)",
                    "total_price": "Total ($)",
                    "profit_margin": st.column_config.NumberColumn(
                        "Margin (%)", min_value=0, max_value=100, step=5
                    ),
                },
                disabled=["product_name", "quantity", "unit_price", "total_price"],
                hide_index=True,
                use_container_width=True,
            )

            st.divider()

            if st.button("🚀 Save to Google Sheets"):
                try:
                    # Update ticket items with modified margins from DataFrame
                    updated_items = []
                    for _, row in edited_df.iterrows():
                        item = TicketItem(
                            product_name=row["product_name"],
                            quantity=row["quantity"],
                            unit_price=row["unit_price"],
                            total_price=row["total_price"],
                            profit_margin=float(row["profit_margin"]) / 100.0,
                        )
                        updated_items.append(item)

                    ticket_data.items = updated_items

                    creds_file = Path("credentials.json")
                    sheets_service = GoogleSheetsService(
                        credentials_path=creds_file,
                        spreadsheet_name="Control_inventario",
                        worksheet_name="Datos",
                    )
                    rows_added = sheets_service.append_ticket_data(
                        ticket=ticket_data,
                        default_category=category,
                    )
                    st.balloons()
                    st.success(
                        f"Successfully added {rows_added} items to 'Datos' sheet in 'Control_inventario'!"
                    )
                except Exception as e:
                    st.error(f"Failed to export to Google Sheets: {e}")