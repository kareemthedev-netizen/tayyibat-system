import os
import json
import requests
import time
from firebase_admin import credentials, firestore, initialize_app
from datetime import datetime

# ========== الإعدادات ==========
FIREBASE_CRED = json.loads(os.environ.get("FIREBASE_SERVICE_ACCOUNT"))
PEXELS_KEY = os.environ.get("PEXELS_API_KEY")

if not FIREBASE_CRED:
    raise Exception("Missing Firebase credentials")

cred = credentials.Certificate(FIREBASE_CRED)
initialize_app(cred)
db = firestore.client()

PLACEHOLDER = "https://via.placeholder.com/300x200?text=%D8%B5%D9%88%D8%B1%D8%A9+%D8%BA%D9%8A%D8%B1+%D9%85%D8%AA%D9%88%D9%81%D8%B1%D8%A9"

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

# ========== البحث عن الصور (Pexels) ==========
def search_pexels(food):
    if not PEXELS_KEY:
        return None
    try:
        q = search_word(food)
        r = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_KEY},
            params={'query': q, 'per_page': 5},
            timeout=15
        )
        if r.status_code == 200:
            data = r.json()
            if data.get('photos'):
                # نفضل الصور اللي فيها خلفية بيضا
                for photo in data['photos']:
                    alt = photo.get('alt', '').lower()
                    if 'white' in alt or 'isolated' in alt:
                        return photo['src']['medium']
                return data['photos'][0]['src']['medium']
    except Exception as e:
        print(f"  ⚠️ Pexels فشل: {e}")
    return None

# ========== مزامنة البيانات ==========
def sync():
    print("=" * 60)
    print("🚀 تحديث الصور (Pexels)")
    print(f"📅 {datetime.now()}")
    print("=" * 60)
    
    # جلب الأطعمة من foods.json
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
    print("\n🖼️ الخطوة 2: تحديث الصور...")
    docs = db.collection('foods').stream()
    updated = 0
    total = 0
    failed = 0
    
    for doc in docs:
        total += 1
        food_name = doc.id
        current = doc.to_dict().get('imageUrl', '')
        
        # لو الصورة موجودة وصحيحة، نتخطى
        if current and current != PLACEHOLDER:
            print(f"⏩ {food_name}: صورة موجودة ✓")
            continue
        
        print(f"\n📸 {food_name}: أبحث عن صورة...")
        img = search_pexels(food_name)
        
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
            print(f"  ⚠️ افتراضي لـ {food_name}")
        
        time.sleep(0.5)
    
    print("\n" + "=" * 60)
    print(f"📊 التقرير النهائي:")
    print(f"   ✅ أضيف جديد: {added}")
    print(f"   🖼️ تم تحديث صور: {updated}")
    print(f"   ⚠️ فشل (افتراضي): {failed}")
    print(f"   📋 إجمالي الأطعمة: {total}")
    print("🎉 انتهى!")

if __name__ == "__main__":
    sync()
