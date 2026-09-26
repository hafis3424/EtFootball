"""List all available models from Gemini and Groq APIs."""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Gemini Models ──
def list_gemini_models():
    import google.generativeai as genai
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("  [!] GEMINI_API_KEY not set in .env")
        return
    
    genai.configure(api_key=api_key)
    
    print("  {:40s} {:20s} {}".format("Model ID", "Display Name", "Supported Methods"))
    print("  " + "-" * 90)
    
    for model in genai.list_models():
        methods = ", ".join(model.supported_generation_methods)
        print(f"  {model.name:40s} {model.display_name:20s} {methods}")


# ── Groq Models ──
def list_groq_models():
    from groq import Groq
    
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("  [!] GROQ_API_KEY not set in .env")
        return
    
    client = Groq(api_key=api_key)
    models = client.models.list()
    
    print("  {:40s} {:20s} {}".format("Model ID", "Owned By", "Context Window"))
    print("  " + "-" * 90)
    
    for model in models.data:
        ctx = getattr(model, 'context_window', 'N/A')
        print(f"  {model.id:40s} {model.owned_by:20s} {ctx}")


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  GOOGLE GEMINI MODELS")
    print("=" * 50)
    try:
        list_gemini_models()
    except Exception as e:
        print(f"  [ERROR] {e}")

    print("\n" + "=" * 50)
    print("  GROQ MODELS")
    print("=" * 50)
    try:
        list_groq_models()
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    print()




# from google import genai

# client = genai.Client(api_key="GEMINI_API_KEY")

# for model in client.models.list():
#     print(model.name)
