# FJNote 助手插件

为 Blinko 笔记服务开发的高质量 AstrBot (QQ) 插件，提供流畅的闪念记录和 ToDo 管理功能。

## 🚀 快速开始

### 🧪 本地测试
```bash
# 交互式测试 (推荐)
python3 run.py

# 输入示例:
# 今天学了新知识 #学习     → 闪念记录
# #todo 完成项目 #工作      → 添加待办  
# #list                   → 查看待办列表
# #find 关键词             → 搜索
# #tags                   → 查看标签
```

### 🚁 部署使用
1. 将整个插件目录复制到 `AstrBot/data/plugins/`
2. 在 AstrBot WebUI 中配置 Blinko 连接信息
3. 重启插件即可使用

## 📁 项目结构

```
fjnote_plugin/
├── fjnote/                 # 核心包
│   ├── core/              # 核心领域模型
│   ├── services/          # 服务层 (Blinko API 客户端)
│   ├── strategies/        # 策略层 (笔记策略)
│   ├── handlers/          # 处理器层 (命令处理器)
│   └── utils/             # 工具层 (会话管理等)
├── main.py                # 主插件文件 (228行)
├── run.py                 # 交互式测试工具
├── _conf_schema.json      # 配置模式定义
├── requirements.txt       # 依赖文件
├── metadata.yaml          # 插件元数据
└── README.md             # 项目说明
```

## 🏗️ 架构设计

### 设计模式应用
- **策略模式**: `FlashNoteStrategy` / `TodoNoteStrategy` - 不同类型笔记处理
- **工厂模式**: `CommandFactory` - 动态创建命令处理器
- **观察者模式**: `SessionManager` - 会话超时事件监听
- **仓储模式**: `BlinkoApiClient` - 数据访问层抽象
- **模板方法**: `ITemplateRenderer` - 统一模板渲染接口

### 核心特性
- ⚡ **闪念记录**: 30秒内连续消息自动合并，支持多媒体内容
- 📝 **ToDo管理**: 完整的CRUD操作，使用 blinko 真实标签系统
- 🎨 **优雅展示**: HTML模板渲染，精美的界面设计  
- 🔍 **智能搜索**: 全局搜索闪念和待办事项
- 🏷️ **标签管理**: 使用 blinko 原生标签系统

## 📝 使用示例

### 闪念记录
```
用户: 今天看了一部很棒的电影 #娱乐
用户: 电影名是《星际穿越》
用户: 诺兰的作品总是那么震撼 #电影
(30秒后自动保存到 blinko，type=0)
```

### ToDo管理
```
用户: #todo 完成项目文档 #工作 #重要
机器人: ✅ 待办已添加: 完成项目文档 (标签: 工作, 重要)
(保存到 blinko，type=1，自动创建标签)

用户: #list
机器人: [显示所有待办事项，按标签分组]

用户: #find 项目
机器人: [搜索包含"项目"的所有笔记]
```

## ⚙️ 配置说明

在 AstrBot WebUI 中配置：
- `blinko_base_url`: Blinko服务器地址
- `blinko_token`: API访问令牌
- `flash_session_timeout`: 闪念会话超时时间(默认30秒)
- `enable_rich_display`: 启用富文本图片显示(默认true)

## 🤝 代码质量

- **高度模块化**: 8个独立模块，职责清晰分离
- **设计模式**: 5种设计模式确保可扩展性
- **类型安全**: 完整的类型注解
- **异常处理**: 完善的错误处理机制
- **真实API**: 直接调用 Blinko API，无模拟
- **标签系统**: 使用 blinko 原生标签 (#标签 格式)

### 关键修正
- ✅ **TODO 正确分类**: type=1 发送到 blinko TODO 分类
- ✅ **闪念正确分类**: type=0 发送到 blinko 笔记分类
- ✅ **真实标签系统**: 内容中的 #标签 自动创建 blinko 标签
- ✅ **简化格式**: 移除复杂的截止时间和格式化内容
- ✅ **直接API调用**: 无任何模拟，所有数据真实保存

## 🎯 功能验证

使用 `python3 run.py` 可以验证：
- ✅ 插件初始化成功
- ✅ 闪念记录功能 (自动保存为 type=0)
- ✅ ToDo管理功能 (保存为 type=1，标签正确关联)
- ✅ 命令处理系统
- ✅ 会话管理机制
- ✅ 真实 blinko API 集成

---

**开发者**: FjNote Team  
**版本**: v1.0.0  
**许可**: MIT License# FJNoteBot
