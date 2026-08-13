import argparse
from pathlib import Path
from ticket_parser_ai.vision_service import VisionTicketParser


def main():
    parser = argparse.ArgumentParser(
        description="Extract structured purchase ticket items using Vision Multimodal LLMs."
    )
    parser.add_argument("image_path", type=Path, help="Path to the receipt image file")
    parser.add_argument(
        "--provider",
        choices=["openrouter", "groq"],
        default="openrouter",
        help="API Provider to use for vision analysis (default: openrouter)",
    )

    args = parser.parse_args()

    try:
        vision_parser = VisionTicketParser(provider=args.provider)
        ticket_data = vision_parser.extract_ticket_data(args.image_path)
        print("\n--- Extracted Ticket Data ---")
        print(ticket_data.model_dump_json(indent=2))

    except Exception as e:
        print(f"[!] Error processing ticket: {e}")


if __name__ == "__main__":
    main()