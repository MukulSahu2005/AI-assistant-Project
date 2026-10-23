import requests
import json
from bs4 import BeautifulSoup
from readability import Document
from urllib.parse import unquote, urlparse, parse_qs
import base64
import sys # To flush print output immediately

# --- Configuration ---
OLLAMA_API_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "llama3.1:8b" # Default model if fetching fails or no GUI
MAX_WEB_RESULTS = 2
MAX_CHARS_PER_WEB_DOC = 1000

# --- Chat Memory ---
messages = []

# --- System Prompt ---
# This system prompt is added once at the beginning of the conversation.
SYSTEM_PROMPT = (
    "You are an intelligent assistant with access to local knowledge. "
    "If the user provides external info from the web, use it. "
    "Do not ask for internet access yourself. "
    "The user's name is Bhimashri. Refer to the user by name only—no greetings or pleasantries, please."
)

# Add the system prompt to messages at the start
messages.append({"role": "system", "content": SYSTEM_PROMPT})

# --- Web Trigger Detector ---
def needs_web_search(prompt: str) -> bool:
    """
    Determines if a web search is needed based on keywords in the user's prompt.
    """
    keywords = [
        "latest", "current", "today", "todays", "live", "news", "update", "weather",
        "temperature", "price", "who won", "score", "time in", "trending", "event",
        "forecast", "match", "stock", "exchange rate", "currency", "date", "what is today's"
    ]
    return any(k in prompt.lower() for k in keywords)

# --- Decode Bing URL ---
def extract_original_bing_url(bing_url: str) -> str:
    """
    Extracts the original URL from a Bing redirect URL.
    """
    try:
        parsed = urlparse(bing_url)
        qs = parse_qs(parsed.query)
        if 'u' in qs:
            encoded = qs['u'][0]
            if encoded.startswith('a1'): # Specific Bing prefix
                encoded = encoded[2:]
            # Ensure proper base64 padding
            if len(encoded) % 4 != 0:
                encoded += '=' * (4 - len(encoded) % 4)
            decoded = base64.b64decode(encoded).decode('utf-8')
            return unquote(decoded)
    except Exception:
        pass
    return bing_url

# --- Extract Readable Content ---
def extract_main_content(url: str) -> str:
    """
    Fetches a web page and extracts its main readable content using readability-lxml.
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.88 Safari/537.36"}
        page = requests.get(url, headers=headers, timeout=10)
        page.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        doc = Document(page.text)
        soup = BeautifulSoup(doc.summary(), 'html.parser')
        paragraphs = soup.find_all('p')
        return "\n".join(p.get_text() for p in paragraphs if p.get_text()).strip()
    except requests.exceptions.RequestException:
        # print(f"Error: Network error accessing {url}: {e}", file=sys.stderr) # Suppress for cleaner output
        return ""
    except Exception:
        # print(f"Error: Processing content from {url}: {e}", file=sys.stderr) # Suppress for cleaner output
        return ""

# --- Bing Search and Extract ---
def search_and_extract_text(query: str) -> str:
    """
    Performs a Bing search, extracts content from top results, and returns it as context.
    """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.88 Safari/537.36"}
    full_context = []
    visited_urls = set()

    try:
        print(f"🌐 Searching the web for: '{query}'...", end='', flush=True) # Keep this initial indicator
        res = requests.get("https://www.bing.com/search", params={"q": query}, headers=headers, timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')

        results = soup.find_all('li', class_='b_algo')
        if not results:
            results = soup.find_all('div', class_='b_algoc')

        for i, r in enumerate(results[:MAX_WEB_RESULTS]):
            a = r.find('a')
            if a and a.get("href"):
                real_url = extract_original_bing_url(a["href"])

                if real_url in visited_urls:
                    continue
                visited_urls.add(real_url)

                # Removed: print(f"\n  Fetching content from: {real_url[:70]}...", end='', flush=True)
                content = extract_main_content(real_url)
                if content:
                    snippet = content[:MAX_CHARS_PER_WEB_DOC] + "..." if len(content) > MAX_CHARS_PER_WEB_DOC else content
                    full_context.append(f"Source: {real_url}\n\nContent:\n{snippet}")
                else:
                    # Removed: print(f" (No meaningful content extracted)", flush=True)
                    pass

        if not full_context:
            print("\n  No relevant web results or content could be extracted.", flush=True)
            return ""
        
        # Removed: print("\n🌐 Web search complete.", flush=True)
        return "\n\n---\n\n".join(full_context)
    except requests.exceptions.RequestException as e:
        print(f"\nError: Network error during Bing search for '{query}': {e}", file=sys.stderr, flush=True)
        return ""
    except Exception as e:
        print(f"\nError: An unexpected error occurred during search: {e}", file=sys.stderr, flush=True)
        return ""

# --- Call Ollama API ---
def query_ollama(prompt: str, model: str):
    """
    Sends a prompt to the Ollama API and yields tokens of the response.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True,
        "options": {"temperature": 0.5, "num_ctx": 4096}
    }
    
    try:
        with requests.post(OLLAMA_API_URL, json=payload, stream=True, timeout=120) as r:
            r.raise_for_status() # Raise HTTPError for bad responses
            for line in r.iter_lines():
                if line:
                    data = json.loads(line.decode("utf-8"))
                    token = data.get("response", "")
                    yield token # Yield token directly, don't print here
    except requests.exceptions.RequestException as e:
        yield f"\n❌ Ollama connection error: {e}. Is Ollama running and accessible at {OLLAMA_API_URL}?"
    except json.JSONDecodeError:
        yield "\n❌ Ollama response error: Invalid JSON received from server."
    except Exception as e:
        yield f"\n❌ An unexpected error occurred with Ollama: {e}"

# --- Main Chat Loop ---
def main():
    print("🧠 Hybrid ChatBot (Ollama + Web)")
    print("Type 'exit' or 'quit' to end the chat.")
    print(f"Using Ollama model: {DEFAULT_MODEL}")
    print("-" * 30)

    while True:
        # Display chat history (excluding the system prompt for cleaner display)
        for msg in messages[1:]: # Start from index 1 to skip system prompt
            if msg["role"] == "user":
                print(f"\n🧍 You: {msg['content']}")
            elif msg["role"] == "assistant":
                print(f"\n🤖 Bot: {msg['content']}")

        user_input = input("\n🧍 You: ").strip()
        if user_input.lower() in ["exit", "quit"]:
            print("Exiting chat. Goodbye!")
            break

        messages.append({"role": "user", "content": user_input})

        print("\n🤖 Bot: ", end='', flush=True) # Print "Bot:" once

        ollama_input_prompt = user_input

        # Check if a web search is triggered by keywords
        if needs_web_search(user_input):
            web_data = search_and_extract_text(user_input) # This function now handles its own status prints
            
            if web_data:
                ollama_input_prompt += f"\n\nHere is some relevant information from the internet:\n{web_data}\n\nPlease answer the original query using this information."
            # else: no web data, prompt remains original

        # Stream Ollama's response and accumulate it
        full_assistant_response = ""
        for token in query_ollama(ollama_input_prompt, DEFAULT_MODEL):
            full_assistant_response += token
            # The token is printed here by the main loop, not by query_ollama
            # This ensures only one stream of text output.

        print("\n", flush=True) # Add a newline after the streamed response is complete

        messages.append({"role": "assistant", "content": full_assistant_response})

if __name__ == "__main__":
    main()