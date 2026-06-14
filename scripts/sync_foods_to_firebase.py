import os
import json
import requests
from tavily import TavilyClient
from firebase_admin import credentials, firestore, initialize_app
from PIL import Image
from io import BytesIO

TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
FIREBASE_CRED = json.loads(os.environ.get("FIREBASE_SERVICE_ACCOUNT"))

if not TAVILY_API_KEY or not FIREBASE_CRED:
    raise Exception("Missing secrets")

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
        print(f"⚠️ {food_name}: {e}")
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
            print(f"✅ {filename}")
            return f"images/{filename}"
    except Exception as e:
        print(f"❌ {food_name}: {e}")
    return None

def sync_food(food, food_type):
    doc_ref = db.collection('foods').document(food['name'])
    doc = doc_ref.get()
    
    if doc.exists:
        existing = doc.to_dict()
        if not existing.get('imageUrl'):
            print(f"📸 {food['name']} بدون صورة...")
            url = fetch_image_url(food['name'])
            if url:
                path = download_and_upload_image(url, food['name'])
                if path:
                    doc_ref.update({'imageUrl': path, 'updatedAt': firestore.SERVER_TIMESTAMP})
    else:
        print(f"➕ إضافة {food['name']}")
        url = fetch_image_url(food['name'])
        path = download_and_upload_image(url, food['name']) if url else None
        doc_ref.set({**food, "type": food_type, "imageUrl": path, "createdAt": firestore.SERVER_TIMESTAMP, "updatedAt": firestore.SERVER_TIMESTAMP})

def main():
    print("🚀 بدء المزامنة...")
    with open("foods.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    for food in data.get("allowed", []):
        sync_food(food, "allowed")
    for food in data.get("forbidden", []):
        sync_food(food, "forbidden")
    for food in data.get("limited", []):
        sync_food(food, "limited")
    print("🎉 انتهى!")

if __name__ == "__main__":
    main()
