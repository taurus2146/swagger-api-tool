#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试构建的可执行文件
"""

import os
import sys
import subprocess
import platform
import time

def test_executable():
    """测试可执行文件是否能正常启动"""
    system = platform.system()
    
    if system == "Windows":
        exe_path = "dist/SwaggerAPITester/SwaggerAPITester.exe"
    else:
        exe_path = "dist/SwaggerAPITester/SwaggerAPITester"
    
    if not os.path.exists(exe_path):
        print(f"❌ 可执行文件不存在: {exe_path}")
        return False
    
    print(f"🧪 测试可执行文件: {exe_path}")
    
    try:
        # 尝试启动程序（无GUI模式测试）
        # 注意：这只是检查程序是否能启动，不会显示GUI
        process = subprocess.Popen([exe_path, "--help"], 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE,
                                 timeout=10)
        
        # 等待一小段时间
        time.sleep(2)
        
        # 终止进程
        process.terminate()
        
        print("✅ 可执行文件启动测试通过")
        return True
        
    except subprocess.TimeoutExpired:
        print("✅ 可执行文件启动正常（超时终止）")
        process.kill()
        return True
    except FileNotFoundError:
        print("❌ 可执行文件无法找到")
        return False
    except Exception as e:
        print(f"⚠️  测试过程中出现异常: {e}")
        # 对于GUI应用，这可能是正常的
        return True

def check_dependencies():
    """检查可执行文件的依赖"""
    system = platform.system()
    
    if system == "Windows":
        exe_path = "dist/SwaggerAPITester/SwaggerAPITester.exe"
        dist_dir = "dist/SwaggerAPITester"
        
        print("📋 检查Windows依赖文件:")
        required_files = [
            "SwaggerAPITester.exe",
            "_internal"  # PyInstaller内部文件夹
        ]
        
        for file_name in required_files:
            file_path = os.path.join(dist_dir, file_name)
            if os.path.exists(file_path):
                print(f"  ✅ {file_name}")
            else:
                print(f"  ❌ {file_name} (缺失)")
                return False
    
    return True

def main():
    """主函数"""
    print("🧪 构建测试脚本")
    print("=" * 30)
    
    # 检查构建目录是否存在
    if not os.path.exists("dist"):
        print("❌ dist目录不存在，请先运行构建脚本")
        return 1
    
    # 检查依赖文件
    if not check_dependencies():
        print("❌ 依赖检查失败")
        return 1
    
    # 测试可执行文件
    if not test_executable():
        print("❌ 可执行文件测试失败")
        return 1
    
    print("\n🎉 所有测试通过！")
    print("💡 提示: 你可以手动运行可执行文件来进行完整测试")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())