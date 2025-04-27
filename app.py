import os
import logging
import logging.handlers
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_file, make_response, render_template
from flask_restful import Api, Resource
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError
from functools import wraps
import jwt
import json
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, get_jwt
from bson import ObjectId
import bcrypt
from werkzeug.utils import secure_filename
import pandas as pd
import io
from flask_pymongo import PyMongo
import json
from pymongo.errors import OperationFailure
import urllib.parse
import math
import re
from deepseek_client import DeepSeekClient

# 创建logs目录（如果不存在）
os.makedirs('logs', exist_ok=True)

# 配置日志记录
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# 创建文件处理器
file_handler = logging.handlers.RotatingFileHandler(
    'logs/app.log',
    maxBytes=1024 * 1024,  # 1MB
    backupCount=5
)
file_handler.setLevel(logging.DEBUG)

# 创建控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# 创建格式化器
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# 添加处理器到logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

app = Flask(__name__)
# 允许任何域名使用
CORS(app, 
     origins="*", 
     allow_headers=["Content-Type", "Authorization", "Access-Control-Allow-Origin", "Access-Control-Allow-Headers", "Access-Control-Allow-Methods"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     supports_credentials=True,
     expose_headers=["Content-Type", "Authorization"],
     max_age=21600
)

# 配置
app.config['JWT_SECRET_KEY'] = 'jwt-secret-key'  # JWT密钥
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=1)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['TEMPLATES_FOLDER'] = 'templates'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['MONGO_URI'] = "mongodb://root:zqkz5vgv@therapy-mongodb.ns-4221v9wq.svc:27017/therapy_db?authSource=admin"
app.config['SECRET_KEY'] = 'your-secret-key'  # 在生产环境中应该使用安全的密钥

# 确保必要的目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['TEMPLATES_FOLDER'], exist_ok=True)

# 初始化扩展
api = Api(app)
jwt = JWTManager(app)  # 使用jwt而不是jwt_manager
mongo = PyMongo(app)

# 初始化DeepSeek客户端
deepseek = DeepSeekClient()

# MongoDB配置
try:
    client = MongoClient(app.config['MONGO_URI'])
    db = client['therapy_db']
    # 测试连接
    client.admin.command('ping')
    logger.info("MongoDB连接成功！")
    
    # 创建或更新索引
    try:
        # 删除现有索引
        db.users.drop_indexes()
        
        # 创建新索引
        db.users.create_index([('username', ASCENDING)], unique=True)
        db.users.create_index([('email', ASCENDING)], unique=True, sparse=True)
        db.users.create_index([('phone', ASCENDING)], unique=True, sparse=True)
        logger.info("索引创建成功")
    except OperationFailure as e:
        logger.warning(f"索引操作失败: {str(e)}")
except Exception as e:
    logger.error(f"MongoDB连接失败: {str(e)}")
    raise

# Token验证装饰器
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return {'error': '无效的认证头'}, 401

        if not token:
            return {'error': '缺少token'}, 401

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = db.users.find_one({'_id': ObjectId(data['user_id'])})
            if not current_user:
                return {'error': '用户不存在'}, 401
        except jwt.ExpiredSignatureError:
            return {'error': 'token已过期'}, 401
        except jwt.InvalidTokenError:
            return {'error': '无效的token'}, 401
        except Exception as e:
            logger.error(f"Token验证错误: {str(e)}")
            return {'error': '验证过程中发生错误'}, 401

        return f(current_user, *args, **kwargs)
    return decorated

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 用户注册
class Register(Resource):
    def post(self):
        try:
            data = request.get_json()
            if not data:
                logger.warning("无效的请求数据")
                return {'error': '无效的请求数据'}, 400

            # 验证必需字段
            if not data.get('username') or not data.get('phone') or not data.get('password'):
                logger.warning("缺少必需字段")
                return {'error': '用户名、手机号和密码是必需的'}, 400

            # 验证用户名长度
            if len(data['username']) < 2:
                logger.warning(f"用户名太短: {data['username']}")
                return {'error': '用户名至少需要2个字符'}, 400

            # 验证手机号格式
            phone = data['phone']
            if not phone.isdigit() or len(phone) != 11:
                logger.warning(f"无效的手机号格式: {phone}")
                return {'error': '请输入有效的11位手机号'}, 400

            # 验证密码长度
            if len(data['password']) < 6:
                logger.warning("密码太短")
                return {'error': '密码至少需要6个字符'}, 400

            # 检查用户名是否已存在
            if db.users.find_one({'username': data['username']}):
                logger.warning(f"用户名已存在: {data['username']}")
                return {'error': '用户名已存在'}, 409

            # 检查手机号是否已存在
            if db.users.find_one({'phone': phone}):
                logger.warning(f"手机号已被使用: {phone}")
                return {'error': '手机号已被使用'}, 409

            # 创建用户文档
            user = {
                'username': data['username'],
                'phone': phone,
                'password': generate_password_hash(data['password']),
                'created_at': datetime.utcnow()
            }

            if data.get('email'):
                user['email'] = data['email']

            logger.info(f"尝试创建用户: {data['username']}")
            result = db.users.insert_one(user)
            logger.info(f"用户注册成功: {data['username']}")

            return {
                'message': '用户注册成功',
                'user': {
                    'id': str(result.inserted_id),
                    'username': data['username'],
                    'phone': phone
                }
            }, 201

        except DuplicateKeyError as e:
            logger.warning(f"注册失败 - 重复键: {str(e)}")
            return {'error': '用户名或手机号已被使用'}, 409
        except Exception as e:
            logger.error(f"注册过程中出错: {str(e)}", exc_info=True)
            return {'error': '注册过程中发生错误'}, 500

# 用户登录
class Login(Resource):
    def post(self):
        try:
            data = request.get_json()
            if not data:
                logger.warning("无效的请求数据")
                return {'error': '无效的请求数据'}, 400

            # 验证必需字段
            if not data.get('phone') or not data.get('password'):
                logger.warning("缺少必需字段")
                return {'error': '手机号和密码是必需的'}, 400

            # 验证手机号格式
            phone = data['phone']
            if not phone.isdigit() or len(phone) != 11:
                logger.warning(f"无效的手机号格式: {phone}")
                return {'error': '请输入有效的11位手机号'}, 400

            # 查找用户 - 仅通过手机号查找
            user = db.users.find_one({'phone': phone})
            if not user:
                logger.warning(f"手机号不存在: {phone}")
                return {'error': '手机号或密码错误'}, 401

            # 验证密码
            if not check_password_hash(user['password'], data['password']):
                logger.warning(f"密码错误: {user['username']}")
                return {'error': '手机号或密码错误'}, 401

            # 生成访问令牌
            access_token = create_access_token(
                identity=str(user['_id']),
                additional_claims={
                    'username': user['username'],
                    'phone': user['phone']
                }
            )
            logger.info(f"用户登录成功: {user['phone']}")

            return {
                'message': '登录成功',
                'access_token': access_token,
                'user': {
                    'id': str(user['_id']),
                    'phone': user['phone']
                }
            }, 200

        except Exception as e:
            logger.error(f"登录过程中出错: {str(e)}", exc_info=True)
            return {'error': '登录过程中发生错误'}, 500

# 下载模板
class Template(Resource):
    def get(self):
        try:
            template_path = os.path.join(app.config['TEMPLATES_FOLDER'], 'treatment_template.xlsx')
            if not os.path.exists(template_path):
                return {'error': '模板文件不存在'}, 404

            # 添加时间戳到文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            download_name = f'treatment_template_{timestamp}.xlsx'

            logger.info(f"模板下载请求: 通用模板")
            response = make_response(send_file(
                template_path,
                as_attachment=True,
                download_name=download_name,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            ))
            response.headers['Content-Disposition'] = f'attachment; filename="{download_name}"'
            return response

        except Exception as e:
            logger.error(f"模板下载过程中出错: {str(e)}")
            return {'error': '模板下载过程中发生错误'}, 500

# 上传文件
class Upload(Resource):
    @jwt_required()
    def post(self):
        try:
            if 'file' not in request.files:
                return {'error': 'No file uploaded'}, 400
                
            file = request.files['file']
            if file.filename == '':
                return {'error': 'No file selected'}, 400
                
            if not allowed_file(file.filename):
                return {'error': 'Invalid file format'}, 400
                
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # 保存文件信息到数据库
            file_doc = {
                'user_id': get_jwt_identity(),
                'file_name': filename,
                'file_path': file_path,
                'upload_time': datetime.utcnow()
            }
            result = db.files.insert_one(file_doc)
            
            return {
                'message': 'File uploaded successfully',
                'file_id': str(result.inserted_id)
            }, 200
        except Exception as e:
            logger.error(f"文件上传失败: {str(e)}", exc_info=True)
            return {'error': f'File upload failed: {str(e)}'}, 500

# 验证Excel文件格式是否符合模板要求，并返回模板数据和模板类型
def validate_excel_template(file_path):
    try:
        # 读取上传的文件
        df = pd.read_excel(file_path)
        
        # 必需的核心列，不再区分模板类型
        required_columns = [
            '疾病', '方案名称', '方案简介', '治疗时间', '费用范围'
        ]
        
        # 统一模板类型为通用类型
        template_type = 'general'
        logger.info(f"使用通用模板类型处理")
        
        # 加载通用模板文件，用于获取默认值
        template_file = f'templates/literature_template.xlsx'  # 默认使用literature模板
        template_df = pd.read_excel(template_file)
        
        # 检查是否缺少必需的列
        df_columns = df.columns.tolist()
        missing_required_cols = [col for col in required_columns if col not in df_columns]
        
        if missing_required_cols:
            return False, f"文件格式不符合要求：缺少必需的列 {', '.join(missing_required_cols)}", None, None
            
        # 分析数据，只做基本验证而不拒绝整个文件
        warnings = []
        for index, row in df.iterrows():
            row_number = index + 2  # Excel行号从1开始，标题行占据第1行
            
            # 验证必需的文本字段
            for field in required_columns:
                if field in df.columns and (pd.isna(row[field]) or not isinstance(row[field], str)):
                    warnings.append(f"警告：第{row_number}行：{field}不是有效的文本，将使用默认值")
            
            # 检查数值字段，如果存在则验证
            if '总人数' in df.columns:
                try:
                    if pd.isna(row['总人数']):
                        warnings.append(f"警告：第{row_number}行：总人数为空，将使用默认值")
                    else:
                        total = int(row['总人数'])
                        if total <= 0:
                            warnings.append(f"警告：第{row_number}行：总人数必须大于0，将使用默认值")
                except:
                    warnings.append(f"警告：第{row_number}行：总人数不是有效的整数，将使用默认值")
        
        # 如果有警告，记录到日志但不阻止处理
        if warnings:
            for warning in warnings:
                logger.warning(warning)
                
        # 返回结果，允许继续处理
        return True, "文件格式检查完成，可能存在部分数据不规范，将使用默认值补全", template_df, template_type
    except Exception as e:
        logger.error(f"文件格式验证失败：{str(e)}", exc_info=True)
        return False, f"文件格式验证失败：{str(e)}", None, None

# 生成卡片
class GenerateCard(Resource):
    @jwt_required()
    def post(self):
        try:
            current_user_id = get_jwt_identity()

            # 获取当前用户的用户名
            user = db.users.find_one({"_id": ObjectId(current_user_id)})
            current_username = user.get("username", "未知用户") if user else "未知用户"
            
            logger.info(f"当前用户: {current_user_id}, 用户名: {current_username}")
            
            # 获取请求数据
            data = request.get_json()
            file_id = data.get('file_id')
            
            if not file_id:
                return {'error': '缺少文件ID'}, 400
            
            # 查找文件
            file_info = db.files.find_one({"_id": ObjectId(file_id)})
            if not file_info:
                return {'error': '文件不存在'}, 404
            
            # 验证文件所有者
            if str(file_info.get('user_id')) != current_user_id:
                return {'error': '无权访问此文件'}, 403
            
            file_path = file_info.get('file_path')
            if not os.path.exists(file_path):
                return {'error': '文件不存在'}, 404
            
            # 辅助函数：获取字段值，如果不存在则使用默认值
            def get_field_value(row, field, default_value=''):
                value = row.get(field)
                if value is None or value == '' or (isinstance(value, float) and math.isnan(value)):
                    return default_value
                return value
            
            # 辅助函数：获取数值，确保是浮点数
            def get_numeric_value(row, field, default_value=0.0):
                value = row.get(field)
                try:
                    if value is None or value == '' or (isinstance(value, float) and math.isnan(value)):
                        return default_value
                    return float(value)
                except (ValueError, TypeError):
                    return default_value
            
            # 读取Excel文件
            df = pd.read_excel(file_path)
            
            # 将DataFrame转换为字典列表
            records = df.to_dict('records')
            
            cards_created = 0
            # 处理每一行数据
            for row in records:
                # 设置数据来源
                data_source = "未知来源"
                if '来源' in row and row['来源'] and not pd.isna(row['来源']):
                    data_source = row['来源']
                
                # 创建卡片主页数据
                main_page = {
                    'plan_name': get_field_value(row, '方案名称', '未命名方案'),
                    'disease': get_field_value(row, '疾病', '未指定疾病'),
                    'benefit_grade': get_field_value(row, '受益评级', '中'),
                    'benefit_score': get_numeric_value(row, '受益评分', 5.0),
                    'risk_grade': get_field_value(row, '风险评级', '中'),
                    'risk_score': get_numeric_value(row, '风险评分', 5.0),
                    'treatment_duration': get_field_value(row, '治疗时间', '未知'),
                    'cost_range': get_field_value(row, '费用范围', '未知'),
                    'convenience_grade': get_field_value(row, '便利度评级', '中'),
                    'convenience_score': get_numeric_value(row, '便利度评分', 5.0)
                }
                
                # 创建卡片详情页数据
                detail_page = {
                    'total_patients': get_numeric_value(row, '总人数', 0),
                    'effective_patients': get_numeric_value(row, '有效人数', 0),
                    'cured_patients': get_numeric_value(row, '临床治愈人数', 0),
                    'no_relapse_patients': get_numeric_value(row, '未复发人数', 0),
                    'effective_rate': get_field_value(row, '有效率', '0%'),
                    'cure_rate': get_field_value(row, '临床治愈率', '0%'),
                    'no_relapse_rate': get_field_value(row, '未复发率', '0%'),
                    'risk_level_1': get_field_value(row, '一级风险表现', '未知'),
                    'risk_level_2': get_field_value(row, '二级风险表现', '未知'),
                    'risk_level_3': get_field_value(row, '三级风险表现', '未知'),
                    'risk_prob_1': get_field_value(row, '一级风险概率和', '0%'),
                    'risk_prob_2': get_field_value(row, '二级风险概率和', '0%'),
                    'risk_prob_3': get_field_value(row, '三级风险概率和', '0%'),
                    'intro': get_field_value(row, '方案简介', '无简介')
                }
                
                # 单独记录频次字段的内容，确保正确读取
                excel_frequency = get_field_value(row, '频次', '未知')
                detail_page['frequency'] = excel_frequency
                logger.info(f"Excel频次数据: 频次={excel_frequency}")
                
                # 记录Excel原始数据
                logger.info(f"Excel原始数据: 总人数={get_numeric_value(row, '总人数', 0)}, 有效人数={get_numeric_value(row, '有效人数', 0)}, 临床治愈人数={get_numeric_value(row, '临床治愈人数', 0)}, 未复发人数={get_numeric_value(row, '未复发人数', 0)}")
                logger.info(f"Excel原始比率: 有效率={get_field_value(row, '有效率', '0%')}, 临床治愈率={get_field_value(row, '临床治愈率', '0%')}, 未复发率={get_field_value(row, '未复发率', '0%')}")
                logger.info(f"Excel风险等级: 一级风险={get_field_value(row, '一级风险表现', '未知')}, 二级风险={get_field_value(row, '二级风险表现', '未知')}, 三级风险={get_field_value(row, '三级风险表现', '未知')}")
                logger.info(f"Excel风险概率: 一级概率={get_field_value(row, '一级风险概率和', '0%')}, 二级概率={get_field_value(row, '二级风险概率和', '0%')}, 三级概率={get_field_value(row, '三级风险概率和', '0%')}")
                
                # 直接使用Excel中的数据，不进行计算覆盖
                # 如果Excel中的值是0%，且相应的人数大于0，才进行计算
                # 有效率处理
                excel_effective_rate = get_field_value(row, '有效率', '')
                if excel_effective_rate == '0%' and detail_page['effective_patients'] > 0 and detail_page['total_patients'] > 0:
                    effective_patients = min(detail_page['effective_patients'], detail_page['total_patients'])
                    effective_rate = round(effective_patients / detail_page['total_patients'] * 100, 1)
                    detail_page['effective_rate'] = f"{effective_rate}%"
                    logger.info(f"计算有效率: {detail_page['effective_rate']}")
                else:
                    logger.info(f"使用Excel提供的有效率: {detail_page['effective_rate']}")
                
                # 临床治愈率处理
                excel_cure_rate = get_field_value(row, '临床治愈率', '')
                if excel_cure_rate == '0%' and detail_page['cured_patients'] > 0 and detail_page['total_patients'] > 0:
                    cured_patients = min(detail_page['cured_patients'], detail_page['total_patients'])
                    cure_rate = round(cured_patients / detail_page['total_patients'] * 100, 1)
                    detail_page['cure_rate'] = f"{cure_rate}%"
                    logger.info(f"计算临床治愈率: {detail_page['cure_rate']}")
                else:
                    logger.info(f"使用Excel提供的临床治愈率: {detail_page['cure_rate']}")
                
                # 未复发率处理
                excel_no_relapse_rate = get_field_value(row, '未复发率', '')
                if excel_no_relapse_rate == '0%' and detail_page['no_relapse_patients'] > 0 and detail_page['total_patients'] > 0:
                    no_relapse_patients = min(detail_page['no_relapse_patients'], detail_page['total_patients'])
                    no_relapse_rate = round(no_relapse_patients / detail_page['total_patients'] * 100, 1)
                    detail_page['no_relapse_rate'] = f"{no_relapse_rate}%"
                    logger.info(f"计算未复发率: {detail_page['no_relapse_rate']}")
                else:
                    logger.info(f"使用Excel提供的未复发率: {detail_page['no_relapse_rate']}")
                
                # 记录最终使用的数据
                logger.info(f"卡片最终数据: 总人数={detail_page['total_patients']}, 有效人数={detail_page['effective_patients']}, 临床治愈人数={detail_page['cured_patients']}, 未复发人数={detail_page['no_relapse_patients']}")
                logger.info(f"卡片最终比率: 有效率={detail_page['effective_rate']}, 临床治愈率={detail_page['cure_rate']}, 未复发率={detail_page['no_relapse_rate']}")
                
                # 创建卡片文档
                card = {
                    'user_id': ObjectId(current_user_id),
                    'username': current_username,  # 确保包含用户名
                    'file_id': ObjectId(file_id),
                    'creation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'template_type': 'general',  # 统一使用general类型
                    'data_source': data_source,
                    'main_page': main_page,
                    'detail_page': detail_page,
                    'uploader': current_username  # 确保包含上传者用户名
                }
                
                logger.info(f"生成卡片: 用户名: {current_username}, 方案: {main_page['plan_name']}")
                
                # 插入数据库
                result = db.treatment_cards.insert_one(card)
                cards_created += 1
            
            logger.info(f"成功生成 {cards_created} 张卡片, 上传用户: {current_username}")
            return {
                'message': f'成功生成 {cards_created} 张卡片',
                'cards_created': cards_created
            }, 200
            
        except Exception as e:
            logger.error(f"生成卡片过程中出错: {str(e)}")
            return {'error': '生成卡片过程中发生错误'}, 500

# 搜索卡片
class SearchCards(Resource):
    @jwt_required()
    def get(self):
        try:
            current_user_id = get_jwt_identity()
            logger.info(f"Cards API - 当前用户ID: {current_user_id}")
            
            # 获取当前用户的用户名
            user = db.users.find_one({"_id": ObjectId(current_user_id)})
            current_username = user.get("username", "未知用户") if user else "未知用户"
            logger.info(f"Cards API - 当前用户名: {current_username}")
            
            # 获取查询参数
            page = int(request.args.get('page', 1))
            limit = int(request.args.get('limit', 10))
            keyword = request.args.get('keyword', '')
            show_details = request.args.get('show_details', 'true').lower() == 'true'  # 默认为true
            
            logger.info(f"Cards API - 搜索关键词: {keyword}")
            
            # 构建查询条件
            search_conditions = {'user_id': ObjectId(current_user_id)}
            
            # 添加关键词搜索
            if keyword:
                search_conditions['$or'] = [
                    {'main_page.plan_name': {'$regex': keyword, '$options': 'i'}},
                    {'main_page.disease': {'$regex': keyword, '$options': 'i'}},
                    {'data_source': {'$regex': keyword, '$options': 'i'}}
                ]
            
            logger.info(f"Cards API - 搜索条件: {str(search_conditions)}")
            
            # 计算总数
            total_count = db.treatment_cards.count_documents(search_conditions)
            logger.info(f"Cards API - 找到 {total_count} 条记录")
            
            # 分页查询
            skip = (page - 1) * limit
            cards = list(db.treatment_cards.find(search_conditions).skip(skip).limit(limit))
            logger.info(f"Cards API - 获取到 {len(cards)} 条记录")
            
            # 处理结果
            result_data = []
            for card in cards:
                try:
                    # 确保卡片ID是字符串
                    card_id_str = str(card['_id'])
                    user_id_str = str(card['user_id'])
                    
                    # 获取用户名，使用卡片中已存储的用户名，如果没有则使用当前用户名
                    username = card.get('username', current_username)
                    
                    # 获取上传者，使用卡片中已存储的上传者，如果没有则使用用户名
                    uploader = card.get('uploader', username)
                    
                    # 基本信息
                    card_data = {
                        'card_id': card_id_str,
                        'user_id': user_id_str,
                        'username': username,
                        'creation_date': str(card.get('creation_date', 'Unknown Date')),
                        'template_type': card.get('template_type', 'unknown'),
                        'data_source': card.get('data_source', '未知来源'),
                        'main_page': card.get('main_page', {}),
                        'uploader': uploader
                    }
                    
                    # 添加详情页 (如果需要)
                    if show_details and 'detail_page' in card:
                        card_data['detail_page'] = card['detail_page']
                        
                        # 确保detail_page中的人数数据显示为整数
                        if 'total_patients' in card_data['detail_page']:
                            try:
                                card_data['detail_page']['total_patients'] = int(card_data['detail_page']['total_patients'])
                            except:
                                pass
                            
                        if 'effective_patients' in card_data['detail_page']:
                            try:
                                card_data['detail_page']['effective_patients'] = int(card_data['detail_page']['effective_patients'])
                            except:
                                pass
                                
                        if 'cured_patients' in card_data['detail_page']:
                            try:
                                card_data['detail_page']['cured_patients'] = int(card_data['detail_page']['cured_patients'])
                            except:
                                pass
                                
                        # 处理未复发人数，即使不存在也提供默认值
                        if 'no_relapse_patients' in card_data['detail_page']:
                            try:
                                no_relapse_value = int(card_data['detail_page']['no_relapse_patients'])
                                card_data['detail_page']['no_relapse_patients'] = no_relapse_value
                                # 添加别名字段用于前端 - 同时提供数字和字符串版本
                                card_data['detail_page']['non_recurrence_count'] = no_relapse_value
                                card_data['non_recurrence_count'] = no_relapse_value
                                card_data['non_recurrence_count_str'] = str(no_relapse_value)
                            except:
                                # 如果转换失败，设置默认值
                                card_data['detail_page']['no_relapse_patients'] = 0
                                card_data['detail_page']['non_recurrence_count'] = 0
                                card_data['non_recurrence_count'] = 0
                                card_data['non_recurrence_count_str'] = "0"
                        else:
                            # 如果字段不存在，添加默认值
                            card_data['detail_page']['no_relapse_patients'] = 0
                            card_data['detail_page']['non_recurrence_count'] = 0
                            card_data['non_recurrence_count'] = 0
                            card_data['non_recurrence_count_str'] = "0"
                        
                        # 确保有效率使用百分比格式
                        if 'effective_rate' in card_data['detail_page']:
                            try:
                                effective_rate = card_data['detail_page']['effective_rate']
                                logger.info(f"Cards API - 有效率原始值类型: {type(effective_rate)}, 值: {effective_rate}")
                                
                                # 检查是否已经是百分比格式
                                if isinstance(effective_rate, str) and '%' in effective_rate:
                                    logger.info(f"Cards API - 有效率已经是百分比格式: {effective_rate}")
                                else:
                                    # 尝试将小数或非百分比字符串转换为百分比格式
                                    try:
                                        # 确保值是浮点数
                                        rate_value = float(effective_rate)
                                        # 如果值小于1，假设它是小数格式(0.x)，需要乘以100
                                        if rate_value < 1:
                                            rate_value = rate_value * 100
                                        card_data['detail_page']['effective_rate'] = f"{rate_value:.1f}%"
                                        logger.info(f"Cards API - 转换有效率格式: {effective_rate} -> {card_data['detail_page']['effective_rate']}")
                                    except (ValueError, TypeError) as e:
                                        logger.warning(f"Cards API - 转换有效率失败: {str(e)}")
                            except Exception as e:
                                logger.warning(f"Cards API - 处理有效率异常: {str(e)}")
                        
                        # 确保未复发率使用百分比格式
                        if 'no_relapse_rate' in card_data['detail_page']:
                            try:
                                relapse_rate = card_data['detail_page']['no_relapse_rate']
                                logger.info(f"Cards API - 未复发率原始值类型: {type(relapse_rate)}, 值: {relapse_rate}")
                                
                                # 检查是否已经是百分比格式
                                if isinstance(relapse_rate, str) and '%' in relapse_rate:
                                    logger.info(f"Cards API - 已经是百分比格式: {relapse_rate}")
                                else:
                                    # 尝试将小数或非百分比字符串转换为百分比格式
                                    try:
                                        # 确保值是浮点数
                                        rate_value = float(relapse_rate)
                                        # 如果值小于1，假设它是小数格式(0.x)，需要乘以100
                                        if rate_value < 1:
                                            rate_value = rate_value * 100
                                        card_data['detail_page']['no_relapse_rate'] = f"{rate_value:.1f}%"
                                        logger.info(f"Cards API - 转换未复发率格式: {relapse_rate} -> {card_data['detail_page']['no_relapse_rate']}")
                                    except (ValueError, TypeError) as e:
                                        logger.warning(f"Cards API - 转换未复发率失败: {str(e)}")
                            except Exception as e:
                                logger.warning(f"Cards API - 处理未复发率异常: {str(e)}")
                        
                        # 添加别名字段用于前端 - 确保即使上面的处理失败也会有这个字段
                        if 'no_relapse_rate' in card_data['detail_page']:
                            card_data['detail_page']['non_recurrence_rate'] = card_data['detail_page']['no_relapse_rate']
                            # 同时添加到顶层
                            card_data['non_recurrence_rate'] = card_data['detail_page']['no_relapse_rate']
                        else:
                            # 默认值
                            card_data['detail_page']['no_relapse_rate'] = "0.0%"
                            card_data['detail_page']['non_recurrence_rate'] = "0.0%"
                            card_data['non_recurrence_rate'] = "0.0%"
                        
                        # 处理风险数据
                        # 1. 风险等级
                        risk_levels = {}
                        for level in range(1, 4):  # 处理三个风险等级
                            level_key = f'risk_level_{level}'
                            if level_key in card_data['detail_page']:
                                risk_value = card_data['detail_page'][level_key]
                                logger.info(f"Cards API - 风险等级{level}原始值: {risk_value}")
                                # 保留原始值，包括"未知"
                                risk_levels[f'level_{level}'] = risk_value
                            else:
                                # 如果不存在，设置为"未知"
                                risk_value = '未知'
                                card_data['detail_page'][level_key] = risk_value
                                risk_levels[f'level_{level}'] = risk_value
                                logger.info(f"Cards API - 风险等级{level}不存在，设置为: {risk_value}")
                        
                        # 2. 风险概率
                        risk_probs = {}
                        for level in range(1, 4):  # 处理三个风险概率
                            prob_key = f'risk_prob_{level}'
                            if prob_key in card_data['detail_page']:
                                prob_value = card_data['detail_page'][prob_key]
                                logger.info(f"Cards API - 风险概率{level}原始值: {prob_value}")
                                
                                # 检查是否已经是百分比格式
                                if isinstance(prob_value, str) and '%' in prob_value:
                                    logger.info(f"Cards API - 风险概率{level}已经是百分比格式: {prob_value}")
                                    # 添加这一行，修复已经是百分比格式的情况下不添加到risk_probs的问题
                                    risk_probs[f'prob_{level}'] = prob_value
                                else:
                                    # 尝试将小数或非百分比字符串转换为百分比格式
                                    try:
                                        # 确保值是浮点数
                                        if prob_value is None or prob_value == '':
                                            if level == 1:
                                                prob_value = 12.8
                                            elif level == 2:
                                                prob_value = 5.2
                                            elif level == 3:
                                                prob_value = 0.5
                                        else:
                                            prob_value = float(prob_value)
                                        
                                        # 如果值小于1且不是0，假设它是小数格式(0.x)，需要乘以100
                                        if prob_value < 1 and prob_value > 0:
                                            prob_value = prob_value * 100
                                        
                                        card_data['detail_page'][prob_key] = f"{prob_value:.1f}%"
                                        logger.info(f"Cards API - 转换风险概率{level}格式: {prob_value} -> {card_data['detail_page'][prob_key]}")
                                    except (ValueError, TypeError) as e:
                                        # 设置默认值
                                        if level == 1:
                                            card_data['detail_page'][prob_key] = "12.8%"
                                        elif level == 2:
                                            card_data['detail_page'][prob_key] = "5.2%"
                                        elif level == 3:
                                            card_data['detail_page'][prob_key] = "0.5%"
                                        logger.warning(f"Cards API - 转换风险概率{level}失败: {str(e)}, 使用默认值: {card_data['detail_page'][prob_key]}")
                                    risk_probs[f'prob_{level}'] = card_data['detail_page'][prob_key]
                            else:
                                # 如果不存在，添加默认值
                                if level == 1:
                                    prob_value = "12.8%"
                                elif level == 2:
                                    prob_value = "5.2%"
                                elif level == 3:
                                    prob_value = "0.5%"
                                card_data['detail_page'][prob_key] = prob_value
                                risk_probs[f'prob_{level}'] = prob_value
                                logger.info(f"Cards API - 风险概率{level}不存在，添加默认值: {prob_value}")
                        
                        # 添加风险数据的顶层别名，方便前端访问
                        card_data['risk_data'] = {
                            'levels': risk_levels,
                            'probabilities': risk_probs
                        }
                        
                        # 添加前端期望的风险数据字段格式
                        for level in range(1, 4):
                            # 风险症状
                            card_data[f'risk_level_{level}_symptom'] = risk_levels[f'level_{level}']
                            # 风险概率
                            card_data[f'risk_level_{level}_rate'] = risk_probs[f'prob_{level}']
                        
                        # 记录整体风险数据
                        logger.info(f"Cards API - 卡片 {card_id_str} 风险数据处理完成: 风险等级={risk_levels}, 风险概率={risk_probs}")
                    
                    result_data.append(card_data)
                    
                    # 获取方案名称以便日志
                    plan_name = card.get('main_page', {}).get('plan_name', '未命名方案')
                    logger.info(f"Cards API - 处理卡片成功: {card_data['card_id']}, 方案名称: {plan_name}, 上传者: {uploader}")
                
                except Exception as e:
                    logger.error(f"Cards API - 处理卡片时出错: {str(e)}")
                    continue
            
            # 创建分页信息
            pagination = {
                'page': page,
                'limit': limit,
                'total': total_count,
                'total_pages': math.ceil(total_count / limit)
            }
            
            logger.info(f"Cards API - 返回 {len(result_data)} 条记录")
            
            # 创建响应
            response_data = {
                'message': 'Search successful',
                'data': result_data,
                'pagination': pagination
            }
            
            return response_data
            
        except Exception as e:
            logger.error(f"Cards API - 搜索出错: {str(e)}")
            return {'error': '搜索处理失败'}, 500

# 添加一个健康检查接口
class HealthCheck(Resource):
    def get(self):
        try:
            if db is None:
                return {'status': 'error', 'message': 'Database not connected'}, 500
            
            # 测试数据库连接
            db.command('ping')
            return {
                'status': 'healthy',
                'database': 'connected',
                'message': 'Service is running normally'
            }
        except Exception as e:
            return {
                'status': 'error',
                'database': 'disconnected',
                'message': f'Database error: {str(e)}'
            }, 500

# 新增模板管理相关API
@app.route('/api/templates/upload', methods=['POST'])
@token_required
def upload_template():
    if 'file' not in request.files:
        return jsonify({'message': '没有文件上传'}), 400
    
    file = request.files['file']
    template_type = request.form.get('type', 'literature')  # 默认为literature类型
    template_name = request.form.get('name', '默认模板')
    
    if file.filename == '':
        return jsonify({'message': '没有选择文件'}), 400
        
    try:
        # 读取Excel文件内容
        file_content = file.read()
        
        # 将文件内容存储到MongoDB
        template_doc = {
            'name': template_name,
            'type': template_type,
            'content': file_content,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        db.templates.insert_one(template_doc)
        
        return jsonify({
            'message': '模板上传成功',
            'template_id': str(template_doc.get('_id'))
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'模板上传失败: {str(e)}'}), 500

@app.route('/api/templates', methods=['GET'])
@token_required
def list_templates():
    try:
        templates = list(db.templates.find({}, {
            'content': 0  # 不返回文件内容
        }))
        
        # 转换ObjectId为字符串
        for template in templates:
            template['_id'] = str(template['_id'])
            
        return jsonify({
            'templates': templates
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'获取模板列表失败: {str(e)}'}), 500

@app.route('/api/templates/<template_id>', methods=['GET'])
@token_required
def download_template(template_id):
    try:
        # 从MongoDB获取模板
        template = db.templates.find_one({'_id': ObjectId(template_id)})
        
        if not template:
            return jsonify({'message': '模板不存在'}), 404
            
        # 创建内存文件对象
        file_obj = io.BytesIO(template['content'])
        
        return send_file(
            file_obj,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f"{template['name']}.xlsx"
        )
        
    except Exception as e:
        return jsonify({'message': f'下载模板失败: {str(e)}'}), 500

@app.route('/api/templates/<template_id>', methods=['DELETE'])
@token_required
def delete_template(template_id):
    try:
        result = db.templates.delete_one({'_id': ObjectId(template_id)})
        
        if result.deleted_count == 0:
            return jsonify({'message': '模板不存在'}), 404
            
        return jsonify({'message': '模板删除成功'}), 200
        
    except Exception as e:
        return jsonify({'message': f'删除模板失败: {str(e)}'}), 500

@app.route('/api/templates/<template_id>', methods=['PUT'])
@token_required
def update_template(template_id):
    if 'file' not in request.files:
        return jsonify({'message': '没有文件上传'}), 400
    
    file = request.files['file']
    template_name = request.form.get('name')
    
    update_data = {
        'updated_at': datetime.utcnow()
    }
    
    if template_name:
        update_data['name'] = template_name
        
    if file.filename != '':
        try:
            file_content = file.read()
            update_data['content'] = file_content
            
            result = db.templates.update_one(
                {'_id': ObjectId(template_id)},
                {'$set': update_data}
            )
            
            if result.matched_count == 0:
                return jsonify({'message': '模板不存在'}), 404
                
            return jsonify({'message': '模板更新成功'}), 200
            
        except Exception as e:
            return jsonify({'message': f'更新模板失败: {str(e)}'}), 500
    
    return jsonify({'message': '没有提供更新内容'}), 400

# 修改现有的模板下载接口
@app.route('/api/download_template', methods=['GET'])
def download_default_template():
    template_type = request.args.get('type', 'literature')
    
    try:
        # 查找最新的指定类型模板
        template = db.templates.find_one(
            {'type': template_type},
            sort=[('created_at', -1)]
        )
        
        if not template:
            return jsonify({'message': f'未找到{template_type}类型的模板'}), 404
            
        # 创建内存文件对象
        file_obj = io.BytesIO(template['content'])
        
        return send_file(
            file_obj,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f"{template['name']}.xlsx"
        )
        
    except Exception as e:
        return jsonify({'message': f'下载模板失败: {str(e)}'}), 500

# 获取用户信息
class UserInfo(Resource):
    @jwt_required()
    def get(self):
        try:
            # 获取当前用户ID
            current_user_id = get_jwt_identity()
            
            # 查询用户信息
            user = db.users.find_one({'_id': ObjectId(current_user_id)})
            
            if not user:
                logger.warning(f"用户不存在: {current_user_id}")
                return {'error': '用户不存在'}, 404
                
            # 返回用户信息
            return {
                'message': '获取用户信息成功',
                'user': {
                    'id': str(user['_id']),
                    'username': user['username'],
                    'phone': user['phone'],
                    'email': user.get('email', ''),
                    'created_at': user['created_at'].strftime('%Y-%m-%d %H:%M:%S') if 'created_at' in user else ''
                }
            }, 200
            
        except Exception as e:
            logger.error(f"获取用户信息过程中出错: {str(e)}", exc_info=True)
            return {'error': '获取用户信息过程中发生错误'}, 500

# Cards类，作为SearchCards的别名
class Cards(Resource):
    @jwt_required()
    def get(self):
        try:
            current_user_id = get_jwt_identity()
            logger.info(f"Cards API - 当前用户ID: {current_user_id}")
            
            # 获取当前用户的用户名
            user = db.users.find_one({"_id": ObjectId(current_user_id)})
            current_username = user.get("username", "未知用户") if user else "未知用户"
            logger.info(f"Cards API - 当前用户名: {current_username}")
            
            # 获取查询参数
            page = int(request.args.get('page', 1))
            limit = int(request.args.get('limit', 10))
            keyword = request.args.get('keyword', '')
            show_details = request.args.get('show_details', 'true').lower() == 'true'  # 默认为true
            
            logger.info(f"Cards API - 搜索关键词: {keyword}")
            
            # 构建查询条件
            search_conditions = {'user_id': ObjectId(current_user_id)}
            
            # 添加关键词搜索
            if keyword:
                search_conditions['$or'] = [
                    {'main_page.plan_name': {'$regex': keyword, '$options': 'i'}},
                    {'main_page.disease': {'$regex': keyword, '$options': 'i'}},
                    {'data_source': {'$regex': keyword, '$options': 'i'}}
                ]
            
            logger.info(f"Cards API - 搜索条件: {str(search_conditions)}")
            
            # 计算总数
            total_count = db.treatment_cards.count_documents(search_conditions)
            logger.info(f"Cards API - 找到 {total_count} 条记录")
            
            # 分页查询
            skip = (page - 1) * limit
            cards = list(db.treatment_cards.find(search_conditions).skip(skip).limit(limit))
            logger.info(f"Cards API - 获取到 {len(cards)} 条记录")
            
            # 处理结果
            result_data = []
            for card in cards:
                try:
                    # 确保卡片ID是字符串
                    card_id_str = str(card['_id'])
                    user_id_str = str(card['user_id'])
                    
                    # 获取用户名，使用卡片中已存储的用户名，如果没有则使用当前用户名
                    username = card.get('username', current_username)
                    
                    # 获取上传者，使用卡片中已存储的上传者，如果没有则使用用户名
                    uploader = card.get('uploader', username)
                    
                    # 基本信息
                    card_data = {
                        'card_id': card_id_str,
                        'user_id': user_id_str,
                        'username': username,
                        'creation_date': str(card.get('creation_date', 'Unknown Date')),
                        'template_type': card.get('template_type', 'unknown'),
                        'data_source': card.get('data_source', '未知来源'),
                        'main_page': card.get('main_page', {}),
                        'uploader': uploader
                    }
                    
                    # 添加详情页 (如果需要)
                    if show_details and 'detail_page' in card:
                        card_data['detail_page'] = card['detail_page']
                        
                        # 确保detail_page中的人数数据显示为整数
                        if 'total_patients' in card_data['detail_page']:
                            try:
                                card_data['detail_page']['total_patients'] = int(card_data['detail_page']['total_patients'])
                            except:
                                pass
                            
                        if 'effective_patients' in card_data['detail_page']:
                            try:
                                card_data['detail_page']['effective_patients'] = int(card_data['detail_page']['effective_patients'])
                            except:
                                pass
                                
                        if 'cured_patients' in card_data['detail_page']:
                            try:
                                card_data['detail_page']['cured_patients'] = int(card_data['detail_page']['cured_patients'])
                            except:
                                pass
                                
                        # 处理未复发人数，即使不存在也提供默认值
                        if 'no_relapse_patients' in card_data['detail_page']:
                            try:
                                no_relapse_value = int(card_data['detail_page']['no_relapse_patients'])
                                card_data['detail_page']['no_relapse_patients'] = no_relapse_value
                                # 添加别名字段用于前端 - 同时提供数字和字符串版本
                                card_data['detail_page']['non_recurrence_count'] = no_relapse_value
                                card_data['non_recurrence_count'] = no_relapse_value
                                card_data['non_recurrence_count_str'] = str(no_relapse_value)
                            except:
                                # 如果转换失败，设置默认值
                                card_data['detail_page']['no_relapse_patients'] = 0
                                card_data['detail_page']['non_recurrence_count'] = 0
                                card_data['non_recurrence_count'] = 0
                                card_data['non_recurrence_count_str'] = "0"
                        else:
                            # 如果字段不存在，添加默认值
                            card_data['detail_page']['no_relapse_patients'] = 0
                            card_data['detail_page']['non_recurrence_count'] = 0
                            card_data['non_recurrence_count'] = 0
                            card_data['non_recurrence_count_str'] = "0"
                        
                        # 确保有效率使用百分比格式
                        if 'effective_rate' in card_data['detail_page']:
                            try:
                                effective_rate = card_data['detail_page']['effective_rate']
                                logger.info(f"Cards API - 有效率原始值类型: {type(effective_rate)}, 值: {effective_rate}")
                                
                                # 检查是否已经是百分比格式
                                if isinstance(effective_rate, str) and '%' in effective_rate:
                                    logger.info(f"Cards API - 有效率已经是百分比格式: {effective_rate}")
                                else:
                                    # 尝试将小数或非百分比字符串转换为百分比格式
                                    try:
                                        # 确保值是浮点数
                                        rate_value = float(effective_rate)
                                        # 如果值小于1，假设它是小数格式(0.x)，需要乘以100
                                        if rate_value < 1:
                                            rate_value = rate_value * 100
                                        card_data['detail_page']['effective_rate'] = f"{rate_value:.1f}%"
                                        logger.info(f"Cards API - 转换有效率格式: {effective_rate} -> {card_data['detail_page']['effective_rate']}")
                                    except (ValueError, TypeError) as e:
                                        logger.warning(f"Cards API - 转换有效率失败: {str(e)}")
                            except Exception as e:
                                logger.warning(f"Cards API - 处理有效率异常: {str(e)}")
                        
                        # 确保未复发率使用百分比格式
                        if 'no_relapse_rate' in card_data['detail_page']:
                            try:
                                relapse_rate = card_data['detail_page']['no_relapse_rate']
                                logger.info(f"Cards API - 未复发率原始值类型: {type(relapse_rate)}, 值: {relapse_rate}")
                                
                                # 检查是否已经是百分比格式
                                if isinstance(relapse_rate, str) and '%' in relapse_rate:
                                    logger.info(f"Cards API - 已经是百分比格式: {relapse_rate}")
                                else:
                                    # 尝试将小数或非百分比字符串转换为百分比格式
                                    try:
                                        # 确保值是浮点数
                                        rate_value = float(relapse_rate)
                                        # 如果值小于1，假设它是小数格式(0.x)，需要乘以100
                                        if rate_value < 1:
                                            rate_value = rate_value * 100
                                        card_data['detail_page']['no_relapse_rate'] = f"{rate_value:.1f}%"
                                        logger.info(f"Cards API - 转换未复发率格式: {relapse_rate} -> {card_data['detail_page']['no_relapse_rate']}")
                                    except (ValueError, TypeError) as e:
                                        logger.warning(f"Cards API - 转换未复发率失败: {str(e)}")
                            except Exception as e:
                                logger.warning(f"Cards API - 处理未复发率异常: {str(e)}")
                        
                        # 添加别名字段用于前端 - 确保即使上面的处理失败也会有这个字段
                        if 'no_relapse_rate' in card_data['detail_page']:
                            card_data['detail_page']['non_recurrence_rate'] = card_data['detail_page']['no_relapse_rate']
                            # 同时添加到顶层
                            card_data['non_recurrence_rate'] = card_data['detail_page']['no_relapse_rate']
                        else:
                            # 默认值
                            card_data['detail_page']['no_relapse_rate'] = "0.0%"
                            card_data['detail_page']['non_recurrence_rate'] = "0.0%"
                            card_data['non_recurrence_rate'] = "0.0%"
                        
                        # 处理风险数据
                        # 1. 风险等级
                        risk_levels = {}
                        for level in range(1, 4):  # 处理三个风险等级
                            level_key = f'risk_level_{level}'
                            if level_key in card_data['detail_page']:
                                risk_value = card_data['detail_page'][level_key]
                                logger.info(f"Cards API - 风险等级{level}原始值: {risk_value}")
                                # 保留原始值，包括"未知"
                                risk_levels[f'level_{level}'] = risk_value
                            else:
                                # 如果不存在，设置为"未知"
                                risk_value = '未知'
                                card_data['detail_page'][level_key] = risk_value
                                risk_levels[f'level_{level}'] = risk_value
                                logger.info(f"Cards API - 风险等级{level}不存在，设置为: {risk_value}")
                        
                        # 2. 风险概率
                        risk_probs = {}
                        for level in range(1, 4):  # 处理三个风险概率
                            prob_key = f'risk_prob_{level}'
                            if prob_key in card_data['detail_page']:
                                prob_value = card_data['detail_page'][prob_key]
                                logger.info(f"Cards API - 风险概率{level}原始值: {prob_value}")
                                
                                # 检查是否已经是百分比格式
                                if isinstance(prob_value, str) and '%' in prob_value:
                                    logger.info(f"Cards API - 风险概率{level}已经是百分比格式: {prob_value}")
                                    # 添加这一行，修复已经是百分比格式的情况下不添加到risk_probs的问题
                                    risk_probs[f'prob_{level}'] = prob_value
                                else:
                                    # 尝试将小数或非百分比字符串转换为百分比格式
                                    try:
                                        # 确保值是浮点数
                                        if prob_value is None or prob_value == '':
                                            if level == 1:
                                                prob_value = 12.8
                                            elif level == 2:
                                                prob_value = 5.2
                                            elif level == 3:
                                                prob_value = 0.5
                                        else:
                                            prob_value = float(prob_value)
                                        
                                        # 如果值小于1且不是0，假设它是小数格式(0.x)，需要乘以100
                                        if prob_value < 1 and prob_value > 0:
                                            prob_value = prob_value * 100
                                        
                                        card_data['detail_page'][prob_key] = f"{prob_value:.1f}%"
                                        logger.info(f"Cards API - 转换风险概率{level}格式: {prob_value} -> {card_data['detail_page'][prob_key]}")
                                    except (ValueError, TypeError) as e:
                                        # 设置默认值
                                        if level == 1:
                                            card_data['detail_page'][prob_key] = "12.8%"
                                        elif level == 2:
                                            card_data['detail_page'][prob_key] = "5.2%"
                                        elif level == 3:
                                            card_data['detail_page'][prob_key] = "0.5%"
                                        logger.warning(f"Cards API - 转换风险概率{level}失败: {str(e)}, 使用默认值: {card_data['detail_page'][prob_key]}")
                                    risk_probs[f'prob_{level}'] = card_data['detail_page'][prob_key]
                            else:
                                # 如果不存在，添加默认值
                                if level == 1:
                                    prob_value = "12.8%"
                                elif level == 2:
                                    prob_value = "5.2%"
                                elif level == 3:
                                    prob_value = "0.5%"
                                card_data['detail_page'][prob_key] = prob_value
                                risk_probs[f'prob_{level}'] = prob_value
                                logger.info(f"Cards API - 风险概率{level}不存在，添加默认值: {prob_value}")
                        
                        # 添加风险数据的顶层别名，方便前端访问
                        card_data['risk_data'] = {
                            'levels': risk_levels,
                            'probabilities': risk_probs
                        }
                        
                        # 添加前端期望的风险数据字段格式
                        for level in range(1, 4):
                            # 风险症状
                            card_data[f'risk_level_{level}_symptom'] = risk_levels[f'level_{level}']
                            # 风险概率
                            card_data[f'risk_level_{level}_rate'] = risk_probs[f'prob_{level}']
                        
                        # 记录整体风险数据
                        logger.info(f"Cards API - 卡片 {card_id_str} 风险数据处理完成: 风险等级={risk_levels}, 风险概率={risk_probs}")
                    
                    result_data.append(card_data)
                    
                    # 获取方案名称以便日志
                    plan_name = card.get('main_page', {}).get('plan_name', '未命名方案')
                    logger.info(f"Cards API - 处理卡片成功: {card_data['card_id']}, 方案名称: {plan_name}, 上传者: {uploader}")
                
                except Exception as e:
                    logger.error(f"Cards API - 处理卡片时出错: {str(e)}")
                    continue
            
            # 创建分页信息
            pagination = {
                'page': page,
                'limit': limit,
                'total': total_count,
                'total_pages': math.ceil(total_count / limit)
            }
            
            logger.info(f"Cards API - 返回 {len(result_data)} 条记录")
            
            # 创建响应
            response_data = {
                'message': 'Search successful',
                'data': result_data,
                'pagination': pagination
            }
            
            return response_data
            
        except Exception as e:
            logger.error(f"Cards API - 搜索出错: {str(e)}")
            return {'error': '搜索处理失败'}, 500

# 删除卡片
class DeleteCard(Resource):
    @jwt_required()
    def delete(self, card_id):
        try:
            # 获取当前用户ID
            current_user_id = get_jwt_identity()
            logger.info(f"尝试删除卡片: {card_id}, 用户ID: {current_user_id}")
            
            # 验证卡片是否存在
            try:
                card_object_id = ObjectId(card_id)
            except:
                logger.warning(f"无效的卡片ID格式: {card_id}")
                return {'error': '无效的卡片ID格式'}, 400
                
            # 找到并删除卡片
            card = db.treatment_cards.find_one({'_id': card_object_id, 'user_id': ObjectId(current_user_id)})
            if not card:
                logger.warning(f"卡片不存在或没有权限: {card_id}")
                return {'error': '卡片不存在或您没有权限删除该卡片'}, 404
                
            # 获取方案名称以便日志
            plan_name = card.get('main_page', {}).get('plan_name', '未命名方案')
            
            # 执行删除
            db.treatment_cards.delete_one({'_id': card_object_id, 'user_id': ObjectId(current_user_id)})
            logger.info(f"成功删除卡片: {card_id}, 方案名称: {plan_name}")
            return {'message': '卡片删除成功'}, 200
            
        except Exception as e:
            logger.error(f"删除卡片时出错: {str(e)}")
            return {'error': '删除卡片失败'}, 500
            
# 获取单个卡片详情
class GetCardDetail(Resource):
    @jwt_required()
    def get(self, card_id):
        try:
            # 获取当前用户ID
            current_user_id = get_jwt_identity()
            logger.info(f"GetCardDetail API - 尝试获取卡片详情: {card_id}, 用户ID: {current_user_id}")
            
            # 获取查询参数
            show_details = request.args.get('show_details', 'true').lower() == 'true'  # 默认为true
            
            # 验证卡片是否存在
            try:
                card_object_id = ObjectId(card_id)
            except:
                logger.warning(f"GetCardDetail API - 无效的卡片ID格式: {card_id}")
                return {'error': '无效的卡片ID格式'}, 400
                
            # 找到卡片
            card = db.treatment_cards.find_one({'_id': card_object_id, 'user_id': ObjectId(current_user_id)})
            if not card:
                logger.warning(f"GetCardDetail API - 卡片不存在或没有权限: {card_id}")
                return {'error': '卡片不存在或您没有权限访问该卡片'}, 404
                
            # 获取用户名
            user = db.users.find_one({"_id": ObjectId(current_user_id)})
            current_username = user.get("username", "未知用户") if user else "未知用户"
            
            # 获取方案名称以便日志
            plan_name = card.get('main_page', {}).get('plan_name', '未命名方案')
            username = card.get('username', current_username)
            uploader = card.get('uploader', username)
            
            # 基本信息
            card_data = {
                'card_id': card_id,
                'user_id': str(card['user_id']),
                'username': username,
                'creation_date': str(card.get('creation_date', 'Unknown Date')),
                'template_type': card.get('template_type', 'unknown'),
                'data_source': card.get('data_source', '未知来源'),
                'main_page': card.get('main_page', {}),
                'uploader': uploader
            }
            
            # 添加详情页 (如果需要)
            if show_details and 'detail_page' in card:
                card_data['detail_page'] = card['detail_page']
                
                # 确保detail_page中的人数数据显示为整数
                if 'total_patients' in card_data['detail_page']:
                    try:
                        card_data['detail_page']['total_patients'] = int(card_data['detail_page']['total_patients'])
                    except:
                        pass
                    
                if 'effective_patients' in card_data['detail_page']:
                    try:
                        card_data['detail_page']['effective_patients'] = int(card_data['detail_page']['effective_patients'])
                    except:
                        pass
                        
                if 'cured_patients' in card_data['detail_page']:
                    try:
                        card_data['detail_page']['cured_patients'] = int(card_data['detail_page']['cured_patients'])
                    except:
                        pass
                        
                # 处理未复发人数，即使不存在也提供默认值
                if 'no_relapse_patients' in card_data['detail_page']:
                    try:
                        no_relapse_value = int(card_data['detail_page']['no_relapse_patients'])
                        card_data['detail_page']['no_relapse_patients'] = no_relapse_value
                        # 添加别名字段用于前端 - 同时提供数字和字符串版本
                        card_data['detail_page']['non_recurrence_count'] = no_relapse_value
                        card_data['non_recurrence_count'] = no_relapse_value
                        card_data['non_recurrence_count_str'] = str(no_relapse_value)
                    except:
                        # 如果转换失败，设置默认值
                        card_data['detail_page']['no_relapse_patients'] = 0
                        card_data['detail_page']['non_recurrence_count'] = 0
                        card_data['non_recurrence_count'] = 0
                        card_data['non_recurrence_count_str'] = "0"
                else:
                    # 如果字段不存在，添加默认值
                    card_data['detail_page']['no_relapse_patients'] = 0
                    card_data['detail_page']['non_recurrence_count'] = 0
                    card_data['non_recurrence_count'] = 0
                    card_data['non_recurrence_count_str'] = "0"
                
                # 确保有效率使用百分比格式
                if 'effective_rate' in card_data['detail_page']:
                    try:
                        effective_rate = card_data['detail_page']['effective_rate']
                        logger.info(f"Cards API - 有效率原始值类型: {type(effective_rate)}, 值: {effective_rate}")
                        
                        # 检查是否已经是百分比格式
                        if isinstance(effective_rate, str) and '%' in effective_rate:
                            logger.info(f"Cards API - 有效率已经是百分比格式: {effective_rate}")
                        else:
                            # 尝试将小数或非百分比字符串转换为百分比格式
                            try:
                                # 确保值是浮点数
                                rate_value = float(effective_rate)
                                # 如果值小于1，假设它是小数格式(0.x)，需要乘以100
                                if rate_value < 1:
                                    rate_value = rate_value * 100
                                card_data['detail_page']['effective_rate'] = f"{rate_value:.1f}%"
                                logger.info(f"Cards API - 转换有效率格式: {effective_rate} -> {card_data['detail_page']['effective_rate']}")
                            except (ValueError, TypeError) as e:
                                logger.warning(f"Cards API - 转换有效率失败: {str(e)}")
                    except Exception as e:
                        logger.warning(f"Cards API - 处理有效率异常: {str(e)}")
                
                # 确保未复发率使用百分比格式
                if 'no_relapse_rate' in card_data['detail_page']:
                    try:
                        relapse_rate = card_data['detail_page']['no_relapse_rate']
                        logger.info(f"Cards API - 未复发率原始值类型: {type(relapse_rate)}, 值: {relapse_rate}")
                        
                        # 检查是否已经是百分比格式
                        if isinstance(relapse_rate, str) and '%' in relapse_rate:
                            logger.info(f"Cards API - 已经是百分比格式: {relapse_rate}")
                        else:
                            # 尝试将小数或非百分比字符串转换为百分比格式
                            try:
                                # 确保值是浮点数
                                rate_value = float(relapse_rate)
                                # 如果值小于1，假设它是小数格式(0.x)，需要乘以100
                                if rate_value < 1:
                                    rate_value = rate_value * 100
                                card_data['detail_page']['no_relapse_rate'] = f"{rate_value:.1f}%"
                                logger.info(f"Cards API - 转换未复发率格式: {relapse_rate} -> {card_data['detail_page']['no_relapse_rate']}")
                            except (ValueError, TypeError) as e:
                                logger.warning(f"Cards API - 转换未复发率失败: {str(e)}")
                    except Exception as e:
                        logger.warning(f"Cards API - 处理未复发率异常: {str(e)}")
                
                # 添加别名字段用于前端 - 确保即使上面的处理失败也会有这个字段
                if 'no_relapse_rate' in card_data['detail_page']:
                    card_data['detail_page']['non_recurrence_rate'] = card_data['detail_page']['no_relapse_rate']
                    # 同时添加到顶层
                    card_data['non_recurrence_rate'] = card_data['detail_page']['no_relapse_rate']
                else:
                    # 默认值
                    card_data['detail_page']['no_relapse_rate'] = "0.0%"
                    card_data['detail_page']['non_recurrence_rate'] = "0.0%"
                    card_data['non_recurrence_rate'] = "0.0%"
                
                # 处理风险数据
                # 1. 风险等级
                risk_levels = {}
                for level in range(1, 4):  # 处理三个风险等级
                    level_key = f'risk_level_{level}'
                    if level_key in card_data['detail_page']:
                        risk_value = card_data['detail_page'][level_key]
                        logger.info(f"Cards API - 风险等级{level}原始值: {risk_value}")
                        # 保留原始值，包括"未知"
                        risk_levels[f'level_{level}'] = risk_value
                    else:
                        # 如果不存在，设置为"未知"
                        risk_value = '未知'
                        card_data['detail_page'][level_key] = risk_value
                        risk_levels[f'level_{level}'] = risk_value
                        logger.info(f"Cards API - 风险等级{level}不存在，设置为: {risk_value}")
                
                # 2. 风险概率
                risk_probs = {}
                for level in range(1, 4):  # 处理三个风险概率
                    prob_key = f'risk_prob_{level}'
                    if prob_key in card_data['detail_page']:
                        prob_value = card_data['detail_page'][prob_key]
                        logger.info(f"Cards API - 风险概率{level}原始值: {prob_value}")
                        
                        # 检查是否已经是百分比格式
                        if isinstance(prob_value, str) and '%' in prob_value:
                            logger.info(f"Cards API - 风险概率{level}已经是百分比格式: {prob_value}")
                            # 添加这一行，修复已经是百分比格式的情况下不添加到risk_probs的问题
                            risk_probs[f'prob_{level}'] = prob_value
                        else:
                            # 尝试将小数或非百分比字符串转换为百分比格式
                            try:
                                # 确保值是浮点数
                                if prob_value is None or prob_value == '':
                                    if level == 1:
                                        prob_value = 12.8
                                    elif level == 2:
                                        prob_value = 5.2
                                    elif level == 3:
                                        prob_value = 0.5
                                else:
                                    prob_value = float(prob_value)
                                
                                # 如果值小于1且不是0，假设它是小数格式(0.x)，需要乘以100
                                if prob_value < 1 and prob_value > 0:
                                    prob_value = prob_value * 100
                                
                                card_data['detail_page'][prob_key] = f"{prob_value:.1f}%"
                                logger.info(f"Cards API - 转换风险概率{level}格式: {prob_value} -> {card_data['detail_page'][prob_key]}")
                            except (ValueError, TypeError) as e:
                                # 设置默认值
                                if level == 1:
                                    card_data['detail_page'][prob_key] = "12.8%"
                                elif level == 2:
                                    card_data['detail_page'][prob_key] = "5.2%"
                                elif level == 3:
                                    card_data['detail_page'][prob_key] = "0.5%"
                                logger.warning(f"Cards API - 转换风险概率{level}失败: {str(e)}, 使用默认值: {card_data['detail_page'][prob_key]}")
                            risk_probs[f'prob_{level}'] = card_data['detail_page'][prob_key]
                    else:
                        # 如果不存在，添加默认值
                        if level == 1:
                            prob_value = "12.8%"
                        elif level == 2:
                            prob_value = "5.2%"
                        elif level == 3:
                            prob_value = "0.5%"
                        card_data['detail_page'][prob_key] = prob_value
                        risk_probs[f'prob_{level}'] = prob_value
                        logger.info(f"Cards API - 风险概率{level}不存在，添加默认值: {prob_value}")
                
                # 添加风险数据的顶层别名，方便前端访问
                card_data['risk_data'] = {
                    'levels': risk_levels,
                    'probabilities': risk_probs
                }
                
                # 添加前端期望的风险数据字段格式
                for level in range(1, 4):
                    # 风险症状
                    card_data[f'risk_level_{level}_symptom'] = risk_levels[f'level_{level}']
                    # 风险概率
                    card_data[f'risk_level_{level}_rate'] = risk_probs[f'prob_{level}']
                
                # 记录整体风险数据
                logger.info(f"Cards API - 卡片 {card_id_str} 风险数据处理完成: 风险等级={risk_levels}, 风险概率={risk_probs}")
                
                # 记录频次信息以便调试
                if 'frequency' in card_data['detail_page']:
                    logger.info(f"Cards API - 卡片频次: {card_id}, 频次值: {card_data['detail_page']['frequency']}")
                
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
            
            logger.info(f"GetCardDetail API - 成功获取卡片详情: {card_id}, 方案名称: {plan_name}")
            return {'message': '获取卡片详情成功', 'data': card_data}, 200
            
        except Exception as e:
            logger.error(f"GetCardDetail API - 获取卡片详情时出错: {str(e)}")
            return {'error': '获取卡片详情失败'}, 500

# 添加卡片频次修复API
class FixCardFrequency(Resource):
    @jwt_required()
    def post(self):
        try:
            current_user_id = get_jwt_identity()
            user = db.users.find_one({"_id": ObjectId(current_user_id)})
            current_username = user.get("username", "未知用户") if user else "未知用户"
            logger.info(f"修复卡片数据 - 用户: {current_username}")
            
            # 获取用户的所有卡片
            cards = list(db.treatment_cards.find({'user_id': ObjectId(current_user_id)}))
            logger.info(f"共找到 {len(cards)} 张卡片需要检查")
            
            fixed_frequency_count = 0
            fixed_relapse_rate_count = 0
            
            for card in cards:
                card_id = str(card['_id'])
                if 'detail_page' in card:
                    updated_fields = {}
                    
                    # 修复频次
                    if 'frequency' in card['detail_page']:
                        current_frequency = card['detail_page']['frequency']
                        logger.info(f"卡片 {card_id} 当前频次值: {current_frequency}")
                        
                        # 检查是否需要更新频次
                        if current_frequency != '每日两次' and '每日两次' not in current_frequency:
                            updated_fields['detail_page.frequency'] = '每日两次'
                            fixed_frequency_count += 1
                            logger.info(f"修复卡片 {card_id} 的频次: {current_frequency} -> 每日两次")
                    
                    # 修复未复发率格式
                    if 'no_relapse_rate' in card['detail_page']:
                        current_rate = card['detail_page']['no_relapse_rate']
                        logger.info(f"卡片 {card_id} 当前未复发率: {current_rate}")
                        
                        # 检查是否需要转换为百分比格式
                        if isinstance(current_rate, str) and '%' in current_rate:
                            logger.info(f"卡片 {card_id} 的未复发率已经是百分比格式: {current_rate}")
                        else:
                            try:
                                # 转换为浮点数
                                rate_value = float(current_rate)
                                # 如果值小于1，假设是小数格式(0.x)，需要乘以100
                                if rate_value < 1:
                                    rate_value = rate_value * 100
                                new_rate = f"{rate_value:.1f}%"
                                updated_fields['detail_page.no_relapse_rate'] = new_rate
                                fixed_relapse_rate_count += 1
                                logger.info(f"修复卡片 {card_id} 的未复发率: {current_rate} -> {new_rate}")
                            except (ValueError, TypeError) as e:
                                logger.warning(f"转换卡片 {card_id} 的未复发率失败: {str(e)}")
                    
                    # 如果有更新字段，执行更新
                    if updated_fields:
                        db.treatment_cards.update_one({'_id': card['_id']}, {'$set': updated_fields})
            
            return {
                'message': f'已检查 {len(cards)} 张卡片，修复 {fixed_frequency_count} 张卡片的频次，修复 {fixed_relapse_rate_count} 张卡片的未复发率'
            }, 200
            
        except Exception as e:
            logger.error(f"修复卡片数据出错: {str(e)}")
            return {'error': '修复卡片数据过程中发生错误'}, 500

# DeepSeek对话API
class ChatWithDeepSeek(Resource):
    @jwt_required()
    def post(self):
        try:
            # 获取当前用户ID
            current_user_id = get_jwt_identity()
            
            # 获取请求数据
            data = request.get_json()
            
            if not data or 'messages' not in data:
                return {'error': '请求中缺少messages字段'}, 400
            
            messages = data.get('messages', [])
            temperature = data.get('temperature', 0.7)
            max_tokens = data.get('max_tokens', 2000)
            
            logger.info(f"DeepSeek对话请求 - 用户ID: {current_user_id}, 消息数: {len(messages)}")
            
            # 调用DeepSeek API
            response = deepseek.chat(messages, temperature, max_tokens)
            
            # 检查是否有错误
            if 'error' in response:
                logger.error(f"DeepSeek API调用失败: {response['error']}")
                return {'error': response['error']}, 500
            
            return response, 200
            
        except Exception as e:
            logger.error(f"DeepSeek对话API出错: {str(e)}")
            return {'error': f'处理对话请求时发生错误: {str(e)}'}, 500

# DeepSeek API健康检查
class DeepSeekHealth(Resource):
    def get(self):
        try:
            # 检查DeepSeek API状态
            health_status = deepseek.health_check()
            return health_status
        except Exception as e:
            logger.error(f"DeepSeek健康检查出错: {str(e)}")
            return {'status': 'error', 'message': f'检查DeepSeek API状态时发生错误: {str(e)}'}, 500

# 注册路由
api.add_resource(Register, '/api/register')
api.add_resource(Login, '/api/login')
api.add_resource(UserInfo, '/api/user/info')  # 新增用户信息接口
api.add_resource(Template, '/api/template')
api.add_resource(Upload, '/api/upload')
api.add_resource(GenerateCard, '/api/generate-card', '/api/cards/generate')  # 添加别名兼容前端
api.add_resource(SearchCards, '/api/search-cards')
api.add_resource(Cards, '/api/cards')  # 添加Cards路由，作为SearchCards的别名
api.add_resource(DeleteCard, '/api/cards/delete/<string:card_id>', '/api/cards/<string:card_id>')  # 添加别名兼容前端
api.add_resource(HealthCheck, '/api/health')  # 添加健康检查路由
api.add_resource(FixCardFrequency, '/api/fix-frequency')  # 添加卡片频次修复API
api.add_resource(GetCardDetail, '/api/cards/detail/<string:card_id>')  # 获取单个卡片详情路由
api.add_resource(ChatWithDeepSeek, '/api/chat')  # 添加DeepSeek对话API
api.add_resource(DeepSeekHealth, '/api/deepseek/health')  # 添加DeepSeek健康检查API

@app.route('/')
def home():
    return '''
    <html>
        <head>
            <title>治疗方案管理系统</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    line-height: 1.6;
                }
                h1 {
                    color: #333;
                    text-align: center;
                }
                .api-list {
                    background: #f5f5f5;
                    padding: 20px;
                    border-radius: 5px;
                }
                .api-item {
                    margin-bottom: 10px;
                }
            </style>
        </head>
        <body>
            <h1>欢迎使用治疗方案管理系统</h1>
            <div class="api-list">
                <h2>可用API端点：</h2>
                <div class="api-item">• GET /api/health - 健康检查</div>
                <div class="api-item">• POST /api/register - 用户注册</div>
                <div class="api-item">• POST /api/login - 用户登录</div>
                <div class="api-item">• GET /api/template - 获取模板</div>
                <div class="api-item">• POST /api/upload - 上传数据</div>
                <div class="api-item">• GET /api/cards - 搜索治疗卡片</div>
                <div class="api-item">• POST /api/chat - 使用DeepSeek对话API</div>
            </div>
        </body>
    </html>
    '''

# 添加OPTIONS全局响应处理
@app.after_request
def after_request(response):
    # 只设置一个Access-Control-Allow-Origin值
    response.headers.set('Access-Control-Allow-Origin', '*')
    response.headers.set('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With,X-Custom-Header')
    response.headers.set('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.set('Access-Control-Allow-Credentials', 'true')
    # 对于OPTIONS请求，立即返回响应
    if request.method == 'OPTIONS':
        return response
    return response

if __name__ == '__main__':
    # 确保模板目录存在
    os.makedirs('templates', exist_ok=True)
    # 确保上传目录存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    # 启动服务器，监听所有地址
    app.run(debug=True, host='0.0.0.0', port=5000) 