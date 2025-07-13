import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import CollectionManager from './components/CollectionManager';
import CollectionDetail from './components/CollectionDetail';
import QueryPage from './components/QueryPage';
import AppRouter from './components/AppRouter';
import './App.css';

function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <div className="App">
        <Router>
          <AppRouter />
        </Router>
      </div>
    </ConfigProvider>
  );
}

export default App;
