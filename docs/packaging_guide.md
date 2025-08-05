# 打包和分发指南

## 📦 打包选项

本项目提供三种打包方式，满足不同的使用场景：

### 1. 目录版本（推荐用于开发）
- **配置文件**: `build_simple.spec`
- **输出**: `dist/SwaggerAPITester/` 目录
- **大小**: 约 50-80 MB
- **启动速度**: 快
- **便携性**: 需要整个目录

**使用场景**:
- 开发和测试
- 本地使用
- 对启动速度有要求

### 2. 单文件版本（推荐用于分发）
- **配置文件**: `build_onefile.spec`
- **输出**: `dist/SwaggerAPITester.exe`
- **大小**: 约 206 MB
- **启动速度**: 首次较慢，后续正常
- **便携性**: 完全便携

**使用场景**:
- 发送给用户
- USB 驱动器运行
- 无需安装的场景
- 快速分发

### 3. 安装包版本（推荐用于正式发布）
- **工具**: Inno Setup 或 NSIS
- **输出**: `.exe` 安装程序
- **功能**: 桌面快捷方式、卸载程序
- **体验**: 专业安装体验

**使用场景**:
- 正式软件发布
- 企业环境部署
- 需要系统集成

## 🛠️ 构建方法

### 方法 1: 使用本地构建工具（推荐）

```bash
python scripts/build_local.py
```

选择构建选项：
1. 目录版本
2. 单文件版本
3. 构建两个版本
4. 清理构建目录

### 方法 2: 手动构建

```bash
# 目录版本
pyinstaller build_simple.spec --clean

# 单文件版本
pyinstaller build_onefile.spec --clean
```

### 方法 3: GitHub Actions 自动构建

推送标签触发自动构建：
```bash
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

## 📋 构建要求

### 系统要求
- Python 3.9+
- PyInstaller 6.0+
- PyQt5 5.15.9

### 依赖安装
```bash
pip install -r requirements.txt
pip install pyinstaller pillow
pip install pyinstaller-hooks-contrib
```

## 🔧 配置说明

### PyQt5 配置要点
1. **collect_all('PyQt5')**: 自动收集所有 PyQt5 组件
2. **hookspath=['hooks']**: 使用自定义 hooks
3. **完整隐藏导入**: 包含 sip、cryptography 等
4. **二进制文件收集**: 确保运行时依赖完整

### 关键差异

| 配置项 | 目录版本 | 单文件版本 |
|--------|----------|------------|
| exclude_binaries | True | False |
| 输出结构 | COLLECT | EXE only |
| 启动方式 | 解压到临时目录 | 直接运行 |

## 🚀 分发建议

### 给最终用户
1. **首选**: 单文件版本 (`SwaggerAPITester.exe`)
   - 下载即用，无需安装
   - 可以放在任意位置运行

2. **备选**: 安装包版本
   - 专业安装体验
   - 自动创建快捷方式

### 给开发者
1. **开发**: 目录版本
   - 启动速度快
   - 便于调试

2. **测试**: 两个版本都测试
   - 确保功能一致性

## 📊 性能对比

| 指标 | 目录版本 | 单文件版本 |
|------|----------|------------|
| 文件大小 | 50-80 MB | 206 MB |
| 首次启动 | 2-3 秒 | 5-8 秒 |
| 后续启动 | 2-3 秒 | 2-3 秒 |
| 磁盘占用 | 分散文件 | 单个文件 |
| 便携性 | 低 | 高 |

## 🔍 故障排除

### 常见问题

1. **PyQt5 模块缺失**
   - 确保使用正确的 spec 文件
   - 检查 hooks 配置

2. **文件过大**
   - 检查 excludes 配置
   - 移除不必要的依赖

3. **启动缓慢**
   - 单文件版本首次启动需要解压
   - 考虑使用目录版本

### 调试方法

1. **查看构建日志**
   ```bash
   pyinstaller build_onefile.spec --clean --log-level DEBUG
   ```

2. **测试导入**
   ```bash
   python -c "import PyQt5.QtCore; print('OK')"
   ```

3. **验证构建**
   ```bash
   python scripts/verify_pyqt5_build.py
   ```

## 📝 最佳实践

1. **构建前准备**
   - 清理之前的构建
   - 验证依赖安装
   - 生成应用图标

2. **测试流程**
   - 本地测试两个版本
   - 在不同环境测试
   - 验证功能完整性

3. **发布流程**
   - 使用语义化版本号
   - 提供详细的发布说明
   - 同时提供多种版本

## 🔗 相关文档

- [部署指南](../DEPLOYMENT.md)
- [构建配置](../build_simple.spec)
- [单文件配置](../build_onefile.spec)
- [GitHub Actions](.github/workflows/build-release.yml)
