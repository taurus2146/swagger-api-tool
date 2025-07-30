# Swagger API 测试工具

一个基于 PyQt5 的图形化 Swagger API 测试工具，支持从 Swagger 文档自动生成测试用例，提供直观的界面进行 API 测试。

## 功能特性

### 🚀 核心功能
- **Swagger 文档解析**：支持从 URL 或本地文件加载 Swagger/OpenAPI 文档
- **自动化测试**：根据 Swagger 定义自动生成 API 测试用例
- **参数编辑器**：智能参数编辑，支持多种数据类型
- **认证管理**：目前支持的认证方式（Bearer Token）
- **测试结果展示**：详细的测试结果展示和历史记录
- **数据生成**：自动生成测试数据，支持 Faker 库

### 🎨 界面特性
- **现代化 UI**：基于 PyQt5 的现代化界面设计
- **主题支持**：支持多种主题切换
- **响应式布局**：自适应窗口大小的布局设计
- **图标系统**：内置图标生成器，提供美观的应用图标

### 🔧 技术特性
- **多线程测试**：异步执行 API 测试，不阻塞界面
- **配置管理**：支持认证配置的保存和加载
- **日志系统**：完整的日志记录和错误处理
- **扩展性**：模块化设计，易于扩展新功能

## 项目结构

```
├── assets/                 # 资源文件
│   ├── app_icon.png       # 应用图标
│   └── app_icon.svg       # 矢量图标
├── config/                # 配置文件
│   ├── auth_config.json   # 认证配置
│   └── test_history.json  # 测试历史
├── core/                  # 核心模块
│   ├── api_tester.py      # API 测试执行器
│   ├── auth_manager.py    # 认证管理器
│   ├── data_generator.py  # 测试数据生成器
│   └── swagger_parser.py  # Swagger 文档解析器
├── gui/                   # 图形界面模块
│   ├── main_window.py     # 主窗口
│   ├── api_list_widget.py # API 列表组件
│   ├── api_param_editor.py # 参数编辑器
│   ├── test_result_widget.py # 测试结果组件
│   ├── auth_config_dialog.py # 认证配置对话框
│   ├── theme_manager.py   # 主题管理器
│   └── styles.py          # 样式定义
├── models/                # 数据模型
├── tests/                 # 测试文件
├── utils/                 # 工具模块
├── main.py               # 程序入口
└── requirements.txt      # 依赖列表
```

## 安装和使用

### 环境要求

- Python 3.7+
- PyQt5
- 其他依赖见 `requirements.txt`

### 安装步骤

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd swagger-api-tester
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **运行程序**
   ```bash
   python main.py
   ```

### 使用指南

#### 1. 加载 Swagger 文档
- 点击"加载 Swagger"按钮
- 输入 Swagger 文档的 URL 或选择本地文件
- 程序会自动解析并显示所有可用的 API 接口

#### 2. 配置认证
- 点击"认证配置"按钮
- 选择适合的认证方式：
  - **Bearer Token**：JWT 或其他 Bearer 令牌


#### 3. 编辑测试参数
- 在左侧 API 列表中选择要测试的接口
- 在参数编辑器中修改请求参数
- 支持自动生成测试数据或手动输入

#### 4. 执行测试
- 点击"测试"按钮执行单个 API 测试
- 或使用"批量测试"功能测试多个接口
- 测试结果会实时显示在右侧面板

#### 5. 查看结果
- 测试结果包括：
  - HTTP 状态码
  - 响应时间
  - 响应头信息
  - 响应体内容
  - 错误信息（如有）

## 主要依赖

| 依赖包 | 版本 | 用途 |
|--------|------|------|
| PyQt5 | 5.15.9 | GUI 框架 |
| requests | 2.28.2 | HTTP 请求 |
| PyYAML | 6.0 | YAML 文件解析 |
| swagger-parser | 1.0.3 | Swagger 文档解析 |
| jsonschema | 4.17.3 | JSON 模式验证 |
| faker | 18.7.0 | 测试数据生成 |
| pytest | 7.3.1 | 单元测试 |

## 开发说明

### 代码结构

- **core/**：核心业务逻辑，包括 API 测试、认证管理、数据解析等
- **gui/**：图形界面组件，采用 MVC 模式设计
- **models/**：数据模型定义
- **utils/**：通用工具函数

### 扩展开发

1. **添加新的认证方式**：在 `AuthManager` 类中添加新的认证方法
2. **自定义主题**：在 `theme_manager.py` 中添加新的主题配置
3. **扩展数据生成器**：在 `DataGenerator` 中添加新的数据生成规则
4. **添加新的测试功能**：继承 `ApiTester` 类实现特定的测试逻辑

### 测试

运行单元测试：
```bash
pytest tests/
```

生成测试报告：
```bash
pytest --html=report.html tests/
```

## 贡献指南

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 更新日志

### v1.0.0
- 初始版本发布
- 支持基本的 Swagger 文档解析和 API 测试
- 实现图形化界面和认证管理
- 添加主题支持和数据生成功能

---

**注意**：本工具仅用于 API 测试和开发调试。