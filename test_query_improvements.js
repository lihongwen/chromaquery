#!/usr/bin/env node

/**
 * 测试查询功能改进
 * 1. 测试查询结果过滤（只显示相似度 > 0 的结果）
 * 2. 测试无结果时的处理
 */

const axios = require('axios');

const API_BASE_URL = 'http://localhost:8000/api';

async function testQueryFiltering() {
  console.log('🧪 测试查询功能改进...\n');

  try {
    // 测试1: 相关查询（应该有结果）
    console.log('📋 测试1: 相关查询 - "水利工程"');
    const relevantQuery = await axios.post(`${API_BASE_URL}/query`, {
      query: '水利工程',
      collections: ['中文测试'],
      limit: 5
    });

    console.log(`✅ 返回结果数量: ${relevantQuery.data.results.length}`);
    console.log(`⏱️  处理时间: ${(relevantQuery.data.processing_time * 1000).toFixed(0)}ms`);
    
    if (relevantQuery.data.results.length > 0) {
      console.log('📊 相似度分析:');
      relevantQuery.data.results.forEach((result, index) => {
        const similarity = ((1 - result.distance) * 100).toFixed(1);
        console.log(`   ${index + 1}. 相似度: ${similarity}% (距离: ${result.distance.toFixed(4)})`);
      });
    }
    console.log('');

    // 测试2: 不相关查询（应该没有结果或很少结果）
    console.log('📋 测试2: 不相关查询 - "量子计算机编程"');
    const irrelevantQuery = await axios.post(`${API_BASE_URL}/query`, {
      query: '量子计算机编程',
      collections: ['中文测试'],
      limit: 5
    });

    console.log(`✅ 返回结果数量: ${irrelevantQuery.data.results.length}`);
    console.log(`⏱️  处理时间: ${(irrelevantQuery.data.processing_time * 1000).toFixed(0)}ms`);
    
    if (irrelevantQuery.data.results.length > 0) {
      console.log('📊 相似度分析:');
      irrelevantQuery.data.results.forEach((result, index) => {
        const similarity = ((1 - result.distance) * 100).toFixed(1);
        console.log(`   ${index + 1}. 相似度: ${similarity}% (距离: ${result.distance.toFixed(4)})`);
      });
    } else {
      console.log('✅ 正确过滤：没有找到相关结果');
    }
    console.log('');

    // 测试3: 空查询
    console.log('📋 测试3: 空查询');
    try {
      await axios.post(`${API_BASE_URL}/query`, {
        query: '',
        collections: ['中文测试'],
        limit: 5
      });
    } catch (error) {
      if (error.response && error.response.status === 400) {
        console.log('✅ 正确处理：空查询被拒绝');
      } else {
        console.log('❌ 意外错误:', error.message);
      }
    }
    console.log('');

    // 测试4: 不存在的集合
    console.log('📋 测试4: 不存在的集合');
    try {
      await axios.post(`${API_BASE_URL}/query`, {
        query: '测试查询',
        collections: ['不存在的集合'],
        limit: 5
      });
    } catch (error) {
      if (error.response && error.response.status === 404) {
        console.log('✅ 正确处理：不存在的集合被拒绝');
      } else {
        console.log('❌ 意外错误:', error.message);
      }
    }
    console.log('');

    console.log('🎉 查询功能改进测试完成！');

  } catch (error) {
    console.error('❌ 测试失败:', error.message);
    if (error.response) {
      console.error('响应状态:', error.response.status);
      console.error('响应数据:', error.response.data);
    }
  }
}

// 运行测试
testQueryFiltering();
