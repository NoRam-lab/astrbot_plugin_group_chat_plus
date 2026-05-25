# Group Chat Plus - 个人自用魔改版

> 这是基于 `Him666233/astrbot_plugin_group_chat_plus` 改出来的个人自用版本。它不再追随上游发布节奏，也不保证保留原版所有功能；文档以当前目录里的代码为准，目标是让bot阅读上下文可以更接近人类看群聊的状态。所以默认理解全部群聊图片、表情包，但对发送给llm的图片理解内容会做重要性筛选（也算是一种简单的注意力机制了），以降低上下文数量。新的上下文机制是基于插件有的数据库，不再使用astrbot本体的对话数据录和群聊上下文感知，astrbot的对话数据是一问一答保存，会出现上下文断层，astrbot的上下文感知会让系统输入内出现大量聊天记录。然后就是添加了多群聊并发和单群聊多消息并发。

## 与原版 `Him666233/astrbot_plugin_group_chat_plus` 的区别

| 项目 | 原版 `main_old` | 当前魔改版 |
| --- | --- | --- |
| 插件身份 | `name: astrbot_plugin_group_chat_plus`，绑定原 GitHub 仓库 | `name: noram_group_chat_plus`，`repo: ""`，避免 AstrBot 市场自动更新覆盖本地版 |
| 展示名与目录 | 展示名 `chat_plus`，目录同插件名 | 展示名仍为 `chat_plus`，目录/Python 包仍是 `astrbot_plugin_group_chat_plus` |
| 数据目录 | 原版按自身插件名/旧逻辑保存 | 业务数据固定写入 `data/plugin_data/noram`，避免迁移旧数据 |
| Web 管理 | 独立 `web/` 服务、登录、认证、静态资源 | 删除独立 Web server，改为 AstrBot 插件 Page API：`core/page_api.py` + `pages/dashboard/` |
| 上下文 | 原版存在文件缓存、Smart 并发、平台历史重写等复杂链路 | 当前主链路是插件自有 SQLite 热库/冷库，未回复消息也可进入上下文 |
| 私聊/主动对话 | 原版包含 `private_chat/`、主动对话管理器等模块 | 当前版本聚焦群聊，私聊和主动对话模块不保留 |
| 并发 | 原版 Smart 并发/批次合并体系 | 当前使用 runtime chat key 隔离；同群根消息可并行，每条消息独立走完整回复流程 |
| 等待窗口 | 同用户窗口期消息可被合批吸收 | 并行模式下每条消息独立开窗口，不吸收其它消息；关闭并行后恢复合批逻辑 |
| 图片链路 | 旧图片处理与缓存逻辑 | 插件自有图片转写、重要性门控、刷图门控、图片状态和引用补救 |
| 测试 | 原版缺少当前这套本地回归测试 | 新增 runtime key、等待窗口、图片、SQLite WebUI、工具提醒、Agent 保护等测试 |

这个版本适合“自己部署、自己调参、自己维护”的场景。不要把它当作上游原版的直接升级包；如果要回到原版，请单独备份配置和 `data/plugin_data/noram`。

## 它做什么

Group Chat Plus 是一个群聊增强插件，核心目标是让 bot 先读空气，再决定要不要参与群聊。

当前主链路：

- 群消息进入插件后先解析文本、图片、引用、转发和特殊消息。
- 用户消息写入 GCP 自有 SQLite 热库，冷数据按维护任务归档到冷库。
- 普通消息走概率、本地规则和读空气 AI；`@bot`、关键词、引用回复、戳一戳等按配置提高优先级。
- 决定回复后，最终回复 AI 使用 SQLite 历史、当前消息、长期记忆、工具提醒和拟人状态生成回复。
- bot 实际发出的回复再写回 SQLite，成为后续上下文。

长期记忆插件只负责召回补充，不替代 GCP 的短期群聊上下文库。

## 快速开始

1. 保持目录名为 `astrbot_plugin_group_chat_plus`，放入 AstrBot 插件目录。
2. 在 AstrBot Dashboard 启用插件，插件列表中应显示 `chat_plus / noram_group_chat_plus`。
3. 确认 `enable_group_chat=true`，并按需设置 `enabled_groups`。
4. 如需图片理解，开启 `enable_image_processing` 并配置 `image_to_text_provider_id`。
5. 群里发送 `gcp_status`，确认 SQLite、图片状态、队列和数据目录正常。

建议关闭 AstrBot 官方主动回复、官方自动图片理解和其它主动插话插件，避免重复回复或上下文污染。GCP 会自己维护短期上下文和图片说明。

## 推荐最小配置

```json
{
  "enable_group_chat": true,
  "enabled_groups": [],
  "initial_probability": 0.02,
  "after_reply_probability": 0.8,
  "probability_duration": 120,
  "decision_ai_provider_id": "",
  "decision_ai_timeout": 30,
  "decision_ai_max_tokens": 4,
  "decision_context_messages": 30,
  "max_context_messages": 80,
  "enable_same_chat_parallel_reply": true,
  "enable_group_wait_window": true,
  "group_wait_window_timeout_ms": 3000,
  "group_wait_window_max_extra_messages": 3,
  "enable_image_processing": false,
  "image_to_text_provider_id": "",
  "enable_memory_injection": false,
  "memory_plugin_mode": "livingmemory",
  "memory_insertion_timing": "post_decision"
}
```

关键点：

- `decision_context_messages` 只影响读空气 AI。
- `max_context_messages` 只影响最终回复 AI。
- `decision_ai_max_tokens` 建议保持很小，目标是只输出 `yes/no`。
- `enable_same_chat_parallel_reply=true` 时，同群多条通过筛选的根消息可以并行生成回复。
- 并行模式下等待窗口只属于当前根消息，不会吸收其它消息；关闭并行后才恢复同用户分段合批。

完整配置见 [配置指南](docs/CONFIGURATION.md)。

## WebUI 与命令

WebUI 入口：

```text
AstrBot Dashboard -> 插件 -> chat_plus / noram_group_chat_plus -> GCP 上下文管理
```

兼容 Page API 前缀：

```text
/astrbot_plugin_group_chat_plus/page
/noram/page
/noram_group_chat_plus/page
```

群聊命令：

| 命令 | 作用 |
| --- | --- |
| `gcp_status` | 查看当前群 SQLite、图片状态、队列、最近错误和数据路径 |
| `gcp_reset_here` | 清理当前群 GCP 上下文和运行期状态，然后重启 AstrBot |
| `gcp_reset` | 清理全局 GCP 上下文和运行期状态，然后重启 AstrBot |
| `gcp_clear_image_cache` | 清理本地图片描述缓存，然后重启 AstrBot |

更多细节见 [WebUI 与命令](docs/WEBUI_AND_COMMANDS.md)。

## 数据与更新注意

这个本地签名版刻意使用：

```text
metadata.name = noram_group_chat_plus
metadata.repo = ""
业务数据目录 = data/plugin_data/noram
```

不要为了“统一名字”手动改插件目录名、插件内部名或数据目录。这样做容易导致 AstrBot 生成新配置、新数据目录，或者让市场更新重新匹配到上游。

## 常见排查

优先按这个顺序：

1. 群里发 `gcp_status`，看 SQLite、图片状态、队列和最近错误。
2. 打开 Page WebUI，确认消息是否落库、是否软删除、图片说明是否写入。
3. 搜索日志里的 `gcp_trace` / `消息轨迹` / `决策AI` / `图片状态` / `同群并行`。
4. 如果 token 或请求量异常，先区分请求来自读空气、最终回复、图片转写还是长期记忆。

详细步骤见 [故障排查](docs/TROUBLESHOOTING.md)。

## 文档

- [文档索引](docs/README.md)
- [功能总览](docs/FEATURES.md)
- [配置指南](docs/CONFIGURATION.md)
- [消息流程](docs/MESSAGE_FLOW.md)
- [WebUI 与命令](docs/WEBUI_AND_COMMANDS.md)
- [故障排查](docs/TROUBLESHOOTING.md)
- [开发维护与审查结论](docs/DEVELOPMENT.md)

## 测试

```bash
pytest -q astrbot_plugin_group_chat_plus/tests
```

当前测试重点覆盖读空气输出限制、上下文条数、图片门控、引用图片、等待窗口、运行期缓存、SQLite WebUI、工具提醒、Agent 中间回复保护和同群并行隔离。
