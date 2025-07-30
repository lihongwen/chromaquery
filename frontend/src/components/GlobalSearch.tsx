import React, { useState, useCallback } from 'react';
import { AutoComplete, Input, message } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { debounce } from 'lodash-es';

interface SearchResult {
  value: string;
  label: string;
  type: 'collection' | 'document';
}

const GlobalSearch: React.FC = () => {
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);

  const performSearch = useCallback(
    debounce(async (value: string) => {
      if (!value.trim()) {
        setSearchResults([]);
        return;
      }

      setLoading(true);
      try {
        // TODO: 实现实际的搜索逻辑
        // 这里是模拟搜索结果
        const mockResults: SearchResult[] = [
          {
            value: `collection-${value}`,
            label: `集合: ${value}`,
            type: 'collection',
          },
          {
            value: `document-${value}`,
            label: `文档: ${value}`,
            type: 'document',
          },
        ];

        setSearchResults(mockResults);
      } catch (error) {
        message.error('搜索失败');
        setSearchResults([]);
      } finally {
        setLoading(false);
      }
    }, 300),
    []
  );

  const handleSearch = (value: string) => {
    performSearch(value);
  };

  const handleSelect = (value: string) => {
    // TODO: 根据选中的项目类型进行相应的导航
    console.log('Selected:', value);
  };

  return (
    <AutoComplete
      style={{ width: 400 }}
      options={searchResults}
      onSearch={handleSearch}
      onSelect={handleSelect}
      placeholder="搜索集合、文档..."
    >
      <Input.Search
        size="middle"
        loading={loading}
        prefix={<SearchOutlined />}
        allowClear
      />
    </AutoComplete>
  );
};

export default GlobalSearch;