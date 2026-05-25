# WebUI 与命令

Group Chat Plus 提供群聊命令和 AstrBot 插件页 WebUI。两者都操作 GCP 自有 SQLite 和插件运行期状态，不会清理平台官方聊天记录。

当前版本使用 AstrBot Plugin Page API，不再包含原版 `web/` 独立服务、独立登录页、认证面板或额外监听端口。Dashboard 的登录态就是 WebUI 的访问边界。

## WebUI 入口

```text
AstrBot Dashboard -> 插件 -> chat_plus / noram_group_chat_plus -> GCP 上下文管理
```

Page API 兼容三个前缀：

```text
/astrbot_plugin_group_chat_plus/page
/noram/page
/noram_group_chat_plus/page
```

这样既兼容插件目录名，也兼容旧运行名和本地签名名。

## WebUI 能力

WebUI 管理的是 GCP 自有 SQLite 短期上下文。

支持：

- 查看当前群或全局统计。
- 查询热库、冷库或两者。
- 按平台、群、角色、图片状态、触发来源筛选。
- 关键词搜索。
- 编辑消息内容、发送者名、图片状态和图片说明。
- 单条软删除。
- 批量软删除。
- 恢复软删除消息。
- 手动执行归档维护。

软删除消息默认不会进入后续 prompt，但仍可在 WebUI 中显示并恢复。

## Page API

`core/page_api.py` 注册的接口：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/stats` | 获取 scoped 和 global 状态 |
| `GET` | `/messages` | 分页查询消息 |
| `POST` | `/messages/update` | 更新消息字段 |
| `POST` | `/messages/soft-delete` | 软删除单条消息 |
| `POST` | `/messages/batch-soft-delete` | 批量软删除消息 |
| `POST` | `/messages/restore` | 恢复软删除消息 |
| `POST` | `/maintenance` | 手动执行归档维护 |

常见查询参数：

- `page`、`page_size`：分页，单页最大 200。
- `db`：`hot`、`cold` 或实现支持的范围。
- `keyword`：关键词搜索。
- `platform_id`、`chat_id`：限定平台和会话。
- `role`：用户或 assistant 等角色。
- `image_status`：图片状态。
- `source`：触发来源。
- `include_deleted`：是否包含软删除消息。

接口依赖 AstrBot Dashboard 登录态，不额外提供独立端口、密码或 JWT。

如果看到旧文档里的 `enable_web_panel`、独立 Web server、用户名密码或 JWT 配置，请忽略；这些是 `astrbot_plugin_group_chat_plus-main_old` 的说明，不适用于当前魔改版。

## `gcp_status`

群聊发送：

```text
gcp_status
```

用于查看当前群和全局状态：

- 当前群热库消息数。
- 当前群冷库消息数。
- 全局写入队列长度。
- 图片成功、待补救、最终失败数量。
- FTS5 是否可用。
- 热库和冷库数据库路径。
- 最近错误摘要。

这是日常排查的第一入口。

## `gcp_reset_here`

群聊发送：

```text
gcp_reset_here
```

作用：

- 清理当前群的 GCP SQLite 上下文。
- 清理当前群运行期状态，例如等待窗口、快照、概率、注意力、冷却、情绪等。
- 设置历史截止点，避免重置前的旧消息被重新读入 GCP 流程。
- 记录重启信息并请求重启 AstrBot。

限制：

- 只在群聊生效。
- 需要当前群启用插件。
- 消息必须是纯文本命令。
- 受 `plugin_gcp_reset_here_allowed_user_ids` 白名单控制。

## `gcp_reset`

群聊发送：

```text
gcp_reset
```

作用：

- 清理全局 GCP SQLite 上下文。
- 清理插件全局运行期状态。
- 删除插件本地缓存文件。
- 设置历史截止点。
- 记录重启信息并请求重启 AstrBot。

限制：

- 只在群聊生效。
- 需要当前群启用插件。
- 消息必须是纯文本命令。
- 受 `plugin_gcp_reset_allowed_user_ids` 白名单控制。

`gcp_reset` 影响所有会话，建议只给可信管理员开放。

## `gcp_clear_image_cache`

群聊发送：

```text
gcp_clear_image_cache
```

作用：

- 清空本地图片描述缓存。
- 记录清理前缓存条数。
- 请求重启 AstrBot。

限制：

- 只在群聊生效。
- 需要当前群启用插件。
- 消息必须是纯文本命令。
- 受 `gcp_clear_image_cache_allowed_user_ids` 白名单控制。

此命令不会删除 SQLite 中已经保存的消息或图片状态，只清理图片说明缓存。

## 权限建议

- 日常群可以把 `gcp_status` 留给所有人。
- `gcp_reset_here` 建议限制给群管理员或 bot 维护者。
- `gcp_reset` 建议只给插件维护者。
- `gcp_clear_image_cache` 在视觉模型成本较高时也建议加白名单。

## 数据路径提醒

本地签名版仍使用旧业务数据目录：

```text
data/plugin_data/noram
```

WebUI 中显示的热库和冷库路径应位于该目录下。看到 `noram_group_chat_plus` 作为运行名是正常的，不代表数据已迁移。
