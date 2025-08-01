# 部署和发布指南

## 🚀 自动化构建和发布流程

本项目使用 GitHub Actions 实现完全自动化的构建和发布流程。

### 工作流程概述

1. **开发阶段**：在本地开发和测试
2. **提交代码**：推送到 GitHub 触发测试构建
3. **创建标签**：创建版本标签触发正式构建
4. **自动发布**：GitHub Actions 自动构建并发布可执行文件

## 📋 文件说明

### GitHub Actions 工作流

- `.github/workflows/test-build.yml` - 测试构建（每次推送代码时）
- `.github/workflows/build-release.yml` - 正式构建和发布（创建标签时）

### 构建配置

- `build.spec` - PyInstaller 构建配置文件
- `build_local.py` - 本地构建测试脚本
- `create_icon.py` - 图标生成脚本

### 发布管理

- `release.py` - 版本发布脚本
- `version.py` - 版本信息管理
- `release_notes_template.md` - 发布说明模板

## 🛠️ 本地开发和测试

### 1. 环境准备

```bash
# 克隆项目
git clone <your-repo-url>
cd swagger-api-tester

# 安装依赖
pip install -r requirements.txt

# 安装构建工具
pip install pyinstaller pillow
```

### 2. 本地测试构建

```bash
# 一键构建（推荐）
python build_local.py

# 或者分步执行：
# 1. 生成图标文件
python create_icon.py

# 2. 手动构建
pyinstaller build.spec --clean

# 3. 测试构建结果
python test_build.py
```

### 3. 测试可执行文件

```bash
# Windows
cd dist/SwaggerAPITester
SwaggerAPITester.exe

# Linux
cd dist/SwaggerAPITester
./SwaggerAPITester
```

## 🏷️ 版本发布流程

### 方法一：使用发布脚本（推荐）

```bash
# 运行发布脚本
python release.py

# 脚本会引导你完成：
# 1. 检查工作目录状态
# 2. 输入新版本号
# 3. 创建并推送标签
# 4. 生成发布说明
```

### 方法二：手动发布

```bash
# 1. 确保所有更改已提交
git status

# 2. 创建版本标签
git tag -a v1.0.0 -m "Release v1.0.0"

# 3. 推送标签
git push origin v1.0.0

# 4. GitHub Actions 会自动开始构建
```

## 📦 构建产物

### Windows 版本
- 文件名：`SwaggerAPITester-windows.zip`
- 包含：完整的可执行文件和依赖库
- 支持：Windows 10/11 64位

### Linux 版本
- 文件名：`SwaggerAPITester-linux.tar.gz`
- 包含：完整的可执行文件和依赖库
- 支持：Ubuntu 18.04+ / CentOS 7+

## 🔧 构建配置详解

### PyInstaller 配置 (build.spec)

```python
# 主要配置项
- console=False          # 隐藏控制台窗口
- upx=True              # 启用UPX压缩
- icon='assets/icon.ico' # 应用图标
- name='SwaggerAPITester' # 可执行文件名
```

### 包含的文件和目录

- `templates/` - 模板文件
- `config/` - 配置文件
- `assets/` - 资源文件
- 所有Python依赖库

## 🚨 故障排除

### 构建失败

1. **检查依赖**：确保 requirements.txt 包含所有必要依赖
2. **检查路径**：确保所有文件路径在 build.spec 中正确配置
3. **查看日志**：在 GitHub Actions 页面查看详细构建日志
4. **本地测试**：使用 `python build_local.py` 在本地测试构建
5. **图标问题**：如果图标创建失败，会自动使用默认图标

### 可执行文件问题

1. **缺少依赖**：检查 hiddenimports 配置
2. **文件缺失**：检查 datas 配置
3. **权限问题**：Linux 下确保文件有执行权限

### 发布问题

1. **标签冲突**：确保版本标签唯一
2. **权限不足**：检查 GitHub Token 权限
3. **文件上传失败**：检查文件大小和网络连接

## 📊 监控和维护

### 构建状态监控

- 访问 GitHub Actions 页面查看构建状态
- 设置邮件通知获取构建结果
- 使用 README 中的状态徽章显示构建状态

### 版本管理

- 使用语义化版本号 (v1.0.0)
- 维护 CHANGELOG.md 记录版本变更
- 定期清理旧的构建产物

### 用户反馈

- 通过 GitHub Issues 收集用户反馈
- 监控下载统计和使用情况
- 及时修复发现的问题

## 🔄 持续改进

### 构建优化

- 定期更新依赖版本
- 优化可执行文件大小
- 改进构建速度

### 功能扩展

- 支持更多操作系统
- 添加自动更新功能
- 集成错误报告系统

---

**注意**：首次设置时，请确保在 GitHub 仓库设置中启用 Actions 功能，并检查相关权限配置。