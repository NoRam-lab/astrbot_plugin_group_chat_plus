# 故障排查

排查顺序建议固定为：

1. 群里发送 `gcp_status`。
2. 打开 WebUI 看消息和图片状态。
3. 查看 LLM request logger。
4. 查看 AstrBot 日志。
5. 再调整配置。

## 一次回复出现多条大 prompt 请求

常见原因：

- 主模型返回空响应，AstrBot 自动重试。
- 主 Provider 失败后切换 fallback Provider。
- `max_context_messages` 太大。
- LivingMemory 召回太多或记忆内容太长。
- 其他插件在最终回复链路注入了大量 prompt。
- 同群并行开启后，多条根消息同时通过筛选，各自完整进入最终回复链路。

日志关键词：

```text
returned empty output on attempt
OpenAI completion has no choices
Switched from
ToolLoopAgentRunner
```

处理建议：

- 先换稳定的主 Provider。
- 降低 `max_context_messages`，例如从 `-1` 改为 `60` 或 `80`。
- 降低 `livingmemory_top_k`。
- 保持 `memory_insertion_timing=post_decision`。
- 确认大 prompt 来自最终回复，而不是图片转写或读空气。
- 需要区分成本来源：读空气看 `decision_context_messages`，最终回复看 `max_context_messages`，图片转写看视觉 Provider，请求量高还要检查 LivingMemory 召回。

## 读空气输出很短但 token 仍高

`decision_ai_max_tokens=4` 只能限制最终输出，不一定能限制中转站或模型内部 reasoning tokens。

处理建议：

- 给读空气单独配置轻量非推理模型。
- 避免使用 thinking/reasoning 模型做读空气。
- 保持 `decision_context_messages` 在 20-50。
- 若读空气仍慢，降低 `decision_ai_timeout`。

## bot 不回复

先判断是“没触发”还是“触发后决定不回复”。

检查：

- `enable_group_chat` 是否开启。
- 当前群是否在 `enabled_groups` 中。
- 是否被用户黑名单、关键词黑名单、命令过滤、`@all` 或 `@其他人` 过滤。
- 普通消息是否被低概率、本地规则、回复密度、全局时间控制拦截。
- 读空气 AI 是否超时或返回 `no`。
- `gcp_status` 最近错误是否有 SQLite 或 Provider 异常。

调试方法：

- 临时开启 `enable_debug_log`。
- 临时提高 `initial_probability`。
- 临时关闭 `enable_reply_density_limit` 或全局时间控制。
- 用 `@bot` 或关键词测试强触发路径。

## 群消息没有进入上下文

检查顺序：

- WebUI 中搜索这条消息。
- 确认平台 ID 和群 ID 是否正确。
- 确认消息是否被软删除。
- 确认热库保留时间是否太短。
- 确认消息是否属于未处理平台或被基础过滤挡住。

说明：

- 日常 prompt 读取热库，不默认读取冷库。
- 冷库存在不代表 `max_context_messages=-1` 会把长期归档全部塞进 prompt。
- 等待窗口追加消息会落库，但窗口内存缓冲只用于当前回复。

## 同群多条消息没有被合批

这是当前默认行为。`enable_same_chat_parallel_reply=true` 时，同群每条通过筛选的根消息都会独立走完整流程：

- 不会被其它等待窗口吸收。
- 会创建自己的窗口 key 和 `WaitWindowBuffer`。
- 会各自启动记忆预取、读空气、最终回复和发送后保存。

如果你想恢复“同一用户短时间分段消息合成一次回复”的旧体验，把 `enable_same_chat_parallel_reply=false`，并确认 `enable_group_wait_window=true`、`group_wait_window_max_extra_messages > 0`。

## 同群消息互相等待

如果不同群互相等待，重点看日志里的 `runtime_key`：

- 不同平台或不同群号应生成不同 runtime key。
- `group_id` 缺失时会尝试从 `event.message_obj.group_id` 或原始消息兜底。
- 如果日志里两个群的 runtime key 完全相同，说明平台事件缺少群 ID 或适配器字段异常。

如果同一群互相等待：

- `enable_same_chat_parallel_reply=false` 时是预期行为。
- `enable_same_chat_parallel_reply=true` 时只应去重同一个 `message_id` 的重复推送，不应因为同群已有处理中消息而等待。
- 搜索日志 `同群并行`、`并发检测`、`runtime_key` 和 `message_id` 判断是哪一种。

## 图片没有被理解

检查：

- `enable_image_processing` 是否开启。
- `image_to_text_provider_id` 是否配置。
- `image_to_text_scope` 是否覆盖当前消息类型。
- 视觉 Provider 是否可用。
- 图片是否超过 `max_images_per_message`。
- 是否被图片重要性门控或刷图门控跳过。
- WebUI 里的 `image_status` 是 `success`、`pending_retry` 还是 `failed_final`。

处理建议：

- 先用 `@bot` 发单张图片测试。
- 暂时把 `image_to_text_scope` 调成 `all` 验证链路。
- 打开 `enable_image_importance_gate_log` 看门控原因。
- 开启 `enable_image_description_cache` 降低重复图片成本。

## 图片显示待补救

`pending_retry` 表示首次转写失败，插件保留了图片引用，等待后续引用补救。

补救依赖平台能力：

- OneBot/NapCat 场景可通过 `get_msg` 拉原消息，成功率较高。
- 其他平台可能无法补救，只能记录失败。

如果补救仍失败，状态会变成 `failed_final`，后续不再自动重试。

## WebUI 打不开或数据为空

检查：

- 插件是否已启用。
- AstrBot Dashboard 中是否进入 `chat_plus / noram_group_chat_plus` 的插件页。
- SQLite 是否初始化，群里发 `gcp_status` 看路径。
- Page API 前缀是否被代理或前端缓存影响。
- 浏览器控制台是否有请求错误。

兼容前缀：

```text
/astrbot_plugin_group_chat_plus/page
/noram/page
/noram_group_chat_plus/page
```

当前版没有独立 Web server。旧文档里的独立端口、登录账号、密码、JWT、`enable_web_panel` 都不适用于当前版本。

## 市场仍提示更新

本地签名版的防更新策略是：

- `metadata.yaml` 的 `name` 为 `noram_group_chat_plus`。
- `metadata.yaml` 的 `repo` 为 `""`。
- `@register(...)` 使用同一本地名和空仓库地址。

如果仍提示更新：

- 确认 AstrBot 加载的是当前本地目录。
- 确认没有另一个同源插件副本。
- 重启 AstrBot 后再检查插件列表。
- 确认没有手动把 `repo` 改回远程仓库地址。

## 数据目录看起来不是新名字

这是预期行为。本地签名版只改插件运行名，不迁移业务数据。

业务数据仍在：

```text
data/plugin_data/noram
```

不要手动迁移到 `data/plugin_data/noram_group_chat_plus`，否则旧上下文、图片状态、注意力/冷却等持久化信息可能断开。

## 重置命令没反应

检查：

- 是否在群聊中发送。
- 当前群是否启用插件。
- 命令消息是否纯文本。
- 发送者是否在对应白名单。
- `enable_group_chat` 是否开启。

白名单为空表示所有用户可用；非空时只允许列表中的用户 ID。

## 回复重复或像卡住一样重复说同一句

检查：

- `enable_duplicate_filter` 是否开启。
- `duplicate_filter_check_count` 是否过小或过大。
- `enable_duplicate_time_limit` 和 `duplicate_filter_time_limit` 是否符合群节奏。
- 主 LLM 是否因为空响应重试后返回相同内容。

处理建议：

- 保持重复拦截开启。
- 降低最终回复温度或换稳定模型。
- 确认保存到 SQLite 的 bot 回复没有被保存前过滤成空或相同模板。

## 合并转发或入群消息解析无效

这些能力主要面向 `aiocqhttp` / OneBot v11。

检查：

- 平台是否支持对应 API。
- `enable_forward_message_parsing` 或 `enable_welcome_message_parsing` 是否开启。
- OneBot 实现是否允许拉取转发或成员信息。
- 嵌套转发是否超过 `forward_max_nesting_depth` 或 API 次数限制。

非支持平台会跳过增强，不影响普通消息。
