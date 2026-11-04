# Grounds AI: Local Knowledge on Spent Coffee Grounds in Bangkok

A Gen AI class project on "AI with local knowledge".

## Team

| Name |
|---|
| Yosapat Suttirattanapan |
| Pholaphat Atchararuji |
| Pasawich Meemanee |

## Topic

How can an AI with local knowledge answer questions about reusing spent coffee grounds from Bangkok cafés?

Bangkok has thousands of cafés, and most of their used coffee grounds go to waste. General AI chatbots know a lot about coffee in general, but very little about local cafés, Thai research and what is actually possible in Bangkok. We want to see if giving the AI our own local documents makes its answers more accurate and more useful.

## How the app works

Grounds AI is a small website that runs on your own computer. It uses **Retrieval-Augmented Generation (RAG)**:

1. You upload PDFs on the **Documents** page.
2. The app reads each page with PyMuPDF and cuts the text into short, overlapping passages.
3. Each passage is turned into a vector (embedding) by the local `nomic-embed-text` model and saved in a SQLite file.
4. When you ask a question, the app finds the most similar passages and sends them to the local `gemma3:1b` model with your question.
5. The answer cites the file and page it came from. If the documents do not cover the question, the AI says so.

You can untick **Use my documents** on the chat page to compare with a normal AI answer.

## Documents we use

The PDFs are not stored in this repository (they stay on our own computers).

1. Al Balushi et al. (2025). *A Comprehensive Review on Sustainable Conversion of Spent Coffee Grounds into Energy Resources and Environmental Applications.* Biomass, 5(3), 55. https://www.mdpi.com/2673-8783/5/3/55
2. Thuthaisong et al. (2025). *Antioxidant Compounds from Spent Coffee Grounds (SCGs).* 1st Sustainable Development National Conference, Mahidol University. https://en.mahidol.ac.th/ensdp/index.php/ensdproceeding/article/download/36/22/92
3. Putri, Djamil and Faizatun (2021). *Body Scrub Containing Virgin Coconut Oil, Coffee Grounds and Activated Carbon Coconut Shell as a Moisturiser and a Skin Brightener.* Scripta Medica, 52(1), 76-81. https://scindeks-clanci.ceon.rs/data/pdf/2490-3329/2021/2490-33292101076D.pdf

## Requirements

- Python 3.9 or newer
- [Ollama](https://ollama.com/) installed and running

Download the two models once:

```bash
ollama pull gemma3:1b
ollama pull nomic-embed-text
```

## Run the app

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000 in your browser.

## Project files

| File | What it does |
|---|---|
| `app.py` | Flask server: PDF upload, passage splitting, embeddings, search and chat |
| `templates/` | HTML pages (chat and documents) |
| `static/app.js` | Chat page logic (sends messages, shows sources, keeps history in the browser) |
| `static/style.css` | Page styles |
| `requirements.txt` | Python packages |

## Example questions

- How can cafés reuse spent coffee grounds?
- Can spent coffee grounds be used in a body scrub? What did the study find?
- What antioxidant compounds are found in spent coffee grounds?
- What are the energy uses of spent coffee grounds, and what are the challenges?
