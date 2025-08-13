# 建议的命令

## 项目启动
```bash
# 一键部署和启动 (推荐)
python deploy.py    # 部署环境和依赖
python start.py     # 启动前后端服务

# 手动启动
# 后端
cd backend
python main.py

# 前端  
cd frontend
npm run dev
```

## 开发命令
```bash
# 前端
cd frontend
npm install         # 安装依赖
npm run dev         # 开发服务器
npm run build       # 构建生产版本
npm run lint        # 代码检查

# 后端
cd backend
pip install -r requirements.txt  # 安装依赖
python main.py      # 启动服务器
```

## 数据管理
```bash
# 数据清理和恢复
python cleanup_orphaned_data.py    # 清理孤立数据
python emergency_recovery.py       # 紧急数据恢复
python check_orphaned_data.py      # 检查数据状态
```

## 测试命令
```bash
python simple_test.py       # 基本功能测试
python debug_test.py        # 调试测试
python final_test.py        # 最终验证测试
```

## 系统命令 (Windows)
```cmd
dir                 # 列出目录内容
cd                  # 切换目录
findstr             # 文本搜索
type                # 查看文件内容
del                 # 删除文件
```