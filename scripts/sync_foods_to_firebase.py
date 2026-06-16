import os
import json
import requests
import time
import subprocess
import sys
from firebase_admin import credentials, firestore, initialize_app
from datetime import datetime
from PIL import Image, ImageOps
import shutil

# ========== الإعدادات ==========
FIREBASE_CRED = json.loads(os.environ.get("FIREBASE_SERVICE_ACCOUNT"))
PEXELS_KEY = os.environ.get("PEXELS_API_KEY")

if not FIREBASE_CRED:
    raise Exception("Missing Firebase credentials")

cred = credentials.Certificate(FIREBASE_CRED)
initialize_app(cred)
db = firestore.client()

PLACEHOLDER = "https://via.placeholder.com/300x200?text=%D8%B5%D9%88%D8%B1%D8%A9+%D8%BA%D9%8A%D8%B1+%D9%85%D8%AA%D9%88%D9%81%D8%B1%D8%A9"
TEMP_FOLDER = "temp_images"
FINAL_FOLDER = "images"
os.makedirs(TEMP_FOLDER, exist_ok=True)
os.makedirs(FINAL_FOLDER, exist_ok=True)

# ========== كلمات البحث ==========
SEARCH_WORDS = {
    "الأرز": "rice grains white background",
    "البطاطس": "potato isolated white background",
    "خبز القمح الكامل": "whole wheat bread isolated",
    "الذرة": "corn cob isolated",
    "زيت الزيتون": "olive oil bottle white background",
    "لحم الضأن": "lamb meat cut white background",
    "لحم البقر": "beef steak isolated",
    "السمك البلطي": "tilapia fish white background",
    "التفاح": "red apple isolated white background",
    "المانجو": "mango fruit isolated",
    "الفراولة": "strawberries isolated",
    "التمر": "dates fruit isolated",
    "الخيار": "cucumber isolated",
    "الخس": "lettuce leaves isolated",
    "السبانخ": "spinach leaves isolated",
    "الملوخية": "molokhia leaves white background",
    "المكرونة": "pasta isolated white background",
    "الدجاج": "chicken breast white background",
    "الخبز الأبيض": "white bread sliced isolated",
    "اللبن": "glass of milk isolated",
    "الفول": "fava beans isolated",
    "البيض": "eggs isolated white background",
    "الموز": "banana isolated white background",
    "العسل": "honey jar white background",
}

def search_word(food):
    return SEARCH_WORDS.get(food, f"{food} food white background isolated")

# ========== الأداة 1: google_images_download ==========
def search_google_download(food):
    try:
        from google_images_download import google_images_download
        response = google_images_download.googleimagesdownload()
        arguments = {
            "keywords": search_word(food),
            "limit": 3,
            "print_urls": True,
            "output_directory": TEMP_FOLDER,
            "image_name": food
        }
        paths = response.download(arguments)
        if paths and paths.get(food):
            return paths[food][0]
    except Exception as e:
        print(f"  ⚠️ google_images_download فشل: {e}")
    return None

# ========== الأداة 2: photos_downloader_v2 ==========
def search_photos_downloader(food):
    try:
        cmd = f"python photos_downloader_v2/google_images_grabber.py --query '{search_word(food)}' --limit 3 --output {TEMP_FOLDER}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            for file in os.listdir(TEMP_FOLDER):
                if food in file and file.endswith(('.jpg', '.png', '.jpeg')):
                    return os.path.join(TEMP_FOLDER, file)
    except Exception as e:
        print(f"  ⚠️ photos_downloader_v2 فشل: {e}")
    return None

# ========== الأداة 3: find-images-from-search-engine ==========
def search_find_images(food):
    try:
        search_json = {"active": [search_word(food)], "images_count": 3}
        with open("settings.json", "w") as f:
            json.dump(search_json, f)
        
        subprocess.run(["python", "find_images/search.py"], timeout=60, check=False)
        
        with open("result.json", "r", encoding="utf-8") as f:
            results = json.load(f)
        if results and results[0].get('links'):
            return results[0]['links'][0]
    except Exception as e:
        print(f"  ⚠️ find-images-from-search-engine فشل: {e}")
    return None

# ========== الأداة 4: Selenium (مباشر) ==========
def search_selenium_google(food):
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service
        
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(f"https://www.google.com/search?q={search_word(food)}&tbm=isch")
        time.sleep(3)
        
        images = driver.find_elements(By.CSS_SELECTOR, 'img.rg_i.Q4LuWd')
        for img in images[:3]:
            src = img.get_attribute('src')
            if src and src.startswith('http'):
                driver.quit()
                return src
        driver.quit()
    except Exception as e:
        print(f"  ⚠️ Selenium فشل: {e}")
    return None

# ========== Pexels API (احتياطي) ==========
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
    except Exception as e:
        print(f"  ⚠️ Pexels فشل: {e}")
    return None

# ========== تحميل الصورة ==========
def download_image(url, filename):
    try:
        r = requests.get(url, timeout=15, stream=True)
        if r.status_code == 200:
            path = os.path.join(TEMP_FOLDER, filename)
            with open(path, 'wb') as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)
            return path
    except:
        pass
    return None

# ========== إزالة الخلفية ==========
def remove_background(input_path, output_path):
    try:
        # استخدام backgroundremover (CLI)
        cmd = f"backgroundremover -i {input_path} -o {output_path} -m u2net"
        subprocess.run(cmd, shell=True, timeout=30, check=True)
        if os.path.exists(output_path):
            return output_path
    except:
        pass
    
    # بديل: استخدام rembg (مكتبة)
    try:
        from rembg import remove
        with open(input_path, 'rb') as i:
            input_data = i.read()
            output_data = remove(input_data)
            with open(output_path, 'wb') as o:
                o.write(output_data)
            return output_path
    except:
        pass
    
    return None

# ========== ضبط المقاسات ==========
def resize_image(input_path, output_path, width=400, height=400):
    try:
        img = Image.open(input_path)
        img = ImageOps.fit(img, (width, height), Image.Resampling.LANCZOS, centering=(0.5, 0.5))
        img.save(output_path, 'PNG')
        return output_path
    except:
        return None

# ========== نظام البحث الطبقي ==========
def get_image(food):
    print(f"  🔍 {food}...", end=" ")
    
    tools = [
        ("google_images_download", search_google_download),
        ("photos_downloader_v2", search_photos_downloader),
        ("find_images_search_engine", search_find_images),
        ("selenium_google", search_selenium_google),
    ]
    
    for name, func in tools:
        result = func(food)
        if result:
            # لو رجع رابط، نحمله
            if isinstance(result, str) and result.startswith('http'):
                temp_path = download_image(result, f"{food}.jpg")
                if temp_path:
                    print(f"✅ {name}")
                    return temp_path
            # لو رجع مسار ملف محلي
            elif isinstance(result, str) and os.path.exists(result):
                print(f"✅ {name}")
                return result
    
    # الاحتياطي: Pexels
    url = search_pexels(food)
    if url:
        temp_path = download_image(url, f"{food}_pexels.jpg")
        if temp_path:
            print("⚠️ Pexels (احتياطي)")
            return temp_path
    
    print("❌ مفيش")
    return None

# ========== معالجة الصورة كاملة (بحث + إزالة خلفية + ضبط مقاس) ==========
def process_image(food):
    """تبحث عن صورة، تزيل الخلفية، وتضبط المقاس"""
    temp_path = get_image(food)
    if not temp_path:
        return None
    
    # إزالة الخلفية
    no_bg_path = os.path.join(TEMP_FOLDER, f"{food}_no_bg.png")
    if remove_background(temp_path, no_bg_path):
        # ضبط المقاس
        final_path = os.path.join(FINAL_FOLDER, f"{food}.png")
        if resize_image(no_bg_path, final_path, 400, 400):
            return final_path
    
    # لو فشلت المعالجة، نرجع الصورة الأصلية
    return temp_path

# ========== المزامنة ==========
def sync():
    print("=" * 70)
    print("🚀 المزامنة الشاملة: بحث + إزالة خلفية + ضبط مقاسات")
    print("   الأدوات: google_images_download → photos_downloader_v2 → find_images → Selenium → Pexels")
    print("   المعالجة: إزالة الخلفية (backgroundremover) → ضبط مقاس 400x400 (Pillow)")
    print(f"📅 {datetime.now()}")
    print("=" * 70)
    
    # إضافة الأطعمة
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
    
    # تحديث الصور
    print("\n🖼️ الخطوة 2: بحث وتجهيز الصور...")
    docs = db.collection('foods').stream()
    updated = 0
    total = 0
    failed = 0
    
    for doc in docs:
        total += 1
        food_name = doc.id
        print(f"\n📸 {food_name}:", end=" ")
        
        # نبحث عن صورة ونجهزها
        final_path = process_image(food_name)
        
        if final_path:
            # رفع الصورة إلى Firebase Storage (أو حفظ الرابط)
            # نستخدم Placeholder مؤقتاً (سنطور رفع الصور لاحقاً)
            doc.reference.update({
                'imageUrl': f"images/{food_name}.png",
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
            print(f"  ⚠️ افتراضي لـ {food_name}")
        
        time.sleep(1)
    
    print("\n" + "=" * 70)
    print(f"📊 التقرير النهائي:")
    print(f"   ✅ أضيف جديد: {added}")
    print(f"   🖼️ تم تحديث صور: {updated}")
    print(f"   ⚠️ فشل (افتراضي): {failed}")
    print(f"   📋 إجمالي الأطعمة: {total}")
    print("🎉 انتهى!")

if __name__ == "__main__":
    sync()
