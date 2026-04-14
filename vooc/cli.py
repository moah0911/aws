from __future__ import annotations

from vooc.services.ai_engine import AIEngine
from vooc.services.content_search import ContentSearchService
from vooc.services.image_generation import GeminiImageService
from vooc.services.local_model import PyTorchLocalModelClient
from vooc.services.session_memory import SessionMemory
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
    images = GeminiImageService()
    sessions = SessionMemory()

    current_session = sessions.create_session("default")

    print(ascii_art())
    print("Welcome to vooc")
    print("Create content with persistent memory and asset tracking per session.\n")

    while True:
        print_menu(current_session)
        choice = input("vooc> ").strip()

        try:
            if choice == "1":
                current_session = handle_session_switch(sessions, current_session)
            elif choice == "2":
                creator_id = input("Creator ID: ").strip()
                raw = input("Paste 10+ samples separated by '|': ")
                samples = [x.strip() for x in raw.split("|") if x.strip()]
                profile = ai.analyze_voice(creator_id, samples)
                print(f"Created profile: {profile.id}")
            elif choice == "3":
                creator_id = input("Creator ID: ").strip()
                seed = input("Seed topic: ").strip()
                for idx, item in enumerate(ai.suggest_topics(creator_id, seed), start=1):
                    print(f"{idx}. {item.topic} | relevance={item.relevance_score} | similarity={item.similarity_to_existing}")
            elif choice == "4":
                prompt = input("Your message: ").strip()
                context = sessions.build_context_text(current_session)
                req = ContentGenerationRequest(
                    brief_id=f"session-{current_session}",
                    prompt=prompt,
                    session_id=current_session,
                    constraints=ContentConstraints(tone=input("Tone (optional): ").strip() or None),
                )
                generated = ai.generate_content(req, context=context)
                sessions.append(current_session, "user", prompt)
                sessions.append(current_session, "assistant", generated.content)
                sessions.register_artifact(current_session, "text", f"session://{current_session}/turn", prompt)
                print("\nAssistant:\n")
                print(generated.content)
            elif choice == "5":
                content = input("Content to optimize: ").strip()
                platform = input("Platform [youtube/tiktok/linkedin/substack]: ").strip()
                print(ai.optimize_for_platform(content, platform))
            elif choice == "6":
                query = input("Search query: ").strip()
                results = search.search(query)
                for idx, result in enumerate(results, start=1):
                    print(f"{idx}. {result.title} (score={result.score:.2f})")
                    print(f"   {result.url}")
            elif choice == "7":
                text = input("Text to synthesize: ").strip()
                output = input("Output file path [default: ./vooc-voice.wav]: ").strip() or "./vooc-voice.wav"
                result = voice.synthesize(text, output)
                sessions.register_artifact(current_session, "voice", result.output_path, text)
                print(f"Saved voice output to {result.output_path}")
            elif choice == "8":
                prompt = input("Image prompt: ").strip()
                output = input("Output file path [default: ./vooc-image.png]: ").strip() or "./vooc-image.png"
                context = sessions.build_context_text(current_session)
                result = images.generate(prompt, output, context=context)
                sessions.append(current_session, "user", f"[image] {prompt}")
                sessions.append(current_session, "assistant", f"[image-generated] {result.output_path}")
                sessions.register_artifact(current_session, "image", result.output_path, prompt)
                print(f"Saved image to {result.output_path}")
            elif choice == "9":
                print(model_client.preload_model())
            elif choice == "10":
                print("\n" + sessions.session_brief(current_session))
            elif choice == "0":
                print("Goodbye from vooc 👋")
                return
            else:
                print("Unknown option")
        except Exception as exc:  # noqa: BLE001
            print(f"Error: {exc}")


def handle_session_switch(sessions: SessionMemory, current_session: str) -> str:
    print(f"Current session: {current_session}")
    all_sessions = sessions.list_sessions()
    if all_sessions:
        print("Available sessions:")
        for name in all_sessions:
            print(f"- {name}")
    new_name = input("Enter session name to switch/create: ").strip()
    switched = sessions.create_session(new_name)
    print(f"Switched to session: {switched}")
    return switched


def print_menu(current_session: str) -> None:
    print(f"\nSession: {current_session}")
    print("1) Switch/create session")
    print("2) Build voice profile")
    print("3) Suggest topics")
    print("4) Chat with context")
    print("5) Optimize for platform")
    print("6) Search content")
    print("7) Generate voice")
    print("8) Generate image")
    print("9) Prepare local model")
    print("10) Session brief (USP)")
    print("0) Exit")


if __name__ == "__main__":
    run()
