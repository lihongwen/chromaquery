#!/usr/bin/env python3
"""
ChromaDB Web Manager 启动脚本
跨平台一键启动前后端服务
"""

import os
import sys
import subprocess
import platform
import time
import signal
import webbrowser
import threading
from pathlib import Path
from typing import Optional, List


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
    END = '\033[0m'


class ServiceManager:
    """服务管理器"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.absolute()
        self.is_windows = platform.system().lower() == "windows"
        self.venv_path = self.project_root / ".venv"
        self.backend_process: Optional[subprocess.Popen] = None
        self.frontend_process: Optional[subprocess.Popen] = None
        self.services_running = False
        
        # 设置信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        if not self.is_windows:
            signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        print(f"\n{Colors.YELLOW}接收到停止信号，正在关闭服务...{Colors.END}")
        self.stop_services()
        sys.exit(0)
    
    def print_info(self, message: str):
        """打印信息"""
        print(f"{Colors.CYAN}[INFO]{Colors.END} {message}")
    
    def print_success(self, message: str):
        """打印成功信息"""
        print(f"{Colors.GREEN}[SUCCESS]{Colors.END} {message}")
    
    def print_error(self, message: str):
        """打印错误信息"""
        print(f"{Colors.RED}[ERROR]{Colors.END} {message}")
    
    def print_warning(self, message: str):
        """打印警告信息"""
        print(f"{Colors.YELLOW}[WARNING]{Colors.END} {message}")
    
    def check_environment(self) -> bool:
        """检查环境"""
        self.print_info("检查运行环境...")
        
        # 检查虚拟环境
        if not self.venv_path.exists():
            self.print_error("虚拟环境不存在，请先运行 python deploy.py")
            return False
        
        # 检查配置文件
        config_file = self.project_root / "config.json"
        if not config_file.exists():
            self.print_error("配置文件不存在，请先运行 python deploy.py")
            return False
        
        # 检查前端依赖
        frontend_node_modules = self.project_root / "frontend" / "node_modules"
        if not frontend_node_modules.exists():
            self.print_error("前端依赖未安装，请先运行 python deploy.py")
            return False
        
        self.print_success("环境检查通过")
        return True
    
    def get_venv_python(self) -> Path:
        """获取虚拟环境中的 Python 路径"""
        if self.is_windows:
            return self.venv_path / "Scripts" / "python.exe"
        else:
            return self.venv_path / "bin" / "python3"
    
    def start_backend(self) -> bool:
        """启动后端服务"""
        self.print_info("启动后端服务...")

        try:
            python_path = self.get_venv_python()
            backend_script = self.project_root / "backend" / "main.py"

            if not python_path.exists():
                self.print_error(f"Python 可执行文件不存在: {python_path}")
                return False

            if not backend_script.exists():
                self.print_error(f"后端脚本不存在: {backend_script}")
                return False

            # 设置环境变量
            env = os.environ.copy()
            env["PYTHONPATH"] = str(self.project_root / "backend")
            env["PYTHONUNBUFFERED"] = "1"

            # Windows特殊处理：设置编码
            if self.is_windows:
                env["PYTHONIOENCODING"] = "utf-8"
                env["PYTHONUTF8"] = "1"

            # 启动后端进程
            startup_info = None
            if self.is_windows:
                # Windows下隐藏控制台窗口
                startup_info = subprocess.STARTUPINFO()
                startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startup_info.wShowWindow = subprocess.SW_HIDE

            self.backend_process = subprocess.Popen(
                [str(python_path), str(backend_script)],
                cwd=self.project_root,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                startupinfo=startup_info,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if self.is_windows else 0
            )

            # 等待后端启动
            time.sleep(3)

            if self.backend_process.poll() is None:
                self.print_success("后端服务启动成功 (http://localhost:8000)")
                return True
            else:
                stdout, stderr = self.backend_process.communicate()
                self.print_error("后端服务启动失败")
                if stderr:
                    self.print_error(f"错误信息: {stderr}")
                if stdout:
                    self.print_info(f"输出信息: {stdout}")
                return False

        except Exception as e:
            self.print_error(f"启动后端服务时发生错误: {e}")
            return False
    
    def start_frontend(self) -> bool:
        """启动前端服务"""
        self.print_info("启动前端服务...")

        try:
            frontend_dir = self.project_root / "frontend"

            # Windows下使用npm.cmd
            npm_cmd = "npm.cmd" if self.is_windows else "npm"

            # 设置环境变量
            env = os.environ.copy()
            if self.is_windows:
                env["NODE_OPTIONS"] = "--max-old-space-size=4096"

            # 启动前端开发服务器
            startup_info = None
            if self.is_windows:
                # Windows下隐藏控制台窗口
                startup_info = subprocess.STARTUPINFO()
                startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startup_info.wShowWindow = subprocess.SW_HIDE

            self.frontend_process = subprocess.Popen(
                [npm_cmd, "run", "dev"],
                cwd=frontend_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                startupinfo=startup_info,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if self.is_windows else 0
            )

            # 等待前端启动
            time.sleep(5)

            if self.frontend_process.poll() is None:
                self.print_success("前端服务启动成功 (http://localhost:5173)")
                return True
            else:
                stdout, stderr = self.frontend_process.communicate()
                self.print_error("前端服务启动失败")
                if stderr:
                    self.print_error(f"错误信息: {stderr}")
                if stdout:
                    self.print_info(f"输出信息: {stdout}")
                return False

        except Exception as e:
            self.print_error(f"启动前端服务时发生错误: {e}")
            return False
    
    def open_browser(self):
        """打开浏览器"""
        def _open():
            time.sleep(8)  # 等待服务完全启动
            try:
                webbrowser.open("http://localhost:5173")
                self.print_success("已在浏览器中打开应用")
            except Exception as e:
                self.print_warning(f"无法自动打开浏览器: {e}")
        
        threading.Thread(target=_open, daemon=True).start()
    
    def stop_services(self):
        """停止所有服务"""
        if not self.services_running:
            return

        self.print_info("正在停止服务...")

        # 停止后端服务
        if self.backend_process and self.backend_process.poll() is None:
            try:
                if self.is_windows:
                    # Windows下发送CTRL_BREAK_EVENT信号
                    self.backend_process.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    self.backend_process.terminate()

                self.backend_process.wait(timeout=5)
                self.print_success("后端服务已停止")
            except subprocess.TimeoutExpired:
                try:
                    self.backend_process.kill()
                    self.backend_process.wait(timeout=3)
                    self.print_warning("强制终止后端服务")
                except Exception as e:
                    self.print_error(f"强制终止后端服务失败: {e}")
            except Exception as e:
                self.print_error(f"停止后端服务时发生错误: {e}")

        # 停止前端服务
        if self.frontend_process and self.frontend_process.poll() is None:
            try:
                if self.is_windows:
                    # Windows下发送CTRL_BREAK_EVENT信号
                    self.frontend_process.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    self.frontend_process.terminate()

                self.frontend_process.wait(timeout=5)
                self.print_success("前端服务已停止")
            except subprocess.TimeoutExpired:
                try:
                    self.frontend_process.kill()
                    self.frontend_process.wait(timeout=3)
                    self.print_warning("强制终止前端服务")
                except Exception as e:
                    self.print_error(f"强制终止前端服务失败: {e}")
            except Exception as e:
                self.print_error(f"停止前端服务时发生错误: {e}")

        self.services_running = False

    def monitor_services(self):
        """监控服务状态"""
        while self.services_running:
            try:
                # 检查后端服务
                if self.backend_process and self.backend_process.poll() is not None:
                    self.print_error("后端服务意外停止")
                    self.services_running = False
                    break

                # 检查前端服务
                if self.frontend_process and self.frontend_process.poll() is not None:
                    self.print_error("前端服务意外停止")
                    self.services_running = False
                    break

                time.sleep(2)

            except Exception as e:
                self.print_error(f"监控服务时发生错误: {e}")
                break

    def start_services(self) -> bool:
        """启动所有服务"""
        print(f"{Colors.BOLD}{Colors.BLUE}ChromaDB Web Manager 启动器{Colors.END}")
        print(f"{Colors.BLUE}平台: {platform.system()} {platform.release()}{Colors.END}")
        print()

        # 检查环境
        if not self.check_environment():
            return False

        # 启动后端服务
        if not self.start_backend():
            return False

        # 启动前端服务
        if not self.start_frontend():
            self.stop_services()
            return False

        self.services_running = True

        # 打开浏览器
        self.open_browser()

        # 显示服务信息
        print()
        print(f"{Colors.BOLD}服务已启动:{Colors.END}")
        print(f"- 前端界面: {Colors.CYAN}http://localhost:5173{Colors.END}")
        print(f"- 后端API: {Colors.CYAN}http://localhost:8000{Colors.END}")
        print(f"- API文档: {Colors.CYAN}http://localhost:8000/docs{Colors.END}")
        print()
        print(f"{Colors.YELLOW}按 Ctrl+C 停止服务{Colors.END}")
        print()

        # 监控服务
        try:
            self.monitor_services()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop_services()

        return True


def main():
    """主函数"""
    try:
        service_manager = ServiceManager()
        success = service_manager.start_services()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}服务被用户停止{Colors.END}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.RED}启动过程中发生错误: {e}{Colors.END}")
        sys.exit(1)


if __name__ == "__main__":
    main()
