# 代码规范和约定

## Python 后端规范
- 遵循 PEP 8 代码规范
- 使用 Type Hints 进行类型标注
- 类名使用 PascalCase (如 `DataCleanupTool`)
- 函数名使用 snake_case (如 `scan_orphaned_data`)
- 常量使用 UPPER_CASE
- 使用 docstring 进行函数和类的文档说明
- 异常处理使用 try-except 结构
- 导入顺序: 标准库 -> 第三方库 -> 本地模块

## TypeScript 前端规范  
- 使用 TypeScript 严格模式
- 组件名使用 PascalCase (如 `CollectionDetail`)
- 接口和类型以 I 或 Type 开头
- 使用 ESLint 进行代码检查
- 使用函数式组件和 React Hooks
- Props 和 State 进行类型定义

## 文件命名约定
- Python 文件: snake_case.py
- TypeScript 组件: PascalCase.tsx
- 工具脚本: descriptive_name.py
- 配置文件: kebab-case.json

## 项目特殊约定
- 集合名称编码: 中文名称通过MD5哈希转换为UUID
- 错误处理: 统一的错误响应格式
- 日志记录: 使用标准 logging 模块
- 异步操作: 使用 FastAPI 的异步特性