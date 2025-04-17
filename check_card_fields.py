import pymongo
import json
from bson import ObjectId

# 自定义编码器，处理MongoDB特殊类型
class MongoEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return super(MongoEncoder, self).default(obj)

# 连接到MongoDB
mongo_uri = "mongodb://root:zqkz5vgv@therapy-mongodb.ns-4221v9wq.svc:27017/therapy_db?authSource=admin"
client = pymongo.MongoClient(mongo_uri)
db = client["therapy_db"]

# 获取一个卡片记录进行分析
card = db.cards.find_one({})

if card:
    # 打印卡片的完整字段结构
    print("卡片字段结构:")
    for key in card.keys():
        print(f"- {key}: {type(card[key])}")
    
    # 检查是否存在评分相关字段
    score_fields = [
        "操作难度评分", "complexity_score", "复杂度评分", 
        "时间成本评分", "time_cost_score", 
        "生活干扰评分", "life_interference_score"
    ]
    
    print("\n评分字段检查:")
    for field in score_fields:
        if field in card:
            print(f"✓ 字段存在: {field} = {card[field]}")
        else:
            print(f"✗ 字段不存在: {field}")
    
    # 检查Excel中的这些字段是否有对应的MongoDB字段
    print("\n可能的字段映射:")
    all_fields = list(card.keys())
    for field in ["操作难度评分", "时间成本评分", "生活干扰评分"]:
        found = False
        for db_field in all_fields:
            if field.lower() in db_field.lower() or db_field.lower() in field.lower():
                print(f"Excel字段 '{field}' 可能映射到 '{db_field}'")
                found = True
        if not found:
            print(f"Excel字段 '{field}' 没有找到可能的映射")
    
    # 打印卡片的部分关键信息
    print("\n卡片基本信息:")
    card_sample = {k: card[k] for k in ["_id", "name", "user_name", "created_at"] if k in card}
    print(json.dumps(card_sample, ensure_ascii=False, indent=2, cls=MongoEncoder))
    
    # 检查是否有risk_data字段，这通常用于存储风险相关信息
    if "risk_data" in card:
        print("\n风险数据字段:")
        print(json.dumps(card["risk_data"], ensure_ascii=False, indent=2, cls=MongoEncoder))
else:
    print("未找到卡片数据") 