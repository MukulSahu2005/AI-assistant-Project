import streamlit as st
import requests
import json
from bs4 import BeautifulSoup
from readability import Document
from urllib.parse import unquote, urlparse, parse_qs
import base64
import logging

# Configure logging for better error visibility in the console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Page Setup ---
st.set_page_config(page_title="🧠 Hybrid Ollama ChatBot", layout="centered")
st.title("🧠 Hybrid ChatBot (Ollama + Web)")
st.markdown("_By Bhimashri_")

# --- Initialize Chat Memory ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Ollama Model List ---
try:
    res = requests.get("http://localhost:11434/api/tags", timeout=5)
    res.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
    available_models = [m['model'] for m in res.json().get('models', [])]
    if not available_models:
        available_models = ["llama3.1:8b"] # Fallback if no models are returned
except requests.exceptions.RequestException as e:
    st.warning(f"Could not connect to Ollama server or fetch models: {e}. Using default model.")
    logging.error(f"Ollama connection error: {e}")
    available_models = ["llama3.1:8b"] # Fallback on connection/request error

# --- Sidebar Controls ---
selected_model = st.sidebar.selectbox("🧠 Select Ollama Model", available_models)
web_access_enabled = st.sidebar.toggle("🌐 Enable Internet Access", value=True)

# --- System Prompt (Only at Start) ---
if len(st.session_state.messages) == 0:
    intro = (
        "You are an intelligent assistant with access to local knowledge. "
        "If the user provides external info from the web, use it. "
        "Do not ask for internet access yourself. "
        "The user's name is Bhimashri. Refer to the user by name only—no greetings or pleasantries, please."
    )
    st.session_state.messages.append({"role": "system", "content": intro})

# --- Web Trigger Detector ---
def needs_web_search(prompt: str) -> bool:
    """
    Determines if a web search is needed based on keywords in the user's prompt.
    """
    keywords = [
        "who is", "latest", "current", "today", "todays", "live", "news", "update", "weather",
        "temperature", "price", "who won", "score", "time in", "trending", "event",
        "forecast", "match", "stock", "exchange rate", "currency", "date", "what is today's",
        "recent", "current affairs" # Added a couple more common triggers
    ]
    return any(k in prompt.lower() for k in keywords)

# --- Decode Bing URL ---
def extract_original_bing_url(bing_url: str) -> str:
    """
    Extracts the original URL from a Bing redirect URL.
    Handles potential Base64 encoding.
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
    except Exception as e: # Catching specific error in case of bad encoding
        logging.warning(f"Error decoding Bing URL '{bing_url}': {e}")
        pass # Fall through and return the original URL if decoding fails
    return bing_url

# --- Extract Readable Content ---
def extract_main_content(url: str) -> str:
    """
    Fetches a web page and extracts its main readable content using readability-lxml.
    Includes robust error handling for network issues and content parsing.
    """
    try:
        # Using a more common User-Agent string to avoid being blocked
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.88 Safari/537.36"}
        page = requests.get(url, headers=headers, timeout=10)
        page.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        doc = Document(page.text)
        soup = BeautifulSoup(doc.summary(), 'html.parser')
        paragraphs = soup.find_all('p')
        return "\n".join(p.get_text() for p in paragraphs if p.get_text()).strip()
    except requests.exceptions.RequestException as e:
        logging.warning(f"Network error accessing {url}: {e}")
        return ""
    except Exception as e:
        logging.warning(f"Error processing content from {url}: {e}")
        return ""

# --- Bing Search and Extract ---
def search_and_extract_text(query: str, max_results: int = 2, max_chars: int = 1000) -> str:
    """
    Performs a Bing search for the query, extracts content from the top results,
    and returns the compiled context as a string.
    """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.88 Safari/537.36"}
    full_context = []
    visited_urls = set() # Track URLs to avoid duplicates

    try:
        res = requests.get("https://www.bing.com/search", params={"q": query}, headers=headers, timeout=15)
        res.raise_for_status() # Ensure we got a successful response from Bing
        soup = BeautifulSoup(res.text, 'html.parser')

        # Find top search results (common Bing classes for organic results)
        results = soup.find_all('li', class_='b_algo')
        if not results: # Fallback to another common structure if 'b_algo' isn't found
            results = soup.find_all('div', class_='b_algoc')

        for r in results[:max_results]: # Iterate only up to max_results
            a = r.find('a')
            if a and a.get("href"):
                real_url = extract_original_bing_url(a["href"])

                if real_url in visited_urls:
                    continue # Skip if this URL has already been processed
                visited_urls.add(real_url)

                content = extract_main_content(real_url)
                if content:
                    # Truncate content if it's too long
                    snippet = content[:max_chars] + "..." if len(content) > max_chars else content
                    full_context.append(f"Source: {real_url}\n\nContent:\n{snippet}")
                # No 'else' needed here, just don't add if content is empty

        if not full_context:
            st.info("🌐 No relevant web results or content could be extracted.")
            return ""

        return "\n\n---\n\n".join(full_context)
    except requests.exceptions.RequestException as e:
        st.error(f"Error during Bing search for '{query}': {e}")
        logging.error(f"Bing search request error for '{query}': {e}")
        return ""
    except Exception as e:
        st.error(f"An unexpected error occurred during search: {e}")
        logging.error(f"Unexpected error during Bing search: {e}")
        return ""

# --- Call Ollama API ---
def query_ollama(prompt: str, model: str):
    """
    Sends a prompt to the Ollama API and streams the response tokens.
    """
    ollama_api_url = "http://localhost:11434/api/generate"
    
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True,
        "options": {"temperature": 0.5, "num_ctx": 4096} # Set context window
    }

    try:
        with requests.post(ollama_api_url, json=payload, stream=True, timeout=120) as r:
            r.raise_for_status() # Check for HTTP errors (e.g., 404, 500 from Ollama)
            for line in r.iter_lines():
                if line:
                    data = json.loads(line.decode("utf-8"))
                    token = data.get("response", "")
                    yield token
    except requests.exceptions.RequestException as e:
        error_message = f"\n❌ Ollama connection error: {e}. Is Ollama running and accessible at {ollama_api_url}?"
        logging.error(error_message)
        yield error_message
    except json.JSONDecodeError as e:
        error_message = f"\n❌ Ollama response error: Invalid JSON received from server. {e}"
        logging.error(error_message)
        yield error_message
    except Exception as e:
        error_message = f"\n❌ An unexpected error occurred with Ollama: {e}"
        logging.error(error_message)
        yield error_message

# --- Display Chat History ---
for msg in st.session_state.messages:
    # Only display 'user' and 'assistant' roles to the user interface
    if msg["role"] in ["user", "assistant"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# --- Main Input + Flow ---
if prompt := st.chat_input("🧍 You:"):
    # Add user's message to session state and display it in the chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        response_box = st.empty() # Placeholder to stream the LLM's response
        full_output = ""
        ollama_input_prompt = prompt # Start with the original user prompt

        # Perform web search only if 'Enable Internet Access' is toggled ON and keywords match
        if web_access_enabled and needs_web_search(prompt):
            with st.spinner("🌐 Searching the web..."):
                web_data = search_and_extract_text(prompt)

            if web_data:
                # Construct a more conversational prompt that incorporates web data
                ollama_input_prompt = (
                    f"Here is some relevant information from the internet:\n{web_data}\n\n"
                    f"Based on this information, please answer the following question: {prompt}"
                )
            else:
                st.warning("🌐 Web search triggered, but no useful information found. Answering based on internal knowledge.")
                # If no useful web data, ollama_input_prompt remains the original user prompt

        # Call Ollama with the (potentially augmented) prompt and stream the response
        for token in query_ollama(ollama_input_prompt, selected_model):
            full_output += token
            response_box.markdown(full_output)

        # Append the final, complete assistant response to the chat history
        st.session_state.messages.append({"role": "assistant", "content": full_output})