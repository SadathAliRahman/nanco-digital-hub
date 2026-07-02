from flask import Flask, request, jsonify, send_from_directory, send_file, after_this_request
from flask_cors import CORS
import os
from groq import Groq
from dotenv import load_dotenv
import tempfile

# Load environment variables relative to this file
current_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(current_dir, '.env')
load_dotenv(dotenv_path)

# Safely extract GROQ_API_KEY from environment
api_key = os.environ.get("GROQ_API_KEY")

# Initialize Flask app to serve local static files from the card folder
app = Flask(__name__, static_folder=current_dir, static_url_path='')
CORS(app)

@app.route('/')
def serve_index():
    return send_from_directory(current_dir, 'index.html')

@app.route('/api/translate', methods=['POST'])
@app.route('/translate', methods=['POST'])
def translate_api():
    data = request.json or {}
    text = data.get('text', '')
    source_lang = data.get('source_lang', 'auto')
    target_lang = data.get('target_lang', 'English')
    model = data.get('model', 'groq-8b')
    client_api_key = data.get('api_key', '')

    if not text:
        return jsonify({'error': 'Text is required'}), 400

    use_key = client_api_key or api_key
    if not use_key:
        return jsonify({'error': 'No Groq API Key configured on server. Please supply one in Config settings.'}), 400

    try:
        temp_client = Groq(key=use_key) if hasattr(Groq, 'key') else Groq(api_key=use_key)
        
        groq_model_name = 'llama-3.1-8b-instant'
        if model == 'groq-70b':
            groq_model_name = 'llama-3.3-70b-versatile'
        elif model == 'groq-mixtral':
            groq_model_name = 'mixtral-8x7b-32768'
        elif model == 'groq-gemma2':
            groq_model_name = 'gemma2-9b-it'
        
        system_prompt = f"You are an expert, fluent translator. Translate the following text into {target_lang}. ONLY output the raw translated text. Do not include quotes, conversational filler, or explanations."
        
        chat_completion = temp_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            model=groq_model_name,
            temperature=0.3,
            max_tokens=1024
        )
        translated_text = chat_completion.choices[0].message.content.strip()
        return jsonify({
            'translated_text': translated_text,
            'model_used': model
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tts', methods=['POST'])
def tts_api():
    data = request.json or {}
    text = data.get('text', '')
    lang = data.get('lang', 'en')

    if not text:
        return jsonify({'error': 'Text is required'}), 400

    try:
        from gtts import gTTS
        import tempfile

        # Clean lang code to match gtts expected format (e.g., 'en' instead of 'en-US')
        lang_code = lang.split('-')[0]

        tts = gTTS(text=text, lang=lang_code)
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_audio:
            temp_path = temp_audio.name
            
        tts.save(temp_path)

        @after_this_request
        def cleanup(response):
            try:
                os.remove(temp_path)
            except Exception as e:
                app.logger.error(f"Error removing temp tts file: {e}")
            return response

        return send_file(temp_path, mimetype='audio/mpeg')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/transcribe-raw', methods=['POST'])
@app.route('/transcribe-raw', methods=['POST'])
def transcribe_raw():
    client_api_key = request.form.get('api_key', '')
    use_key = client_api_key or api_key
    if not use_key:
        return jsonify({'error': 'No Groq API Key configured on server. Please supply one in Config settings.'}), 400

    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
        
    audio_file = request.files['audio']
    source_lang = request.form.get('source_lang', 'auto')
    
    try:
        temp_client = Groq(key=use_key) if hasattr(Groq, 'key') else Groq(api_key=use_key)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as temp_audio:
            audio_file.save(temp_audio.name)
            temp_audio_path = temp_audio.name

        with open(temp_audio_path, "rb") as file:
            transcribe_args = {
                "file": (temp_audio_path, file.read()),
                "model": "whisper-large-v3",
                "response_format": "json"
            }
            if source_lang and source_lang != 'auto':
                lang_code = source_lang.split('-')[0]
                transcribe_args["language"] = lang_code
                
            transcription = temp_client.audio.transcriptions.create(**transcribe_args)
            
        os.remove(temp_audio_path)
        
        return jsonify({
            'text': transcription.text
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Running on port 5001 to keep it separated from the main Nanco web application
    print("Starting separated Nanco AI Voice Translator backend on port 5001...")
    app.run(port=5001, debug=True)
