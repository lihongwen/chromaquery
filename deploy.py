#!/usr/bin/env python3
"""
ChromaDB Web Manager 部署脚本
跨平台自动化环境设置和依赖安装
"""

import os
import sys
import subprocess
import platform
import shutil
import json
from pathlib import Path
from typing import Optional, List, Union


class Colors:
    """终端颜色"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


class DeployManager:
    """部署管理器"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.absolute()
        self.is_windows = platform.system().lower() == "windows"
        self.python_cmd = "python" if self.is_windows else "python3"
        self.venv_path = self.project_root / ".venv"
        self.venv_activate = self._get_venv_activate_path()
    
    def _get_venv_activate_path(self) -> Path:
        """获取虚拟环境激活脚本路径"""
        if self.is_windows:
            return self.venv_path / "Scripts" / "activate.bat"
        else:
            return self.venv_path / "bin" / "activate"
    
    def print_step(self, step: str, message: str):
        """打印步骤信息"""
        print(f"{Colors.CYAN}{Colors.BOLD}[{step}]{Colors.END} {message}")
    
    def print_success(self, message: str):
        """打印成功信息"""
        print(f"{Colors.GREEN}✓{Colors.END} {message}")
    
    def print_error(self, message: str):
        """打印错误信息"""
        print(f"{Colors.RED}✗{Colors.END} {message}")
    
    def print_warning(self, message: str):
        """打印警告信息"""
        print(f"{Colors.YELLOW}⚠{Colors.END} {message}")
    
    def run_command(self, cmd: Union[List[str], str], cwd: Optional[Path] = None, check: bool = True, shell: bool = False) -> subprocess.CompletedProcess:
        """运行命令"""
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd or self.project_root,
                check=check,
                capture_output=True,
                text=True,
                shell=shell
            )
            return result
        except subprocess.CalledProcessError as e:
            self.print_error(f"命令执行失败: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
            self.print_error(f"错误信息: {e.stderr}")
            raise
    
    def check_prerequisites(self) -> bool:
        """检查前置条件"""
        self.print_step("1/7", "检查前置条件")
        
        # 检查 Python 版本
        try:
            result = self.run_command([self.python_cmd, "--version"])
            python_version = result.stdout.strip()
            self.print_success(f"Python 版本: {python_version}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.print_error("Python 未安装或不在 PATH 中")
            return False
        
        # 检查 uv 包管理器
        try:
            result = self.run_command(["uv", "--version"])
            uv_version = result.stdout.strip()
            self.print_success(f"uv 版本: {uv_version}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.print_warning("uv 未安装，将使用 pip 作为备选")
        
        # 检查 Node.js
        try:
            result = self.run_command(["node", "--version"])
            node_version = result.stdout.strip()
            self.print_success(f"Node.js 版本: {node_version}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.print_error("Node.js 未安装或不在 PATH 中")
            return False
        
        # 检查 npm
        try:
            if self.is_windows:
                # Windows 下 npm 是 .cmd 文件，需要使用 shell=True
                result = self.run_command("npm --version", shell=True)
            else:
                result = self.run_command(["npm", "--version"])
            npm_version = result.stdout.strip()
            self.print_success(f"npm 版本: {npm_version}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.print_error("npm 未安装或不在 PATH 中")
            return False
        
        return True
    
    def create_virtual_environment(self) -> bool:
        """创建虚拟环境"""
        self.print_step("2/7", "创建 Python 虚拟环境")
        
        if self.venv_path.exists():
            self.print_warning("虚拟环境已存在，跳过创建")
            return True
        
        try:
            # 优先使用 uv
            try:
                self.run_command(["uv", "venv", str(self.venv_path)])
                self.print_success("使用 uv 创建虚拟环境成功")
            except (subprocess.CalledProcessError, FileNotFoundError):
                # 备选使用 python -m venv
                self.run_command([self.python_cmd, "-m", "venv", str(self.venv_path)])
                self.print_success("使用 venv 创建虚拟环境成功")
            
            return True
        except subprocess.CalledProcessError:
            self.print_error("创建虚拟环境失败")
            return False
    
    def install_python_dependencies(self) -> bool:
        """安装 Python 依赖"""
        self.print_step("3/7", "安装 Python 依赖")
        
        requirements_file = self.project_root / "backend" / "requirements.txt"
        if not requirements_file.exists():
            self.print_error("requirements.txt 文件不存在")
            return False
        
        try:
            # 获取虚拟环境中的 Python 和 pip 路径
            if self.is_windows:
                venv_python = self.venv_path / "Scripts" / "python.exe"
                venv_pip = self.venv_path / "Scripts" / "pip.exe"
            else:
                venv_python = self.venv_path / "bin" / "python"
                venv_pip = self.venv_path / "bin" / "pip"
            
            # 优先使用 uv
            try:
                self.run_command([
                    "uv", "pip", "install", 
                    "-i", "https://pypi.tuna.tsinghua.edu.cn/simple",
                    "-r", str(requirements_file)
                ], cwd=self.venv_path)
                self.print_success("使用 uv 安装 Python 依赖成功")
            except (subprocess.CalledProcessError, FileNotFoundError):
                # 备选使用 pip
                self.run_command([
                    str(venv_pip), "install",
                    "-i", "https://pypi.tuna.tsinghua.edu.cn/simple",
                    "-r", str(requirements_file)
                ])
                self.print_success("使用 pip 安装 Python 依赖成功")
            
            return True
        except subprocess.CalledProcessError:
            self.print_error("安装 Python 依赖失败")
            return False
    
    def install_frontend_dependencies(self) -> bool:
        """安装前端依赖"""
        self.print_step("4/7", "安装前端依赖")
        
        frontend_dir = self.project_root / "frontend"
        package_json = frontend_dir / "package.json"
        
        if not package_json.exists():
            self.print_error("frontend/package.json 文件不存在")
            return False
        
        try:
            if self.is_windows:
                # Windows 下 npm 是 .cmd 文件，需要使用 shell=True
                self.run_command("npm install", cwd=frontend_dir, shell=True)
            else:
                self.run_command(["npm", "install"], cwd=frontend_dir)
            self.print_success("安装前端依赖成功")
            return True
        except subprocess.CalledProcessError:
            self.print_error("安装前端依赖失败")
            return False

    def initialize_configuration(self) -> bool:
        """初始化配置文件"""
        self.print_step("5/7", "初始化配置文件")

        config_file = self.project_root / "config.json"
        config_template = self.project_root / "config.template.json"

        if config_file.exists():
            self.print_warning("配置文件已存在，跳过初始化")
            return True

        if not config_template.exists():
            self.print_error("配置模板文件不存在")
            return False

        try:
            # 读取模板配置
            with open(config_template, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # 设置默认路径
            chroma_data_path = self.project_root / "chromadbdata"
            config["chroma_db_path"] = str(chroma_data_path.absolute())
            config["path_history"] = [str(chroma_data_path.absolute())]
            config["last_updated"] = ""

            # 保存配置文件
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            self.print_success("配置文件初始化成功")
            return True
        except Exception as e:
            self.print_error(f"初始化配置文件失败: {e}")
            return False

    def prepare_data_directories(self) -> bool:
        """准备数据目录"""
        self.print_step("6/7", "准备数据目录")

        directories = [
            self.project_root / "chromadbdata",
            self.project_root / "data"
        ]

        try:
            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)
                self.print_success(f"创建目录: {directory}")

            return True
        except Exception as e:
            self.print_error(f"创建数据目录失败: {e}")
            return False

    def create_environment_files(self) -> bool:
        """创建环境变量文件"""
        self.print_step("7/7", "创建环境变量文件")

        # 后端环境文件
        backend_env = self.project_root / "backend" / ".env"
        if not backend_env.exists():
            env_content = """# ChromaDB Web Manager 后端环境变量

# 阿里云DashScope API密钥 - 用于LLM功能
DASHSCOPE_API_KEY=your_dashscope_api_key_here

# ChromaDB配置
CHROMA_HOST=localhost
CHROMA_PORT=8000

# FastAPI配置
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=true

# 日志级别
LOG_LEVEL=INFO

# CORS配置
CORS_ORIGINS=["http://localhost:3000", "http://localhost:5173"]
"""
            try:
                with open(backend_env, 'w', encoding='utf-8') as f:
                    f.write(env_content)
                self.print_success("创建后端环境文件成功")
            except Exception as e:
                self.print_error(f"创建后端环境文件失败: {e}")
                return False

        # 前端环境文件
        frontend_env = self.project_root / "frontend" / ".env"
        if not frontend_env.exists():
            env_content = """# ChromaDB Web Manager 前端环境变量

# API基础URL - 开发环境
VITE_API_BASE_URL=http://localhost:8000/api

# 应用标题
VITE_APP_TITLE=ChromaDB Web Manager

# 是否启用开发模式调试
VITE_DEBUG=true
"""
            try:
                with open(frontend_env, 'w', encoding='utf-8') as f:
                    f.write(env_content)
                self.print_success("创建前端环境文件成功")
            except Exception as e:
                self.print_error(f"创建前端环境文件失败: {e}")
                return False

        return True

    def deploy(self) -> bool:
        """执行完整部署"""
        print(f"{Colors.BOLD}{Colors.BLUE}ChromaDB Web Manager 部署脚本{Colors.END}")
        print(f"{Colors.BLUE}平台: {platform.system()} {platform.release()}{Colors.END}")
        print()

        steps = [
            self.check_prerequisites,
            self.create_virtual_environment,
            self.install_python_dependencies,
            self.install_frontend_dependencies,
            self.initialize_configuration,
            self.prepare_data_directories,
            self.create_environment_files
        ]

        for step in steps:
            if not step():
                self.print_error("部署失败")
                return False
            print()

        self.print_success("部署完成！")
        print()
        print(f"{Colors.BOLD}下一步:{Colors.END}")
        print(f"1. 运行 {Colors.GREEN}python start.py{Colors.END} 启动应用")
        print(f"2. 或者分别启动前后端服务:")
        print(f"   - 后端: {Colors.GREEN}python backend/main.py{Colors.END}")
        print(f"   - 前端: {Colors.GREEN}cd frontend && npm run dev{Colors.END}")
        print()
        print(f"{Colors.BOLD}访问地址:{Colors.END}")
        print(f"- 前端界面: {Colors.CYAN}http://localhost:5173{Colors.END}")
        print(f"- 后端API: {Colors.CYAN}http://localhost:8000{Colors.END}")
        print(f"- API文档: {Colors.CYAN}http://localhost:8000/docs{Colors.END}")

        return True


def main():
    """主函数"""
    try:
        deploy_manager = DeployManager()
        success = deploy_manager.deploy()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}部署被用户中断{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}部署过程中发生错误: {e}{Colors.END}")
        sys.exit(1)


if __name__ == "__main__":
    main()
