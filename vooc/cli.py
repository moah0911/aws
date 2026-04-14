from __future__ import annotations

from vooc.services.ai_engine import AIEngine
from vooc.services.local_model import PyTorchLocalModelClient
from vooc.services.content_search import ContentSearchService
from vooc.services.voice_service import VibeVoiceService
from vooc.types import ContentConstraints, ContentGenerationRequest


def ascii_art() -> str:
    return (
        "\n"
        "██    ██  ██████   ██████   ██████ \n"
        "██    ██ ██    ██ ██    ██ ██      \n"
        "██    ██ ██    ██ ██    ██ ██      \n"
        " ██  ██  ██    ██ ██    ██ ██      \n"
        "  ████    ██████   ██████   ██████ \n"
    )


def run() -> None:
    model_client = PyTorchLocalModelClient()
    ai = AIEngine(model_client)
    search = ContentSearchService()
    voice = VibeVoiceService()

    print(ascii_art())
    print("Welcome to vooc")
    print("Local content generation, search, and voice synthesis.\n")

    while True:
        print_menu()
        choice = input("vooc> ").strip()

        try:
            if choice == "1":
                creator_id = input("Creator ID: ").strip()
                raw = input("Paste 10+ samples separated by '|': ")
                samples = [x.strip() for x in raw.split("|") if x.strip()]
                profile = ai.analyze_voice(creator_id, samples)
                print(f"Created profile: {profile.id}")
            elif choice == "2":
                creator_id = input("Creator ID: ").strip()
                seed = input("Seed topic: ").strip()
                for idx, item in enumerate(ai.suggest_topics(creator_id, seed), start=1):
                    print(f"{idx}. {item.topic} | relevance={item.relevance_score} | similarity={item.similarity_to_existing}")
            elif choice == "3":
                req = ContentGenerationRequest(
                    brief_id=input("Brief ID: ").strip(),
                    prompt=input("Prompt: ").strip(),
                    voice_profile_id=input("Voice profile ID (optional): ").strip() or None,
                    constraints=ContentConstraints(tone=input("Tone [professional/casual/inspiring] (optional): ").strip() or None),
                )
                generated = ai.generate_content(req)
                print(generated.content)
                print(f"Voice consistency: {generated.voice_consistency_score}")
            elif choice == "4":
                content = input("Content to optimize: ").strip()
                platform = input("Platform [youtube/tiktok/linkedin/substack]: ").strip()
                print(ai.optimize_for_platform(content, platform))
            elif choice == "5":
                query = input("Search query: ").strip()
                results = search.search(query)
                for idx, result in enumerate(results, start=1):
                    print(f"{idx}. [{result.source}] {result.title} (score={result.score:.2f})")
                    print(f"   {result.url}")
            elif choice == "6":
                text = input("Text to synthesize: ").strip()
                output = input("Output file path [default: ./vooc-vibevoice.wav]: ").strip() or "./vooc-vibevoice.wav"
                result = voice.synthesize(text, output)
                print(f"Saved voice output to {result.output_path}")
            elif choice == "7":
                print(model_client.preload_model())
            elif choice == "0":
                print("Goodbye from vooc 👋")
                return
            else:
                print("Unknown option")
        except Exception as exc:  # noqa: BLE001
            print(f"Error: {exc}")



def print_menu() -> None:
    print("1) Build voice profile")
    print("2) Suggest topics")
    print("3) Generate script (local Qwen model)")
    print("4) Optimize for platform")
    print("5) Search content (DDG/Wikipedia/Grokipedia fallback)")
    print("6) Synthesize voice (Microsoft VibeVoice)")
    print("7) Download/cache local model")
    print("0) Exit")


if __name__ == "__main__":
    run()
