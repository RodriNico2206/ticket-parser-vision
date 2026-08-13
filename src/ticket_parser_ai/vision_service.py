import base64
from pathlib import Path
from openai import OpenAI
from ticket_parser_ai.config import settings
from ticket_parser_ai.models import TicketData


class VisionTicketParser:
    def __init__(self, provider: str = "openrouter"):
        self.provider = provider.lower()
        if self.provider == "openrouter":
            self.client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=settings.openrouter_api_key,
            )
            # Use active stable model from config or fallback
            self.model = settings.vision_model_name or "google/gemini-2.0-flash-lite-001"
        elif self.provider == "groq":
            self.client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=settings.groq_api_key,
            )
            # Active Vision model for Groq
            self.model = "llama-3.2-90b-vision-preview"
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    @staticmethod
    def _encode_image(image_path: Path) -> str:
        """Encode image file to base64 string."""
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found at: {image_path}")
        
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode("utf-8")

    def extract_ticket_data(self, image_path: Path) -> TicketData:
        """Extract structured receipt items using Vision LLM."""
        print(f"[*] Encoding image: {image_path.name}")
        base64_image = self._encode_image(image_path)

        prompt = """
        Analyze this receipt image and extract the following information in strict JSON format:
        {
            "store_name": "Store name or null",
            "date": "YYYY-MM-DD or null",
            "total_amount": 0.00,
            "items": [
                {
                    "product_name": "Item description",
                    "quantity": 1.0,
                    "unit_price": 0.00,
                    "total_price": 0.00
                }
            ]
        }
        Requirements:
        - Return ONLY raw JSON without markdown or backticks.
        - Ensure numerical values are numeric, not strings.
        """

        print(f"[*] Sending request to {self.provider.upper()} using model {self.model}...")
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
            temperature=0.1,
            max_tokens=1000,
        )

        raw_output = response.choices[0].message.content.strip()
        print("[+] Received response from Vision API.")

        # Clean markdown code blocks if present
        if raw_output.startswith("```"):
            lines = raw_output.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            raw_output = "\n".join(lines).strip()

        if not (raw_output.startswith("{") and raw_output.endswith("}")):
            raise ValueError(f"Model returned non-JSON response:\n{raw_output}")

        return TicketData.model_validate_json(raw_output)