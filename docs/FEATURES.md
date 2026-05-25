# 功能总览

本文按功能域审查 Group Chat Plus 当前能力。字段名和默认值以 `_conf_schema.json` 为准，运行细节以源码为准。

## 插件身份与数据

- 本地签名名：`noram_group_chat_plus`。
- 展示名：`chat_plus`。
- 插件目录和 Python 包名：`astrbot_plugin_group_chat_plus`。
- 业务数据目录：`data/plugin_data/noram`。
- 仓库地址为空，用于避免市场自动更新覆盖本地版本。

## 群聊入口与权限

- 只处理群聊消息，私聊不会进入主流程。
- `enable_group_chat` 是总开关。
- `enabled_groups` 留空表示所有群启用，填写群号后只在指定群启用。
- `enable_debug_log` 可打开详细流程日志。
- `gcp_reset`、`gcp_reset_here`、`gcp_clear_image_cache` 都支持用户 ID 白名单；白名单为空表示所有人可用。

## 触发来源

插件会区分不同触发来源，并写入 SQLite 便于 WebUI 排查：

- `@bot`：通常跳过普通概率筛选，直接进入更高优先级处理。
- 关键词：可配置强制回复，也可开启智能模式，让关键词只跳过概率但仍交给读空气 AI 判断。
- 普通群聊：先经过概率、本地规则和读空气 AI。
- 戳一戳：支持忽略、仅 bot、全部处理等模式，并可在回复后按概率戳回发送者。
- 入群消息：支持把新成员入群空消息解析为系统提示，并按配置跳过概率或完整处理。
- 引用回复 bot：可被全局时间控制等规则识别为强触发类型。

## 读空气与最终回复

- 读空气 AI 由 `DecisionAI` 负责，目标只返回 `yes/no`。
- `decision_ai_provider_id` 可为读空气单独选择 Provider，留空则使用默认 Provider。
- `decision_ai_timeout` 超时后默认不回复。
- `decision_ai_max_tokens` 默认 `4`，用于限制读空气输出长度。
- `read_air_blacklist_user_ids` 可让指定用户的普通消息只落库、不主动读空气；`@bot`、引用回复和触发关键词仍按原逻辑处理。
- `decision_context_messages` 控制读空气阶段读取多少条 SQLite 热库历史。
- 最终回复由 `ReplyHandler` 走 AstrBot 标准 LLM 链路，因此其他插件仍可通过 AstrBot 的 LLM 事件注入内容。
- `max_context_messages` 控制最终回复阶段读取多少条 SQLite 热库历史。

## 概率与本地调节

- 基础概率：`initial_probability`。
- 回复后概率提升：`after_reply_probability` 和 `probability_duration`。
- 全局时间控制：按时间段降低普通读空气概率，并可限制 `@bot`、关键词、引用回复等强触发放行概率。
- 频率调整：定期分析群里 bot 发言频率，动态降低或提高概率。
- 回复密度限制：滑动窗口统计 bot 最近回复次数，超过软限后衰减，达到硬限后拦截普通读空气回复。
- 消息质量和表情包处理：可识别低信息量消息或表情包，并降低触发概率。

## 自有 SQLite 上下文

- 热库：保存近期消息，是日常读空气和最终回复 prompt 的来源。
- 冷库：保存归档消息，用于 WebUI 检索和长期维护，不作为日常 prompt 默认来源。
- 消息按 `platform_id + chat_id` 隔离，避免不同平台或不同群串上下文。
- 用户消息、bot 回复、图片状态、触发来源、软删除状态都会进入数据库。
- 软删除消息默认不会进入后续 prompt，可通过 WebUI 恢复。
- `gcp_hot_retention_days`、`gcp_cold_retention_days`、`gcp_cold_max_messages_per_chat` 控制归档和保留范围。

## 运行期并发模型

- 运行期隔离使用 runtime chat key，而不是单纯的 `chat_id`。
- 群聊 runtime key 包含平台、会话类型、`chat_id` 和真实 `group_id`，用于避免不同群同时发消息时互相等待。
- 私聊 runtime key 保留兜底逻辑，但当前主流程聚焦群聊。
- `processing_sessions` 仍按 `message_id` 登记，主要用于防平台重复推送和让发送前/发送后 hook 识别本插件回复。
- `enable_same_chat_parallel_reply=true` 时，同一群内多条通过筛选的根消息可以并行进入最终回复链路。
- 并行模式下，每条根消息拥有自己的等待窗口、`WaitWindowBuffer` 和记忆预取任务，不共享其它消息的临时缓冲。
- `enable_same_chat_parallel_reply=false` 时，恢复同会话串行保护；后来的消息会按 `concurrent_wait_max_loops` / `concurrent_wait_interval` 等待前一条处理完成。
- 重复回复缓存按 runtime chat key 隔离，仍会尽量避免同群并行回复产生完全相同的文本。

## 图片理解

- `enable_image_processing` 开启插件自有图片转写链路。
- `image_to_text_provider_id` 指定视觉模型 Provider。
- `image_to_text_scope` 控制图片转写适用范围，例如全部消息、仅 `@bot`、仅关键词等。
- `max_images_per_message` 控制单条消息最多处理多少张图。
- `active_image_understanding_blacklist_user_ids` 可让指定用户的图片只以 `[图片]` 占位入库，不主动理解；后续被引用且需要回复时再补救理解。
- 图片重要性门控会结合阈值、短时间刷图窗口和批量图片数量决定是否转写。
- 图片刷图门控会在图片过密时进入冷却，降低视觉模型调用量。
- 图片说明缓存可减少重复图片的转写成本。
- 图片首次转写失败会记录 `pending_retry`，被引用时可尝试从 OneBot/NapCat 拉原消息补救；补救仍失败则标记 `failed_final`。

## 等待窗口

- `enable_group_wait_window` 开启后，普通消息通过概率筛选会短暂等待，再继续读空气和最终回复。
- 并行模式下，等待窗口只属于当前根消息；其它消息不会被这个窗口吸收或提前返回。
- 串行模式下，等待窗口保留旧合批语义，同一用户窗口期内的后续消息可追加进当前窗口。
- 追加消息会立即写入 SQLite，同时暂存在当前窗口自己的 `WaitWindowBuffer`，只用于当前 prompt 的追加消息区域。
- `group_wait_window_timeout_ms` 控制等待时长。
- `group_wait_window_max_extra_messages` 控制最多收集几条追加消息。
- `group_wait_window_max_users` 控制同一 runtime 会话内活跃窗口数量；达到上限时跳过等待窗口，但不跳过后续完整流程。
- `group_wait_window_merge_at_messages` 只对串行合批模式有意义；并行模式下 `@bot` 消息仍作为独立根消息处理。

## 关键词、命令和黑名单

- `trigger_keywords` 配置触发关键词。
- `keyword_smart_mode` 控制关键词是否仍交给读空气 AI 判断。
- `blacklist_keywords` 可让命中的消息不触发回复。
- `record_blacklist_keyword_messages` 可选择把命中黑名单关键词的消息仍写入上下文。
- 用户黑名单可按用户 ID 禁止触发。
- 命令过滤默认开启，可避免 `/`、`!`、`#` 等命令被当作普通聊天。
- `record_filtered_command_messages` 可选择把被指令过滤的消息仍写入上下文，不影响其他插件继续处理指令。
- 完整命令检测和命令前缀匹配可覆盖更细的指令场景。

## 戳一戳、表情和特殊消息

- 戳一戳支持 `ignore`、`bot_only`、`all` 等处理策略。
- 可配置戳 bot 时跳过概率、参考概率提升、反向触发概率。
- 可配置回复后戳一戳发送者。
- 戳一戳轨迹提示可把近期戳一戳行为注入 prompt。
- 表情包识别可给消息加标记，并按配置降低触发概率。
- 支持忽略 `@其他人` 和 `@all`，减少无关触发。

## 记忆、工具与提示词

- LivingMemory 和 legacy 记忆插件都可作为长期记忆来源。
- `memory_insertion_timing=pre_decision` 时记忆影响是否回复；`post_decision` 时只影响最终回复内容。
- `livingmemory_top_k` 控制召回条数，过大容易增加 prompt 成本。
- 读空气 AI 和回复 AI 都支持默认提示词追加或覆盖。
- 工具提醒可把当前可用工具注入最终回复 prompt，并可按人格工具配置过滤。

## 拟人增强、情绪和频率

- 注意力机制按用户维护关注度，影响回复概率。
- 注意力支持半衰期、情绪加成、负面下降、溢出、冷却和疲劳拦截。
- 对话疲劳会在连续回复较多时降低概率，并可注入收尾提示。
- 拟人模式支持沉默模式、动态消息阈值、决策历史和兴趣话题加成。
- 群情绪系统会从近期消息识别群内情绪，并注入最终回复 prompt。
- 打字延迟模拟会按回复长度增加短暂延迟，避免秒回感。

## 内容过滤与重复拦截

- 输出内容过滤：发送给用户前清理指定范围、头部或尾部内容。
- 保存内容过滤：保存到 SQLite 前清理指定内容。
- 重复消息拦截：发送前检查最近 bot 回复，避免连续重复。
- 可配置重复检测条数和时间窗口。
- 多工具调用场景下，插件会尽量按实际顺序保存文本与工具调用相关回复。

## WebUI 与维护

- WebUI 位于 AstrBot 插件页，不额外开放独立端口。
- 支持统计、消息列表、搜索、筛选、编辑、软删除、恢复、批量软删除和手动维护归档。
- `gcp_status` 可查看当前群和全局 SQLite 状态、图片状态、队列和最近错误。
- `gcp_reset_here` 清理当前群运行期状态和上下文。
- `gcp_reset` 清理全局运行期状态和上下文。
- `gcp_clear_image_cache` 清理图片说明缓存。

## 平台边界

- 合并转发解析和入群消息解析主要面向 `aiocqhttp` / OneBot v11。
- 图片引用补救依赖能通过平台 API 拉取原消息，OneBot/NapCat 场景支持最好。
- 回复后戳一戳主要面向 QQ + aiocqhttp。
- 非对应平台会自动跳过相关增强，不影响普通群聊处理。

## 已不保留的原版模块

当前魔改版不继续维护原版的这些模块或文档语义：

- `private_chat/` 私聊增强。
- `web/` 独立 Web server、独立登录和认证面板。
- Smart 并发管理器。
- 主动对话管理器。
- 旧文件缓存链路和围绕它的上下文重写说明。

这些能力不应作为当前版本的排障依据；以本目录 `main.py`、`core/page_api.py`、`utils/sqlite_context_store.py` 和本文档为准。
