import os
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

cred = credentials.Certificate(FIREBASE_CRED)
initialize_app(cred)
db = firestore.client()
tavily = TavilyClient(api_key=TAVILY_API_KEY)

IMAGES_FOLDER = "images"
os.makedirs(IMAGES_FOLDER, exist_ok=True)

# قائمة الأطعمة الأساسية (مرة واحدة فقط)
FOODS_DATA = [
    {"name": "الأرز", "type": "allowed", "category": "نشويات", "desc": "الأرز الأبيض أو البني", "benefits": "سهل الهضم، مصدر طاقة سريع", "warning": "لا تفرط في الكمية", "quantity": "حسب الجوع"},
    {"name": "البطاطس", "type": "allowed", "category": "نشويات", "desc": "البطاطس المسلوقة أو المشوية", "benefits": "غنية بالبوتاسيوم، تشعر بالشبع", "warning": "ممنوع القلي", "quantity": "حبة متوسطة يومياً"},
    {"name": "خبز القمح الكامل", "type": "allowed", "category": "نشويات", "desc": "خبز أسمر 100%", "benefits": "غني بالألياف، يحسن الهضم", "warning": "لا تخلطه مع غيره", "quantity": "شريحتان يومياً"},
    {"name": "زيت الزيتون", "type": "allowed", "category": "دهون", "desc": "زيت زيتون بكر ممتاز", "benefits": "مفيد للقلب والشرايين", "warning": "لا تستخدمه للقلي", "quantity": "ملعقتان يومياً"},
    {"name": "لحم الضأن", "type": "allowed", "category": "لحوم حمراء", "desc": "لحم الخروف", "benefits": "غني بالحديد والبروتين", "warning": "مرة واحدة أسبوعياً", "quantity": "100-150 جرام"},
    {"name": "السمك البلطي", "type": "allowed", "category": "مأكولات بحرية", "desc": "سمك بلطي طازج", "benefits": "غني بالبروتين", "warning": "لا تقليه، اشويه", "quantity": "مرتين أسبوعياً"},
    {"name": "التفاح", "type": "allowed", "category": "فواكه", "desc": "تفاح طازج", "benefits": "غني بالألياف", "warning": "تناوله بقشره", "quantity": "تفاحة يومياً"},
    {"name": "الخبز الأبيض", "type": "forbidden", "category": "نشويات ممنوعة", "desc": "خبز مصنع من دقيق أبيض", "benefits": "لا فوائد صحية", "warning": "يسبب التهابات", "quantity": "ممنوع"},
    {"name": "الدجاج", "type": "forbidden", "category": "لحوم دواجن", "desc": "لحم دجاج", "benefits": "مصدر بروتين", "warning": "يمنعه الدكتور العوضي", "quantity": "ممنوع"},
    {"name": "اللبن", "type": "forbidden", "category": "ألبان", "desc": "حليب البقر", "benefits": "مصدر كالسيوم", "warning": "يسبب التهابات", "quantity": "ممنوع"},
]

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
            print(f"✅ تحميل: {filename}")
            return f"images/{filename}"
    except Exception as e:
        print(f"❌ {food_name}: {e}")
    return None

def main():
    print("🚀 بدء المزامنة مع Firebase (إضافة فقط)...")
    
    for food in FOODS_DATA:
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
                "imageUrl": image_path,
                "createdAt": firestore.SERVER_TIMESTAMP,
                "updatedAt": firestore.SERVER_TIMESTAMP
            })
            print(f"✅ تمت إضافة {food['name']}")

    print("\n🎉 انتهت المزامنة (تمت إضافة الجديد فقط، وتم تحديث الصور الناقصة).")

if __name__ == "__main__":
    main()
