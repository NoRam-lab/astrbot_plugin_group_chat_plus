# 消息流程

本文说明一条群聊消息进入 Group Chat Plus 后的当前真实处理顺序。

## 1. 入口检查

`on_group_message()` 只处理群聊消息。进入主流程前会检查：

- `enable_group_chat` 是否开启。
- 当前群是否在 `enabled_groups` 允许范围内。
- 消息是否来自 bot 自己、用户是否在黑名单、是否是应过滤的命令。
- 是否需要忽略 `@其他人`、`@all`、特殊组件或无效空消息。
- 是否命中戳一戳、入群消息、合并转发等特殊输入。

未通过基础检查的消息不会进入读空气和最终回复流程。

## 2. 触发分类

插件会把消息归类为不同触发来源：

- 普通群聊消息：走概率和本地规则。
- `@bot`：通常跳过普通概率，直接进入高优先级流程。
- 关键词：根据 `keyword_smart_mode` 决定强制回复或保留读空气判断。
- 戳一戳：按 `poke_message_mode` 和相关概率处理。
- 新成员入群：按 `welcome_message_mode` 处理。
- 引用回复 bot：可作为强触发类型参与全局时间控制。

触发来源会写入 SQLite 的消息记录，方便 WebUI 筛选和排查。

## 3. 文本、组件与图片处理

进入内容处理后，插件会整理当前消息：

- 提取普通文本、reply、json、file、video、image 等组件中的可读内容。
- 解析 OneBot 合并转发，按嵌套深度和 API 次数限制展开。
- 解析新成员入群空消息，转换成系统提示。
- 检测表情包并按配置加标记。
- 处理图片，转写成功后把图片说明放入消息正文和元数据。
- 记录失败图片状态，保留后续引用补救所需的信息。
- 按配置加入时间戳、发送者信息、触发来源和系统提示。

图片转写不是 AstrBot 官方图片理解的结果回填，而是 GCP 自己的链路。

## 4. SQLite 落库与历史读取

消息最终会写入 GCP 自有 SQLite，但落库时机按路径不同略有差异：

- 热库保存近期消息，给读空气和最终回复读取。
- 冷库保存归档消息，主要给 WebUI 搜索和人工维护。
- `platform_id + chat_id` 用于隔离不同平台和群。
- 用户消息、bot 回复、图片状态、触发来源、软删除状态都会记录。
- 普通消息未通过概率时，会在返回前按可保存内容直接落库，避免上下文断裂。
- 普通消息通过概率时，会先进入等待窗口和内容处理，再把结构化后的当前消息写入 SQLite。
- 等待窗口追加消息会在被吸收时立即写入 SQLite，同时进入当前窗口的运行期缓冲。

当前 prompt 历史读取的是 GCP SQLite 热库，不从 AstrBot 官方会话历史构建主上下文。

## 5. 运行期隔离与并发登记

插件使用 runtime chat key 隔离运行期状态：

- 群聊 key 包含平台、会话类型、`chat_id` 和真实 `group_id`。
- 私聊 key 有兜底逻辑，但当前主流程聚焦群聊。
- 不同群即使 `chat_id` 偶然相同，也不会共享 `processing_sessions`、等待窗口和重复回复缓存。

`processing_sessions` 按 `message_id -> runtime_chat_key` 登记：

- 相同 `message_id` 再次到达时会被视为平台重复推送并跳过。
- `enable_same_chat_parallel_reply=true` 时，同一 runtime key 下已有消息处理中也不阻塞新根消息。
- `enable_same_chat_parallel_reply=false` 时，同一 runtime key 下已有消息处理中，新消息会按 `concurrent_wait_max_loops` / `concurrent_wait_interval` 等待。
- 这个登记还用于 `on_llm_response()`、`on_decorating_result()` 和 `after_message_sent()` 判断哪些回复属于本插件。

## 6. 普通概率与本地规则

普通消息会经过概率层：

- 基础概率 `initial_probability`。
- bot 回复后的临时概率提升。
- 全局时间控制。
- 频率调整。
- 回复密度限制。
- 注意力、冷却、对话疲劳和拟人模式。
- 表情包、消息质量、关键词和黑名单规则。

未通过概率或本地规则的消息不会调用读空气 AI。只要消息已经落库，它仍可作为后续上下文被读取。

## 7. 等待窗口

如果普通消息通过概率，且 `enable_group_wait_window=true`：

1. 插件为当前根消息生成独立的 `buffer_key`。
2. 插件创建等待窗口，并可在窗口期间启动长期记忆预取。
3. 窗口结束后继续执行图片/引用/上下文构建、读空气和最终回复。
4. 构建 prompt 时，当前 `buffer_key` 对应的追加消息会放在当前消息下方。
5. 回复发送、重复拦截或兜底保存后，只清理当前根消息的缓冲。

并行和串行模式的差异：

- `enable_same_chat_parallel_reply=true`：活跃窗口不会吸收其它消息。第二条消息会继续完整流程，创建自己的窗口、buffer 和记忆预取任务。
- `enable_same_chat_parallel_reply=false`：保持旧合批行为。同一用户窗口期内的后续消息可被 `_maybe_intercept_for_wait_window()` 吸收，写入当前窗口 buffer 后提前返回。
- `group_wait_window_max_users` 达到上限时，只跳过等待窗口，不跳过后续读空气或回复流程。

等待窗口只是当前回复的合批辅助，不是长期上下文来源。

## 8. 读空气 AI

需要 AI 判断时，插件调用 `DecisionAI.should_reply()`。

读空气 prompt 通常包含：

- 当前消息。
- SQLite 热库最近 `decision_context_messages` 条历史。
- 等待窗口追加消息。
- 当前发送者和触发来源。
- 关键词、全局时间、回复密度、对话疲劳、拟人状态等系统信息。
- 若 `memory_insertion_timing=pre_decision`，还会注入长期记忆召回内容。

读空气结果只使用业务布尔值：

- `yes`：继续生成最终回复。
- `no`：不回复。
- 超时或异常：默认不回复，并记录错误。

## 9. 最终回复 AI

最终回复由 `ReplyHandler.generate_reply()` 触发 AstrBot 标准 LLM 链路。

最终回复 prompt 通常包含：

- SQLite 热库最近 `max_context_messages` 条历史。
- 当前消息。
- 等待窗口追加消息。
- post-decision 长期记忆。
- 群情绪、工具提醒、人格、回复提示词和其他插件注入。

因为最终回复走 AstrBot 标准链路，所以其他插件仍可能通过 AstrBot LLM 事件影响请求。

## 10. 发送前处理

回复发送前可能发生：

- 未完成 Agent 中间结果保护：若工具调用/多轮处理还没结束，插件会在发送前清空临时 `LLM_RESULT`，避免草稿或思考内容被发出。
- 打字延迟模拟。
- 输出内容过滤。
- 重复回复拦截。
- 回复后戳一戳的计划。
- 多工具调用场景下的结果整理。

如果重复回复被拦截，插件会阻止发送，并避免把被拦截内容写成新的 bot 回复。
未完成 Agent 中间结果保护同样发生在发送前，不依赖 `after_message_sent()` 事后补救。

## 11. 发送后保存

`after_message_sent()` 会把实际发送出去的 bot 回复保存到 GCP SQLite。插件还会用运行期快照处理一些边界情况：

- 多段回复。
- 工具多轮调用。
- LLM 响应事件已结束但没有后续发送事件。
- 发送前被清空结果。
- 需要兜底保存用户消息或 bot 回复。

保存后的 bot 回复会成为后续上下文的一部分，并可被重复拦截模块参考。

## 12. 维护与归档

SQLite 存储会按维护间隔执行：

- 把超过热库保留时间的消息归档到冷库。
- 清理超过冷库保留天数或每群上限的消息。
- 保留软删除状态和编辑信息。

WebUI 的手动维护按钮会立即触发同一套维护逻辑。
