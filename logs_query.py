import re

log_file_path = '/home/devbox/project/logs/app.log'

# 搜索风险等级和风险概率
risk_level_pattern = r'Cards API - 风险等级(\d)原始值: (.+)'
risk_prob_pattern = r'Cards API - 风险概率(\d)原始值: (.+)'

try:
    with open(log_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 搜索风险等级数据
    risk_level_matches = re.findall(risk_level_pattern, content)
    risk_prob_matches = re.findall(risk_prob_pattern, content)
    
    print("== 风险等级数据 ==")
    # 只显示一些样本
    unique_values = set()
    for level, value in risk_level_matches:
        unique_values.add(f"风险等级{level}: {value}")
    
    for value in sorted(unique_values):
        print(value)
    
    print("\n== 风险概率数据 ==")
    # 只显示一些样本
    unique_prob_values = set()
    for level, value in risk_prob_matches:
        unique_prob_values.add(f"风险概率{level}: {value}")
    
    for value in sorted(unique_prob_values):
        print(value)
    
    # 搜索风险数据处理完成的记录
    # 提取字段值
    pattern = r"卡片\s+([a-f0-9]+)\s+风险数据处理完成:\s+风险等级=\{'level_1':\s+'([^']+)',\s+'level_2':\s+'([^']+)',\s+'level_3':\s+'([^']+)'\}"
    matches = re.findall(pattern, content)
    
    print("\n== 处理完成的风险数据 ==")
    if matches:
        # 查找包含"未知"的记录
        unknown_records = [m for m in matches if '未知' in m[1] or '未知' in m[2] or '未知' in m[3]]
        if unknown_records:
            print("\n== 包含'未知'的风险数据 ==")
            for card_id, level1, level2, level3 in unknown_records[:5]:
                print(f"卡片ID: {card_id}")
                print(f"风险等级1: {level1}")
                print(f"风险等级2: {level2}")
                print(f"风险等级3: {level3}")
                print("---")
        
        # 打印最新的5条记录
        print("\n== 最新的风险数据 ==")
        for card_id, level1, level2, level3 in matches[-5:]:
            print(f"卡片ID: {card_id}")
            print(f"风险等级1: {level1}")
            print(f"风险等级2: {level2}")
            print(f"风险等级3: {level3}")
            print("---")
    else:
        print("未找到风险数据处理完成的记录")
    
except Exception as e:
    print(f"错误: {e}") 