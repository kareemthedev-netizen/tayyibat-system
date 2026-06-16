import os
import json
import requests
import re
import time
from firebase_admin import credentials, firestore, initialize_app
from datetime import datetime

FIREBASE_CRED = json.loads(os.environ.get("FIREBASE_SERVICE_ACCOUNT"))
PEXELS_KEY = os.environ.get("PEXELS_API_KEY")

if not FIREBASE_CRED:
    raise Exception("Missing Firebase credentials")

cred = credentials.Certificate(FIREBASE_CRED)
initialize_app(cred)
db = firestore.client()

PLACEHOLDER = "https://via.placeholder.com/300x200?text=%D8%B5%D9%88%D8%B1%D8%A9+%D8%BA%D9%8A%D8%B1+%D9%85%D8%AA%D9%88%D9%81%D8%B1%D8%A9"

# ========== كلمات بحث دقيقة لكل صنف ==========
SEARCH_WORDS = {
    "الأرز": "rice grains white background closeup",
    "الأرز البني": "brown rice grains white background",
    "البطاطس": "potato isolated white background",
    "البطاطا الحلوة": "sweet potato isolated white background",
    "خبز القمح الكامل": "whole wheat bread isolated white background",
    "خبز الشعير": "barley bread isolated white background",
    "الذرة": "corn cob isolated white background",
    "الفريك": "freekeh grain white background",
    "البرغل": "bulgur wheat white background",
    "الشوفان": "oats oatmeal white background",
    "زيت الزيتون": "olive oil bottle white background",
    "السمن البلدي": "ghee white background",
    "الزبد البلدي": "butter isolated white background",
    "لحم الضأن": "lamb meat cut white background",
    "لحم البقر": "beef steak isolated white background",
    "لحم الأرنب": "rabbit meat white background",
    "الكوارع": "beef trotters white background",
    "السمك البلطي": "tilapia fish white background",
    "السمك البوري": "mullet fish white background",
    "الجمبري": "shrimp isolated white background",
    "التفاح": "red apple isolated white background",
    "المانجو": "mango fruit isolated white background",
    "الرمان": "pomegranate isolated white background",
    "الفراولة": "strawberries isolated white background",
    "التمر": "dates fruit isolated white background",
    "التين": "fig fruit isolated white background",
    "الجوافة": "guava isolated white background",
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
    "المكرونة": "pasta isolated white background",
    "الدجاج": "raw chicken breast white background",
    "الخبز الأبيض": "white bread isolated white background",
    "اللبن": "milk glass isolated white background",
    "الزبادي": "yogurt isolated white background",
    "الفول": "fava beans isolated white background",
    "العدس": "lentils isolated white background",
    "الحمص": "chickpeas isolated white background",
    "البيض": "eggs isolated white background",
    "السكر الأبيض": "sugar white background",
    "الطماطم": "tomato isolated white background",
    "الجزر": "carrot isolated white background",
    "البرتقال": "orange isolated white background",
    "اليوسفي": "tangerine isolated white background",
    "الكيوي": "kiwi isolated white background",
    "البطيخ": "watermelon isolated white background",
    "الموز": "banana isolated white background",
    "العسل": "honey jar white background",
    "الشوكولاتة الداكنة": "dark chocolate bar white background",
}

def search_word(food):
    return SEARCH_WORDS.get(food, f"{food} food white background isolated")

# ========== فحص الصورة (تتأكد إنها صورة مش ذبابة) ==========
def check_image_quality(url):
    """تتأكد إن الصورة مش بايظة أو فيها حشرات"""
    if not url:
        return False
    if 'placeholder' in url or url == PLACEHOLDER:
        return False
    
    # كلمات ممنوعة في الصورة (زي ذبابة، حشرات)
    bad_words = ['fly', 'insect', 'bug', 'rotten', 'mold', 'dust', 'dirty', 'fake']
    url_lower = url.lower()
    for word in bad_words:
        if word in url_lower:
            print(f"  ⚠️ الصورة فيها {word}، هتتجاهلها")
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

# ========== 7 أدوات مجانية ==========
def search_searxng(food):
    try:
        q = search_word(food)
        r = requests.get("https://searx.tiekoetter.com/search",
                         params={'q': q, 'categories': 'images', 'format': 'json'},
                         timeout=10)
        if r.status_code == 200 and r.json().get('results'):
            for result in r.json()['results']:
                img_url = result.get('img_src')
                if img_url and check_image_quality(img_url):
                    return img_url
    except:
        pass
    return None

def search_openverse(food):
    try:
        q = search_word(food)
        r = requests.get("https://api.openverse.engineering/v1/images/",
                         params={'q': q, 'page_size': 5},
                         timeout=10)
        if r.status_code == 200 and r.json().get('results'):
            for result in r.json()['results']:
                img_url = result.get('url')
                if img_url and check_image_quality(img_url):
                    return img_url
    except:
        pass
    return None

def search_duckduckgo(food):
    try:
        q = search_word(food)
        r = requests.get("https://api.duckduckgo.com/",
                         params={'q': q, 'format': 'json', 'no_html': 1},
                         timeout=10)
        if r.status_code == 200 and r.json().get('Image'):
            img_url = r.json()['Image']
            if check_image_quality(img_url):
                return img_url
    except:
        pass
    return None

def search_bing(food):
    try:
        q = search_word(food)
        r = requests.get(f"https://www.bing.com/images/search?q={q}",
                         headers={'User-Agent': 'Mozilla/5.0'},
                         timeout=10)
        if r.status_code == 200:
            match = re.search(r'murl":"([^"]+)"', r.text)
            if match:
                img_url = match.group(1)
                if check_image_quality(img_url):
                    return img_url
    except:
        pass
    return None

def search_yandex(food):
    try:
        q = search_word(food)
        r = requests.get(f"https://yandex.com/images/search?text={q}",
                         headers={'User-Agent': 'Mozilla/5.0'},
                         timeout=10)
        if r.status_code == 200:
            images = re.findall(r'https?://[^"\']+\.(jpg|jpeg|png|webp)', r.text)
            for img_url in images:
                if check_image_quality(img_url):
                    return img_url
    except:
        pass
    return None

def search_baidu(food):
    try:
        q = search_word(food)
        r = requests.get(f"https://image.baidu.com/search/index?tn=baiduimage&word={q}",
                         headers={'User-Agent': 'Mozilla/5.0'},
                         timeout=10)
        if r.status_code == 200:
            images = re.findall(r'"objURL":"([^"]+)"', r.text)
            for img_url in images:
                img_url = img_url.replace('\\', '')
                if check_image_quality(img_url):
                    return img_url
    except:
        pass
    return None

def search_360(food):
    try:
        q = search_word(food)
        r = requests.get(f"https://image.so.com/i?q={q}",
                         headers={'User-Agent': 'Mozilla/5.0'},
                         timeout=10)
        if r.status_code == 200:
            images = re.findall(r'"img":"([^"]+)"', r.text)
            for img_url in images:
                img_url = img_url.replace('\\/', '/')
                if check_image_quality(img_url):
                    return img_url
    except:
        pass
    return None

# ========== Pexels (بـ API) ==========
def search_pexels(food):
    if not PEXELS_KEY:
        return None
    try:
        q = search_word(food)
        r = requests.get("https://api.pexels.com/v1/search",
                         headers={"Authorization": PEXELS_KEY},
                         params={'query': q, 'per_page': 3},
                         timeout=10)
        if r.status_code == 200 and r.json().get('photos'):
            for photo in r.json()['photos']:
                img_url = photo['src']['medium']
                if check_image_quality(img_url):
                    return img_url
    except:
        pass
    return None

def get_image(food):
    print(f"  🔍 {food}...", end=" ")
    
    for name, func in [
        ("SearXNG", search_searxng),
        ("Openverse", search_openverse),
        ("DuckDuckGo", search_duckduckgo),
        ("Bing", search_bing),
        ("Yandex", search_yandex),
        ("Baidu", search_baidu),
        ("360", search_360),
    ]:
        url = func(food)
        if url:
            print(f"✅ {name}")
            return url
    
    url = search_pexels(food)
    if url:
        print("⚠️ Pexels")
        return url
    
    print("❌ مفيش")
    return None

# ========== السكريبت الشامل ==========
def sync():
    print("=" * 60)
    print("🚀 المزامنة الشاملة: إضافة الأطعمة + تحديث الصور")
    print(f"📅 {datetime.now()}")
    print("=" * 60)
    
    # الخطوة 1: إضافة الأطعمة من foods.json (لو مش موجودة)
    print("\n📥 الخطوة 1: التحقق من الأطعمة في Firebase...")
    with open("foods.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    all_foods = data.get("allowed", []) + data.get("forbidden", []) + data.get("limited", [])
    
    existing_docs = db.collection('foods').stream()
    existing_names = {doc.id for doc in existing_docs}
    
    added = 0
    for food in all_foods:
        name = food['name']
        if name not in existing_names:
            db.collection('foods').document(name).set({
                "name": name,
                "type": food.get("type", "allowed"),
                "category": food.get("category", ""),
                "desc": food.get("desc", ""),
                "benefits": food.get("benefits", ""),
                "warning": food.get("warning", ""),
                "quantity": food.get("quantity", ""),
                "createdAt": firestore.SERVER_TIMESTAMP,
            })
            print(f"  ✅ إضافة: {name}")
            added += 1
        else:
            print(f"  ⏩ {name}: موجود بالفعل")
    
    print(f"📊 تم إضافة {added} صنف جديد")
    
    # الخطوة 2: تحديث الصور (للأكلات اللي مفيهاش صور أو صورها غلط)
    print("\n🖼️ الخطوة 2: فحص وتحديث الصور...")
    docs = db.collection('foods').stream()
    updated = 0
    total = 0
    fixed = 0
    
    for doc in docs:
        total += 1
        food_name = doc.id
        data = doc.to_dict()
        current = data.get('imageUrl', '')
        
        # فحص الصورة الحالية (لو موجودة وصحيحة)
        if current and current != PLACEHOLDER:
            if check_image_quality(current):
                print(f"⏩ {food_name}: صورة صحيحة ✓")
                continue
            else:
                print(f"\n📸 {food_name}: صورة بايظة (هتتغير)")
                fixed += 1
        else:
            print(f"\n📸 {food_name}: مفيش صورة")
        
        # البحث عن صورة جديدة
        img = get_image(food_name)
        
        if img:
            doc.reference.update({
                'imageUrl': img,
                'updatedAt': firestore.SERVER_TIMESTAMP
            })
            updated += 1
            print(f"  ✅ تم تحديث {food_name}")
        else:
            doc.reference.update({
                'imageUrl': PLACEHOLDER,
                'updatedAt': firestore.SERVER_TIMESTAMP
            })
            print(f"  ⚠️ صورة افتراضية لـ {food_name}")
        
        time.sleep(0.5)
    
    print("\n" + "=" * 60)
    print(f"📊 التقرير النهائي:")
    print(f"   ✅ أضيف جديد: {added}")
    print(f"   🖼️ تم تحديث/إصلاح صور: {updated}")
    print(f"   🔧 صور بايظة تم إصلاحها: {fixed}")
    print(f"   📋 إجمالي الأطعمة في Firebase: {total}")
    print("🎉 انتهى!")

if __name__ == "__main__":
    sync()
