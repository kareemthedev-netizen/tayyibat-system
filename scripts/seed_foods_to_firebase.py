import os
import json
from firebase_admin import credentials, firestore, initialize_app

FIREBASE_CRED = json.loads(os.environ.get("FIREBASE_SERVICE_ACCOUNT"))

cred = credentials.Certificate(FIREBASE_CRED)
initialize_app(cred)
db = firestore.client()

def seed_database():
    print("🚀 بدء استبدال البيانات في Firebase...")
    
    # قراءة الملف الجديد
    with open("foods.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # مسح المجموعة القديمة (اختياري - لو عايز تمسح كل حاجة)
    # docs = db.collection('foods').stream()
    # for doc in docs:
    #     doc.reference.delete()
    #     print(f"🗑️ تم مسح: {doc.id}")
    
    # إضافة البيانات الجديدة
    all_foods = data.get("allowed", []) + data.get("forbidden", []) + data.get("limited", [])
    count = 0
    
    for food in all_foods:
        doc_ref = db.collection('foods').document(food['name'])
        doc_ref.set({
            "name": food['name'],
            "type": food.get("type", "allowed"),
            "category": food.get("category", ""),
            "desc": food.get("desc", ""),
            "benefits": food.get("benefits", ""),
            "warning": food.get("warning", ""),
            "quantity": food.get("quantity", ""),
            "createdAt": firestore.SERVER_TIMESTAMP,
        })
        count += 1
        print(f"✅ {food['name']}")
    
    print(f"🎉 تم تحديث {count} صنف في Firebase!")

if __name__ == "__main__":
    seed_database()
