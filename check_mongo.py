from pymongo import MongoClient; client = MongoClient("mongodb://root:zqkz5vgv@therapy-mongodb.ns-4221v9wq.svc:27017/therapy_db?authSource=admin"); db = client["therapy_db"]; cards = db.treatment_cards.find({}, {"detail_page.no_relapse_rate": 1}); print("所有卡片的未复发率:"); for card in cards: if "detail_page" in card and "no_relapse_rate" in card["detail_page"]: print(f"ID: {card[\"_id\"]}, 未复发率: {card[\"detail_page\"][\"no_relapse_rate\"]}")
