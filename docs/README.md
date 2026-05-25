# Group Chat Plus 文档索引

这组文档按“先会用，再会调，再会维护”的顺序组织。README 只做入口和本地魔改版差异说明，细节放在 docs。

## 阅读路线

| 目标 | 文档 |
| --- | --- |
| 快速了解当前版能做什么 | [功能总览](FEATURES.md) |
| 第一次配置或调参数 | [配置指南](CONFIGURATION.md) |
| 理解一条消息从收到到回复的真实流程 | [消息流程](MESSAGE_FLOW.md) |
| 使用 Page WebUI、命令和 API 前缀 | [WebUI 与命令](WEBUI_AND_COMMANDS.md) |
| 排查不回复、乱回复、图片失败、并发等待 | [故障排查](TROUBLESHOOTING.md) |
| 二开、审查、补测试、看风险边界 | [开发维护与审查结论](DEVELOPMENT.md) |

## 当前架构一句话

当前魔改版用插件自有 SQLite 管理群聊短期上下文：群消息经过基础解析、概率、本地规则、等待窗口、读空气 AI 和最终回复 AI，并按处理路径写入热库。长期记忆插件只做召回增强，不替代短期聊天记录库。

## 本地签名版身份

| 项 | 当前值 |
| --- | --- |
| 展示名 | `chat_plus` |
| AstrBot 内部插件名 | `noram_group_chat_plus` |
| 插件目录 / Python 包 | `astrbot_plugin_group_chat_plus` |
| 业务数据目录 | `data/plugin_data/noram` |
| 仓库地址 | `""` |

这个组合用于避免 AstrBot 市场按原仓库或原插件名提示/执行自动更新，同时保留旧业务数据。

## 和 `main_old` 文档的关系

`astrbot_plugin_group_chat_plus-main_old/docs` 里的独立 Web 面板、私聊、主动对话、Smart 并发、文件缓存等说明不再作为当前版依据。当前版文档只描述本目录代码实际保留的能力。
