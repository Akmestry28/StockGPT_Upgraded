import os
from dotenv import load_dotenv

# -------------------------------------------------------------------------
# ✅ STEP 1: Load .env file automatically (from project root)
# -------------------------------------------------------------------------
# verbose=True will print debug info if .env is not found or loaded
env_loaded = load_dotenv(verbose=True)

# -------------------------------------------------------------------------
# ✅ STEP 2: Check if the .env file was loaded and key is present
# -------------------------------------------------------------------------
if not env_loaded:
    print("⚠️ Warning: .env file not found. Make sure it exists in the project root.")

# -------------------------------------------------------------------------
# ✅ STEP 3: Get the OpenAI API key from environment variables
# -------------------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# -------------------------------------------------------------------------
# ✅ STEP 4: Print status for debugging
# -------------------------------------------------------------------------
if OPENAI_API_KEY:
    print("✅ OPENAI_API_KEY successfully loaded.")
    print(f"🔑 Starts with: {OPENAI_API_KEY[:4]}****")
else:
    raise ValueError(
        "🚨 OPENAI_API_KEY not found.\n"
        "👉 Create a .env file in your project root with the line:\n"
        "OPENAI_API_KEY=sk-your_real_openai_api_key_here"
    )

# -------------------------------------------------------------------------
# ✅ STEP 5: Optional – Print confirmation for import success
# -------------------------------------------------------------------------
if __name__ == "__main__":
    print("✅ Config file loaded and OpenAI key available for app use.")
