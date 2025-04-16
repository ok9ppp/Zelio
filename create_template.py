import pandas as pd
import os
from openpyxl.utils import get_column_letter

# 医生模板数据
doctor_template_data = {
    '医生及联系方式': ['张三  1599939029'],
    '疾病': ['慢性萎缩性胃炎'],
    '方案名称': [''],
    '方案简介': ['针药结合治疗（脾胃培源方+针刺）'],
    '治疗时间': ['总疗程为3个月。'],
    '频次': ['观察组：针刺治疗1次/天；脾胃培源方每天2次。'],
    '费用范围': ['100-1000'],
    '总人数': ['93人'],
    '有效人数': ['40人'],
    '临床治愈人数': ['16人'],
    '未复发人数': ['0'],
    '有效率': ['85.11%'],
    '临床治愈率': ['59.8%'],
    '未复发率': ['0.0'],
    '受益评分': ['5.8'],
    '受益评级': ['中受益'],
    '一级风险表现': ['疼痛'],
    '二级风险表现': ['肝功能'],
    '三级风险表现': ['严重过敏'],
    '一级风险概率和': ['25%'],
    '二级风险概率和': ['3%'],
    '三级风险概率和': ['0.15%'],
    '风险评分': ['0.7'],
    '风险评级': ['低风险'],
    '操作难度': ['1'],
    '时间成本': ['2'],
    '生活干扰': ['5'],
    '便利度评分': ['8'],
    '便利度评级': ['中']
}

# 文献模板数据
literature_template_data = {
    '标题及来源': ['腰椎间盘突出的物理治疗方案研究 - 中国康复医学杂志'],
    '疾病': ['腰椎间盘突出症'],
    '方案名称': ['综合物理治疗方案'],
    '方案简介': ['结合推拿、针灸、理疗等多种方式的综合治疗方案'],
    '治疗时间': ['45分钟'],
    '频次': ['每周3次'],
    '费用范围': ['300-500元/次'],
    '总人数': ['100'],
    '有效率': ['85%'],
    '临床治愈率': ['60%'],
    '未复发率': ['75%'],
    '有效人数': ['85'],
    '临床治愈人数': ['60'],
    '未复发人数': ['75'],
    '受益评分': ['8.5'],
    '受益评级': ['A'],
    '一级风险表现': ['轻微疼痛'],
    '二级风险表现': ['短期不适'],
    '三级风险表现': ['无'],
    '一级风险概率和': ['5%'],
    '二级风险概率和': ['2%'],
    '三级风险概率和': ['0%'],
    '风险评分': ['2.1'],
    '风险评级': ['低风险'],
    '操作难度': ['中等'],
    '时间成本': ['中等'],
    '生活干扰': ['轻微'],
    '便利度评分': ['7.5'],
    '便利度评级': ['B']
}

# 确保模板目录存在
os.makedirs('templates', exist_ok=True)

def create_excel_template(data, filename):
    df = pd.DataFrame(data)
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
        worksheet = writer.sheets['Sheet1']
        
        # 调整列宽
        for idx, col in enumerate(df.columns):
            column_letter = get_column_letter(idx + 1)
            max_length = max(
                df[col].astype(str).apply(len).max(),
                len(str(col))
            )
            worksheet.column_dimensions[column_letter].width = max_length + 2
            
            # 设置第一行（标题行）的样式
            cell = worksheet[f"{column_letter}1"]
            cell.font = cell.font.copy(bold=True)
            
    # 同时创建CSV文件
    df.to_csv(filename.replace('.xlsx', '.csv'), index=False, encoding='utf-8')

# 创建医生模板
create_excel_template(doctor_template_data, 'templates/doctor_template.xlsx')

# 创建文献模板
create_excel_template(literature_template_data, 'templates/literature_template.xlsx')

print("模板文件已创建：")
print("- templates/doctor_template.xlsx")
print("- templates/doctor_template.csv")
print("- templates/literature_template.xlsx")
print("- templates/literature_template.csv")

# 创建文献模板
literature_columns = [
    '来源', '疾病', '方案名称', '方案简介', '治疗时间', '频次', '费用范围',
    '总人数', '有效人数', '临床治愈人数', '未复发人数',
    '有效率', '临床治愈率', '未复发率',
    '一级风险表现', '二级风险表现', '三级风险表现',
    '一级风险概率和', '二级风险概率和', '三级风险概率和',
    '风险评级', '受益评级', '便利度评级',
    '受益评分', '风险评分', '便利度评分',
    '操作难度评分', '时间成本评分', '生活干扰评分'
]

# 创建示例数据
literature_data = {col: [''] for col in literature_columns}
literature_df = pd.DataFrame(literature_data)

# 保存模板
literature_template_path = 'templates/literature_template.xlsx'
literature_df.to_excel(literature_template_path, index=False)

print(f"文献模板已创建：{literature_template_path}") 