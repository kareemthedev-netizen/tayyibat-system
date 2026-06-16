import os
import json
import requests
from firebase_admin import credentials, firestore, initialize_app
from datetime import datetime
import time

FIREBASE_CRED = json.loads(os.environ.get("FIREBASE_SERVICE_ACCOUNT"))
PEXELS_KEY = os.environ.get("PEXELS_API_KEY")

if not FIREBASE_CRED:
    raise Exception("Missing Firebase credentials")

cred = credentials.Certificate(FIREBASE_CRED)
initialize_app(cred)
db = firestore.client()

PLACEHOLDER = "https://via.placeholder.com/300x200?text=%D8%B5%D9%88%D8%B1%D8%A9+%D8%BA%D9%8A%D8%B1+%D9%85%D8%AA%D9%88%D9%81%D8%B1%D8%A9"

# كلمات بحث مخصصة لـ Pexels
SEARCH_WORDS = {
    "الأرز": "rice grains",
    "البطاطس": "potato",
    "خبز القمح الكامل": "whole wheat bread",
    "الذرة": "corn cob",
    "زيت الزيتون": "olive oil",
    "لحم الضأن": "lamb meat",
    "لحم البقر": "beef steak",
    "السمك البلطي": "tilapia fish",
    "التفاح": "red apple",
    "المانجو": "mango fruit",
    "الفراولة": "strawberries",
    "التمر": "dates fruit",
    "الخيار": "cucumber",
    "الخس": "lettuce",
    "السبانخ": "spinach",
    "الملوخية": "molokhia",
    "المكرونة": "pasta",
    "الدجاج": "chicken breast",
    "الخبز الأبيض": "white bread",
    "اللبن": "milk",
    "الفول": "fava beans",
    "البيض": "eggs",
    "الموز": "banana",
    "العسل": "honey",
}

def search_word(food):
    return SEARCH_WORDS.get(food, food)

def search_pexels(food):
    """Pexels فقط - بيجيب صور احترافية"""
    if not PEXELS_KEY:
        return None
    try:
        q = search_word(food)
        r = requests.get("https://api.pexels.com/v1/search",
                         headers={"Authorization": PEXELS_KEY},
                         params={'query': q, 'per_page': 5},
                         timeout=10)
        if r.status_code == 200 and r.json().get('photos'):
            # بيختار الصورة الأولى اللي مش بايظة
            for photo in r.json()['photos']:
                url = photo['src']['medium']
                if url and 'pexels' in url:
                    return url
    except Exception as e:
        print(f"  ⚠️ Pexels error: {e}")
    return None

def get_image(food):
    print(f"  🔍 {food}...", end=" ")
    url = search_pexels(food)
    if url:
        print("✅ Pexels")
        return url
    print("❌ مفيش")
    return None

def sync():
    print("=" * 60)
    print("🚀 تحديث الصور (Pexels فقط - احترافي)")
    print(f"📅 {datetime.now()}")
    print("=" * 60)
    
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
    
    # تحديث الصور (من الصفر)
    print("\n🖼️ الخطوة 2: تحديث الصور...")
    docs = db.collection('foods').stream()
    updated = 0
    total = 0
    
    for doc in docs:
        total += 1
        food_name = doc.id
        print(f"\n📸 {food_name}:", end=" ")
        
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
            print(f"  ⚠️ افتراضي")
        
        time.sleep(0.5)
    
    print("\n" + "=" * 60)
    print(f"📊 التقرير النهائي:")
    print(f"   ✅ أضيف جديد: {added}")
    print(f"   🖼️ تم تحديث: {updated}")
    print(f"   📋 إجمالي الأطعمة: {total}")
    print("🎉 انتهى!")

if __name__ == "__main__":
    sync()
