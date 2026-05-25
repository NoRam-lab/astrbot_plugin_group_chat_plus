# 开发维护

本文面向二开、审查和维护。用户配置优先看 [配置指南](CONFIGURATION.md)。

## 当前审查结论

本次审查只做文档和维护边界整理，没有修改 `main.py` 或 `utils/` 业务逻辑。

总体判断：

- 当前目录已经不是原版 `astrbot_plugin_group_chat_plus-main_old` 的轻微配置改动，而是个人自用魔改版。
- 主链路以 GCP 自有 SQLite、AstrBot Page API、图片门控、runtime chat key、等待窗口 buffer 和同群根消息并行为核心。
- 原版独立 Web 面板、私聊增强、主动对话、Smart 并发管理器和旧文件缓存链路不再适合作为当前版本说明。

高风险区域：

- `main.py` 体量很大，群消息入口、读空气、回复生成、等待窗口、命令和 hook 混在同一文件，后续改并发或保存逻辑时要小步验证。
- `on_llm_response()`、`on_decorating_result()`、`after_message_sent()` 的顺序依赖 AstrBot 事件生命周期，Agent、多工具调用、重复拦截和空结果场景容易互相影响。
- 多处 `except Exception` 选择静默降级或只写日志，有利于不中断群聊，但会让真实失败更依赖 debug 日志和测试复现。
- Page API 目前以单元测试和轻量接口测试为主，缺少完整浏览器端到端测试。
- 图片 `pending_retry -> 引用补救 -> success/failed_final` 的集成覆盖仍偏薄，平台 API 差异会放大这个风险。

已修正文档漂移：

- 等待窗口并行语义：并行模式下每条通过筛选的根消息独立开窗口，不吸收其它消息。
- WebUI 说明：当前使用 AstrBot Plugin Page API，不再使用原版独立 Web server/auth 面板。
- 原版私聊、主动对话、Smart 并发和旧文件缓存说明不再适用。

测试现状：

- 已有测试覆盖 runtime chat key、同群并行隔离、等待窗口 buffer、等待窗口预取、图片策略、图片结构化 prompt、引用图片、SQLite WebUI、工具提醒、读空气输出限制和未完成 Agent 中间回复保护。
- 缺口主要在 Page API 浏览器端、图片补救链路全流程、工具多轮发送后保存和真实平台事件兼容。

## 架构原则

Group Chat Plus 的短期上下文主链路是插件自有 SQLite：

```text
群消息
  -> 文本/图片/转发/入群消息解析
  -> 写入 GCP SQLite 热库
  -> 概率、本地规则、等待窗口
  -> 读空气 AI 判断 yes/no
  -> 最终回复 AI 生成回复
  -> bot 回复写回 GCP SQLite
  -> 维护任务将旧消息归档到冷库
```

当前 prompt 历史不从 AstrBot 官方会话历史构建。这样做是为了保存未回复群消息，避免群聊上下文在“一问一答”历史结构中断层。

## 关键路径

| 路径 | 职责 |
| --- | --- |
| `main.py` | 插件入口、配置读取、事件处理、读空气流程、等待窗口、回复生成、命令和 hook |
| `plugin_identity.py` | 本地签名名、旧数据名、插件目录名和空仓库地址 |
| `core/page_api.py` | AstrBot 插件页 API |
| `utils/context_manager.py` | 上下文读写、格式化、兼容函数 |
| `utils/sqlite_context_store.py` | 热库/冷库 SQLite、归档、软删除、编辑、图片状态和 WebUI 查询 |
| `utils/decision_ai.py` | 读空气 AI prompt、Provider 调用、短输出参数、yes/no 解析 |
| `utils/reply_handler.py` | 最终回复 AI 调用 |
| `utils/image_handler.py` | 图片提取、转写和图片处理决策 |

## 行为模块

| 模块 | 职责 |
| --- | --- |
| `probability_manager.py` | 基础概率和回复后概率提升 |
| `global_time_control.py` | 全局时间段响应控制 |
| `frequency_adjuster.py` | 发言频率分析与概率调整 |
| `reply_density_manager.py` | 短时间回复密度限制 |
| `attention_manager.py` | 注意力、情绪、溢出、疲劳和冷却联动 |
| `cooldown_manager.py` | 注意力冷却持久化与释放 |
| `humanize_mode.py` | 沉默模式、动态阈值、兴趣话题和决策历史 |
| `mood_tracker.py` | 群情绪识别和 prompt 注入 |
| `typing_simulator.py` | 回复延迟模拟 |

## 消息解析模块

| 模块 | 职责 |
| --- | --- |
| `message_processor.py` | 时间、发送者、触发来源等元数据格式化 |
| `message_cleaner.py` | 清理消息、戳一戳标记、reply/json 等组件格式化 |
| `keyword_checker.py` | 触发关键词和黑名单关键词 |
| `emoji_detector.py` | 表情包识别和标记 |
| `forward_message_parser.py` | OneBot 合并转发解析 |
| `welcome_message_parser.py` | 入群消息解析 |
| `content_filter.py` | 输出前和保存前内容过滤 |
| `ai_response_filter.py` | 思考链过滤、读空气结果提取 |

## 记忆、工具和运行期状态

| 模块 | 职责 |
| --- | --- |
| `memory_injector.py` | LivingMemory / legacy 记忆插件适配 |
| `tools_reminder.py` | 可用工具格式化和 prompt 注入 |
| `runtime_message_snapshot_store.py` | 当前处理消息快照，不作为长期上下文 |
| `wait_window_buffer.py` | 等待窗口追加消息缓冲，只用于当前 prompt |
| `image_description_cache.py` | 图片说明缓存 |
| `image_importance_policy.py` | 图片重要性和刷图保留策略 |
| `image_spam_gate.py` | 图片刷图冷却门 |
| `platform_ltm_helper.py` | 平台消息组件辅助，保留兼容用途 |

## 本地签名约束

不要把以下值随手统一成同一个名字：

| 常量 | 当前含义 |
| --- | --- |
| `PLUGIN_PACKAGE_NAME` | 插件目录/Python 包：`astrbot_plugin_group_chat_plus` |
| `PLUGIN_LOCAL_NAME` | 本地签名运行名：`noram_group_chat_plus` |
| `PLUGIN_LEGACY_NAME` | 旧运行名/数据名：`noram` |
| `PLUGIN_DATA_NAME` | 业务数据名，等于 `noram` |
| `PLUGIN_REPO_URL` | 空字符串 |

所有 `StarTools.get_data_dir()` 业务数据调用应显式走旧数据名，避免迁移或新建 `noram_group_chat_plus` 业务数据目录。

## WebUI API 维护

Page API 需要继续兼容：

```text
/astrbot_plugin_group_chat_plus/page
/noram/page
/noram_group_chat_plus/page
```

新增 API 时应同时注册到所有前缀。WebUI 不应假设只有一个运行名。

## 测试

现有测试入口：

```bash
pytest -q astrbot_plugin_group_chat_plus/tests
```

当前测试覆盖：

- runtime chat key 生成和跨群隔离。
- 同群并行开关下的 processing 等待行为。
- 读空气输出 token 限制和 yes/no 解析。
- 读空气与最终回复上下文条数。
- 图片重要性和刷图门控。
- 图片结构化 prompt。
- 引用图片上下文。
- 等待窗口 buffer 隔离、预取和 trace。
- 运行期快照与等待窗口缓冲。
- SQLite WebUI 查询、编辑、软删除、恢复。
- 工具提醒格式化。
- 未完成 Agent 中间回复保护。

## 维护注意

- 修改配置字段时，同步 `_conf_schema.json`、配置读取、文档和必要测试。
- 修改上下文读取时，明确读空气和最终回复两个历史条数的差异。
- 修改图片链路时，保留 `success`、`pending_retry`、`failed_final` 三类状态语义。
- 修改 WebUI 消息编辑或删除时，确保软删除消息默认不进入 prompt。
- 修改多工具调用保存逻辑时，注意 `on_llm_response`、`on_decorating_result` 和 `after_message_sent` 的顺序。
- 修改本地签名身份时，不得导致业务数据目录从 `data/plugin_data/noram` 迁移。
- 修改并发逻辑时，先明确是在改 runtime 会话隔离、同群根消息并行，还是等待窗口合批语义；三者不要混在一起改。
- 修改 README/docs 时，同步检查 `_conf_schema.json` 的 hint，避免 Dashboard 配置页和文档互相打架。

## 已知风险和测试缺口

- `_conf_schema.json` 与代码兼容默认值中，`initial_probability` 仍存在历史差异，需要后续统一。
- `main.py` 仍是最大复杂度集中点，建议后续把等待窗口、运行期状态、命令和 hook 保存逻辑逐步拆出。
- WebUI Page API 路由层缺少更完整的端到端测试。
- 图片 `pending_retry -> 引用补救 -> failed_final/success` 缺少完整集成测试。
- 工具多轮、无最终文本、重复拦截场景下的发送后保存仍需要更强覆盖。
- 广泛异常兜底可能掩盖真实回归，排查时应优先打开 `enable_debug_log` 并保留完整日志。
- Windows 控制台可能显示中文编码异常，但源码和文档应保持 UTF-8。
