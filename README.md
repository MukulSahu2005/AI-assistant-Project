# llama3.1-8b_hybrid_AI_chatbot

A smart, real-time chatbot that combines the power of **Ollama's local LLMs** with **live web search** to provide rich, contextual answers. It supports both a sleek **GUI using Streamlit** and a fast **CLI mode** for terminal lovers.

---

## Features

- Streamed responses using local **LLaMA 3.1 8B** via [Ollama](https://ollama.com)
- Real-time **web search integration** (using Bing)
- Clean **web content extraction** via `readability-lxml` and `BeautifulSoup`
- User-friendly **Streamlit GUI**
- Lightweight **command-line interface**
- Supports multiple Ollama models
- Robust error handling and logging

---

## Project Structure

```

HybridChatBot  
├── gui_model.py          # Streamlit-based graphical chatbot  
├── model_ignition.py     # Command-line chatbot version  
├── requirements.txt      # Python dependencies  
└── README.md             # Documentation (this file)
```
---

## GUI Demo (Streamlit)
<img width="1902" height="864" alt="Screenshot 2026-09-18 162242" src="https://github.com/user-attachments/assets/a3e4f641-5eae-4b9e-93f9-db98977604f0" />


### Run the GUI

```
streamlit run gui_model.py
```
### Features

- Select Ollama model from sidebar
- Toggle internet access
- Ask both offline and real-time questions

Example prompts:

- "Explain how transformers work."
- "What's the temperature in Delhi today?"
- "Who won the latest World Cup?"

---

## CLI Demo

### Run the CLI

```

python model_ignition.py
```
### Features

- Terminal chat experience
- Type `exit` or `quit` to end the session
- Web triggers like:
  - "latest news"
  - "today’s weather"
  - "current stock price of Apple"

---

## Getting Started with Ollama (Offline LLaMA)

To run this chatbot offline using a local LLM (no OpenAI keys needed), follow these steps:

### Step 1: Install Ollama

Download and install Ollama from the official site:  
https://ollama.com/download

Choose your OS (Windows, macOS, Linux) and follow the installation instructions.

---

### Step 2: Download the Model

```

ollama pull llama3.1:8b
```
You can also pull other models like `mistral`, `gemma`, or `llama2`.

---

### Step 3: Start the ChatBot

Once the model is downloaded and Ollama is running in the background:

**For GUI:**

```

streamlit run gui_model.py
```
**For CLI:**

```

python model_ignition.py
```
Make sure Ollama is accessible at `http://localhost:11434`.

---

## Installation & Setup

### Step 1: Clone the Repo

```

git clone https://github.com/Bhimashri-Deka/miniature-goggles
```
cd miniature-goggles

### Step 2: Install Python Requirements

```

pip install -r requirements.txt
```
---

## How It Works

``` 
    A[User Prompt] --> B{Does it require web search?}
    B -- Yes --> C[Perform Bing Search]
    C --> D[Extract Relevant Web Content]
    D --> E[Append Web Content to Prompt]
    B -- No --> F[Use Original Prompt]
    E --> G[Send Prompt to Ollama API]
    F --> G
    G --> H[Stream Response Back to User]

```
---

## Tech Stack

| Component        | Technology              |
|------------------|--------------------------|
| Language Model   | Ollama + LLaMA 3.1       |
| GUI              | Streamlit                |
| Web Search       | Bing + BeautifulSoup     |
| Content Cleaner  | readability-lxml         |

---

## TODO / Future Plans

- Add citation-aware responses  
- PDF & document ingestion  
- Chat history saving/export  
- Speech-to-text input (voice chat)  
- Deploy on cloud (optional remote mode)

---

## Author

**Bhimashri Deka**  
---
