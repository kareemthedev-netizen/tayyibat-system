import os
import json
import requests
from firebase_admin import credentials, firestore, initialize_app
from PIL import Image
from io import BytesIO

# ========== الإعدادات ==========
FIREBASE_CRED = json.loads(os.environ.get("FIREBASE_SERVICE_ACCOUNT"))
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")

if not FIREBASE_CRED:
    raise Exception("Missing Firebase credentials")

cred = credentials.Certificate(FIREBASE_CRED)
initialize_app(cred)
db = firestore.client()

IMAGES_FOLDER = "images"
os.makedirs(IMAGES_FOLDER, exist_ok=True)

PLACEHOLDER_URL = "https://via.placeholder.com/300x200?text=%D8%B5%D9%88%D8%B1%D8%A9+%D8%BA%D9%8A%D8%B1+%D9%85%D8%AA%D9%88%D9%81%D8%B1%D8%A9"

# ========== كلمات بحث مخصصة ==========
SEARCH_QUERIES = {
    "الأرز": "rice grains",
    "البطاطس": "potato vegetable",
    "خبز القمح الكامل": "whole wheat bread",
    "الذرة": "corn cob",
    "زيت الزيتون": "olive oil",
    "لحم الضأن": "lamb meat",
    "لحم البقر": "beef steak",
    "السمك البلطي": "fresh fish tilapia",
    "التفاح": "red apple",
    "الموز": "banana fruit",
    "المانجو": "mango fruit",
    "الفراولة": "strawberries",
    "التمر": "dates fruit",
    "الخيار": "cucumber vegetable",
    "الخس": "lettuce leaves",
    "السبانخ": "spinach leaves",
    "الملوخية": "molokhia",
    "الدجاج": "chicken breast",
    "الخبز الأبيض": "white bread",
    "المكرونة": "pasta",
    "اللبن": "milk glass",
    "الفول": "fava beans",
}

def get_search_query(food_name):
    return SEARCH_QUERIES.get(food_name, f"{food_name} food")

# ========== 1️⃣ SearXNG (مجاني، بدون مفتاح) ==========
def search_searxng(food_name):
    try:
        query = get_search_query(food_name)
        url = "https://searx.tiekoetter.com/search"
        params = {'q': query, 'categories': 'images', 'format': 'json', 'image_proxy': True}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('results'):
                for result in data['results']:
                    img_url = result.get('img_src')
                    if img_url and not img_url.endswith('.svg') and 'placeholder' not in img_url:
                        return img_url
    except Exception as e:
        print(f"  ⚠️ SearXNG: {e}")
    return None

# ========== 2️⃣ Openverse (مجاني، بدون مفتاح) ==========
def search_openverse(food_name):
    try:
        query = get_search_query(food_name)
        url = f"https://api.openverse.engineering/v1/images/?q={query}&page_size=5"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('results'):
                for result in data['results']:
                    img_url = result.get('url')
                    if img_url:
                        return img_url
    except Exception as e:
        print(f"  ⚠️ Openverse: {e}")
    return None

# ========== 3️⃣ Tavily (احتياطي، يحتاج مفتاح) ==========
def search_tavily(food_name):
    if not TAVILY_API_KEY:
        return None
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=TAVILY_API_KEY)
        response = client.search(f"{food_name} طعام", include_images=True, max_results=1)
        images = response.get('images', [])
        return images[0] if images else None
    except Exception as e:
        print(f"  ⚠️ Tavily: {e}")
    return None

# ========== نظام البحث الطبقي ==========
def get_image_url(food_name):
    print(f"  🔍 {food_name}...", end=" ")
    
    url = search_searxng(food_name)
    if url:
        print("✅ SearXNG")
        return url
    
    url = search_openverse(food_name)
    if url:
        print("✅ Openverse")
        return url
    
    url = search_tavily(food_name)
    if url:
        print("⚠️ Tavily (احتياطي)")
        return url
    
    print("❌ مفيش صورة")
    return None

def download_and_optimize(image_url, food_name):
    if not image_url:
        return None
    try:
        response = requests.get(image_url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            img.thumbnail((300, 300))
            filename = f"{food_name}.webp"
            filepath = os.path.join(IMAGES_FOLDER, filename)
            img.save(filepath, 'webp', quality=75)
            return f"images/{filename}"
    except Exception as e:
        print(f"  ❌ فشل تحميل {food_name}: {e}")
    return None

# ========== المزامنة الذكية (تضيف الصور الناقصة بس) ==========
def sync_missing_images():
    print("🚀 بدء البحث عن الصور الناقصة...")
    print("=" * 50)
    
    # جلب جميع الأطعمة من Firebase
    docs = db.collection('foods').get()
    total = 0
    updated = 0
    
    for doc in docs:
        food_data = doc.to_dict()
        food_name = doc.id
        existing_image = food_data.get('imageUrl')
        
        # لو الصورة موجودة وليست placeholder، نتخطى
        if existing_image and existing_image != PLACEHOLDER_URL and 'placeholder' not in existing_image:
            print(f"⏩ {food_name}: صورة موجودة ✓")
            continue
        
        total += 1
        print(f"\n📸 {food_name}: ليس لديه صورة، أبحث...")
        
        image_url = get_image_url(food_name)
        if image_url:
            image_path = download_and_optimize(image_url, food_name)
            if image_path:
                doc.reference.update({
                    'imageUrl': image_path,
                    'updatedAt': firestore.SERVER_TIMESTAMP
                })
                updated += 1
                print(f"  ✅ تمت إضافة صورة {food_name}")
        else:
            print(f"  ❌ لم أجد صورة لـ {food_name}")
    
    print("\n" + "=" * 50)
    print(f"✅ تمت معالجة {total} صنف، وتم تحديث {updated} صورة جديدة")
    print("🎉 انتهى!")

if __name__ == "__main__":
    sync_missing_images()
