import os
import json
import requests
from firebase_admin import credentials, firestore, initialize_app
from datetime import datetime
from urllib.parse import quote

FIREBASE_CRED = json.loads(os.environ.get("FIREBASE_SERVICE_ACCOUNT"))

if not FIREBASE_CRED:
    raise Exception("Missing Firebase credentials")

cred = credentials.Certificate(FIREBASE_CRED)
initialize_app(cred)
db = firestore.client()

PLACEHOLDER = "https://via.placeholder.com/300x200?text=%D8%B5%D9%88%D8%B1%D8%A9+%D8%BA%D9%8A%D8%B1+%D9%85%D8%AA%D9%88%D9%81%D8%B1%D8%A9"

def compress_image_url(image_url):
    """تضغط الصورة بإضافة معاملات للرابط"""
    if not image_url:
        return None
    if image_url == PLACEHOLDER:
        return image_url
    
    # Pexels
    if 'pexels.com' in image_url:
        if '?' in image_url:
            return image_url + '&auto=compress&cs=tinysrgb&w=300&h=200&fit=crop'
        else:
            return image_url + '?auto=compress&cs=tinysrgb&w=300&h=200&fit=crop'
    
    # Unsplash
    if 'unsplash.com' in image_url or 'images.unsplash.com' in image_url:
        if '?' in image_url:
            return image_url + '&w=300&h=200&fit=crop'
        else:
            return image_url + '?w=300&h=200&fit=crop'
    
    # أي رابط تاني - weserv.nl
    return f"https://images.weserv.nl/?url={quote(image_url)}&w=300&h=200&fit=cover&q=80"

def compress_all_images():
    print("=" * 60)
    print("🚀 ضغط الصور في Firebase")
    print(f"📅 {datetime.now()}")
    print("=" * 60)
    
    docs = db.collection('foods').stream()
    updated = 0
    total = 0
    skipped = 0
    
    for doc in docs:
        total += 1
        food_name = doc.id
        food_data = doc.to_dict()
        current = food_data.get('imageUrl', '')
        
        if not current or current == PLACEHOLDER:
            print(f"⏩ {food_name}: صورة افتراضية، نتخطى")
            skipped += 1
            continue
        
        compressed = compress_image_url(current)
        
        if compressed and compressed != current:
            doc.reference.update({
                'imageUrl': compressed,
                'updatedAt': firestore.SERVER_TIMESTAMP
            })
            updated += 1
            print(f"  ✅ {food_name}: تم ضغط الصورة")
        else:
            print(f"  ⏩ {food_name}: الصورة مضغوطة بالفعل")
        
        time.sleep(0.3)
    
    print("\n" + "=" * 60)
    print(f"📊 التقرير النهائي:")
    print(f"   ✅ تم ضغط: {updated}")
    print(f"   ⏩ تم تخطي: {skipped}")
    print(f"   📋 إجمالي الأطعمة: {total}")
    print("🎉 انتهى!")

if __name__ == "__main__":
    compress_all_images()
