import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import { Result, Button } from 'antd';
import { ExceptionOutlined, ReloadOutlined } from '@ant-design/icons';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.setState({
      error,
      errorInfo,
    });
  }

  handleReload = () => {
    window.location.reload();
  };

  handleReset = () => {
    this.setState({ hasError: false, error: undefined, errorInfo: undefined });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div style={{ 
          padding: '50px', 
          display: 'flex', 
          justifyContent: 'center', 
          alignItems: 'center',
          minHeight: '400px'
        }}>
          <Result
            status="error"
            icon={<ExceptionOutlined style={{ color: '#ff4d4f' }} />}
            title="应用出现错误"
            subTitle="很抱歉，应用遇到了意外错误。请尝试重新加载页面。"
            extra={[
              <Button 
                type="primary" 
                icon={<ReloadOutlined />} 
                onClick={this.handleReload}
                key="reload"
              >
                重新加载
              </Button>,
              <Button onClick={this.handleReset} key="retry">
                重试
              </Button>,
            ]}
          >
            {import.meta.env.DEV && this.state.error && (
              <div style={{ 
                textAlign: 'left', 
                marginTop: '20px',
                padding: '16px',
                backgroundColor: '#f5f5f5',
                borderRadius: '8px',
                fontSize: '12px',
                fontFamily: 'monospace'
              }}>
                <details>
                  <summary style={{ marginBottom: '8px', cursor: 'pointer' }}>
                    错误详情 (开发模式)
                  </summary>
                  <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                    {this.state.error.toString()}
                    {this.state.errorInfo?.componentStack}
                  </pre>
                </details>
              </div>
            )}
          </Result>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
