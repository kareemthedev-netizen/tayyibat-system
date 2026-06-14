import os
import json
import requests
import re
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

# ========== 3️⃣ Imgur Scraper (مجاني، بدون مفتاح) ==========
def search_imgur(food_name):
    try:
        query = get_search_query(food_name)
        url = f"https://api.imgur.com/3/gallery/search/top/all/1?q={query}"
        # بعض نسخ Imgur API بتقبل طلبات بدون مفتاح للقراءة العامة
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('data'):
                for item in data['data']:
                    if item.get('images'):
                        for img in item['images']:
                            img_url = img.get('link')
                            if img_url and ('.jpg' in img_url or '.png' in img_url or '.jpeg' in img_url):
                                return img_url
    except Exception as e:
        print(f"  ⚠️ Imgur: {e}")
    return None

# ========== 4️⃣ Tavily (احتياطي، يحتاج مفتاح API) ==========
def search_tavily(food_name):
    if not TAVILY_API_KEY:
        print("  ⚠️ Tavily مفتاح غير موجود")
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
    
    # المصادر المجانية (بدون مفاتيح)
    url = search_searxng(food_name)
    if url:
        print("✅ SearXNG")
        return url
    
    url = search_openverse(food_name)
    if url:
        print("✅ Openverse")
        return url
    
    url = search_imgur(food_name)
    if url:
        print("✅ Imgur")
        return url
    
    # الحل الاحتياطي: Tavily (بمفتاح)
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

def sync_food(food, food_type):
    doc_ref = db.collection('foods').document(food['name'])
    doc = doc_ref.get()
    
    if doc.exists:
        existing = doc.to_dict()
        if not existing.get('imageUrl'):
            img_url = get_image_url(food['name'])
            if img_url:
                img_path = download_and_optimize(img_url, food['name'])
                if img_path:
                    doc_ref.update({'imageUrl': img_path, 'updatedAt': firestore.SERVER_TIMESTAMP})
                    print(f"  🖼️ تحديث صورة {food['name']}")
    else:
        img_url = get_image_url(food['name'])
        img_path = download_and_optimize(img_url, food['name']) if img_url else PLACEHOLDER_URL
        doc_ref.set({
            **food,
            "type": food_type,
            "imageUrl": img_path,
            "createdAt": firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.SERVER_TIMESTAMP
        })
        print(f"  ✅ إضافة {food['name']}")

def main():
    print("🚀 بدء المزامنة...")
    print("=" * 50)
    print("ترتيب البحث: SearXNG → Openverse → Imgur → Tavily (احتياطي)")
    print("=" * 50)
    
    with open("foods.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    allowed_names = {f['name'] for f in data.get("allowed", [])}
    forbidden_names = {f['name'] for f in data.get("forbidden", [])}
    limited_names = {f['name'] for f in data.get("limited", [])}
    
    for food in data.get("allowed", []) + data.get("forbidden", []) + data.get("limited", []):
        if food['name'] in allowed_names:
            sync_food(food, "allowed")
        elif food['name'] in forbidden_names:
            sync_food(food, "forbidden")
        else:
            sync_food(food, "limited")
    
    print("=" * 50)
    print("🎉 انتهت المزامنة!")

if __name__ == "__main__":
    main()
