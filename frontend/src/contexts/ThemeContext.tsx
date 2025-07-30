import React, { createContext, useContext, useState, useEffect } from 'react';
import type { ThemeMode } from '../config/theme';

interface ThemeContextType {
  theme: ThemeMode;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

interface ThemeProviderProps {
  children: React.ReactNode;
}

export const ThemeProvider: React.FC<ThemeProviderProps> = ({ children }) => {
  const [theme, setTheme] = useState<ThemeMode>(() => {
    const savedTheme = localStorage.getItem('chromadb-theme');
    return (savedTheme as ThemeMode) || 'light';
  });

  useEffect(() => {
    localStorage.setItem('chromadb-theme', theme);

    // 更新 HTML 根元素的 data-theme 属性
    document.documentElement.setAttribute('data-theme', theme);

    // 更新 body 的背景色 - 使用简洁的纯色背景
    if (theme === 'dark') {
      document.body.style.background = '#111827';
    } else {
      document.body.style.background = '#ffffff';
    }
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};