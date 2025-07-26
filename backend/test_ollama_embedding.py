#!/usr/bin/env python3
"""
测试Ollama嵌入模型功能
"""

import sys
import os
import logging

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ollama_embedding import create_ollama_embedding_function, get_recommended_models, OllamaEmbeddingFunction

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_ollama_service():
    """测试Ollama服务是否可用"""
    print("=" * 50)
    print("测试Ollama服务连接")
    print("=" * 50)
    
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models_data = response.json()
            available_models = [model['name'] for model in models_data.get('models', [])]
            print(f"✅ Ollama服务运行正常")
            print(f"可用模型: {available_models}")
            return True, available_models
        else:
            print(f"❌ Ollama服务响应异常: {response.status_code}")
            return False, []
    except Exception as e:
        print(f"❌ 无法连接到Ollama服务: {e}")
        print("请确保Ollama服务正在运行 (ollama serve)")
        return False, []

def test_supported_models():
    """测试获取推荐的模型列表"""
    print("\n" + "=" * 50)
    print("测试推荐的模型列表")
    print("=" * 50)

    try:
        models = get_recommended_models()
        print("推荐的嵌入模型:")
        for model in models:
            print(f"  - {model['name']}: {model['description']}")
            print(f"    维度: {model['dimension']}, 推荐: {model['recommended']}")
        return True
    except Exception as e:
        print(f"❌ 获取推荐的模型列表失败: {e}")
        return False

def test_available_models():
    """测试获取实际可用的模型列表"""
    print("\n" + "=" * 50)
    print("测试实际可用的模型列表")
    print("=" * 50)

    try:
        result = OllamaEmbeddingFunction.get_available_models()
        if result["success"]:
            print("✅ 成功获取可用模型列表")
            print(f"总模型数: {result['total_models']}")

            if result["embedding_models"]:
                print("可用的嵌入模型:")
                for model in result["embedding_models"]:
                    print(f"  - {model['name']} (大小: {model['size']} bytes)")
            else:
                print("未找到嵌入模型")

            if result["other_models"]:
                print("其他可用模型:")
                for model in result["other_models"][:3]:  # 只显示前3个
                    print(f"  - {model['name']} (大小: {model['size']} bytes)")
                if len(result["other_models"]) > 3:
                    print(f"  ... 还有 {len(result['other_models']) - 3} 个其他模型")

            return True
        else:
            print(f"❌ 获取可用模型失败: {result['error']}")
            return False
    except Exception as e:
        print(f"❌ 测试获取可用模型失败: {e}")
        return False

def test_embedding_function(model_name="mxbai-embed-large"):
    """测试嵌入函数"""
    print(f"\n" + "=" * 50)
    print(f"测试嵌入函数: {model_name}")
    print("=" * 50)
    
    try:
        # 创建嵌入函数
        embedding_func = create_ollama_embedding_function(model_name=model_name)
        print(f"✅ 成功创建嵌入函数: {model_name}")
        
        # 测试单个文本
        test_text = "这是一个测试文本"
        print(f"测试文本: {test_text}")
        
        embeddings = embedding_func([test_text])
        if embeddings and len(embeddings) > 0:
            embedding = embeddings[0]
            print(f"✅ 成功生成嵌入向量")
            print(f"向量维度: {len(embedding)}")
            print(f"向量前5个值: {embedding[:5]}")
            
            # 测试批量文本
            test_texts = [
                "这是第一个测试文本",
                "这是第二个测试文本",
                "This is an English test text"
            ]
            print(f"\n测试批量文本: {len(test_texts)} 个文本")
            
            batch_embeddings = embedding_func(test_texts)
            if batch_embeddings and len(batch_embeddings) == len(test_texts):
                print(f"✅ 成功生成批量嵌入向量")
                print(f"生成向量数量: {len(batch_embeddings)}")
                for i, emb in enumerate(batch_embeddings):
                    print(f"  文本{i+1}向量维度: {len(emb)}")
                return True
            else:
                print(f"❌ 批量嵌入向量生成失败")
                return False
        else:
            print(f"❌ 嵌入向量生成失败")
            return False
            
    except Exception as e:
        print(f"❌ 测试嵌入函数失败: {e}")
        return False

def test_model_info(model_name="mxbai-embed-large"):
    """测试获取模型信息"""
    print(f"\n" + "=" * 50)
    print(f"测试获取模型信息: {model_name}")
    print("=" * 50)
    
    try:
        embedding_func = create_ollama_embedding_function(model_name=model_name)
        model_info = embedding_func.get_model_info()
        
        if "error" not in model_info:
            print(f"✅ 成功获取模型信息")
            print(f"模型信息: {model_info}")
            return True
        else:
            print(f"❌ 获取模型信息失败: {model_info['error']}")
            return False
            
    except Exception as e:
        print(f"❌ 测试获取模型信息失败: {e}")
        return False

def main():
    """主测试函数"""
    print("Ollama嵌入模型功能测试")
    print("=" * 50)
    
    # 测试结果统计
    test_results = []
    
    # 1. 测试Ollama服务
    service_ok, available_models = test_ollama_service()
    test_results.append(("Ollama服务连接", service_ok))
    
    if not service_ok:
        print("\n❌ Ollama服务不可用，无法继续测试")
        print("请先启动Ollama服务: ollama serve")
        return
    
    # 2. 测试支持的模型列表
    models_ok = test_supported_models()
    test_results.append(("支持的模型列表", models_ok))
    
    # 3. 测试获取实际可用的模型
    available_models_ok = test_available_models()
    test_results.append(("实际可用的模型列表", available_models_ok))

    # 4. 选择一个可用的嵌入模型进行测试
    test_model = None

    # 优先使用实际可用的嵌入模型
    if available_models_ok:
        try:
            result = OllamaEmbeddingFunction.get_available_models()
            if result["success"] and result["embedding_models"]:
                test_model = result["embedding_models"][0]["name"]
                print(f"\n✅ 选择可用的嵌入模型: {test_model}")
        except Exception as e:
            print(f"⚠️  获取可用模型时出错: {e}")

    # 如果没有找到可用的嵌入模型，使用推荐模型
    if not test_model:
        recommended_models = ["mxbai-embed-large", "nomic-embed-text", "all-minilm", "snowflake-arctic-embed"]
        for model in recommended_models:
            if any(model in available for available in available_models):
                test_model = model
                break

    if not test_model:
        print(f"\n⚠️  没有找到可用的嵌入模型，尝试使用 mxbai-embed-large")
        test_model = "mxbai-embed-large"
    
    # 5. 测试嵌入函数
    embedding_ok = test_embedding_function(test_model)
    test_results.append((f"嵌入函数({test_model})", embedding_ok))

    # 6. 测试模型信息
    info_ok = test_model_info(test_model)
    test_results.append((f"模型信息({test_model})", info_ok))
    
    # 输出测试结果总结
    print("\n" + "=" * 50)
    print("测试结果总结")
    print("=" * 50)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！Ollama嵌入模型功能正常")
    else:
        print("⚠️  部分测试失败，请检查配置和服务状态")

if __name__ == "__main__":
    main()
