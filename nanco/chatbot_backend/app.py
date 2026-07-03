from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from groq import Groq
from dotenv import load_dotenv
import tempfile
import uuid
from functools import wraps
from supabase import create_client, Client
import bcrypt

load_dotenv()

app = Flask(__name__)
# Enable CORS so our frontend can communicate with the backend
CORS(app)

# Initialize Supabase
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SECRET_KEY")
supabase: Client = None
if supabase_url and supabase_key:
    supabase = create_client(supabase_url, supabase_key)

ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "super-secret-nanco-token")

def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get("Authorization")
        if not token or token != f"Bearer {ADMIN_TOKEN}":
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function

# Initialize Groq client. Make sure GROQ_API_KEY is set in your environment or .env file!
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are Nanco AI, a helpful assistant for Nanco Paints (an ISO 9001-2015 certified company in Malappuram, Kerala). ONLY answer questions related to painting, paint products, and our services. Keep answers VERY short and concise.
You have access to several website tools and sections. When the user asks about a topic, you MUST suggest the relevant tool using exactly this format: [TOOL:Name|image_file|url].
Here is the exact syntax for each section you can suggest:
- Paint prices, costs, or estimating: [TOOL:Paint Calculator|assets/paint calculator.jpg|calculators.html] and [TOOL:Products|assets/products.jpg|products.html]
- Seeing how paint looks in a room: [TOOL:Virtual Paint Visualizer|assets/paint visualizer.jpg|paint_visualizer.html]
- Finding colors and inspiration: [TOOL:Color Studio|assets/colors.jpg|services.html]
- Downloading catalogs: [TOOL:Catalogs|assets/catelog.jpg|services.html]
- Info for paint workers/contractors: [TOOL:Worker Portal|assets/Paint Workers Portal.jpg|login/login.php]
- Finding nearby shops/outlets: [TOOL:Factory Outlets|assets/outlet.png|index.html]
- General services we offer: [TOOL:All Services|assets/house-bg1.png|services.html]
- Knowing more about Nanco: [TOOL:About Us|assets/sa.png|about_us.html]
Always include these [TOOL:...] tags in your response when applicable! DO NOT wrap them in markdown code blocks."""

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    
    if not user_message:
        return jsonify({'error': 'Message is required'}), 400

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            model="llama-3.1-8b-instant",
        )
        response_text = chat_completion.choices[0].message.content
        return jsonify({'response': response_text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/voice', methods=['POST'])
def voice():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
        
    audio_file = request.files['audio']
    
    try:
        # Save audio to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as temp_audio:
            audio_file.save(temp_audio.name)
            temp_audio_path = temp_audio.name

        # Transcribe using Groq Whisper API
        with open(temp_audio_path, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=(temp_audio_path, file.read()),
                model="whisper-large-v3",
                response_format="json",
                language="en"
            )
            
        # Clean up temp file
        os.remove(temp_audio_path)
        
        user_text = transcription.text
        
        # Forward the transcribed text to the LLM
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": user_text
                }
            ],
            model="llama-3.1-8b-instant",
        )
        response_text = chat_completion.choices[0].message.content
        
        return jsonify({
            'transcription': user_text,
            'response': response_text
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/videos', methods=['GET'])
def get_videos():
    videos_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'videos')
    if not os.path.exists(videos_dir):
        return jsonify([])
    try:
        files = [f for f in os.listdir(videos_dir) if f.lower().endswith('.mp4')]
        def get_sort_key(filename):
            name_without_ext = os.path.splitext(filename)[0]
            try:
                return (0, int(name_without_ext))
            except ValueError:
                return (1, filename)
        files.sort(key=get_sort_key)
        return jsonify(files)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- SUPABASE ENDPOINTS ---

@app.route('/api/data', methods=['GET'])
def get_data():
    if not supabase:
        return jsonify({"error": "Supabase not configured"}), 500
    try:
        products = supabase.table('products').select('*').order('created_at', desc=True).execute()
        images = supabase.table('gallery_images').select('*').order('created_at', desc=True).execute()
        hero = supabase.table('hero_backgrounds').select('*').order('created_at', desc=True).execute()
        
        return jsonify({
            "products": products.data,
            "images": images.data,
            "heroBgs": hero.data
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/upload', methods=['POST'])
@require_auth
def upload_file():
    if not supabase: return jsonify({"error": "Supabase not configured"}), 500
    if 'image' not in request.files: return jsonify({"error": "No image provided"}), 400
        
    file = request.files['image']
    file_ext = file.filename.split('.')[-1]
    file_name = f"{uuid.uuid4().hex}.{file_ext}"
    
    try:
        file_bytes = file.read()
        supabase.storage.from_('nanco-assets').upload(file_name, file_bytes, {"content-type": file.content_type})
        public_url = supabase.storage.from_('nanco-assets').get_public_url(file_name)
        return jsonify({"publicUrl": public_url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/products', methods=['POST'])
@require_auth
def add_product():
    if not supabase: return jsonify({"error": "Supabase not configured"}), 500
    try:
        res = supabase.table('products').insert(request.json).execute()
        return jsonify(res.data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/products/<int:item_id>', methods=['DELETE'])
@require_auth
def delete_product(item_id):
    if not supabase: return jsonify({"error": "Supabase not configured"}), 500
    try:
        # Fetch product to delete its image from storage
        res = supabase.table('products').select('image_url').eq('id', item_id).execute()
        if res.data and len(res.data) > 0 and res.data[0].get('image_url'):
            url = res.data[0]['image_url']
            if 'nanco-assets/' in url:
                file_name = url.split('nanco-assets/')[-1]
                if file_name:
                    supabase.storage.from_('nanco-assets').remove([file_name])
        
        supabase.table('products').delete().eq('id', item_id).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/images', methods=['POST'])
@require_auth
def add_image():
    if not supabase: return jsonify({"error": "Supabase not configured"}), 500
    try:
        res = supabase.table('gallery_images').insert(request.json).execute()
        return jsonify(res.data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/images/<int:item_id>', methods=['DELETE'])
@require_auth
def delete_image(item_id):
    if not supabase: return jsonify({"error": "Supabase not configured"}), 500
    try:
        # Fetch image to delete from storage
        res = supabase.table('gallery_images').select('url').eq('id', item_id).execute()
        if res.data and len(res.data) > 0 and res.data[0].get('url'):
            url = res.data[0]['url']
            if 'nanco-assets/' in url:
                file_name = url.split('nanco-assets/')[-1]
                if file_name:
                    supabase.storage.from_('nanco-assets').remove([file_name])

        supabase.table('gallery_images').delete().eq('id', item_id).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/hero', methods=['POST'])
@require_auth
def add_hero():
    if not supabase: return jsonify({"error": "Supabase not configured"}), 500
    try:
        res = supabase.table('hero_backgrounds').insert(request.json).execute()
        return jsonify(res.data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/hero/<int:item_id>', methods=['DELETE'])
@require_auth
def delete_hero(item_id):
    if not supabase: return jsonify({"error": "Supabase not configured"}), 500
    try:
        # Fetch the slide to extract and delete all associated images
        res = supabase.table('hero_backgrounds').select('*').eq('id', item_id).execute()
        if res.data and len(res.data) > 0:
            slide = res.data[0]
            files_to_delete = []
            
            for key in ['bucket_image_url', 'house_bg_url', 'house_bg_mobile_url']:
                if slide.get(key) and 'nanco-assets/' in slide[key]:
                    file_name = slide[key].split('nanco-assets/')[-1]
                    if file_name:
                        files_to_delete.append(file_name)
            
            if files_to_delete:
                supabase.storage.from_('nanco-assets').remove(files_to_delete)

        supabase.table('hero_backgrounds').delete().eq('id', item_id).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/hero/<int:item_id>', methods=['PUT'])
@require_auth
def update_hero(item_id):
    """Update settings for a specific hero background slide."""
    if not supabase: return jsonify({"error": "Supabase not configured"}), 500
    try:
        data = request.json
        res = supabase.table('hero_backgrounds').update(data).eq('id', item_id).execute()
        return jsonify(res.data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- HERO SETTINGS ENDPOINTS ---

@app.route('/api/hero-settings', methods=['GET'])
def get_hero_settings():
    if not supabase:
        return jsonify({"error": "Supabase not configured"}), 500
    try:
        res = supabase.table('hero_settings').select('*').limit(1).execute()
        if res.data and len(res.data) > 0:
            return jsonify(res.data[0])
        # Return defaults if no row exists
        return jsonify({
            "bg_color": "#c8d90f",
            "overlay_color": "#c8d90f",
            "tag_text": "ISO 9001-2015 Certified",
            "headline": "Paint for Better Lives.",
            "sub_text": "Nanco Paints brings premium-quality, certified paints to homes, offices, and factories across Kerala. Bold colours. Lasting finish.",
            "bucket_image_url": "assets/HERO-PAINT.png",
            "house_bg_url": "assets/house-bg.png",
            "hide_default_hero": False
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/hero-settings', methods=['POST'])
@require_auth
def save_hero_settings():
    if not supabase:
        return jsonify({"error": "Supabase not configured"}), 500
    try:
        data = request.json
        # Try to update the existing row (id=1), or insert if missing
        res = supabase.table('hero_settings').select('id').limit(1).execute()
        if res.data and len(res.data) > 0:
            row_id = res.data[0]['id']
            supabase.table('hero_settings').update(data).eq('id', row_id).execute()
        else:
            supabase.table('hero_settings').insert(data).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- AUTH ENDPOINTS ---

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username_or_email = data.get('username', '')
    password = data.get('password', '')

    admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
    admin_password = os.environ.get('ADMIN_PASSWORD', 'nanco-admin-pass')

    # 1. Check admin credentials first
    if username_or_email == admin_username and password == admin_password:
        return jsonify({
            'token': ADMIN_TOKEN,
            'role': 'admin',
            'name': 'Admin'
        })

    # 2. Check regular users in Supabase
    if supabase:
        try:
            result = supabase.table('users').select('*').eq('email', username_or_email).execute()
            if result.data and len(result.data) > 0:
                user = result.data[0]
                stored_hash = user.get('password_hash', '').encode('utf-8')
                if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
                    return jsonify({
                        'token': f"user-{user['id']}-{ADMIN_TOKEN[:8]}",
                        'role': user.get('role', 'user'),
                        'name': user.get('name', 'User'),
                        'email': user.get('email', '')
                    })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return jsonify({'error': 'Invalid credentials'}), 401


@app.route('/api/register', methods=['POST'])
def register():
    if not supabase:
        return jsonify({'error': 'Database not configured'}), 500

    data = request.json
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not name or not email or not password:
        return jsonify({'error': 'All fields are required'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    try:
        # Check if email already exists
        existing = supabase.table('users').select('id').eq('email', email).execute()
        if existing.data and len(existing.data) > 0:
            return jsonify({'error': 'An account with this email already exists'}), 409

        # Hash password with bcrypt
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Insert new user
        result = supabase.table('users').insert({
            'name': name,
            'email': email,
            'password_hash': password_hash,
            'role': 'user'
        }).execute()

        if result.data:
            user = result.data[0]
            return jsonify({
                'token': f"user-{user['id']}-{ADMIN_TOKEN[:8]}",
                'role': 'user',
                'name': user['name'],
                'email': user['email']
            })
        else:
            return jsonify({'error': 'Failed to create account'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(port=5000, debug=True)
