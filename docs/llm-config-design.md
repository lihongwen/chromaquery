# LLM配置数据结构设计

## 概述

基于现有的embedding_config结构，设计LLM配置的数据结构，支持DeepSeek和阿里云通义千问两个提供商。

## 数据结构设计

### 1. 配置文件结构

```json
{
  "llm_config": {
    "default_provider": "alibaba",  // 默认LLM提供商: "deepseek" 或 "alibaba"
    "deepseek": {
      "api_key": "",                // DeepSeek API密钥
      "api_endpoint": "https://api.deepseek.com",
      "model": "deepseek-chat",     // 默认模型
      "models": [                   // 支持的模型列表
        {
          "name": "deepseek-chat",
          "display_name": "DeepSeek Chat",
          "description": "通用对话模型，适合大多数场景",
          "max_tokens": 4096,
          "recommended": true
        },
        {
          "name": "deepseek-reasoner", 
          "display_name": "DeepSeek Reasoner",
          "description": "推理增强模型，适合复杂分析任务",
          "max_tokens": 8192,
          "recommended": false
        }
      ],
      "verified": false,            // 验证状态
      "last_verified": null,        // 最后验证时间
      "verification_error": null    // 验证错误信息
    },
    "alibaba": {
      "api_key": "",                // 阿里云API密钥
      "api_endpoint": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "model": "qwen-plus",         // 默认模型
      "models": [                   // 支持的模型列表
        {
          "name": "qwen-plus",
          "display_name": "通义千问Plus",
          "description": "平衡性能和成本的通用模型",
          "max_tokens": 8192,
          "recommended": true
        },
        {
          "name": "qwen-max-latest",
          "display_name": "通义千问Max",
          "description": "最强性能模型，适合复杂任务",
          "max_tokens": 8192,
          "recommended": false
        },
        {
          "name": "qwen-turbo-2025-07-15",
          "display_name": "通义千问Turbo",
          "description": "快速响应模型，适合简单任务",
          "max_tokens": 8192,
          "recommended": false
        }
      ],
      "verified": false,            // 验证状态
      "last_verified": null,        // 最后验证时间
      "verification_error": null    // 验证错误信息
    }
  }
}
```

### 2. Python类型定义

```python
from typing import Dict, List, Optional
from datetime import datetime

class LLMModel:
    """LLM模型信息"""
    name: str
    display_name: str
    description: str
    max_tokens: int
    recommended: bool

class LLMProviderConfig:
    """LLM提供商配置"""
    api_key: str
    api_endpoint: str
    model: str
    models: List[LLMModel]
    verified: bool
    last_verified: Optional[datetime]
    verification_error: Optional[str]

class LLMConfig:
    """LLM配置"""
    default_provider: str  # "deepseek" 或 "alibaba"
    deepseek: LLMProviderConfig
    alibaba: LLMProviderConfig
```

### 3. 配置管理方法

需要在ConfigManager中添加以下方法：

- `get_llm_config()` - 获取LLM配置
- `set_llm_config(config)` - 设置LLM配置
- `get_default_llm_provider()` - 获取默认LLM提供商
- `set_default_llm_provider(provider)` - 设置默认LLM提供商
- `get_deepseek_config()` - 获取DeepSeek配置
- `set_deepseek_config(config)` - 设置DeepSeek配置
- `get_alibaba_llm_config()` - 获取阿里云LLM配置
- `set_alibaba_llm_config(config)` - 设置阿里云LLM配置
- `get_current_llm_config()` - 获取当前使用的LLM配置
- `set_llm_provider_verification_status(provider, verified, error)` - 设置提供商验证状态

### 4. API接口设计

需要添加以下API接口：

- `GET /api/llm-config` - 获取LLM配置
- `POST /api/llm-config` - 设置LLM配置
- `POST /api/llm-config/test` - 测试LLM连接
- `GET /api/llm-models` - 获取可用模型列表
- `GET /api/llm-providers/status` - 获取提供商状态
- `POST /api/llm-providers/{provider}/verify` - 验证提供商配置

### 5. 前端UI组件

需要在SettingsTab中添加：

- LLM配置选项卡
- 提供商选择（Radio按钮）
- 模型选择下拉框（根据提供商动态更新）
- API Key输入框
- 连接测试按钮
- 验证状态显示

### 6. 兼容性考虑

- 保持现有LLM客户端接口不变
- 支持配置热更新，无需重启服务
- 向后兼容，如果没有配置则使用默认值
- 错误处理和降级机制

## 实现优先级

1. 后端配置管理（ConfigManager扩展）
2. 后端API接口
3. LLM客户端重构
4. 前端UI组件
5. 集成测试

## 注意事项

- API Key需要安全存储，考虑加密
- 验证状态需要定期更新
- 错误信息需要用户友好
- 支持配置导入导出
