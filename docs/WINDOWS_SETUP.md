# ChromaDB Web Manager - Windows 安装指南

本指南专门针对 Windows 10/11 用户，提供详细的安装和配置步骤。

## 📋 系统要求

- **操作系统**: Windows 10 (1903+) 或 Windows 11
- **Python**: 3.8 或更高版本
- **Node.js**: 16.0 或更高版本
- **内存**: 至少 4GB RAM
- **存储**: 至少 2GB 可用空间

## 🛠️ 前置条件安装

### 1. 安装 Python

1. 访问 [Python官网](https://www.python.org/downloads/windows/)
2. 下载最新的 Python 3.x 版本
3. **重要**: 安装时勾选 "Add Python to PATH"
4. 验证安装：
   ```cmd
   python --version
   pip --version
   ```

### 2. 安装 Node.js

1. 访问 [Node.js官网](https://nodejs.org/)
2. 下载 LTS 版本
3. 使用默认设置安装
4. 验证安装：
   ```cmd
   node --version
   npm --version
   ```

### 3. 安装 uv (可选，推荐)

```cmd
pip install uv
```

## 🚀 快速安装

### 方法一：使用批处理脚本（推荐）

1. 下载项目到本地
2. 双击运行 `scripts\deploy.bat`
3. 等待安装完成
4. 双击运行 `scripts\start.bat`

### 方法二：命令行安装

1. 打开命令提示符（建议以管理员身份运行）
2. 切换到项目目录：
   ```cmd
   cd path\to\chromadb-web-manager
   ```
3. 运行部署脚本：
   ```cmd
   python deploy.py
   ```
4. 启动应用：
   ```cmd
   python start.py
   ```

## 🔧 Windows 特定配置

### 编码设置

为避免中文乱码，建议设置以下环境变量：

```cmd
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
```

或在系统环境变量中永久设置。

### 防火墙配置

确保以下端口在 Windows 防火墙中被允许：
- **8000**: 后端 API 服务
- **5173**: 前端开发服务器
- **11434**: Ollama 服务（如果使用）

### 长路径支持

如果遇到路径过长的问题，启用 Windows 长路径支持：

1. 打开组策略编辑器 (`gpedit.msc`)
2. 导航到：计算机配置 > 管理模板 > 系统 > 文件系统
3. 启用 "启用 Win32 长路径"

## 🐛 常见问题解决

### 问题 1: Python 命令不识别

**解决方案**:
1. 重新安装 Python，确保勾选 "Add Python to PATH"
2. 手动添加 Python 到系统 PATH
3. 重启命令提示符

### 问题 2: npm 安装失败

**解决方案**:
```cmd
npm config set registry https://registry.npmmirror.com
npm cache clean --force
```

### 问题 3: 端口被占用

**解决方案**:
```cmd
# 查看端口占用
netstat -ano | findstr :8000
# 结束占用进程
taskkill /PID <进程ID> /F
```

### 问题 4: 权限错误

**解决方案**:
1. 以管理员身份运行命令提示符
2. 检查项目目录的写权限
3. 临时关闭杀毒软件的实时保护

### 问题 5: 中文乱码

**解决方案**:
```cmd
chcp 65001
set PYTHONIOENCODING=utf-8
```

## 🔍 故障排除工具

运行 Windows 故障排除脚本：
```cmd
scripts\windows-troubleshoot.bat
```

该脚本会自动检查：
- 系统环境
- 依赖安装状态
- 端口占用情况
- 权限问题
- 常见配置问题

## 📁 Windows 特定文件位置

- **配置文件**: `项目根目录\config.json`
- **ChromaDB 数据**: `项目根目录\chromadbdata`
- **对话数据**: `项目根目录\data\conversations.db`
- **日志文件**: `项目根目录\logs`
- **虚拟环境**: `项目根目录\.venv`

## 🎯 性能优化建议

1. **关闭 Windows Defender 实时保护**（临时）
2. **增加虚拟内存**（如果物理内存不足）
3. **使用 SSD 存储**（提高 I/O 性能）
4. **关闭不必要的后台程序**

## 📞 获取帮助

如果遇到问题：

1. 首先运行故障排除脚本
2. 查看日志文件
3. 检查 GitHub Issues
4. 提交新的 Issue（包含系统信息和错误日志）

## 🔄 更新指南

更新到新版本：

1. 备份配置文件和数据
2. 拉取最新代码
3. 重新运行部署脚本：
   ```cmd
   python deploy.py
   ```
4. 恢复配置文件（如需要）

---

**注意**: 本指南针对 Windows 平台优化，如果在其他平台使用，请参考主要的 README.md 文档。
