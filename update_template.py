import pymongo
import gridfs
import os
import datetime

# 连接到MongoDB
mongo_uri = "mongodb://root:zqkz5vgv@therapy-mongodb.ns-4221v9wq.svc:27017/therapy_db?authSource=admin"
client = pymongo.MongoClient(mongo_uri)
db = client["therapy_db"]
fs = gridfs.GridFS(db)

# 当前日期时间
now = datetime.datetime.now()

# 已有模板文件的路径
template_files = {
    'doctor': 'templates/doctor_template.xlsx',
    'literature': 'templates/literature_template.xlsx'
}

# 上传到数据库
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
    
    print(f'已更新 {template_type} 模板')

# 更新主模板
with open('templates/literature_template.xlsx', 'rb') as f:
    content = f.read()
    
with open('template.xlsx', 'wb') as f:
    f.write(content)

print('主模板文件已更新') 