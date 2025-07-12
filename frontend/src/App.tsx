import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import CollectionManager from './components/CollectionManager';
import CollectionDetail from './components/CollectionDetail';
import './App.css';

function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <div className="App">
        <Router>
          <Routes>
            <Route path="/" element={<CollectionManager />} />
            <Route path="/collections/:collectionName/detail" element={<CollectionDetail />} />
          </Routes>
        </Router>
      </div>
    </ConfigProvider>
  );
}

export default App;
