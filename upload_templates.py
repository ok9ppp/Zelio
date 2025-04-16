from pymongo import MongoClient
import datetime
import os

# MongoDB配置
MONGO_URI = "mongodb://root:zqkz5vgv@therapy-mongodb.ns-4221v9wq.svc:27017/therapy_db?authSource=admin"
client = MongoClient(MONGO_URI)
db = client.get_database()

def upload_template(file_path, template_type, template_name):
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
            template_doc = {
                'name': template_name,
                'type': template_type,
                'content': content,
                'created_at': datetime.datetime.utcnow(),
                'updated_at': datetime.datetime.utcnow()
            }
            result = db.templates.insert_one(template_doc)
            print(f'上传模板 {template_name} 成功，ID: {result.inserted_id}')
            return True
    except Exception as e:
        print(f'上传模板 {template_name} 失败: {str(e)}')
        return False

def main():
    # 上传文献模板
    template_path = 'templates/literature_template.xlsx'
    if os.path.exists(template_path):
        upload_template(template_path, 'literature', '文献模板')
    else:
        print('未找到文献模板文件')

if __name__ == '__main__':
    main() 