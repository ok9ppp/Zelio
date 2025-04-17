from pymongo import MongoClient
from bson import ObjectId

# 连接数据库
client = MongoClient('mongodb://root:zqkz5vgv@therapy-mongodb.ns-4221v9wq.svc:27017/therapy_db?authSource=admin')
db = client['therapy_db']

# 查询所有卡片
cards = list(db.treatment_cards.find({}))
print(f"找到 {len(cards)} 张卡片")

# 逐一检查和修复
fixed_count = 0
deleted_count = 0

for card in cards:
    card_id = card['_id']
    needs_update = False
    needs_delete = False
    update_data = {}
    
    # 检查detail_page是否存在
    if 'detail_page' in card and 'no_relapse_rate' in card['detail_page']:
        relapse_rate = card['detail_page']['no_relapse_rate']
        print(f"卡片 {card_id}: 未复发率={relapse_rate}, 类型={type(relapse_rate)}")
        
        # 处理字符串类型的值
        if isinstance(relapse_rate, str) and '%' not in relapse_rate:
            try:
                rate_value = float(relapse_rate)
                # 如果是小数格式(0.x)，需要乘以100
                if rate_value < 1:
                    rate_value = rate_value * 100
                new_rate = f"{rate_value:.1f}%"
                update_data['detail_page.no_relapse_rate'] = new_rate
                needs_update = True
                print(f"将转换 {relapse_rate} -> {new_rate}")
            except (ValueError, TypeError) as e:
                print(f"转换失败: {str(e)}")
                needs_delete = True
        # 处理浮点数类型的值
        elif isinstance(relapse_rate, float):
            print(f"发现浮点数类型的未复发率: {relapse_rate}，将删除此卡片")
            needs_delete = True
    
    # 如果需要更新，执行更新
    if needs_update:
        result = db.treatment_cards.update_one(
            {'_id': card_id},
            {'$set': update_data}
        )
        if result.modified_count > 0:
            fixed_count += 1
            print(f"已修复卡片 {card_id}")
        else:
            print(f"卡片 {card_id} 更新失败")
    
    # 如果需要删除，执行删除
    if needs_delete:
        result = db.treatment_cards.delete_one({'_id': card_id})
        if result.deleted_count > 0:
            deleted_count += 1
            print(f"已删除卡片 {card_id}")
        else:
            print(f"卡片 {card_id} 删除失败")

print(f"\n总共修复了 {fixed_count} 张卡片，删除了 {deleted_count} 张卡片")

# 验证修复结果
cards = list(db.treatment_cards.find({}, {'detail_page.no_relapse_rate': 1}))
print("\n修复后所有卡片的未复发率:")
for card in cards:
    card_id = str(card['_id'])
    if 'detail_page' in card and 'no_relapse_rate' in card['detail_page']:
        print(f"ID: {card_id}, 未复发率: {card['detail_page']['no_relapse_rate']}") 