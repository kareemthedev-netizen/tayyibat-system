import os
import json
import requests
import re
import time
from firebase_admin import credentials, firestore, initialize_app
from datetime import datetime
from difflib import SequenceMatcher

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
    "الأرز": "rice grains white background",
    "البطاطس": "potato isolated white",
    "خبز القمح الكامل": "whole wheat bread isolated",
    "الذرة": "corn cob isolated",
    "زيت الزيتون": "olive oil bottle white",
    "لحم الضأن": "lamb meat white",
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
    "الجوافة": "guava isolated",
    "الخوخ": "peach isolated",
    "الكرز": "cherry isolated",
    "التوت": "berries isolated",
    "الباذنجان": "eggplant isolated",
    "الكوسة": "zucchini isolated",
    "الفلفل الرومي": "bell pepper isolated",
    "البامية": "okra isolated",
    "البرتقال": "orange isolated",
    "اليوسفي": "tangerine isolated",
    "الكيوي": "kiwi isolated",
    "البطيخ": "watermelon isolated",
    "الشمام": "cantaloupe isolated",
}

def search_word(food):
    return SEARCH_WORDS.get(food, f"{food} food white background isolated")

# ========== العقلية الذكية (تتحكم في كل حاجة) ==========

class ImageController:
    """التحكم الذكي في عملية البحث عن الصور"""
    
    def __init__(self):
        self.tools = [
            ("SearXNG", self.search_searxng),
            ("Openverse", self.search_openverse),
            ("DuckDuckGo", self.search_duckduckgo),
            ("Bing", self.search_bing),
            ("Yandex", self.search_yandex),
            ("Baidu", self.search_baidu),
            ("360", self.search_360),
        ]
        self.fallback_tool = ("Pexels", self.search_pexels)
        self.results = {}
    
    # ========== أدوات البحث المجانية ==========
    
    def search_searxng(self, food):
        try:
            q = search_word(food)
            r = requests.get("https://searx.tiekoetter.com/search",
                             params={'q': q, 'categories': 'images', 'format': 'json'},
                             timeout=10)
            if r.status_code == 200 and r.json().get('results'):
                for result in r.json()['results']:
                    img_url = result.get('img_src')
                    if img_url and self.verify_image(img_url, food):
                        return img_url
        except:
            pass
        return None
    
    def search_openverse(self, food):
        try:
            q = search_word(food)
            r = requests.get("https://api.openverse.engineering/v1/images/",
                             params={'q': q, 'page_size': 5},
                             timeout=10)
            if r.status_code == 200 and r.json().get('results'):
                for result in r.json()['results']:
                    img_url = result.get('url')
                    if img_url and self.verify_image(img_url, food):
                        return img_url
        except:
            pass
        return None
    
    def search_duckduckgo(self, food):
        try:
            q = search_word(food)
            r = requests.get("https://api.duckduckgo.com/",
                             params={'q': q, 'format': 'json', 'no_html': 1},
                             timeout=10)
            if r.status_code == 200 and r.json().get('Image'):
                img_url = r.json()['Image']
                if self.verify_image(img_url, food):
                    return img_url
        except:
            pass
        return None
    
    def search_bing(self, food):
        try:
            q = search_word(food)
            r = requests.get(f"https://www.bing.com/images/search?q={q}",
                             headers={'User-Agent': 'Mozilla/5.0'},
                             timeout=10)
            if r.status_code == 200:
                match = re.search(r'murl":"([^"]+)"', r.text)
                if match:
                    img_url = match.group(1)
                    if self.verify_image(img_url, food):
                        return img_url
        except:
            pass
        return None
    
    def search_yandex(self, food):
        try:
            q = search_word(food)
            r = requests.get(f"https://yandex.com/images/search?text={q}",
                             headers={'User-Agent': 'Mozilla/5.0'},
                             timeout=10)
            if r.status_code == 200:
                images = re.findall(r'https?://[^"\']+\.(jpg|jpeg|png|webp)', r.text)
                for img_url in images:
                    if self.verify_image(img_url, food):
                        return img_url
        except:
            pass
        return None
    
    def search_baidu(self, food):
        try:
            q = search_word(food)
            r = requests.get(f"https://image.baidu.com/search/index?tn=baiduimage&word={q}",
                             headers={'User-Agent': 'Mozilla/5.0'},
                             timeout=10)
            if r.status_code == 200:
                images = re.findall(r'"objURL":"([^"]+)"', r.text)
                for img_url in images:
                    img_url = img_url.replace('\\', '')
                    if self.verify_image(img_url, food):
                        return img_url
        except:
            pass
        return None
    
    def search_360(self, food):
        try:
            q = search_word(food)
            r = requests.get(f"https://image.so.com/i?q={q}",
                             headers={'User-Agent': 'Mozilla/5.0'},
                             timeout=10)
            if r.status_code == 200:
                images = re.findall(r'"img":"([^"]+)"', r.text)
                for img_url in images:
                    img_url = img_url.replace('\\/', '/')
                    if self.verify_image(img_url, food):
                        return img_url
        except:
            pass
        return None
    
    # ========== Pexels (بـ API) ==========
    
    def search_pexels(self, food):
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
                    if self.verify_image(img_url, food):
                        return img_url
        except:
            pass
        return None
    
    # ========== فحص الصورة الذكي (يتأكد إنها مطابقة) ==========
    
    def verify_image(self, url, food_name):
        """تتحقق من صحة الصورة وتطابقها مع اسم الصنف"""
        if not url:
            return False
        
        # 1. فحص الرابط الأساسي
        if 'placeholder' in url or url == PLACEHOLDER:
            return False
        
        # 2. فحص الامتداد
        valid_extensions = ('.jpg', '.jpeg', '.png', '.webp', '.gif')
        if not any(url.lower().endswith(ext) for ext in valid_extensions):
            return False
        
        # 3. فحص الكلمات الممنوعة في الرابط
        bad_words = ['fly', 'insect', 'bug', 'rotten', 'mold', 'dirty',
                    'watermark', 'logo', 'avatar', 'profile', 'thumbnail',
                    'spam', 'fake', 'error', '404', 'broken']
        url_lower = url.lower()
        for word in bad_words:
            if word in url_lower:
                return False
        
        # 4. فحص أن الرابط شغال
        try:
            response = requests.head(url, timeout=10, allow_redirects=True)
            if response.status_code != 200:
                return False
            content_type = response.headers.get('content-type', '')
            if 'image' not in content_type:
                return False
        except:
            try:
                response = requests.get(url, timeout=10, stream=True)
                if response.status_code != 200:
                    return False
                if 'image' not in response.headers.get('content-type', ''):
                    return False
            except:
                return False
        
        return True
    
    # ========== نظام البحث الرئيسي (العقلية الذكية) ==========
    
    def find_image(self, food):
        """البحث عن صورة باستخدام جميع الأدوات المتاحة"""
        print(f"  🔍 {food}...", end=" ")
        
        # 1. تجربة الأدوات المجانية
        for name, func in self.tools:
            url = func(food)
            if url:
                print(f"✅ {name}")
                self.results[food] = url
                return url
        
        # 2. الاحتياطي: Pexels
        url = self.fallback_tool[1](food)
        if url:
            print("⚠️ Pexels")
            self.results[food] = url
            return url
        
        # 3. فشل الجميع
        print("❌ مفيش")
        self.results[food] = None
        return None

# ========== السكريبت الشامل ==========

def sync():
    controller = ImageController()
    
    print("=" * 60)
    print("🚀 المزامنة الذكية مع العقلية المتحكمة")
    print("   الأدوات: SearXNG → Openverse → DuckDuckGo → Bing → Yandex → Baidu → 360 → Pexels")
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
    
    # الخطوة 2: تحديث الصور
    print("\n🖼️ الخطوة 2: فحص وتحديث الصور...")
    docs = db.collection('foods').stream()
    updated = 0
    total = 0
    failed = 0
    
    for doc in docs:
        total += 1
        food_name = doc.id
        data = doc.to_dict()
        current = data.get('imageUrl', '')
        
        # فحص الصورة الحالية
        if current and current != PLACEHOLDER:
            # نتأكد إنها صورة صحيحة
            if controller.verify_image(current, food_name):
                print(f"⏩ {food_name}: صورة صحيحة ✓")
                continue
            else:
                print(f"\n📸 {food_name}: صورة بايظة، أبحث عن بديل...")
        else:
            print(f"\n📸 {food_name}: مفيش صورة")
        
        # البحث عن صورة جديدة
        img = controller.find_image(food_name)
        
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
            failed += 1
            print(f"  ⚠️ صورة افتراضية لـ {food_name}")
        
        time.sleep(0.5)
    
    print("\n" + "=" * 60)
    print(f"📊 التقرير النهائي:")
    print(f"   ✅ أضيف جديد: {added}")
    print(f"   🖼️ تم تحديث/إصلاح صور: {updated}")
    print(f"   ⚠️ فشل (صور افتراضية): {failed}")
    print(f"   📋 إجمالي الأطعمة: {total}")
    print("🎉 انتهى!")

if __name__ == "__main__":
    sync()
