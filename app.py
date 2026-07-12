import os
import json
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Import agent package
from agents.config import set_api_key, is_live_mode, get_api_key
from agents.coordinator import run_coordination_pipeline

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# Ensure folders exist
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    if request.method == 'POST':
        data = request.json or {}
        api_key = data.get('api_key', '').strip()
        set_api_key(api_key)
        # Optionally write back to a local temporary session/env file if desired
        return jsonify({
            "success": True,
            "is_configured": is_live_mode(),
            "message": "Gemini API key updated successfully." if api_key else "Switched to Simulation Mode."
        })
    else:
        return jsonify({
            "is_configured": is_live_mode(),
            "mode": "Live (Gemini API Connected)" if is_live_mode() else "Simulation Mode (Interactive Mock)"
        })

@app.route('/api/upload', methods=['POST'])
def upload_blueprint():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Append unique prefix to avoid caching issues
        import time
        unique_filename = f"{int(time.time())}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        try:
            # We run blueprint analysis immediately to extract room coords and measurements
            from agents.blueprint import analyze_blueprint
            spatial_data = analyze_blueprint(file_path)
            
            return jsonify({
                "success": True,
                "filename": unique_filename,
                "file_url": f"/uploads/{unique_filename}",
                "image_path": file_path,
                "spatial_data": spatial_data
            })
        except Exception as e:
            return jsonify({"error": f"Failed to analyze floor plan: {str(e)}"}), 500
            
    return jsonify({"error": "Unsupported file format. Please upload PNG, JPG, JPEG, or WEBP."}), 400

def create_schematic_blueprint(file_path):
    from PIL import Image, ImageDraw
    width, height = 1000, 750
    img = Image.new('RGB', (width, height), color='#0b0e1a')
    draw = ImageDraw.Draw(img)
    
    # Draw fine blueprint grid lines
    grid = 50
    for x in range(0, width, grid):
        draw.line([(x, 0), (x, height)], fill='#141a30', width=1)
    for y in range(0, height, grid):
        draw.line([(0, y), (width, y)], fill='#141a30', width=1)
        
    def get_box(pct_coords):
        rx, ry, rw, rh = pct_coords
        return [
            int(rx / 100 * width),
            int(ry / 100 * height),
            int((rx + rw) / 100 * width),
            int((ry + rh) / 100 * height)
        ]
        
    regions = [
        {"name": "Main Office Area\n(40' x 24')", "coords": [10, 10, 40, 35], "color": "#00d2ff"},
        {"name": "Conference Room A\n(24' x 20')", "coords": [55, 10, 35, 20], "color": "#00d2ff"},
        {"name": "Manager Office\n(16' x 24')", "coords": [55, 62, 20, 28], "color": "#00d2ff"},
        {"name": "Pantry & Restroom\n(10' x 25')", "coords": [77, 62, 13, 28], "color": "#00d2ff"},
        {"name": "Corridor A\n(W: 0.9m)", "coords": [10, 48, 70, 10], "color": "#ffaa00"},
        {"name": "Main Exit", "coords": [5, 49, 5, 8], "color": "#00ffaa"},
        {"name": "Fire Exit", "coords": [80, 49, 5, 8], "color": "#00ffaa"}
    ]
    
    for r in regions:
        box = get_box(r["coords"])
        draw.rectangle(box, outline=r["color"], width=3)
        inner_box = [box[0]+4, box[1]+4, box[2]-4, box[3]-4]
        draw.rectangle(inner_box, outline='#1c233a', width=1)
        draw.text((box[0] + 12, box[1] + 12), r["name"], fill='#8b9bb4')

    # Draw door swing details (diagonal lines/arcs)
    draw.line([(50, 370), (20, 340)], fill='#00ffaa', width=2)
    draw.line([(800, 370), (830, 340)], fill='#00ffaa', width=2)
    
    # Title Block
    draw.rectangle([650, 680, 970, 730], outline='#00d2ff', width=2)
    draw.text((665, 690), "BUILDSENSE SCHEMATIC PLAN - PHASE 2", fill='#00d2ff')
    draw.text((665, 708), "SCALE: 1:50 | AREA: 2400 SQ FT | BYELAWS: NBC", fill='#8b9bb4')

    img.save(file_path)

@app.route('/api/query', methods=['POST'])
def process_query():
    data = request.json or {}
    user_query = data.get('query', '').strip()
    image_path = data.get('image_path', '').strip()
    budget_limit_raw = data.get('budget_limit', None)
    
    if not user_query:
        return jsonify({"error": "Query cannot be empty"}), 400
        
    # Budget parsing helper (e.g. ₹15 lakh -> 1500000, 1500000 -> 1500000)
    budget_limit = None
    if budget_limit_raw is not None:
        try:
            budget_limit = int(float(budget_limit_raw))
        except (ValueError, TypeError):
            pass
            
    # Try parsing budget from query text if not explicitly provided
    if budget_limit is None:
        # Detect '15 lakh' -> 1500000, etc.
        import re
        lakh_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:lakh|l)', user_query, re.IGNORECASE)
        if lakh_match:
            try:
                budget_limit = int(float(lakh_match.group(1)) * 100000)
            except ValueError:
                pass
        else:
            # Check for regular numbers e.g. 1500000 or 15,00,000
            numbers_match = re.findall(r'₹?\s*(\d[\d,\s]*)', user_query)
            for num_str in numbers_match:
                clean_num = num_str.replace(',', '').replace(' ', '')
                if clean_num:
                    try:
                        val = int(clean_num)
                        if val > 10000:  # Sensible minimum to ignore small counts
                            budget_limit = val
                            break
                    except ValueError:
                        pass

    # If no image path provided, we can look in upload folder for the latest upload, 
    # or use a mock path if running in simulation
    if not image_path:
        files = os.listdir(app.config['UPLOAD_FOLDER'])
        images = [f for f in files if allowed_file(f)]
        if images:
            # Get latest
            images.sort()
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], images[-1])
        else:
            # Mock file path for simulation mode when no image uploaded yet
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], "mock_blueprint.png")
            # Create a simple mock blank image if it doesn't exist
            if not os.path.exists(image_path):
                create_schematic_blueprint(image_path)
                
    try:
        # Run orchestration
        result = run_coordination_pipeline(image_path, user_query, budget_limit=budget_limit)
        
        # Include budget limit in return
        result["budget_limit_parsed"] = budget_limit
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Error running coordination pipeline: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    print(f"Starting BuildSense server on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=True)
