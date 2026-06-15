import os
import json
import requests
from firebase_admin import credentials, firestore, initialize_app
from datetime import datetime
import time

FIREBASE_CRED = json.loads(os.environ.get("FIREBASE_SERVICE_ACCOUNT"))
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")

cred = credentials.Certificate(FIREBASE_CRED)
initialize_app(cred)
db = firestore.client()

PLACEHOLDER = "https://via.placeholder.com/300x200?text=%D8%B5%D9%88%D8%B1%D8%A9+%D8%BA%D9%8A%D8%B1+%D9%85%D8%AA%D9%88%D9%81%D8%B1%D8%A9"

# ========== كلمات البحث ==========
SEARCH = {
    "الأرز": "rice grains white background",
    "البطاطس": "potato isolated white",
    "المكرونة": "pasta isolated white",
    "الدجاج": "chicken breast white",
    "الموز": "banana isolated white",
    "التفاح": "red apple isolated",
}

def search_word(food):
    return SEARCH.get(food, f"{food} food white background isolated")

# ========== الأداة 1: SearXNG (مجاني) ==========
def search_searxng(food):
    try:
        q = search_word(food)
        r = requests.get("https://searx.tiekoetter.com/search", 
                         params={'q': q, 'categories': 'images', 'format': 'json'},
                         timeout=10)
        if r.status_code == 200 and r.json().get('results'):
            return r.json()['results'][0].get('img_src')
    except:
        pass
    return None

# ========== الأداة 2: Openverse (مجاني) ==========
def search_openverse(food):
    try:
        q = search_word(food)
        r = requests.get(f"https://api.openverse.engineering/v1/images/", 
                         params={'q': q, 'page_size': 5},
                         timeout=10)
        if r.status_code == 200 and r.json().get('results'):
            return r.json()['results'][0].get('url')
    except:
        pass
    return None

# ========== الأداة 3: LibreStock (مجاني) ==========
def search_librestock(food):
    try:
        q = search_word(food)
        r = requests.get(f"https://librestock.com/api/v1/search?q={q}", timeout=10)
        if r.status_code == 200 and r.json().get('images'):
            return r.json()['images'][0].get('thumb')
    except:
        pass
    return None

# ========== Tavily (احتياطي - بمفتاح) ==========
def search_tavily(food):
    if not TAVILY_API_KEY:
        return None
    try:
        from tavily import TavilyClient
        c = TavilyClient(api_key=TAVILY_API_KEY)
        r = c.search(f"{food} طعام خلفية بيضاء", include_images=True, max_results=1)
        return r.get('images', [None])[0]
    except:
        return None

# ========== نظام البحث ==========
def get_image(food):
    print(f"  🔍 {food}...", end=" ")
    
    # الأدوات المجانية بدون API
    url = search_searxng(food)
    if url:
        print("✅ SearXNG")
        return url
    
    url = search_openverse(food)
    if url:
        print("✅ Openverse")
        return url
    
    url = search_librestock(food)
    if url:
        print("✅ LibreStock")
        return url
    
    # الاحتياطي: Tavily (بمفتاح)
    url = search_tavily(food)
    if url:
        print("⚠️ Tavily")
        return url
    
    print("❌ مفيش")
    return None

# ========== المزامنة مع Firebase ==========
def sync():
    print("=" * 60)
    print("🚀 بدء مزامنة الأطعمة والصور")
    print(f"📅 {datetime.now()}")
    print("=" * 60)
    
    # جلب الأطعمة من Firebase
    docs = db.collection('foods').stream()
    foods_in_firebase = {doc.id: doc for doc in docs}
    
    # جلب الأطعمة من foods.json
    with open("foods.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    all_foods = data.get("allowed", []) + data.get("forbidden", []) + data.get("limited", [])
    
    # إضافة الأطعمة الجديدة
    new_count = 0
    for food in all_foods:
        name = food['name']
        if name not in foods_in_firebase:
            db.collection('foods').document(name).set({
                "name": name,
                "category": food.get("category", ""),
                "desc": food.get("desc", ""),
                "benefits": food.get("benefits", ""),
                "warning": food.get("warning", ""),
                "quantity": food.get("quantity", ""),
                "createdAt": firestore.SERVER_TIMESTAMP,
            })
            print(f"✅ إضافة: {name}")
            new_count += 1
    
    # تحديث الصور
    docs = db.collection('foods').stream()
    updated = 0
    for doc in docs:
        food_data = doc.to_dict()
        food_name = doc.id
        current_img = food_data.get('imageUrl', '')
        
        if current_img and current_img != PLACEHOLDER:
            print(f"⏩ {food_name}: صورة موجودة")
            continue
        
        print(f"\n📸 {food_name}: أبحث عن صورة...")
        img = get_image(food_name)
        
        if img:
            doc.reference.update({'imageUrl': img, 'updatedAt': firestore.SERVER_TIMESTAMP})
            updated += 1
        else:
            doc.reference.update({'imageUrl': PLACEHOLDER, 'updatedAt': firestore.SERVER_TIMESTAMP})
        
        time.sleep(0.5)
    
    print("\n" + "=" * 60)
    print(f"📊 التقرير:")
    print(f"   ✅ أضيف جديد: {new_count}")
    print(f"   🖼️ تم تحديث صور: {updated}")
    print("🎉 انتهى!")

if __name__ == "__main__":
    sync()
