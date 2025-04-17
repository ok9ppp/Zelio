import pandas as pd
import os
from openpyxl.utils import get_column_letter
import pymongo
import gridfs
import datetime

# 连接到MongoDB
mongo_uri = "mongodb://root:zqkz5vgv@therapy-mongodb.ns-4221v9wq.svc:27017/therapy_db?authSource=admin"
client = pymongo.MongoClient(mongo_uri)
db = client["therapy_db"]
fs = gridfs.GridFS(db)

# 当前日期时间
now = datetime.datetime.now()

# 读取用户上传的带有示例数据的模板
user_template_path = 'uploads/template.xlsx'
user_data = pd.read_excel(user_template_path)

# 确保取前两行作为示例数据
example_data = user_data.head(2)

# 将示例数据转换为模板格式
literature_data = {}
for col in example_data.columns:
    # 使用列数据，不包含NaN值
    values = example_data[col].dropna().tolist()
    # 如果列为空，则添加空字符串
    if not values:
        values = ['']
    literature_data[col] = values

# 创建包含示例数据的模板
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

# 确保模板目录存在
os.makedirs('templates', exist_ok=True)

# 创建文献模板并添加示例数据
literature_template_path = 'templates/literature_template.xlsx'
create_excel_template(literature_data, literature_template_path)
print(f"已创建文献模板（含示例数据）：{literature_template_path}")

# 复制同样的模板作为医生模板
doctor_template_path = 'templates/doctor_template.xlsx'
pd.read_excel(literature_template_path).to_excel(doctor_template_path, index=False)
print(f"已创建医生模板（含示例数据）：{doctor_template_path}")

# 上传到数据库
template_files = {
    'doctor': doctor_template_path,
    'literature': literature_template_path
}

for template_type, file_path in template_files.items():
    with open(file_path, 'rb') as f:
        content = f.read()
        
    # 删除旧模板
    db.templates.delete_many({'type': template_type})
    
    # 添加新模板
    db.templates.insert_one({
        'name': f'{template_type}_template',
        'type': template_type,
        'content': content,
        'created_at': now
    })
    
    print(f'已更新 {template_type} 模板到数据库')

# 更新主模板
with open(literature_template_path, 'rb') as f:
    content = f.read()
    
with open('template.xlsx', 'wb') as f:
    f.write(content)

print('主模板文件已更新') 