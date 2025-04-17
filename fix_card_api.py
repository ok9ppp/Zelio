import pymongo
from bson import ObjectId
import logging
import datetime

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 连接MongoDB
mongo_uri = "mongodb://root:zqkz5vgv@therapy-mongodb.ns-4221v9wq.svc:27017/therapy_db?authSource=admin"
client = pymongo.MongoClient(mongo_uri)
db = client["therapy_db"]

def fix_cards():
    """修复所有卡片，确保操作难度评分等字段正确保存"""
    
    # 获取所有卡片
    cards = list(db.treatment_cards.find())
    logger.info(f"共找到 {len(cards)} 张卡片需要检查")
    
    # 更新统计
    updated_count = 0
    already_correct_count = 0
    
    for card in cards:
        card_id = str(card['_id'])
        
        # 检查是否需要更新
        needs_update = False
        update_fields = {}
        
        # 1. 检查是否有detail_page字段
        if 'detail_page' not in card:
            logger.warning(f"卡片 {card_id} 没有detail_page字段，跳过")
            continue
            
        # 2. 对于新格式卡片，检查三个评分字段是否在顶层
        if 'operation_difficulty_score' in card['detail_page']:
            # 新格式卡片
            if 'complexity_score' not in card:
                update_fields['complexity_score'] = card['detail_page']['operation_difficulty_score']
                update_fields['操作难度评分'] = card['detail_page']['operation_difficulty_score']
                update_fields['复杂度评分'] = card['detail_page']['operation_difficulty_score']
                needs_update = True
            
            if 'time_cost_score' not in card and 'time_cost_score' in card['detail_page']:
                update_fields['time_cost_score'] = card['detail_page']['time_cost_score']
                update_fields['时间成本评分'] = card['detail_page']['time_cost_score']
                needs_update = True
            
            if 'life_interference_score' not in card and 'life_interference_score' in card['detail_page']:
                update_fields['life_interference_score'] = card['detail_page']['life_interference_score']
                update_fields['生活干扰评分'] = card['detail_page']['life_interference_score']
                needs_update = True
        
        # 3. 对于旧格式卡片，从raw_data或template_reference中提取评分
        elif ('raw_data' in card or 'template_reference' in card) and 'complexity_score' not in card:
            # 从raw_data或template_reference中获取评分数据
            source_data = card.get('raw_data', {}) or card.get('template_reference', {})
            
            # 将文本难度转换为评分
            def text_to_score(text):
                if not text or text == '未知':
                    return 5.0
                
                # 尝试直接转换为数字
                try:
                    return float(text)
                except (ValueError, TypeError):
                    pass
                
                # 文本到评分的映射
                text_mapping = {
                    '极低': 1.0, '非常低': 1.0, '很低': 2.0, '低': 3.0,
                    '较低': 3.0, '中低': 4.0, '适中': 5.0, '中': 5.0, 
                    '一般': 5.0, '中高': 6.0, '较高': 7.0, '高': 7.0, 
                    '很高': 8.0, '非常高': 9.0, '极高': 10.0,
                    
                    '极简单': 1.0, '非常简单': 1.0, '很简单': 2.0, '简单': 3.0,
                    '较简单': 3.0, '中等': 5.0, '较复杂': 7.0, '复杂': 7.0,
                    '很复杂': 8.0, '非常复杂': 9.0, '极复杂': 10.0,
                    
                    '极轻微': 1.0, '非常轻微': 1.0, '很轻微': 2.0, '轻微': 3.0,
                    '较轻微': 3.0, '中度': 5.0, '较严重': 7.0, '严重': 7.0,
                    '很严重': 8.0, '非常严重': 9.0, '极严重': 10.0
                }
                
                # 如果能在映射中找到文本，返回对应的评分
                if text in text_mapping:
                    return text_mapping[text]
                
                # 默认返回中等评分
                return 5.0
            
            # 处理操作难度评分
            operation_difficulty = source_data.get('操作难度', source_data.get('操作难度评分', None))
            if operation_difficulty is not None:
                score = text_to_score(operation_difficulty)
                update_fields['complexity_score'] = score
                update_fields['操作难度评分'] = score
                update_fields['复杂度评分'] = score
                
                # 同时更新detail_page
                if 'detail_page' in card and 'operation_difficulty_score' not in card['detail_page']:
                    update_fields['detail_page.operation_difficulty_score'] = score
                
                needs_update = True
            
            # 处理时间成本评分
            time_cost = source_data.get('时间成本', source_data.get('时间成本评分', None))
            if time_cost is not None:
                score = text_to_score(time_cost)
                update_fields['time_cost_score'] = score
                update_fields['时间成本评分'] = score
                
                # 同时更新detail_page
                if 'detail_page' in card and 'time_cost_score' not in card['detail_page']:
                    update_fields['detail_page.time_cost_score'] = score
                
                needs_update = True
            
            # 处理生活干扰评分
            life_interference = source_data.get('生活干扰', source_data.get('生活干扰评分', None))
            if life_interference is not None:
                score = text_to_score(life_interference)
                update_fields['life_interference_score'] = score
                update_fields['生活干扰评分'] = score
                
                # 同时更新detail_page
                if 'detail_page' in card and 'life_interference_score' not in card['detail_page']:
                    update_fields['detail_page.life_interference_score'] = score
                
                needs_update = True
        
        # 如果需要更新，执行更新操作
        if needs_update:
            # 记录更新前的值
            logger.info(f"准备更新卡片 {card_id} 的评分字段")
            for field, value in update_fields.items():
                if not field.startswith('detail_page.'):
                    logger.info(f"  - {field}: {value}")
            
            # 更新记录
            update_result = db.treatment_cards.update_one(
                {'_id': card['_id']},
                {'$set': update_fields}
            )
            
            if update_result.modified_count > 0:
                updated_count += 1
                logger.info(f"已更新卡片 {card_id} 的评分字段")
            else:
                logger.warning(f"尝试更新卡片 {card_id} 但没有实际修改")
        else:
            already_correct_count += 1
    
    logger.info(f"卡片修复完成: 总计 {len(cards)} 张卡片, 已更新 {updated_count} 张, {already_correct_count} 张无需更新")
    return {
        'total_cards': len(cards),
        'updated_cards': updated_count,
        'already_correct': already_correct_count
    }

if __name__ == "__main__":
    logger.info("开始修复卡片数据...")
    result = fix_cards()
    logger.info(f"修复完成: {result}") 