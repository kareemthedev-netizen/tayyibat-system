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

SEARCH_WORDS = {
    "الأرز": "rice grains white background",
    "البطاطس": "potato isolated white",
    "خبز القمح الكامل": "whole wheat bread isolated",
    "الذرة": "corn cob isolated",
    "زيت الزيتون": "olive oil bottle white",
    "لحم الضأن": "lamb meat white",
    "لحم البقر": "beef steak isolated",
    "السمك البلطي": "tilapia fish white",
    "التفاح": "red apple isolated",
    "الموز": "banana isolated",
    "المانجو": "mango fruit isolated",
    "الفراولة": "strawberries isolated",
    "التمر": "dates fruit isolated",
    "الخيار": "cucumber isolated",
    "الخس": "lettuce leaves isolated",
    "السبانخ": "spinach leaves isolated",
    "الملوخية": "molokhia leaves",
    "المكرونة": "pasta isolated white",
    "الدجاج": "chicken breast white",
    "الخبز الأبيض": "white bread isolated",
    "اللبن": "milk glass isolated",
}

def search_word(food):
    return SEARCH_WORDS.get(food, f"{food} food white background isolated")

# ========== 7 أدوات مجانية ==========
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

def search_openverse(food):
    try:
        q = search_word(food)
        r = requests.get("https://api.openverse.engineering/v1/images/",
                         params={'q': q, 'page_size': 5},
                         timeout=10)
        if r.status_code == 200 and r.json().get('results'):
            return r.json()['results'][0].get('url')
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
            return r.json()['Image']
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
                return match.group(1)
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
            if images:
                return images[0]
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
            if images:
                return images[0].replace('\\', '')
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
            if images:
                return images[0].replace('\\/', '/')
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
                         params={'query': q, 'per_page': 1},
                         timeout=10)
        if r.status_code == 200 and r.json().get('photos'):
            return r.json()['photos'][0]['src']['medium']
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

def sync():
    print("=" * 60)
    print("🚀 تحديث الصور (7 مجانية + Pexels)")
    print(f"📅 {datetime.now()}")
    print("=" * 60)
    
    docs = db.collection('foods').stream()
    updated = 0
    total = 0
    
    for doc in docs:
        total += 1
        food_name = doc.id
        data = doc.to_dict()
        current = data.get('imageUrl', '')
        
        if current and current != PLACEHOLDER:
            print(f"⏩ {food_name}: موجودة")
            continue
        
        print(f"\n📸 {food_name}: أبحث...")
        img = get_image(food_name)
        
        if img:
            doc.reference.update({'imageUrl': img, 'updatedAt': firestore.SERVER_TIMESTAMP})
            updated += 1
        else:
            doc.reference.update({'imageUrl': PLACEHOLDER, 'updatedAt': firestore.SERVER_TIMESTAMP})
        
        time.sleep(0.5)
    
    print("\n" + "=" * 60)
    print(f"✅ تم تحديث {updated} من {total}")
    print("🎉 انتهى!")

if __name__ == "__main__":
    sync()
