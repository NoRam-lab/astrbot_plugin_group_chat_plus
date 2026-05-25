# 配置指南

配置字段来自 `_conf_schema.json`。AstrBot Dashboard 中按分组展示，但插件内部会把分组配置展开为旧版扁平 key，因此旧配置仍可继续读取。

## 配置优先级建议

首次启用时先只调这几类：

1. 基础开关：确认群是否启用。
2. 读空气与上下文：控制 bot 多常插话、看多少历史。
3. 图片处理：需要视觉理解时再开。
4. 等待窗口：群友常分段说话时再开。
5. 记忆注入：LivingMemory 稳定后再接入。

## 基础与权限

| 配置 | 默认值 | 说明 |
| --- | --- | --- |
| `enable_group_chat` | `true` | 群聊功能总开关 |
| `enabled_groups` | `[]` | 留空为所有群启用，填写群号后仅指定群启用 |
| `enable_debug_log` | `false` | 输出详细流程日志，排查后建议关闭 |
| `plugin_gcp_reset_allowed_user_ids` | `[]` | `gcp_reset` 白名单，空列表表示不限制 |
| `plugin_gcp_reset_here_allowed_user_ids` | `[]` | `gcp_reset_here` 白名单，空列表表示不限制 |
| `gcp_clear_image_cache_allowed_user_ids` | `[]` | `gcp_clear_image_cache` 白名单，空列表表示不限制 |

## AI 判断与回复

| 配置 | 默认值 | 说明 |
| --- | --- | --- |
| `decision_ai_provider_id` | `""` | 读空气 AI Provider，留空使用默认 Provider |
| `initial_probability` | schema 为 `0.02` | 普通消息进入读空气前的基础概率；代码仍保留旧配置兼容兜底 |
| `after_reply_probability` | `0.8` | bot 回复后临时提升概率 |
| `probability_duration` | `120` | 概率提升持续秒数 |
| `decision_ai_prompt_mode` | `append` | 读空气额外提示词追加或覆盖默认提示词 |
| `decision_ai_extra_prompt` | `""` | 读空气自定义提示词 |
| `decision_ai_timeout` | `30` | 读空气 AI 超时秒数，超时默认不回复 |
| `decision_ai_max_tokens` | `4` | 读空气最大输出 token，目标只返回 `yes/no` |
| `read_air_blacklist_user_ids` | `[]` | 指定用户普通消息只记录，不主动读空气 |
| `suppress_unfinished_agent_llm_results` | `true` | 发送前拦截工具调用中的临时 LLM 回复，只放行最终回复 |
| `reply_ai_prompt_mode` | `append` | 最终回复额外提示词追加或覆盖默认提示词 |
| `reply_ai_extra_prompt` | `""` | 最终回复自定义提示词 |
| `enable_tools_reminder` | `false` | 是否把可用工具注入最终回复 prompt |
| `tools_reminder_persona_filter` | `false` | 是否按当前人格工具配置过滤工具提醒 |
| `reply_timeout_warning_threshold` | `120` | 整体处理耗时超过该秒数时记录警告 |
| `reply_generation_timeout_warning` | `60` | 最终回复生成耗时超过该秒数时记录警告 |
| `enable_same_chat_parallel_reply` | `true` | 同群多条根消息是否可并行、独立走完整回复流程 |
| `concurrent_wait_max_loops` | `10` | 关闭同群并行后，同会话并发消息等待最大循环次数 |
| `concurrent_wait_interval` | `1.0` | 关闭同群并行后，并发等待每轮间隔秒数 |

建议读空气 Provider 使用轻量、稳定、非深度推理模型。最终回复 Provider 可以更强，但要关注空响应重试和 fallback 成本。

### 同群并行语义

`enable_same_chat_parallel_reply=true` 是当前推荐默认值。它的含义是：同一个群里，多条已经通过基础过滤和概率筛选的根消息，可以同时进入图片/上下文、读空气、等待窗口、记忆预取、最终回复、装饰和发送后保存链路。

并行模式下，等待窗口不再吸收其它消息。每条根消息都有自己的窗口 key 和 `WaitWindowBuffer`，所以用户 B 的消息不会写进用户 A 的窗口，同一用户连续发的第二条根消息也不会被第一条窗口提前拦截返回。

`enable_same_chat_parallel_reply=false` 时恢复旧串行行为：同一 runtime 会话已有消息处理中，新消息会按 `concurrent_wait_max_loops` / `concurrent_wait_interval` 等待；同一用户窗口期内的后续消息可以被等待窗口合批吸收。

## 消息解析与上下文

| 配置 | 默认值 | 说明 |
| --- | --- | --- |
| `include_timestamp` | `true` | 在消息中加入发送时间 |
| `include_sender_info` | `true` | 在消息中加入发送者 ID 和名字 |
| `enable_forward_message_parsing` | `false` | 解析 OneBot 合并转发 |
| `forward_max_nesting_depth` | `3` | 合并转发嵌套解析深度 |
| `enable_welcome_message_parsing` | `false` | 解析新成员入群消息 |
| `welcome_message_mode` | `skip_probability` | 入群消息进入流程的模式 |
| `enable_memory_injection` | `false` | 是否接入长期记忆插件 |
| `memory_plugin_mode` | `legacy` | `legacy` 或 `livingmemory` |
| `livingmemory_version` | `v2` | LivingMemory 架构版本 |
| `livingmemory_top_k` | `5` | LivingMemory 每次召回条数 |
| `memory_insertion_timing` | `post_decision` | 记忆注入到读空气前或最终回复前 |
| `max_context_messages` | `-1` | 最终回复读取热库历史条数，`-1` 受内部硬上限保护 |
| `decision_context_messages` | `30` | 读空气读取热库历史条数 |
| `custom_storage_max_messages` | `500` | 旧配置兼容项，当前主链路使用 SQLite |
| `gcp_hot_retention_days` | `2` | 热库保留天数 |
| `gcp_cold_retention_days` | `90` | 冷库保留天数 |
| `gcp_cold_max_messages_per_chat` | `50000` | 每群冷库最大消息数 |
| `gcp_maintenance_interval_hours` | `24` | 自动归档维护间隔小时 |

`decision_context_messages` 和 `max_context_messages` 是两个独立概念。前者影响是否插话，后者影响回复内容。

## 图片处理

| 配置 | 默认值 | 说明 |
| --- | --- | --- |
| `enable_image_processing` | `false` | 插件自有图片理解主开关 |
| `image_to_text_scope` | `mention_only` | 图片转写适用范围 |
| `image_to_text_provider_id` | `""` | 视觉模型 Provider |
| `image_to_text_prompt` | `请详细描述这张图片的内容` | 图片转写用户提示词 |
| `image_to_text_system_prompt` | `""` | 图片转写系统提示词 |
| `image_to_text_timeout` | `60` | 图片转写超时秒数 |
| `max_images_per_message` | `10` | 单条消息最多处理图片数 |
| `active_image_understanding_blacklist_user_ids` | `[]` | 指定用户图片不主动理解，仅被引用时补救 |
| `enable_image_importance_gate` | `true` | 图片重要性门控 |
| `image_keep_threshold` | `0.35` | 图片保留阈值 |
| `image_burst_window_seconds` | `90` | 刷图窗口秒数 |
| `image_burst_soft_limit` | `3` | 刷图软限 |
| `image_burst_hard_limit` | `8` | 刷图硬限 |
| `image_burst_min_factor` | `0.15` | 刷图时最低保留系数 |
| `image_batch_soft_limit` | `2` | 单消息图片批量软限 |
| `image_batch_hard_limit` | `6` | 单消息图片批量硬限 |
| `image_batch_min_factor` | `0.2` | 批量图片最低保留系数 |
| `enable_image_spam_gate` | `true` | 图片刷图冷却门 |
| `image_spam_batch_soft_limit` | `2` | 刷图门软限 |
| `image_spam_batch_hard_limit` | `6` | 刷图门硬限 |
| `image_spam_cooldown_seconds` | `120` | 刷图冷却秒数 |
| `enable_image_importance_gate_log` | `true` | 输出图片门控日志 |
| `enable_image_description_cache` | `false` | 图片说明缓存 |
| `image_description_cache_max_entries` | `500` | 图片缓存最大条数 |

开启图片理解前，请先确认视觉 Provider 稳定。图片失败会记录状态，不会直接阻塞整个群聊流程。

## 关键词与指令过滤

| 配置 | 默认值 | 说明 |
| --- | --- | --- |
| `trigger_keywords` | `[]` | 触发关键词 |
| `keyword_smart_mode` | `false` | 关键词是否保留读空气判断 |
| `blacklist_keywords` | `[]` | 命中后不触发 |
| `record_blacklist_keyword_messages` | `false` | 命中黑名单关键词后是否仍落库 |
| `enable_user_blacklist` | `false` | 是否启用用户黑名单 |
| `blacklist_user_ids` | `[]` | 黑名单用户 ID |
| `enable_command_filter` | `true` | 是否过滤命令 |
| `record_filtered_command_messages` | `false` | 被指令过滤的消息是否仍落库 |
| `command_prefixes` | `/ ! #` | 命令前缀 |
| `enable_full_command_detection` | `false` | 是否启用完整命令检测 |
| `full_command_list` | `new help reset` | 完整命令列表 |
| `enable_command_prefix_match` | `false` | 是否启用命令前缀匹配 |
| `command_prefix_match_list` | `[]` | 命令前缀匹配列表 |

## 表情包与戳一戳

| 配置 | 默认值 | 说明 |
| --- | --- | --- |
| `enable_emoji_filter` | `false` | 识别表情包并降低概率 |
| `emoji_probability_decay` | `0.7` | 表情包概率衰减系数 |
| `emoji_decay_min_probability` | `0.1` | 表情包衰减最低概率 |
| `poke_message_mode` | `bot_only` | 戳一戳处理模式 |
| `poke_bot_skip_probability` | `true` | 戳 bot 是否跳过概率 |
| `poke_bot_probability_boost_reference` | `0.3` | 戳 bot 概率参考值 |
| `poke_reverse_on_poke_probability` | `0.0` | 收到戳一戳后反戳概率 |
| `enable_poke_after_reply` | `false` | 回复后是否戳发送者 |
| `poke_after_reply_probability` | `0.15` | 回复后戳一戳概率 |
| `poke_after_reply_delay` | `0.5` | 回复后戳一戳延迟秒数 |
| `enable_poke_trace_prompt` | `false` | 是否注入戳一戳轨迹提示 |
| `poke_trace_max_tracked_users` | `5` | 戳一戳轨迹最多跟踪用户 |
| `poke_trace_ttl_seconds` | `300` | 戳一戳轨迹保留秒数 |
| `poke_enabled_groups` | `[]` | 戳一戳启用群，空列表按全局逻辑 |
| `enable_ignore_at_others` | `false` | 是否忽略 `@其他人` |
| `ignore_at_others_mode` | `strict` | 忽略 `@其他人` 的模式 |
| `enable_ignore_at_all` | `false` | 是否忽略 `@all` |

## 注意力与拟人增强

这一组参数较多，建议先按功能开关理解：

| 配置 | 默认值 | 说明 |
| --- | --- | --- |
| `enable_attention_mechanism` | `false` | 注意力系统总开关 |
| `attention_increased_probability` | `0.9` | 注意力提高后的概率参考 |
| `attention_decreased_probability` | `0.1` | 注意力降低后的概率参考 |
| `attention_duration` | `120` | 注意力持续时间 |
| `attention_max_tracked_users` | `10` | 每群最多跟踪用户数 |
| `attention_decay_halflife` | `300` | 注意力半衰期 |
| `enable_attention_emotion_detection` | `false` | 注意力情绪检测 |
| `enable_attention_spillover` | `true` | 注意力溢出 |
| `enable_attention_cooldown` | `true` | 注意力冷却 |
| `enable_conversation_fatigue` | `false` | 对话疲劳 |
| `enable_humanize_mode` | `false` | 拟人沉默/兴趣模式 |
| `humanize_interest_keywords` | `[]` | 兴趣话题关键词 |
| `humanize_interest_boost_probability` | `0.3` | 兴趣话题概率加成 |

更细的步长、阈值、冷却、疲劳等级和否定词配置都在 Dashboard 中可调。高频群建议先只开启回复密度限制，再逐步尝试注意力和拟人模式。

## 情绪与频率调整

| 配置 | 默认值 | 说明 |
| --- | --- | --- |
| `enable_mood_system` | `true` | 群情绪追踪 |
| `enable_negation_detection` | `true` | 情绪关键词否定检测 |
| `mood_decay_time` | `300` | 情绪衰减时间 |
| `mood_cleanup_threshold` | `3600` | 情绪状态清理阈值 |
| `enable_frequency_adjuster` | `true` | 发言频率调整 |
| `frequency_check_interval` | `180` | 频率检查间隔秒数 |
| `frequency_analysis_timeout` | `20` | 频率分析超时秒数 |
| `frequency_adjust_duration` | `360` | 频率调整持续秒数 |
| `frequency_analysis_message_count` | `15` | 频率分析读取消息数 |
| `frequency_min_message_count` | `8` | 触发频率分析的最小消息数 |
| `frequency_decrease_factor` | `0.75` | 频率过高时概率降低系数 |
| `frequency_increase_factor` | `1.1` | 频率过低时概率提高系数 |
| `frequency_min_probability` | `0.01` | 频率调整后最低概率 |
| `frequency_max_probability` | `0.6` | 频率调整后最高概率 |
| `enable_typing_simulator` | `true` | 回复延迟模拟 |
| `typing_speed` | `15.0` | 模拟打字速度 |
| `typing_max_delay` | `3.0` | 最大延迟秒数 |
| `typing_delay_timeout_warning` | `5` | 延迟模拟警告阈值 |

## 动态概率与消息质量

| 配置 | 默认值 | 说明 |
| --- | --- | --- |
| `enable_global_time_control` | `true` | 全局时间响应控制 |
| `global_time_control_rules` | 默认深夜规则 | 按时间段控制普通和强触发放行 |
| `global_time_control_apply_to_at` | `true` | 时间控制是否作用于 `@bot` |
| `global_time_control_apply_to_keyword` | `true` | 时间控制是否作用于关键词 |
| `global_time_control_apply_to_reply` | `true` | 时间控制是否作用于引用回复 |
| `enable_reply_density_limit` | `true` | 回复密度限制 |
| `reply_density_window_seconds` | `300` | 回复密度窗口秒数 |
| `reply_density_max_replies` | `3` | 窗口内硬限回复次数 |
| `reply_density_soft_limit_ratio` | `0.6` | 开始衰减的软限比例 |
| `reply_density_ai_hint` | `true` | 是否把密度提示注入读空气 AI |

## AI 回复内容过滤

| 配置 | 默认值 | 说明 |
| --- | --- | --- |
| `enable_output_content_filter` | `false` | 发送前过滤 |
| `output_content_filter_rules` | 常见思考标签规则 | 发送前过滤规则 |
| `enable_save_content_filter` | `false` | 保存前过滤 |
| `save_content_filter_rules` | 常见内部提示规则 | 保存前过滤规则 |

过滤规则支持范围过滤、头部过滤和尾部过滤。发送过滤不影响保存内容，保存过滤不影响用户看到的内容。

## 群聊等待窗口

| 配置 | 默认值 | 说明 |
| --- | --- | --- |
| `enable_group_wait_window` | `false` | 是否启用等待窗口 |
| `group_wait_window_timeout_ms` | `3000` | 等待时长毫秒 |
| `group_wait_window_max_extra_messages` | `3` | 最多收集追加消息数 |
| `group_wait_window_max_users` | `5` | 同一 runtime 会话内最大活跃窗口数 |
| `group_wait_window_attention_decay_per_msg` | `0.05` | 串行合批时按追加消息数修正注意力 |
| `group_wait_window_merge_at_messages` | `false` | 串行合批模式下，窗口期内合并同用户 `@bot` 消息 |
| `group_wait_window_merge_at_list_mode` | `whitelist` | 合并名单模式 |
| `group_wait_window_merge_at_user_list` | `[]` | 合并用户列表 |

等待窗口在两种并发模式下表现不同：

- 并行模式：每条通过筛选的根消息独立创建窗口。达到 `group_wait_window_max_users` 上限时只跳过等待，不会跳过读空气或最终回复流程。
- 串行模式：同一用户窗口期内的后续消息会被当前窗口吸收并提前返回，适合把分段消息合成一次回复。
- `group_wait_window_merge_at_messages` 只在串行合批语义下有效；并行模式下 `@bot` 消息按独立根消息继续完整处理。

## AI 重复消息拦截

| 配置 | 默认值 | 说明 |
| --- | --- | --- |
| `enable_duplicate_filter` | `true` | 是否拦截重复回复 |
| `duplicate_filter_check_count` | `5` | 参考最近几条 bot 回复 |
| `enable_duplicate_time_limit` | `true` | 是否限制重复检测时效 |
| `duplicate_filter_time_limit` | `1800` | 重复检测时间窗口秒数 |

## 推荐组合

低成本日常群：

```json
{
  "initial_probability": 0.02,
  "max_context_messages": 60,
  "decision_context_messages": 25,
  "enable_memory_injection": false,
  "enable_image_processing": false,
  "enable_reply_density_limit": true
}
```

角色扮演/娱乐群：

```json
{
  "initial_probability": 0.03,
  "after_reply_probability": 0.8,
  "enable_group_wait_window": true,
  "enable_humanize_mode": true,
  "enable_attention_mechanism": true,
  "enable_mood_system": true
}
```

图片较多的群：

```json
{
  "enable_image_processing": true,
  "image_to_text_provider_id": "你的视觉模型Provider",
  "image_to_text_scope": "mention_only",
  "enable_image_spam_gate": true,
  "enable_image_description_cache": true
}
```
