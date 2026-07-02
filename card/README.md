# Nanco AI Live Voice Translator Backend

This folder contains the standalone translation and transcription service powered by Groq.

## Security Setup
The application has been configured to load your Groq API key securely from a `.env` file instead of passing it through the frontend browser.
- The `.env` file has been created and configured with your API key.
- The `.gitignore` file has been updated to ensure your `.env` credentials are never committed.
- In the frontend **Config** panel (gear icon), you can leave the **Groq API Key** field blank, and the app will automatically use the secure server-side key.

## Installation
To run the server, make sure you have Python 3 installed. Install the dependencies by running the module directly (this bypasses Device Guard policies):
```bash
python -m pip install -r requirements.txt
```

## Running the Server
Start the Flask backend:
```bash
python app.py
```
The server will start on port `5001`. You can then open `index.html` directly in your browser or access it at `http://localhost:5001`.
"# nanco-digital-hub" 
