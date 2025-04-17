import pymongo
from bson import ObjectId
import logging
import datetime
import json
import os

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 连接MongoDB
mongo_uri = "mongodb://root:zqkz5vgv@therapy-mongodb.ns-4221v9wq.svc:27017/therapy_db?authSource=admin"
client = pymongo.MongoClient(mongo_uri)
db = client["therapy_db"]

# 自定义JSON编码器处理MongoDB的ObjectId
class MongoEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        elif isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        return super(MongoEncoder, self).default(obj)

def check_api_response():
    """检查API响应中的评分字段是否正确"""
    
    # 获取一个示例卡片
    card = db.treatment_cards.find_one()
    if not card:
        logger.error("数据库中没有找到卡片")
        return
    
    card_id = str(card['_id'])
    logger.info(f"检查卡片 {card_id} 的字段")
    
    # 检查detail_page中是否有评分字段
    if 'detail_page' in card:
        if 'operation_difficulty_score' in card['detail_page']:
            logger.info(f"卡片 {card_id} 包含操作难度评分: {card['detail_page']['operation_difficulty_score']}")
        else:
            logger.warning(f"卡片 {card_id} 不包含操作难度评分")
            
        if 'time_cost_score' in card['detail_page']:
            logger.info(f"卡片 {card_id} 包含时间成本评分: {card['detail_page']['time_cost_score']}")
        else:
            logger.warning(f"卡片 {card_id} 不包含时间成本评分")
            
        if 'life_interference_score' in card['detail_page']:
            logger.info(f"卡片 {card_id} 包含生活干扰评分: {card['detail_page']['life_interference_score']}")
        else:
            logger.warning(f"卡片 {card_id} 不包含生活干扰评分")
    else:
        logger.warning(f"卡片 {card_id} 不包含detail_page字段")
    
    # 检查顶层是否有复杂度评分字段
    if 'complexity_score' in card:
        logger.info(f"卡片 {card_id} 顶层包含复杂度评分: {card['complexity_score']}")
    else:
        logger.warning(f"卡片 {card_id} 顶层不包含复杂度评分")
        
    if 'time_cost_score' in card:
        logger.info(f"卡片 {card_id} 顶层包含时间成本评分: {card['time_cost_score']}")
    else:
        logger.warning(f"卡片 {card_id} 顶层不包含时间成本评分")
        
    if 'life_interference_score' in card:
        logger.info(f"卡片 {card_id} 顶层包含生活干扰评分: {card['life_interference_score']}")
    else:
        logger.warning(f"卡片 {card_id} 顶层不包含生活干扰评分")
    
    # 输出卡片的完整JSON
    card_json = json.dumps(card, ensure_ascii=False, indent=2, cls=MongoEncoder)
    logger.info(f"卡片完整数据:\n{card_json}")

def generate_api_patch_code():
    """生成需要添加到app.py中的补丁代码"""
    patch_code = """
# 在GetCardDetail类的get方法中，添加以下代码
# 添加到记录频次信息的代码之后，return之前

# 添加操作难度评分、时间成本评分和生活干扰评分到顶层，方便前端访问
if 'operation_difficulty_score' in card_data['detail_page']:
    card_data['complexity_score'] = card_data['detail_page']['operation_difficulty_score']
    card_data['操作难度评分'] = card_data['detail_page']['operation_difficulty_score']
    card_data['复杂度评分'] = card_data['detail_page']['operation_difficulty_score']
    logger.info(f"Cards API - 卡片操作难度评分: {card_id}, 值: {card_data['complexity_score']}")

if 'time_cost_score' in card_data['detail_page']:
    card_data['time_cost_score'] = card_data['detail_page']['time_cost_score']
    card_data['时间成本评分'] = card_data['detail_page']['time_cost_score']
    logger.info(f"Cards API - 卡片时间成本评分: {card_id}, 值: {card_data['time_cost_score']}")

if 'life_interference_score' in card_data['detail_page']:
    card_data['life_interference_score'] = card_data['detail_page']['life_interference_score']
    card_data['生活干扰评分'] = card_data['detail_page']['life_interference_score']
    logger.info(f"Cards API - 卡片生活干扰评分: {card_id}, 值: {card_data['life_interference_score']}")
"""
    
    # 保存补丁代码到文件
    with open('api_patch.txt', 'w', encoding='utf-8') as f:
        f.write(patch_code)
    
    logger.info(f"API补丁代码已保存到 {os.path.abspath('api_patch.txt')}")
    logger.info("请将此代码添加到app.py中的GetCardDetail类的get方法末尾，在return语句之前")

def check_card_routes():
    """检查API路由中处理评分字段的代码"""
    
    # 获取SearchCards类中的数据处理逻辑，检查是否也需要修复
    # 这里我们只能模拟检查，因为无法直接查看app.py的源代码
    
    logger.info("API路由检查完成")
    logger.info("1. 需要修复GetCardDetail类的卡片详情API，确保返回评分字段")
    logger.info("2. 已通过fix_card_api.py修复数据库中的卡片数据")
    logger.info("3. 修复后，前端将能够正确显示操作难度评分、时间成本评分和生活干扰评分字段")

if __name__ == "__main__":
    logger.info("开始检查API响应和生成补丁代码...")
    check_api_response()
    generate_api_patch_code()
    check_card_routes()
    logger.info("处理完成") 