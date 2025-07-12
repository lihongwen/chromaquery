import React from 'react';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import CollectionManager from './components/CollectionManager';
import './App.css';

function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <div className="App">
        <CollectionManager />
      </div>
    </ConfigProvider>
  );
}

export default App;
