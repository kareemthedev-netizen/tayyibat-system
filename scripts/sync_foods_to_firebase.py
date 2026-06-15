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

# ========== كلمات بحث مخصصة (صور بخلفية بيضاء وجودة عالية) ==========
SEARCH_QUERIES = {
    # نشويات مسموحة
    "الأرز": "rice grains white background studio lighting",
    "البطاطس": "potato isolated white background high resolution",
    "خبز القمح الكامل": "whole wheat bread isolated white background",
    "الذرة": "corn cob isolated white background",
    "الشوفان": "oats oatmeal white background",
    "الفريك": "freekeh grain white background",
    "البرغل": "bulgur wheat white background",
    
    # دهون مسموحة
    "زيت الزيتون": "olive oil bottle white background product",
    "السمن البلدي": "ghee white background",
    "الزبد البلدي": "butter isolated white background",
    
    # لحوم مسموحة
    "لحم الضأن": "raw lamb meat cut white background",
    "لحم البقر": "raw beef steak isolated white background",
    "لحم الأرنب": "rabbit meat white background",
    "الكوارع": "beef trotters white background",
    "السمك البلطي": "fresh tilapia fish white background",
    "السمك البوري": "fresh mullet fish white background",
    "الجمبري": "shrimp isolated white background",
    "الكابوريا": "crab isolated white background",
    "السبيط": "squid isolated white background",
    
    # فواكه مسموحة
    "التفاح": "red apple isolated white background",
    "المانجو": "mango fruit isolated white background",
    "الرمان": "pomegranate isolated white background",
    "الفراولة": "strawberries isolated white background",
    "التمر": "dates fruit isolated white background",
    "التين": "fig fruit isolated white background",
    "الجوافة": "guava isolated white background",
    "الكمثرى": "pear isolated white background",
    "المشمش": "apricot isolated white background",
    "الخوخ": "peach isolated white background",
    "العنب": "grapes isolated white background",
    
    # خضروات مسموحة
    "الخيار": "cucumber isolated white background",
    "الخس": "lettuce leaves isolated white background",
    "الجرجير": "arugula leaves white background",
    "البقدونس": "parsley leaves white background",
    "السبانخ": "spinach leaves isolated white background",
    "الملوخية": "molokhia leaves white background",
    "الكوسة": "zucchini isolated white background",
    "الباذنجان": "eggplant isolated white background",
    "الفلفل الرومي": "bell pepper isolated white background",
    "البامية": "okra isolated white background",
    
    # ممنوعات (للتوعية)
    "المكرونة": "pasta isolated white background high resolution",
    "اليوسفي": "tangerine fruit isolated white background",
    "الخبز الأبيض": "white bread sliced isolated white background",
    "العيش الفينو": "french bread white background",
    "البيتزا": "pizza isolated white background",
    "الكرواسون": "croissant isolated white background",
    "القطايف": "qatayef white background",
    "الكنافة": "kunafa white background",
    "البقلاوة": "baklava white background",
    "الدجاج": "raw chicken breast white background product photography",
    "البط": "duck meat white background",
    "الأوز": "goose meat white background",
    "الحمام": "pigeon meat white background",
    "البيض": "eggs isolated white background",
    "اللبن": "milk glass isolated white background",
    "الزبادي": "yogurt isolated white background",
    "الجبن الأبيض": "white cheese isolated white background",
    "الجبن الرومي": "romy cheese white background",
    "الفول": "fava beans isolated white background",
    "العدس": "lentils isolated white background",
    "الحمص": "chickpeas isolated white background",
    "الفاصوليا": "beans isolated white background",
    "اللوبيا": "cowpeas white background",
    "السكر الأبيض": "sugar white background",
    "العصائر المعلبة": "canned juice white background",
    "الطماطم": "tomato isolated white background",
    "الجزر": "carrot isolated white background",
    "البرتقال": "orange isolated white background",
    "الكيوي": "kiwi isolated white background",
    "البطيخ": "watermelon isolated white background",
    
    # محدود
    "الموز": "banana isolated white background",
    "العسل": "honey jar isolated white background product",
    "الشوكولاتة الداكنة": "dark chocolate bar isolated white background",
    "الجبن الشيدر": "cheddar cheese slice isolated white background"
}

def get_search_query(food_name):
    return SEARCH_QUERIES.get(food_name, f"{food_name} food white background isolated")

# ========== مصادر البحث المجانية ==========

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
                        # تفضيل الصور ذات الخلفية البيضاء
                        if 'white' in img_url.lower() or 'isolated' in img_url.lower():
                            return img_url
                # لو محصلش صورة بخلفية بيضا، خد أي صورة
                return data['results'][0].get('img_src')
    except Exception as e:
        print(f"  ⚠️ SearXNG: {e}")
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
                        # تفضيل الصور ذات الخلفية البيضاء
                        if 'white' in img_url.lower() or 'isolated' in img_url.lower():
                            return img_url
                return data['results'][0].get('url')
    except Exception as e:
        print(f"  ⚠️ Openverse: {e}")
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
    except Exception as e:
        print(f"  ⚠️ Tavily: {e}")
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
        print("⚠️ Tavily (احتياطي)")
        return url
    
    print("❌ مفيش صورة")
    return None

def update_all_foods_images():
    """يحدث روابط الصور لجميع الأطعمة في Firebase"""
    print("🚀 بدء تحديث روابط الصور في Firebase...")
    print("=" * 60)
    print(f"📅 التاريخ: {datetime.now()}")
    print("🎯 جودة الصور: خلفية بيضاء - جودة عالية - المنتج فقط")
    print("=" * 60)
    
    docs = db.collection('foods').get()
    updated = 0
    skipped = 0
    
    for doc in docs:
        food_data = doc.to_dict()
        food_name = doc.id
        current_image = food_data.get('imageUrl', '')
        
        # لو الرابط مش placeholder، نتخطى
        if current_image and current_image != PLACEHOLDER_URL and 'placeholder' not in current_image:
            print(f"⏩ {food_name}: رابط موجود ✓")
            skipped += 1
            continue
        
        print(f"\n📸 {food_name}: أبحث عن صورة جودة عالية...")
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
            print(f"  ⚠️ تم وضع صورة افتراضية لـ {food_name}")
    
    print("\n" + "=" * 60)
    print(f"📊 التقرير النهائي:")
    print(f"   ✅ تم تحديث {updated} صورة جديدة")
    print(f"   ⏩ تم تخطي {skipped} صورة موجودة")
    print(f"   📋 إجمالي الأطعمة: {docs.size}")
    print("🎉 انتهى التحديث!")

if __name__ == "__main__":
    update_all_foods_images()
