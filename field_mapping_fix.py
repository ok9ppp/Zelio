#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
修复Excel字段映射和API返回字段不一致的问题
"""

import pandas as pd
import re
import os
import logging
from pymongo import MongoClient
from bson import ObjectId

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 连接MongoDB
mongo_uri = "mongodb://root:zqkz5vgv@therapy-mongodb.ns-4221v9wq.svc:27017/therapy_db?authSource=admin"
client = MongoClient(mongo_uri)
db = client["therapy_db"]

def fix_app_mappings():
    """修改app.py中的字段映射，确保前端使用的字段与API一致"""
    
    # 读取app.py文件
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找GetCardDetail类中添加操作难度评分的部分
    pattern = r"(if 'operation_difficulty_score' in card_data\['detail_page'\]:.*?card_data\['complexity_score'\].*?)"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        original = match.group(1)
        # 检查是否已包含time_investment_score
        if 'time_investment_score' not in content:
            logger.info("添加time_investment_score字段映射")
            # 修改处理时间成本评分的部分，添加time_investment_score
            pattern2 = r"(if 'time_cost_score' in card_data\['detail_page'\]:.*?card_data\['time_cost_score'\].*?'time_cost_score': get_numeric_value\(row, '时间成本评分'.*?'life_interference_score': get_numeric_value\(row, '生活干扰评分'.*?\})"
            match2 = re.search(pattern2, content, re.DOTALL)
            if match2:
                original2 = match2.group(1)
                modified2 = original2.replace(
                    "card_data['time_cost_score'] = card_data['detail_page']['time_cost_score']",
                    "# 前端需要的标准字段名\n                    card_data['time_investment_score'] = card_data['detail_page']['time_cost_score']\n                    # 兼容性字段名\n                    card_data['time_cost_score'] = card_data['detail_page']['time_cost_score']"
                )
                content = content.replace(original2, modified2)
                logger.info("成功添加time_investment_score字段到GetCardDetail类")
            else:
                logger.warning("未找到时间成本评分处理代码")
        else:
            logger.info("time_investment_score字段已存在，无需修改")
    else:
        logger.warning("未找到操作难度评分处理代码")
    
    # 修改处理Excel的代码，确保正确映射字段
    pattern3 = r"(detail_page = \{.*?'operation_difficulty_score': get_numeric_value\(row, '操作难度评分'.*?'time_cost_score': get_numeric_value\(row, '时间成本评分'.*?'life_interference_score': get_numeric_value\(row, '生活干扰评分'.*?\})"
    match3 = re.search(pattern3, content, re.DOTALL)
    if match3:
        original3 = match3.group(1)
        # 确保在保存到数据库前设置time_investment_score字段
        if "card['time_investment_score'] = detail_page['time_cost_score']" not in content:
            # 找到创建卡片文档的部分
            pattern4 = r"(# 创建卡片文档\s*card = \{[^}]+\})"
            match4 = re.search(pattern4, content, re.DOTALL)
            if match4:
                original4 = match4.group(1)
                modified4 = original4 + "\n                # 添加前端需要的标准字段\n                card['complexity_score'] = detail_page['operation_difficulty_score']\n                card['time_investment_score'] = detail_page['time_cost_score']"
                content = content.replace(original4, modified4)
                logger.info("成功添加标准字段到卡片创建代码")
            else:
                logger.warning("未找到卡片创建代码")
    else:
        logger.warning("未找到详情页字段处理代码")
    
    # 保存修改后的文件
    backup_file = 'app.py.bak'
    if os.path.exists(backup_file):
        os.remove(backup_file)
    os.rename('app.py', backup_file)
    
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    logger.info("成功修改app.py文件，备份保存为app.py.bak")

def fix_cards_in_database():
    """修复数据库中已存在的卡片，确保包含前端需要的字段"""
    
    cards = list(db.treatment_cards.find({}))
    logger.info(f"共找到 {len(cards)} 张卡片需要检查")
    
    updated_count = 0
    already_correct_count = 0
    
    for card in cards:
        card_id = str(card['_id'])
        needs_update = False
        update_fields = {}
        
        # 1. 检查是否有detail_page字段
        if 'detail_page' not in card:
            logger.warning(f"卡片 {card_id} 没有detail_page字段，跳过")
            continue
        
        # 2. 确保complexity_score存在
        if 'operation_difficulty_score' in card['detail_page'] and 'complexity_score' not in card:
            update_fields['complexity_score'] = card['detail_page']['operation_difficulty_score']
            needs_update = True
        
        # 3. 确保time_investment_score存在
        if 'time_cost_score' in card['detail_page'] and 'time_investment_score' not in card:
            update_fields['time_investment_score'] = card['detail_page']['time_cost_score']
            needs_update = True
        
        # 4. 对于旧格式卡片，检查是否可以从raw_data或template_reference提取
        elif ('raw_data' in card or 'template_reference' in card) and 'complexity_score' not in card:
            source_data = card.get('raw_data', {}) or card.get('template_reference', {})
            
            # 处理操作难度评分
            if 'time_investment_score' not in card and 'time_cost_score' in card:
                update_fields['time_investment_score'] = card['time_cost_score']
                needs_update = True
        
        # 如果需要更新，执行更新操作
        if needs_update:
            # 记录更新前的值
            logger.info(f"准备更新卡片 {card_id} 的字段")
            for field, value in update_fields.items():
                logger.info(f"  - {field}: {value}")
            
            # 更新记录
            update_result = db.treatment_cards.update_one(
                {'_id': card['_id']},
                {'$set': update_fields}
            )
            
            if update_result.modified_count > 0:
                updated_count += 1
                logger.info(f"已更新卡片 {card_id} 的字段")
            else:
                logger.warning(f"尝试更新卡片 {card_id} 但没有实际修改")
        else:
            already_correct_count += 1
    
    logger.info(f"卡片字段修复完成: 总计 {len(cards)} 张卡片, 已更新 {updated_count} 张, {already_correct_count} 张无需更新")
    return {
        'total_cards': len(cards),
        'updated_cards': updated_count,
        'already_correct': already_correct_count
    }

def fix_excel_template():
    """确保模板使用正确的字段名"""
    
    # 检查目录是否存在
    os.makedirs('templates', exist_ok=True)
    
    # 修改创建模板的脚本
    if os.path.exists('create_template.py'):
        with open('create_template.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 确保模板列包含正确的字段名
        modified = False
        if "'操作难度评分'" in content and "'时间成本评分'" in content and "'生活干扰评分'" in content:
            logger.info("模板已包含正确的评分字段名")
        else:
            logger.warning("模板中缺少正确的评分字段名，尝试添加")
            # 查找literature_columns定义
            pattern = r"(literature_columns\s*=\s*\[[^\]]+\])"
            match = re.search(pattern, content, re.DOTALL)
            if match:
                columns = match.group(1)
                if "'操作难度评分'" not in columns:
                    columns = columns.replace("'操作难度'", "'操作难度评分'")
                    modified = True
                if "'时间成本评分'" not in columns:
                    columns = columns.replace("'时间成本'", "'时间成本评分'")
                    modified = True
                if "'生活干扰评分'" not in columns:
                    columns = columns.replace("'生活干扰'", "'生活干扰评分'")
                    modified = True
                
                if modified:
                    content = content.replace(match.group(1), columns)
                    
                    # 备份原文件
                    backup_file = 'create_template.py.bak'
                    if os.path.exists(backup_file):
                        os.remove(backup_file)
                    os.rename('create_template.py', backup_file)
                    
                    # 保存修改后的文件
                    with open('create_template.py', 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    logger.info("成功修改create_template.py，添加了正确的评分字段名")
                else:
                    logger.info("无需修改create_template.py，已包含正确的评分字段名")
            else:
                logger.warning("未找到模板列定义")
    else:
        logger.warning("create_template.py文件不存在")

if __name__ == "__main__":
    print("开始修复字段映射问题...")
    
    # 修复app.py中的字段映射
    fix_app_mappings()
    
    # 修复数据库中的卡片字段
    results = fix_cards_in_database()
    print(f"数据库修复结果: 总计 {results['total_cards']} 张卡片, 已更新 {results['updated_cards']} 张, {results['already_correct']} 张无需更新")
    
    # 修复Excel模板
    fix_excel_template()
    
    print("字段映射修复完成!") 