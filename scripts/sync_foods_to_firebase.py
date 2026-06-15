import os
import json
import requests
from firebase_admin import credentials, firestore, initialize_app
from datetime import datetime
import time

# ========== الإعدادات ==========
FIREBASE_CRED = json.loads(os.environ.get("FIREBASE_SERVICE_ACCOUNT"))
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")

if not FIREBASE_CRED:
    raise Exception("Missing Firebase credentials")

cred = credentials.Certificate(FIREBASE_CRED)
initialize_app(cred)
db = firestore.client()

PLACEHOLDER_URL = "https://via.placeholder.com/300x200?text=%D8%B5%D9%88%D8%B1%D8%A9+%D8%BA%D9%8A%D8%B1+%D9%85%D8%AA%D9%88%D9%81%D8%B1%D8%A9"

# ========== كلمات بحث مخصصة (عشان يجيب صور المنتج بس بخلفية بيضاء) ==========
SEARCH_QUERIES = {
    "الأرز": "rice grains white background",
    "البطاطس": "potato isolated white background",
    "خبز القمح الكامل": "whole wheat bread isolated",
    "الذرة": "corn cob isolated",
    "زيت الزيتون": "olive oil bottle white background",
    "لحم الضأن": "lamb meat cut white background",
    "لحم البقر": "beef steak isolated",
    "السمك البلطي": "tilapia fish white background",
    "التفاح": "red apple isolated white background",
    "الموز": "banana isolated white background",
    "المانجو": "mango fruit isolated",
    "الفراولة": "strawberries isolated",
    "التمر": "dates fruit isolated",
    "الخيار": "cucumber isolated",
    "الخس": "lettuce leaves isolated",
    "السبانخ": "spinach leaves isolated",
    "الملوخية": "molokhia leaves",
    "المكرونة": "pasta isolated white background",
    "اليوسفي": "tangerine fruit isolated",
    "الدجاج": "chicken breast white background",
    "الخبز الأبيض": "white bread sliced isolated",
    "اللبن": "glass of milk isolated",
    "الفول": "fava beans isolated",
    "البيض": "eggs isolated white background",
}

def get_search_query(food_name):
    return SEARCH_QUERIES.get(food_name, f"{food_name} food white background isolated")

# ========== فحص الرابط (يتأكد إن الرابط شغال) ==========
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
        try:
            response = requests.get(url, timeout=10, stream=True)
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '')
                if 'image' in content_type:
                    return True
        except:
            pass
    return False

# ========== المصدر 1: SearXNG (مجاني، بدون API) ==========
def search_searxng(food_name):
    try:
        query = get_search_query(food_name)
        url = "https://searx.tiekoetter.com/search"
        params = {'q': query, 'categories': 'images', 'format': 'json', 'image_proxy': True}
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get('results'):
                for result in data['results']:
                    img_url = result.get('img_src')
                    if img_url and not img_url.endswith('.svg') and 'placeholder' not in img_url:
                        if 'white' in img_url.lower() or 'isolated' in img_url.lower():
                            return img_url
                return data['results'][0].get('img_src')
    except Exception as e:
        print(f"  ⚠️ SearXNG: {e}")
    return None

# ========== المصدر 2: Openverse (مجاني، بدون API) ==========
def search_openverse(food_name):
    try:
        query = get_search_query(food_name)
        url = f"https://api.openverse.engineering/v1/images/?q={query}&page_size=5"
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get('results'):
                for result in data['results']:
                    img_url = result.get('url')
                    if img_url:
                        if 'white' in img_url.lower() or 'isolated' in img_url.lower():
                            return img_url
                return data['results'][0].get('url')
    except Exception as e:
        print(f"  ⚠️ Openverse: {e}")
    return None

# ========== المصدر 3: Tavily (احتياطي، بمفتاح API) ==========
def search_tavily(food_name):
    if not TAVILY_API_KEY:
        return None
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=TAVILY_API_KEY)
        response = client.search(f"{food_name} طعام خلفية بيضاء", include_images=True, max_results=2)
        images = response.get('images', [])
        return images[0] if images else None
    except Exception as e:
        print(f"  ⚠️ Tavily: {e}")
    return None

# ========== نظام البحث الطبقي ==========
def get_image_url(food_name):
    print(f"  🔍 {food_name}...", end=" ")
    
    # المجانية أولاً
    url = search_searxng(food_name)
    if url:
        print("✅ SearXNG")
        return url
    
    url = search_openverse(food_name)
    if url:
        print("✅ Openverse")
        return url
    
    # الاحتياطي بـ API
    url = search_tavily(food_name)
    if url:
        print("⚠️ Tavily (API)")
        return url
    
    print("❌ مفيش")
    return None

# ========== الوظيفة الرئيسية: تحديث الصور المعطلة بس ==========
def update_broken_images_only():
    print("=" * 60)
    print("🚀 بدء تحديث روابط الصور (المجانية أولاً، ثم Tavily)")
    print(f"📅 التاريخ: {datetime.now()}")
    print("=" * 60)
    
    # جلب جميع الأطعمة من Firebase
    docs = db.collection('foods').stream()
    updated = 0
    working = 0
    failed = 0
    total = 0
    
    for doc in docs:
        total += 1
        food_data = doc.to_dict()
        food_name = doc.id
        current_image = food_data.get('imageUrl', '')
        
        print(f"\n📸 {food_name}:", end=" ")
        
        # فحص الرابط الحالي
        if check_image_url(current_image):
            print("✅ رابط شغال ✓")
            working += 1
            continue
        
        print("❌ بايظ أو مفقود، أبحث...")
        
        # البحث عن رابط جديد
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
        
        # تأخير صغير عشان ما نضغطش على السيرفرات
        time.sleep(0.5)
    
    print("\n" + "=" * 60)
    print(f"📊 التقرير النهائي:")
    print(f"   ✅ روابط شغالة وتم تخطيها: {working}")
    print(f"   🔄 تم تحديث روابط جديدة: {updated}")
    print(f"   ⚠️ صور افتراضية: {failed}")
    print(f"   📋 إجمالي الأطعمة: {total}")
    print("🎉 انتهى التحديث!")

# ========== تشغيل السكريبت ==========
if __name__ == "__main__":
    update_broken_images_only()
