import os
import json
import requests
from tavily import TavilyClient
from firebase_admin import credentials, firestore, initialize_app
from PIL import Image
from io import BytesIO

# ========== الإعدادات ==========
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
FIREBASE_CRED = json.loads(os.environ.get("FIREBASE_SERVICE_ACCOUNT"))

if not TAVILY_API_KEY or not FIREBASE_CRED:
    raise Exception("Missing secrets")

# تهيئة Firebase
cred = credentials.Certificate(FIREBASE_CRED)
initialize_app(cred)
db = firestore.client()

tavily = TavilyClient(api_key=TAVILY_API_KEY)

IMAGES_FOLDER = "images"
os.makedirs(IMAGES_FOLDER, exist_ok=True)

def fetch_image_url(food_name):
    try:
        response = tavily.search(f"{food_name} طعام خلفية بيضاء", include_images=True, max_results=1)
        images = response.get('images', [])
        return images[0] if images else None
    except Exception as e:
        print(f"⚠️ بحث عن {food_name}: {e}")
        return None

def download_and_upload_image(image_url, food_name):
    try:
        response = requests.get(image_url, timeout=15)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            img.thumbnail((300, 300))
            filename = f"{food_name}.webp"
            filepath = os.path.join(IMAGES_FOLDER, filename)
            img.save(filepath, 'webp', quality=75)
            print(f"✅ تحميل: {filename}")
            return f"images/{filename}"
    except Exception as e:
        print(f"❌ فشل تحميل {food_name}: {e}")
    return None

def sync_food(food, food_type):
    doc_ref = db.collection('foods').document(food['name'])
    doc = doc_ref.get()
    
    if doc.exists:
        print(f"⏩ {food['name']} موجود بالفعل، أتحقق من الصورة...")
        existing_data = doc.to_dict()
        if not existing_data.get('imageUrl'):
            print(f"📸 {food['name']} بدون صورة، أحاول جلبها...")
            image_url = fetch_image_url(food['name'])
            if image_url:
                image_path = download_and_upload_image(image_url, food['name'])
                if image_path:
                    doc_ref.update({'imageUrl': image_path, 'updatedAt': firestore.SERVER_TIMESTAMP})
                    print(f"🖼️ تم تحديث صورة {food['name']}")
    else:
        print(f"➕ إضافة {food['name']} إلى Firebase...")
        image_url = fetch_image_url(food['name'])
        image_path = download_and_upload_image(image_url, food['name']) if image_url else None
        doc_ref.set({
            **food,
            "type": food_type,
            "imageUrl": image_path,
            "createdAt": firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.SERVER_TIMESTAMP
        })
        print(f"✅ تمت إضافة {food['name']}")

def main():
    print("🚀 بدء مزامنة الأطعمة من foods.json إلى Firebase...")
    
    # قراءة ملف foods.json
    with open("foods.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # مزامنة كل صنف
    for food in data.get("allowed", []):
        sync_food(food, "allowed")
    for food in data.get("forbidden", []):
        sync_food(food, "forbidden")
    for food in data.get("limited", []):
        sync_food(food, "limited")
    
    print("\n🎉 انتهت المزامنة!")

if __name__ == "__main__":
    main()
