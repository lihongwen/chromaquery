import React from 'react';
import { Button, Tooltip } from 'antd';
import { SunOutlined, MoonOutlined } from '@ant-design/icons';
import { useTheme } from '../contexts/ThemeContext';

interface ThemeToggleProps {
  size?: 'small' | 'middle' | 'large';
  type?: 'text' | 'default' | 'primary' | 'dashed' | 'link';
}

const ThemeToggle: React.FC<ThemeToggleProps> = ({ size = 'middle', type = 'text' }) => {
  const { theme, toggleTheme } = useTheme();

  return (
    <Tooltip title={theme === 'light' ? '切换到深色模式' : '切换到浅色模式'}>
      <Button
        type={type}
        size={size}
        icon={theme === 'light' ? <MoonOutlined /> : <SunOutlined />}
        onClick={toggleTheme}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      />
    </Tooltip>
  );
};

export default ThemeToggle;