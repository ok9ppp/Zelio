from pymongo import MongoClient; client = MongoClient("mongodb://root:zqkz5vgv@therapy-mongodb.ns-4221v9wq.svc:27017/therapy_db?authSource=admin"); db = client["therapy_db"]; result = db.treatment_cards.update_many({"detail_page.no_relapse_rate": "0.7"}, {"$set": {"detail_page.no_relapse_rate": "70.0%"}}); print(f"修复0.7: {result.modified_count}张卡片"); result = db.treatment_cards.update_many({"detail_page.no_relapse_rate": "0.9"}, {"$set": {"detail_page.no_relapse_rate": "90.0%"}}); print(f"修复0.9: {result.modified_count}张卡片")
