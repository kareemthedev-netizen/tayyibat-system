import os
import json
from firebase_admin import credentials, firestore, initialize_app

FIREBASE_CRED = json.loads(os.environ.get("FIREBASE_SERVICE_ACCOUNT"))

cred = credentials.Certificate(FIREBASE_CRED)
initialize_app(cred)
db = firestore.client()

def add_empty_image_field():
    print("🚀 إضافة حقل imageUrl فارغ لكل صنف...")
    
    docs = db.collection('foods').stream()
    updated = 0
    
    for doc in docs:
        food_name = doc.id
        data = doc.to_dict()
        
        # لو الحقل مش موجود، نضيفه بقيمة null
        if 'imageUrl' not in data:
            doc.reference.update({
                'imageUrl': None,
                'updatedAt': firestore.SERVER_TIMESTAMP
            })
            updated += 1
            print(f"✅ {food_name}: تم إضافة حقل imageUrl")
        else:
            print(f"⏩ {food_name}: الحقل موجود بالفعل")
    
    print(f"🎉 تم إضافة حقل imageUrl لـ {updated} صنف")

if __name__ == "__main__":
    add_empty_image_field()
