import os
import requests
from PIL import Image
from io import BytesIO
from tavily import TavilyClient

# جلب الـ API Key من GitHub Secrets
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
if not TAVILY_API_KEY:
    raise Exception("TAVILY_API_KEY not found in secrets")

OUTPUT_FOLDER = "images"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# قائمة الأطعمة اللي محتاج صورها
FOODS_LIST = [
    "الارز", "البطاطس", "خبز القمح الكامل", "الذرة",
    "زيت الزيتون", "السمن البلدي", "الزبد البلدي",
    "لحم الضأن", "لحم البقر", "لحم الارنب", "الكوارع", 
    "السمك", "الجمبري", "التفاح", "المانجو", "الرمان",
    "الفراولة", "التمر", "الخيار", "الخس", "السبانخ",
    "الملوخية", "الكوسة", "الموز", "العسل", "الدجاج",
    "اللبن", "الفول", "البيض", "الخبز الابيض", "المكرونة"
]

tavily = TavilyClient(api_key=TAVILY_API_KEY)

def download_and_optimize(image_url, food_name):
    """تحميل وتحسين صورة"""
    try:
        response = requests.get(image_url, timeout=15)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            
            # تحويل للـ RGB لو الصورة فيها شفافية
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # تصغير الحجم
            img.thumbnail((300, 300))
            
            # حفظ كـ WebP
            filepath = os.path.join(OUTPUT_FOLDER, f"{food_name}.webp")
            img.save(filepath, 'webp', quality=75)
            print(f"✅ {food_name}.webp")
            return True
    except Exception as e:
        print(f"❌ {food_name}: {e}")
    return False

# البحث عن الصور
for food in FOODS_LIST:
    print(f"🔍 ببحث عن: {food}")
    try:
        response = tavily.search(f"{food} طعام خلفية بيضاء", include_images=True)
        if response.get('images'):
            download_and_optimize(response['images'][0], food)
        else:
            print(f"⚠️ مفيش صور لـ {food}")
    except Exception as e:
        print(f"❌ خطأ في {food}: {e}")

print("🎉 خلصنا!")
