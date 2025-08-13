# 任务完成工作流程

## 开发完成后的步骤

### 1. 代码质量检查
```bash
# 前端检查
cd frontend
npm run lint        # ESLint 检查
npm run build       # 构建测试

# 后端检查  
cd backend
python -m flake8 .  # 代码规范检查 (如果配置了)
python -m mypy .    # 类型检查 (如果配置了)
```

### 2. 功能测试
```bash
# 基本功能测试
python simple_test.py
python debug_test.py
python final_test.py

# 特定功能测试
python quick_test_rename.py     # 重命名功能
python simple_cleanup_test.py   # 数据清理功能
```

### 3. 数据一致性检查
```bash
python check_orphaned_data.py   # 检查数据状态
python verify_fix.py            # 验证修复结果
```

### 4. 服务重启验证
```bash
# 重启服务确保变更生效
python start.py
```

### 5. 清理临时文件
- 删除测试过程中生成的临时文件
- 清理不必要的日志文件
- 确保数据目录状态良好

### 6. 文档更新
- 更新相关的 README 或文档
- 记录重要的配置变更
- 更新 API 文档 (如有必要)