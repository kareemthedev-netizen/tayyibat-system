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
    "الأرز": "rice grains white food",
    "البطاطس": "potato vegetable raw",
    "خبز القمح الكامل": "whole wheat bread loaf",
    "الذرة": "corn cob fresh yellow",
    "زيت الزيتون": "olive oil bottle",
    "لحم الضأن": "lamb meat raw",
    "لحم البقر": "beef steak raw",
    "السمك البلطي": "fresh tilapia fish",
    "التفاح": "red apple fruit whole",
    "الموز": "banana fruit bunch",
    "المانجو": "mango fruit yellow",
    "الفراولة": "strawberries fresh",
    "التمر": "dates fruit bunch",
    "الخيار": "cucumber vegetable green",
    "الخس": "lettuce leaves green",
    "السبانخ": "spinach leaves fresh",
    "الملوخية": "molokhia leaves",
    "الدجاج": "chicken breast raw",
    "الخبز الأبيض": "white sliced bread",
    "المكرونة": "pasta uncooked",
    "اللبن": "glass of milk",
    "الفول": "fava beans raw",
}

def get_search_query(food_name):
    return SEARCH_QUERIES.get(food_name, f"{food_name} food")

# ========== المصادر المجانية (بدون API keys) ==========

def search_searxng(food_name):
    """SearXNG - مجاني، بدون مفتاح"""
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

def search_openverse(food_name):
    """Openverse - مجاني، بدون مفتاح"""
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

# ========== Tavily (احتياطي - يحتاج مفتاح) ==========

def search_tavily(food_name):
    """Tavily - احتياطي، يستهلك Credits"""
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
    
    # 1. SearXNG (مجاني)
    url = search_searxng(food_name)
    if url:
        print("✅ SearXNG")
        return url
    
    # 2. Openverse (مجاني)
    url = search_openverse(food_name)
    if url:
        print("✅ Openverse")
        return url
    
    # 3. Tavily (احتياطي)
    url = search_tavily(food_name)
    if url:
        print("⚠️ Tavily (احتياطي)")
        return url
    
    print("❌ مفيش صورة")
    return None

def download_and_optimize(image_url, food_name):
    """تحميل الصورة وتحويلها إلى WebP"""
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
            print(f"  ✅ تم تحميل: {filename}")
            return f"images/{filename}"
    except Exception as e:
        print(f"  ❌ فشل تحميل {food_name}: {e}")
    return None

# ========== المزامنة الرئيسية ==========

def sync_all_foods():
    """يضيف جميع الأطعمة من foods.json مع صورها"""
    print("🚀 بدء مزامنة الأطعمة مع Firebase...")
    print("=" * 50)
    print("ترتيب البحث: SearXNG → Openverse → Tavily (احتياطي)")
    print("=" * 50)
    
    # قراءة الأطعمة من foods.json
    with open("foods.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    allowed_names = {f['name'] for f in data.get("allowed", [])}
    forbidden_names = {f['name'] for f in data.get("forbidden", [])}
    limited_names = {f['name'] for f in data.get("limited", [])}
    
    all_foods = data.get("allowed", []) + data.get("forbidden", []) + data.get("limited", [])
    
    for food in all_foods:
        food_name = food['name']
        
        # تحديد النوع
        if food_name in allowed_names:
            food_type = "allowed"
        elif food_name in forbidden_names:
            food_type = "forbidden"
        else:
            food_type = "limited"
        
        print(f"\n📌 معالجة: {food_name} ({food_type})")
        
        # البحث عن صورة
        image_url = get_image_url(food_name)
        image_path = download_and_optimize(image_url, food_name) if image_url else PLACEHOLDER_URL
        
        # حفظ في Firebase
        doc_ref = db.collection('foods').document(food_name)
        doc_ref.set({
            "name": food_name,
            "type": food_type,
            "category": food.get("category", ""),
            "desc": food.get("desc", ""),
            "benefits": food.get("benefits", ""),
            "warning": food.get("warning", ""),
            "quantity": food.get("quantity", ""),
            "imageUrl": image_path,
            "createdAt": firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.SERVER_TIMESTAMP
        })
        print(f"  ✅ تمت إضافة {food_name} إلى Firebase")

def sync_missing_images():
    """يضيف الصور فقط للأطعمة اللي مفيهاش صورة"""
    print("🚀 بدء إضافة الصور الناقصة...")
    print("=" * 50)
    
    docs = db.collection('foods').get()
    updated = 0
    
    for doc in docs:
        food_data = doc.to_dict()
        food_name = doc.id
        existing_image = food_data.get('imageUrl')
        
        # لو الصورة موجودة، نتخطى
        if existing_image and existing_image != PLACEHOLDER_URL and 'placeholder' not in existing_image:
            print(f"⏩ {food_name}: صورة موجودة ✓")
            continue
        
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
    print(f"✅ تم تحديث {updated} صورة جديدة")

if __name__ == "__main__":
    # اختر التشغيل المطلوب:
    
    # 1. لو عايز تضيف كل الأطعمة من البداية (مع الصور):
    sync_all_foods()
    
    # 2. لو عايز تضيف الصور الناقصة فقط (علق السطر اللي فوق وافتح اللي تحت):
    # sync_missing_images()
