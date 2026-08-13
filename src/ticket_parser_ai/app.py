import streamlit as st
from pathlib import Path
from tempfile import NamedTemporaryFile
from ticket_parser_ai.vision_service import VisionTicketParser

# Page configuration
st.set_page_config(page_title="Ticket Parser AI", page_icon="🧾", layout="wide")

st.title("🧾 Ticket Parser AI")
st.markdown("Upload a purchase receipt image to extract structured data using Vision LLMs.")

# Sidebar controls
st.sidebar.header("Settings")
provider = st.sidebar.selectbox(
    "Select API Provider",
    options=["openrouter", "groq"],
    index=0,
)

# File uploader
uploaded_file = st.file_uploader("Choose a receipt image...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # Save uploaded file temporarily to process with VisionTicketParser
    with NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = Path(tmp_file.name)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Receipt Image")
        # Updated width parameter according to Streamlit deprecation warning
        st.image(uploaded_file, width="stretch")

    with col2:
        st.subheader("Extracted Data")
        if st.button("Parse Receipt", type="primary"):
            with st.spinner("Analyzing image with Vision Model..."):
                try:
                    parser = VisionTicketParser(provider=provider)
                    ticket_data = parser.extract_ticket_data(tmp_path)
                    
                    # Display structured metrics
                    st.success("Analysis Completed!")
                    st.metric(label="Store", value=ticket_data.store_name or "N/A")
                    st.metric(label="Date", value=ticket_data.date or "N/A")
                    st.metric(label="Total Amount", value=f"${ticket_data.total_amount:,.2f}" if ticket_data.total_amount else "N/A")

                    # Display items table
                    # Updated width parameter according to Streamlit deprecation warning
                    st.subheader("Items List")
                    items_list = [item.model_dump() for item in ticket_data.items]
                    st.dataframe(items_list, width="stretch")

                    # Display raw JSON output
                    with st.expander("View Raw JSON"):
                        st.json(ticket_data.model_dump())

                except Exception as e:
                    st.error(f"Error processing ticket: {e}")
                finally:
                    # Clean up temporary file
                    if tmp_path.exists():
                        tmp_path.unlink()