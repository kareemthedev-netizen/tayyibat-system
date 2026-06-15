import os
import json
import requests
from firebase_admin import credentials, firestore, initialize_app
from datetime import datetime

# ========== الإعدادات ==========
FIREBASE_CRED = json.loads(os.environ.get("FIREBASE_SERVICE_ACCOUNT"))
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")

if not FIREBASE_CRED:
    raise Exception("Missing Firebase credentials")

cred = credentials.Certificate(FIREBASE_CRED)
initialize_app(cred)
db = firestore.client()

PLACEHOLDER_URL = "https://via.placeholder.com/300x200?text=%D8%B5%D9%88%D8%B1%D8%A9+%D8%BA%D9%8A%D8%B1+%D9%85%D8%AA%D9%88%D9%81%D8%B1%D8%A9"

# ========== كلمات بحث مخصصة ==========
SEARCH_QUERIES = {
    "الأرز": "rice grains white background studio lighting",
    "البطاطس": "potato isolated white background high resolution",
    "خبز القمح الكامل": "whole wheat bread isolated white background",
    "الذرة": "corn cob isolated white background",
    "زيت الزيتون": "olive oil bottle white background product",
    "لحم الضأن": "raw lamb meat cut white background",
    "لحم البقر": "raw beef steak isolated white background",
    "السمك البلطي": "fresh tilapia fish white background",
    "التفاح": "red apple isolated white background",
    "الموز": "banana isolated white background",
    "المانجو": "mango fruit isolated white background",
    "الفراولة": "strawberries isolated white background",
    "التمر": "dates fruit isolated white background",
    "الخيار": "cucumber isolated white background",
    "الخس": "lettuce leaves isolated white background",
    "السبانخ": "spinach leaves isolated white background",
    "الملوخية": "molokhia leaves white background",
    "المكرونة": "pasta isolated white background high resolution",
    "اليوسفي": "tangerine fruit isolated white background",
    "الدجاج": "raw chicken breast white background product photography",
    "الخبز الأبيض": "white bread sliced isolated white background",
    "اللبن": "glass of milk isolated white background",
    "الفول": "fava beans isolated white background",
    "البيض": "eggs isolated white background",
}

def get_search_query(food_name):
    return SEARCH_QUERIES.get(food_name, f"{food_name} food white background isolated")

# ========== فحص الرابط ==========
def check_image_url(url):
    if not url:
        return False
    if 'placeholder' in url or url == PLACEHOLDER_URL:
        return False
    try:
        response = requests.head(url, timeout=10, allow_redirects=True)
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            if 'image' in content_type:
                return True
    except:
        pass
    return False

# ========== مصادر البحث ==========
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
                        if 'white' in img_url.lower() or 'isolated' in img_url.lower():
                            return img_url
                return data['results'][0].get('img_src')
    except:
        pass
    return None

def search_openverse(food_name):
    try:
        query = get_search_query(food_name)
        url = f"https://api.openverse.engineering/v1/images/?q={query}&page_size=10"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('results'):
                for result in data['results']:
                    img_url = result.get('url')
                    if img_url:
                        if 'white' in img_url.lower() or 'isolated' in img_url.lower():
                            return img_url
                return data['results'][0].get('url')
    except:
        pass
    return None

def search_tavily(food_name):
    if not TAVILY_API_KEY:
        return None
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=TAVILY_API_KEY)
        response = client.search(f"{food_name} طعام خلفية بيضاء", include_images=True, max_results=3)
        images = response.get('images', [])
        return images[0] if images else None
    except:
        pass
    return None

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
        print("⚠️ Tavily")
        return url
    
    print("❌ مفيش")
    return None

def update_broken_images_only():
    print("🚀 بدء فحص وتحديث الروابط...")
    print("=" * 50)
    
    docs = db.collection('foods').get()
    docs_list = list(docs)
    total = len(docs_list)
    updated = 0
    working = 0
    failed = 0
    
    for doc in docs_list:
        food_data = doc.to_dict()
        food_name = doc.id
        current_image = food_data.get('imageUrl', '')
        
        print(f"\n📸 {food_name}:", end=" ")
        
        if check_image_url(current_image):
            print("✅ شغال ✓")
            working += 1
            continue
        
        print("❌ بايظ، أبحث...")
        
        image_url = get_image_url(food_name)
        
        if image_url:
            doc.reference.update({
                'imageUrl': image_url,
                'updatedAt': firestore.SERVER_TIMESTAMP
            })
            updated += 1
            print(f"  ✅ تم تحديث {food_name}")
        else:
            doc.reference.update({
                'imageUrl': PLACEHOLDER_URL,
                'updatedAt': firestore.SERVER_TIMESTAMP
            })
            failed += 1
            print(f"  ⚠️ صورة افتراضية لـ {food_name}")
    
    print("\n" + "=" * 50)
    print(f"✅ شغال وتم تخطيه: {working}")
    print(f"🔄 تم تحديث روابط بايظة: {updated}")
    print(f"⚠️ صور افتراضية: {failed}")
    print(f"📋 المجموع: {total}")
    print("🎉 انتهى!")

if __name__ == "__main__":
    update_broken_images_only()
