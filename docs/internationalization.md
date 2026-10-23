# 国际化

平台界面语言统一在项目根目录的 `.env` 文件中配置，支持简体中文（`zh-CN`）和 English（`en-US`）。页面不提供语言切换，浏览器 Cookie 和语言偏好不会覆盖此配置。

```dotenv
LANGUAGE=en-US
```

修改文件后重启应用，所有页面、登录页面和 NiceGUI 内置组件统一使用配置的语言。使用 `zh-CN` 可切换为中文。

Demo 同样从 `.env` 读取语言；文件不存在时使用 `.env.example` 的中文默认值。修改后重新运行：

```bash
sh scripts/demo.sh
```

脚本仅将 Compose 明确引用的配置用于演示，数据库和认证仍使用独立演示配置，不会连接 `.env` 中的业务数据库。不需要在启动命令中指定语言。

覆盖范围包括平台导航、管理表单、表格、主要通知，以及账号初始化、登录、改密和设备授权页面。项目名称、工具标题、描述、业务数据、枚举值和工具脚本自身的界面不自动翻译。日志、第三方异常、服务层原始错误和 API 文档仍保留原文。

## 添加平台文案

中文原文作为翻译键，英文目录位于 `core/i18n/en-US.json`。在页面渲染或回调中调用翻译，避免模块导入时固化语言：

```python
from core.i18n import t, option_labels

ui.label(t("工具中心"))
ui.label(t("项目授权：{arg0}", arg0=username))
ui.select(option_labels({"user": "普通用户", "admin": "管理员"}), value="user")
```

动态值通过命名占位符传入；英文翻译必须保留同名占位符及格式。不要翻译下拉框的机器值、数据库字段或用户输入。未找到翻译时显示中文原文。

平台 NiceGUI 页面使用 `component.language.localized_page`，由它读取统一配置并设置内置组件语言。静态表格插槽可使用 `html_t()` 翻译文字及显示表达式中的字面量，它不处理工具或用户提供的 HTML，也不替代 HTML 转义。

新增其他语言时，需要添加翻译目录，并扩展 `core.i18n` 的语言规范化和目录加载，同时确认 NiceGUI 支持目标语言。

验证：

```bash
uv run python -m unittest discover -s tests -p test_i18n.py
```
