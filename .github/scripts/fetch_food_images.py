import os
import re
import requests
from tavily import TavilyClient
from bs4 import BeautifulSoup

TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
if not TAVILY_API_KEY:
    raise Exception("TAVILY_API_KEY not found in secrets")

tavily = TavilyClient(api_key=TAVILY_API_KEY)

FOODS_FILE = "foods-database.html"
IMAGES_FOLDER = "images"
os.makedirs(IMAGES_FOLDER, exist_ok=True)

def get_food_list_from_html():
    """يقرأ أسماء الأطعمة من ملف HTML"""
    with open(FOODS_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    soup = BeautifulSoup(content, 'html.parser')
    foods = []
    
    # البحث عن بطاقات الطعام
    for card in soup.find_all('div', class_='food-card'):
        name_tag = card.find('h3')
        if name_tag:
            food_name = name_tag.get_text(strip=True)
            foods.append(food_name)
    
    return foods

def fetch_image_url(food_name):
    """يجيب رابط صورة من Tavily"""
    try:
        response = tavily.search(f"{food_name} طعام خلفية بيضاء", include_images=True, max_results=1)
        images = response.get('images', [])
        if images:
            return images[0]
    except Exception as e:
        print(f"⚠️ خطأ في البحث عن {food_name}: {e}")
    return None

def download_image(image_url, food_name):
    """تحميل الصورة وتحويلها لـ WebP"""
    try:
        response = requests.get(image_url, timeout=15)
        if response.status_code == 200:
            from PIL import Image
            from io import BytesIO
            
            img = Image.open(BytesIO(response.content))
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            img.thumbnail((300, 300))
            
            filename = f"{food_name}.webp"
            filepath = os.path.join(IMAGES_FOLDER, filename)
            img.save(filepath, 'webp', quality=75)
            print(f"✅ تحميل: {filename}")
            return filename
    except Exception as e:
        print(f"❌ فشل تحميل {food_name}: {e}")
    return None

def update_html_with_image(food_name, image_filename):
    """يعدل ملف HTML ويضيف الصورة"""
    with open(FOODS_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # البحث عن بطاقة الطعام المطلوبة
    pattern = rf'(<div class="food-card">.*?<h3>{food_name}</h3>.*?<div class="food-card-image">).*?(</div>)'
    
    def replace_image(match):
        return f'{match.group(1)}<img src="{IMAGES_FOLDER}/{image_filename}" alt="{food_name}">{match.group(2)}'
    
    new_content = re.sub(pattern, replace_image, content, flags=re.DOTALL)
    
    with open(FOODS_FILE, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"📝 تم تحديث: {food_name}")

def main():
    print("🚀 بدء تحديث الصور...")
    foods = get_food_list_from_html()
    print(f"📋 وجدت {len(foods)} صنف طعام")
    
    for food in foods:
        print(f"🔍 ببحث عن: {food}")
        image_url = fetch_image_url(food)
        
        if image_url:
            image_file = download_image(image_url, food)
            if image_file:
                update_html_with_image(food, image_file)
        else:
            print(f"⚠️ مفيش صورة لـ {food}")

if __name__ == "__main__":
    main()
