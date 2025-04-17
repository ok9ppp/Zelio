import pandas as pd
import re

def check_mappings():
    # 读取模板
    template_file = 'template.xlsx'
    df = pd.read_excel(template_file)
    template_cols = list(df.columns)
    
    # 读取app.py中的字段映射
    with open('app.py', 'r') as f:
        app_code = f.read()
    
    # 查找get_field_value和get_numeric_value的使用
    field_mappings = []
    
    # 查找main_page映射
    pattern_main = r"main_page\s*=\s*\{([^}]+)\}"
    match_main = re.search(pattern_main, app_code, re.DOTALL)
    if match_main:
        main_content = match_main.group(1)
        for line in main_content.split('\n'):
            if 'get_field_value' in line or 'get_numeric_value' in line:
                field = re.search(r"'([^']+)'", line)
                if field:
                    field_mappings.append(field.group(1))
    
    # 查找detail_page映射
    pattern_detail = r"detail_page\s*=\s*\{([^}]+)\}"
    match_detail = re.search(pattern_detail, app_code, re.DOTALL)
    if match_detail:
        detail_content = match_detail.group(1)
        for line in detail_content.split('\n'):
            if 'get_field_value' in line or 'get_numeric_value' in line:
                field = re.search(r"'([^']+)'", line)
                if field:
                    field_mappings.append(field.group(1))
    
    print("Template columns:", template_cols)
    print("\nField mappings in app.py:")
    for field in field_mappings:
        in_template = field in template_cols
        print(f"- '{field}': {'✓' if in_template else '✗'}")
    
    print("\nTemplate columns not used in app.py:")
    for col in template_cols:
        if col not in field_mappings:
            print(f"- '{col}'")
    
    # 检查评分字段的使用
    score_fields = ['操作难度评分', '时间成本评分', '生活干扰评分']
    print("\nScore fields mapping:")
    for field in score_fields:
        in_template = field in template_cols
        pattern = r"['\"]" + re.escape(field) + r"['\"]"
        uses = re.findall(pattern, app_code)
        print(f"- '{field}': {'✓' if in_template else '✗'} (uses in app.py: {len(uses)})")
        
        # 查找对应的API命名
        if field == '操作难度评分':
            api_fields = ['complexity_score', 'operation_difficulty_score']
        elif field == '时间成本评分':
            api_fields = ['time_investment_score', 'time_cost_score']
        elif field == '生活干扰评分':
            api_fields = ['life_interference_score']
        
        for api_field in api_fields:
            pattern = r"['\"]" + re.escape(api_field) + r"['\"]"
            uses = re.findall(pattern, app_code)
            print(f"  - API field '{api_field}': {len(uses)} uses")

if __name__ == "__main__":
    check_mappings() 