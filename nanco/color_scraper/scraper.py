from bs4 import BeautifulSoup
import colorsys
import json

def get_color_categories(hex_code):
    """
    Calculates and returns a list of all categories a color belongs to, 
    including technical theory and psychological moods.
    """
    categories = []
    hex_code = hex_code.strip('#')
    if len(hex_code) != 6:
        return ["Unknown"]
    
    # Convert hex to RGB (0 to 1)
    r, g, b = tuple(int(hex_code[i:i+2], 16) / 255.0 for i in (0, 2, 4))
    
    # Convert RGB to HSL (Hue 0-1, Lightness 0-1, Saturation 0-1)
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    
    h_deg = h * 360  # 0-360
    s_pct = s * 100  # 0-100
    l_pct = l * 100  # 0-100

    # ---------------------------------------------------------
    # 1. Base & Temperature (Neutral vs. Color Wheel)
    # ---------------------------------------------------------
    is_neutral = s_pct < 15 or l_pct < 15 or l_pct > 90
    
    if is_neutral:
        categories.append("Temperature: Neutral")
        categories.append("Wheel: Neutral Colors")
        if l_pct > 90:
            categories.append("Variation: Tint (Near White)")
        elif l_pct < 15:
            categories.append("Variation: Shade (Near Black)")
        else:
            categories.append("Variation: Tone (Gray/Muted)")
    else:
        # 12-Part Color Wheel & Temperature
        if h_deg < 15 or h_deg >= 345:
            categories.extend(["Wheel: Red (Primary)", "Temperature: Warm"])
        elif h_deg < 30:
            categories.extend(["Wheel: Red-Orange (Tertiary)", "Temperature: Warm"])
        elif h_deg < 45:
            categories.extend(["Wheel: Orange (Secondary)", "Temperature: Warm"])
        elif h_deg < 60:
            categories.extend(["Wheel: Yellow-Orange (Tertiary)", "Temperature: Warm"])
        elif h_deg < 75:
            categories.extend(["Wheel: Yellow (Primary)", "Temperature: Warm"])
        elif h_deg < 105:
            categories.extend(["Wheel: Yellow-Green (Tertiary)", "Temperature: Cool"])
        elif h_deg < 150:
            categories.extend(["Wheel: Green (Secondary)", "Temperature: Cool"])
        elif h_deg < 195:
            categories.extend(["Wheel: Blue-Green (Tertiary)", "Temperature: Cool"])
        elif h_deg < 240:
            categories.extend(["Wheel: Blue (Primary)", "Temperature: Cool"])
        elif h_deg < 270:
            categories.extend(["Wheel: Blue-Purple (Tertiary)", "Temperature: Cool"])
        elif h_deg < 300:
            categories.extend(["Wheel: Purple (Secondary)", "Temperature: Cool"])
        else: 
            categories.extend(["Wheel: Red-Purple (Tertiary)", "Temperature: Warm"])

        # Variation
        if l_pct > 65:
            categories.append("Variation: Tint (Mixed with White)")
        elif l_pct < 35:
            categories.append("Variation: Shade (Mixed with Black)")
        elif s_pct < 50:
            categories.append("Variation: Tone (Mixed with Gray)")
        else:
            categories.append("Variation: Pure/Base Hue")

    # ---------------------------------------------------------
    # 2. Mood & Aesthetic Analysis
    # ---------------------------------------------------------
    
    # Cute / Pastel: Light, softly saturated colors
    if l_pct >= 70 and 20 <= s_pct <= 80:
        categories.append("Mood: Cute / Pastel")
        
    # Calm / Soothing: Cool hues (Green to Purple) that are muted or light
    if (90 <= h_deg <= 270) and (s_pct <= 50 or l_pct >= 70):
        categories.append("Mood: Calm / Soothing")
        
    # Energetic / Vibrant: Highly saturated, mid-lightness colors
    if s_pct >= 75 and 40 <= l_pct <= 65:
        categories.append("Mood: Energetic / Vibrant")
        
    # Elegant / Moody: Dark, desaturated colors
    if l_pct <= 45 and s_pct <= 35:
        categories.append("Mood: Elegant / Moody")
        
    # Earthy / Natural: Warm-to-Green hues that are dark and muted (Browns, Olives, Terracottas)
    if (25 <= h_deg <= 140) and (20 <= l_pct <= 55) and (15 <= s_pct <= 60):
        categories.append("Mood: Earthy / Natural")
        
    # Clean / Minimal: Whites, very light grays
    if l_pct >= 90 and s_pct <= 10:
        categories.append("Mood: Clean / Minimal")

    return categories

def generate_multi_category_json():
    try:
        with open('colors.txt', 'r', encoding='utf-8') as file:
            html_data = file.read()
    except FileNotFoundError:
        print("Error: 'colors.txt' not found.")
        return

    soup = BeautifulSoup(html_data, 'html.parser')
    color_items = soup.find_all('div', class_='color-item')
    
    master_palette = {}

    for item in color_items:
        name = item.get('data-name', '').strip()
        color_id = item.get('data-id', '').strip()
        hex_code = item.get('data-hex', '').strip()
        
        assigned_categories = get_color_categories(hex_code)
        
        color_data = {
            'name': name,
            'id': color_id,
            'hex': hex_code,
            'all_tags': assigned_categories
        }
            
        for category in assigned_categories:
            if category not in master_palette:
                master_palette[category] = []
            master_palette[category].append(color_data)

    with open('multi_category_palette.json', 'w', encoding='utf-8') as json_file:
        json.dump(master_palette, json_file, indent=4)
        
    print("Success! The multi-categorized data is saved to 'multi_category_palette.json'.")

if __name__ == "__main__":
    generate_multi_category_json()