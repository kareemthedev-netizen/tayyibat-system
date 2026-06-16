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
    "البطاطس": "potato isolated white background",
    "خبز القمح الكامل": "whole wheat bread isolated",
    "الذرة": "corn cob isolated",
    "زيت الزيتون": "olive oil bottle white",
    "لحم الضأن": "lamb meat cut white",
    "لحم البقر": "beef steak isolated",
    "السمك البلطي": "tilapia fish white",
    "التفاح": "red apple isolated",
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
    "الفول": "fava beans isolated",
    "البيض": "eggs isolated white",
    "الموز": "banana isolated",
    "العسل": "honey jar white",
    "البرتقال": "orange isolated",
    "اليوسفي": "tangerine isolated",
    "البطيخ": "watermelon isolated",
    "الجوافة": "guava isolated",
    "الخوخ": "peach isolated",
    "الكرز": "cherry isolated",
    "التوت": "berries isolated",
    "الباذنجان": "eggplant isolated",
    "الكوسة": "zucchini isolated",
    "الفلفل الرومي": "bell pepper isolated",
    "البامية": "okra isolated",
}

def search_word(food):
    return SEARCH_WORDS.get(food, f"{food} food white background isolated")

# ========== الرقابة الذكية ==========

class ImageSupervisor:
    """تراقب كل الصور وتتأكد من صحتها"""
    
    def __init__(self):
        self.total_checked = 0
        self.passed = 0
        self.failed = 0
        self.results = {}
    
    def verify_image(self, url, food_name):
        """تتأكد إن الصورة صحيحة ومطابقة للاسم"""
        self.total_checked += 1
        
        if not url:
            self.failed += 1
            return False
        
        # 1. فحص الكلمات الممنوعة
        bad_words = ['fly', 'insect', 'bug', 'rotten', 'mold', 'dirty',
                    'watermark', 'logo', 'avatar', 'profile', 'thumbnail',
                    'spam', 'fake', 'error', '404', 'broken']
        url_lower = url.lower()
        for word in bad_words:
            if word in url_lower:
                print(f"  ⚠️ ممنوع: {word}")
                self.failed += 1
                return False
        
        # 2. فحص الامتداد
        valid_ext = ('.jpg', '.jpeg', '.png', '.webp', '.gif')
        if not any(url_lower.endswith(ext) for ext in valid_ext):
            print(f"  ⚠️ امتداد غير صحيح")
            self.failed += 1
            return False
        
        # 3. فحص أن الرابط شغال
        try:
            response = requests.head(url, timeout=10, allow_redirects=True)
            if response.status_code != 200:
                self.failed += 1
                return False
            if 'image' not in response.headers.get('content-type', ''):
                self.failed += 1
                return False
        except:
            try:
                response = requests.get(url, timeout=10, stream=True)
                if response.status_code != 200:
                    self.failed += 1
                    return False
                if 'image' not in response.headers.get('content-type', ''):
                    self.failed += 1
                    return False
            except:
                self.failed += 1
                return False
        
        self.passed += 1
        self.results[food_name] = url
        return True
    
    def get_report(self):
        return {
            'total': self.total_checked,
            'passed': self.passed,
            'failed': self.failed
        }

# ========== أدوات البحث المجانية ==========

def search_searxng(food):
    try:
        q = search_word(food)
        r = requests.get("https://searx.tiekoetter.com/search",
                         params={'q': q, 'categories': 'images', 'format': 'json'},
                         timeout=10)
        if r.status_code == 200 and r.json().get('results'):
            for result in r.json()['results']:
                return result.get('img_src')
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
            return r.json()['photos'][0]['src']['medium']
    except:
        pass
    return None

# ========== نظام البحث مع الرقابة ==========

def find_image_with_supervision(food, supervisor):
    """يبحث عن صورة تحت رقابة المشرف"""
    print(f"  🔍 {food}...", end=" ")
    
    tools = [
        ("SearXNG", search_searxng),
        ("Openverse", search_openverse),
        ("DuckDuckGo", search_duckduckgo),
        ("Bing", search_bing),
        ("Yandex", search_yandex),
        ("Baidu", search_baidu),
        ("360", search_360),
    ]
    
    for name, func in tools:
        url = func(food)
        if url and supervisor.verify_image(url, food):
            print(f"✅ {name}")
            return url
    
    # الاحتياطي: Pexels
    url = search_pexels(food)
    if url and supervisor.verify_image(url, food):
        print("⚠️ Pexels")
        return url
    
    print("❌ مفيش")
    return None

# ========== السكريبت الرئيسي ==========

def sync():
    supervisor = ImageSupervisor()
    
    print("=" * 60)
    print("🚀 المزامنة الذكية (مع إعادة جميع الصور)")
    print("   هتتجاهل كل الصور الموجودة وتجيب جديدة")
    print(f"📅 {datetime.now()}")
    print("=" * 60)
    
    # الخطوة 1: إضافة الأطعمة الجديدة
    print("\n📥 الخطوة 1: التحقق من الأطعمة...")
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
            print(f"  ⏩ {name}: موجود")
    
    print(f"📊 تم إضافة {added} صنف جديد")
    
    # الخطوة 2: إعادة جميع الصور (حتى الموجودة)
    print("\n🖼️ الخطوة 2: إعادة جميع الصور (حذف القديم وجلب جديد)...")
    docs = db.collection('foods').stream()
    updated = 0
    total = 0
    
    for doc in docs:
        total += 1
        food_name = doc.id
        data = doc.to_dict()
        
        print(f"\n📸 {food_name}: أبحث عن صورة جديدة (بغض النظر عن القديمة)...")
        
        img = find_image_with_supervision(food_name, supervisor)
        
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
    
    # التقرير النهائي
    report = supervisor.get_report()
    print("\n" + "=" * 60)
    print(f"📊 التقرير النهائي:")
    print(f"   ✅ أضيف جديد: {added}")
    print(f"   🖼️ تم تحديث: {updated}")
    print(f"   📋 إجمالي الأطعمة: {total}")
    print(f"   🔍 فحص الصور:")
    print(f"      - إجمالي تم فحصه: {report['total']}")
    print(f"      - ✅ صحيح: {report['passed']}")
    print(f"      - ❌ مرفوض: {report['failed']}")
    print("🎉 انتهى!")

if __name__ == "__main__":
    sync()
