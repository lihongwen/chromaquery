import { theme } from 'antd';

export const lightTheme = {
  algorithm: theme.defaultAlgorithm,
  token: {
    colorPrimary: '#3b82f6',
    colorSuccess: '#10b981',
    colorWarning: '#f59e0b',
    colorError: '#ef4444',
    colorInfo: '#06b6d4',
    colorBgBase: '#ffffff',
    colorBgContainer: '#ffffff',
    colorBgLayout: '#f8fafc',
    colorText: '#1f2937',
    colorTextSecondary: '#6b7280',
    borderRadius: 8,
    fontSize: 14,
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  },
  components: {
    Button: {
      borderRadius: 8,
      primaryShadow: 'none',
    },
    Input: {
      borderRadius: 8,
    },
    Select: {
      borderRadius: 8,
    },
    Card: {
      borderRadius: 12,
      boxShadow: '0 2px 8px rgba(0, 0, 0, 0.06)',
    },
    Modal: {
      borderRadius: 8,
    },
    Table: {
      borderRadius: 8,
    },
    Tabs: {
      borderRadius: 8,
      cardBg: '#ffffff',
    },
  },
};

export const darkTheme = {
  algorithm: theme.darkAlgorithm,
  token: {
    colorPrimary: '#60a5fa',
    colorSuccess: '#34d399',
    colorWarning: '#fbbf24',
    colorError: '#f87171',
    colorInfo: '#22d3ee',
    colorBgBase: '#0f172a',
    colorBgContainer: '#1e293b',
    colorBgLayout: '#0f172a',
    colorBgElevated: '#334155',
    colorText: '#f1f5f9',
    colorTextSecondary: '#94a3b8',
    colorTextTertiary: '#64748b',
    colorTextQuaternary: '#475569',
    colorBorder: '#334155',
    colorBorderSecondary: '#475569',
    colorFill: '#334155',
    colorFillSecondary: '#475569',
    colorFillTertiary: '#64748b',
    colorFillQuaternary: '#94a3b8',
    borderRadius: 8,
    fontSize: 14,
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  },
  components: {
    Button: {
      borderRadius: 8,
      primaryShadow: 'none',
    },
    Input: {
      borderRadius: 8,
    },
    Select: {
      borderRadius: 8,
    },
    Card: {
      borderRadius: 12,
      boxShadow: '0 2px 8px rgba(0, 0, 0, 0.3)',
    },
    Modal: {
      borderRadius: 8,
    },
    Table: {
      borderRadius: 8,
    },
    Tabs: {
      borderRadius: 8,
      cardBg: '#1e293b',
    },
  },
};

export type ThemeMode = 'light' | 'dark';

export const getThemeConfig = (mode: ThemeMode) => {
  return mode === 'dark' ? darkTheme : lightTheme;
};