# ticket-parser-vision


export GROQ_API_KEY="tu_groq_api_key_aqui"
export OPENROUTER_API_KEY="tu_openrouter_api_key_aqui"

poetry run parse-ticket samples/1000123873.jpg --provider openrouter

poetry run parse-ticket samples/1000123873.jpg --provider groq

poetry run uvicorn ticket_parser_ai.api:app --reload --port 8000