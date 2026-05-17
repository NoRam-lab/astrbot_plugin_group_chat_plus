# 群聊增强插件 (Chat Plus)

---

<div align="center">

[![Version](https://img.shields.io/badge/version-v1.2.2-blue.svg)](https://github.com/Him666233/astrbot_plugin_group_chat_plus)
[![AstrBot](https://img.shields.io/badge/AstrBot-%E2%89%A5v4.11.0-green.svg)](https://github.com/AstrBotDevs/AstrBot)
[![License](https://img.shields.io/badge/license-AGPL--3.0-orange.svg)](LICENSE)

一个以 **AI读空气** 为核心的群聊增强插件，让你的Bot更懂氛围、更自然地参与群聊互动

## ⚠️ 注意: AstrBot平台自带的说明文档查看器有一定的问题，可能会导致点击跳转按钮之后，没办法跳转到正常的说明文件中，建议直接在项目的github仓库中查看或者是直接下载压缩包，然后解压自行翻看

[快速开始](#-快速开始) • [功能总览](#-功能总览) • [推荐配置](#-完整推荐配置) • [更新日志](#-更新日志)

[深度指南与常见问题](docs/ARCHITECTURE.md) • [消息工作流程详解](docs/MESSAGE_WORKFLOW.md) • [配置项完整参考](docs/CONFIG_REFERENCE.md) • [项目结构说明](docs/PROJECT_STRUCTURE.md) • [桌面端兼容说明](docs/DESKTOP_COMPATIBILITY.md)

</div>

---

## 🚨 重要声明：防盗版与安全警告

> **本插件完全免费且开源，不会以任何形式进行商业收费！**
>
> 近期我们发现有人疑似在其他渠道贩卖本插件。在此郑重声明：
>
> - 本插件**永久免费、开源**，不存在任何付费版本，不会进行任何商业性收费行为
> - **唯一官方开源仓库**：[GitHub - Him666233/astrbot_plugin_group_chat_plus](https://github.com/Him666233/astrbot_plugin_group_chat_plus)
> - **唯一官方获取渠道**：上述 GitHub 仓库 及 内部内测交流群（QQ群：1021544792）
> - 从其他渠道获取到的版本**可能被篡改并包含恶意代码或病毒**，请务必通过官方渠道获取，保障自身安全
>
> **如果有人向你收费或在非官方渠道分发本插件，请提高警惕！**

---

## ⚠️ 使用前必读

> **关闭AstrBot官方自带的主动回复功能！** 本插件的智能回复与官方主动回复是完全独立的两套系统，同时开启会导致重复回复、刷屏、API费用翻倍等问题。如果您有其他主动回复/主动对话类插件也建议关闭，避免冲突。

> **必须开启平台的"群聊上下文感知"！** 这是本插件正常工作的关键前提之一。不开启时，插件拿到的群聊历史与上下文信息会明显不完整，可能导致读空气判断失真、回复上下文错乱、主动对话判断不准，严重时会表现成"像没理解群里刚刚在聊什么"。推荐配置与原因说明见：[深度指南 → 平台配置](docs/ARCHITECTURE.md#推荐的平台设置)

> **图片处理须知：** 目前必须配置 `image_to_text_provider_id`（图片转文字提供商ID）才能正常处理图片。留空直接传递图片给多模态AI的方式目前无法可靠工作。

## ⚠️ 私聊功能警告

> **私聊处理功能目前仍在开发中，请勿开启 `enable_private_chat`！** 当前版本的私聊模块尚未完善，开启可能导致异常行为。请耐心等待后续版本正式支持。

---


## ❤️ 支持作者（自愿捐款）

> 本插件由个人开发者用爱发电、投入大量精力独立维护，开发与持续更新压力不小。如果你觉得这个插件对你有帮助，欢迎自愿捐款支持作者，让作者有更多动力继续维护和改进。

**⚠️ 重要声明：**

- **捐款完全自愿** — 捐不捐功能完全一样，不会有任何功能差异或特殊对待，纯粹是对作者的支持和认可
- **官方唯一捐款渠道**：[爱发电 (Afdian) — afdian.com/a/chat_plus](https://afdian.com/a/chat_plus)
- **内部交流群**：QQ群 **1021544792**（可在群内直接联系作者本人）
- **⚠️ 防骗警告**：除上述爱发电链接和 QQ 群内与作者本人直接联系外，**任何其他渠道声称代表本插件接受捐款的皆为骗子**，请务必提高警惕，谨防上当受骗

---

## 🔐 Web 管理面板安全提醒

> **强烈建议启用 Web 端功能** — Web 管理面板提供了可视化配置编辑、实时统计、会话管理等完善的插件管理体验，比传统 JSON 配置界面更加直观易用。

> **⚠️ 从旧版本升级的用户请务必注意**：v1.2.2 版本对 Web 面板安全机制进行了全面升级（Argon2id 密码哈希、JWT + HttpOnly Cookie + 服务端会话表等），**请尽快登录一次 Web 面板，让旧版密码自动透明升级为更强的 Argon2id 哈希，同时堵住各项安全漏洞**，确保您的面板安全。

### 关于配置文件：为什么能下载但不能上传？

> 出于安全考虑，Web 面板支持**下载**配置文件，但**不支持直接上传**配置文件。原因是配置文件内部包含了 Web 面板的敏感安全配置（如密码哈希、JWT 密钥存储路径、IP 访问控制规则等），如果直接允许上传，在上传校验未完全覆盖所有安全字段的情况下，攻击者可能通过伪造配置文件替换对应的安全配置，从而导致面板被入侵。

> **如需修改配置**，建议通过以下方式操作：
> - **方式一（推荐）**：直接在 Web 管理面板中可视化修改各项配置并保存
> - **方式二**：手动前往配置文件所在目录，直接编辑或替换配置文件
>
> **配置文件路径**：`<AstrBot 数据目录>/data/config/astrbot_plugin_group_chat_plus_config.json`
>
> AstrBot 插件配置通常存放在 `data/config/` 目录下，插件自身的运行数据存放在 `data/plugin_data/astrbot_plugin_group_chat_plus/` 目录下。
>
> **不确定当前使用的配置文件叫什么名字？** 登录 Web 面板后，在「核心控制面板」或「科技树展览」菜单面板的右下角即可看到当前生效的配置文件名称。

---

## 📚 文档导航

> 不知道从哪里看起？根据你的需求选择对应的文档：

| 你想了解… | 去看这个文档 |
|-----------|-------------|
| **AI 回复太多/太少/读空气不准怎么调？** | [深度指南 → 常见问题排查](docs/ARCHITECTURE.md#ai-回复频率相关问题) |
| **某些 Skill / MCP 工具在开启插件后报参数错配怎么办？** | [深度指南 → 常见问题排查](docs/ARCHITECTURE.md#开启工具提醒后某些-skill--工具出现参数串扰怎么办) |
| **Web 管理面板怎么用？打不开怎么办？** | [深度指南 → Web 管理面板](docs/ARCHITECTURE.md#web-管理面板相关问题) |
| **配置文件怎么下载？下载失败怎么办？** | [深度指南 → 配置文件下载](docs/ARCHITECTURE.md#q-如何下载当前配置文件) |
| **插件的工作原理是什么？为什么要"偷天换日"？** | [深度指南 → 工作原理](docs/ARCHITECTURE.md#一句话概括) |
| **平台的"群聊上下文感知"和"自动理解图片"怎么配？** | [深度指南 → 平台配置](docs/ARCHITECTURE.md#推荐的平台设置) |
| **某个配置项是什么意思？默认值是多少？** | [配置项完整参考](docs/CONFIG_REFERENCE.md) |
| **一条消息从收到到回复经历了什么流程？** | [消息工作流程详解](docs/MESSAGE_WORKFLOW.md) |
| **代码文件结构和各模块职责？** | [项目结构说明](docs/PROJECT_STRUCTURE.md) |
| **使用 AstrBot 桌面端？重启不生效？路径找不到？** | [桌面端兼容说明](docs/DESKTOP_COMPATIBILITY.md) |
| **我用的其他插件和本插件会冲突吗？** | [深度指南 → 兼容性](docs/ARCHITECTURE.md#与其他插件的兼容性) |
| **如果 AstrBot 或其他插件改了内部提示词结构，会不会影响兼容？** | [深度指南 → 兼容性与回退机制](docs/ARCHITECTURE.md#system_prompt-兼容增强与保守回退机制) |
| **第三方插件往 `system_prompt` / `prompt` / `contexts` 注入内容时，AI 现在能看到哪些？** | [深度指南 → 兼容性](docs/ARCHITECTURE.md#与其他插件的兼容性) |
| **记忆插件怎么选？为什么推荐适配过的？** | [深度指南 → 记忆插件](docs/ARCHITECTURE.md#记忆插件的兼容性为什么要用适配过的记忆插件) |

---
## 🤝 插件合作

### 第三方插件兼容性判断

一个其他插件能否与本插件一起使用，取决于它**向 AI 注入提示词的方式**是否匹配以下任意一条保留路径：

| 注入方式 | 说明 | 保留机制 |
|---------|------|---------|
| **向 `system_prompt` 前面插入内容** | 插件在人格设定之前添加了自己的提示词（如规则块、管理指令等） | SystemPromptRewriter 精确命中人格边界，prefix 原样保留 |
| **向 `system_prompt` 后面追加内容** | 插件在人格设定之后追加了提示词（如状态面板、记忆文本等） | SystemPromptRewriter 精确命中人格边界，suffix 原样保留 |
| **向 `req.contexts` 注入对话/工具调用** | 插件在对话历史数组中添加伪造对话示例、协议消息、伪工具调用等 | 差分法提取 → `[第三方插件注入上下文]` 标记合并 |
| **向 `req.prompt` 前后追加长期说明** | 插件在当前用户消息前后附加了记忆说明、解释文本等内容 | 短消息基线分割 → 吸收到 `[第三方插件补充信息]` 固定补充区 |
| **向 `extra_user_content_parts` 追加内容** | 插件通过新版 AstrBot API 在用户消息之外附加内容块 | 原样保护，不做任何修改 |

> **判断方法**：查看该插件的源码，找到它的 `on_llm_request` 钩子，看它修改了 `req` 的哪些字段、是怎么改的（prepend/append/新增）。只要匹配以上任意一条，即可兼容。
>
> 兼容机制的详细原理和风险说明见 [深度指南 → 与其他插件的兼容性](docs/ARCHITECTURE.md#与其他插件的兼容性)。

### AstrBot智能自学习插件

与 [astrbot_plugin_self_learning](https://github.com/NickCharlie/astrbot_plugin_self_learning) 建立官方合作关系：

- **本插件** 负责"智能决策何时回复" — AI读空气、动态概率、注意力机制
- **自学习插件** 负责"智能优化如何回复" — 对话风格学习、人格自动优化、好感度系统

两者功能互补，推荐组合使用。欢迎加入 **QQ群 1021544792** 交流！

### 工具参数串扰排查

如果你发现某些 Skill / MCP 工具在**关闭本插件时正常**、**开启本插件后更容易出现参数错配**，例如：

- `unexpected keyword argument 'silent'`
- `Tool handler parameter mismatch`
- 某个工具收到了明显属于另一个工具的参数

可以优先按这个顺序排查：

1. 确认 AstrBot 当前会话的 `provider_settings.tool_schema_mode`
   - `skills_like`：本插件现在会自动把工具提醒降级为"只展示工具名称与功能描述"
   - `full` / 旧版 AstrBot：仍会完整展示名称、描述和参数
2. 临时关闭 `enable_tools_reminder` 再复测一次
   - 如果问题明显缓解，通常说明是提醒层参数提示过细引发的串扰，而不是工具本身损坏
3. 对照报错工具的真实签名
   - 例如 `astrbot_execute_shell` 只接受 `command / background / env`
   - 如果日志里出现了明显属于其他工具的参数（如 Python 工具常见的 `silent`），就是典型串扰

更详细的背景说明和排障建议见：
- [深度指南 → 开启工具提醒后，某些 Skill / 工具出现参数串扰怎么办？](docs/ARCHITECTURE.md#开启工具提醒后某些-skill--工具出现参数串扰怎么办)

---

## 🆕 v1.2.2 更新亮点

**本次更新带来了全新的 Smart 并发模式、注意力冷却重构、System Prompt 兼容增强、Web 面板安全全面加固，以及多项消息处理链路重构与判断型 AI 增强。**

### Smart 并发模式

- **消息批次智能合并** — 同群多条消息按真实到达顺序注册，最早到达的担任主消息(anchor)，在读空气 AI 前吸收已准备好的后续消息，支持多用户批处理
- **统一上下文回复** — AI 一次性感知来自不同用户的同批次消息，生成连贯统一的自然回复，减少逐条回复的重复感
- **legacy / smart 双模式可切换** — 默认 legacy 传统串行模式保证兜底兼容；切换 smart 后启用智能合并，支持批次回复提示增强
- **与 GWW 独立解耦** — Smart 模式不依赖群聊等待窗口(GWW)，两者可独立使用也可配合

### System Prompt 兼容增强

- **SystemPromptRewriter 三级策略** — 保守增强版 system_prompt 重写器：① **精确命中**（默认，置信度最高）— 从原始 system_prompt 和当前 persona 的 `system_prompt` 文本中提取用户人格内容作为锚点，在平台上调整请求前，从 `raw_system_prompt` 中精确匹配人格边界，将人格之前的内容识别为「第三方插件前置内容（prefix）」，之后的内容识别为「其他插件后置内容（suffix）」并双重保留；② **轻量归一化** — 精确匹配失效时使用人格关键词定位和空白归一化策略重试；③ **保守回退** — 完全无法定位人格时宁重复不缺漏，保证主回复链不断。日志显式提示当前策略与置信度
- **差分法四大通道覆盖** — system_prompt（前/后缀识别）、prompt（短消息基线分割）、contexts（结构特征差分）、extra_user_content_parts（原样保护），全部第三方注入自动保留。5 条兼容路径全面覆盖：[插件合作](#-插件合作) 中列出的所有第三方注入方式均可被本插件的差分法机制自动识别并保留
- **平台提示词构建调整** — 将大型静态系统指令（GCP 插件自身的行为规范、规则和配置说明）从 `prompt` 前端移入 `system_prompt` 尾部，利用 LLM 服务商对 system_prompt 整块缓存优于 prompt 拼接的特性，提高每次 AI 调用的缓存命中概率，不改变原语义。该调整同时增强了与其他插件提示词的共存能力：无论第三方插件向哪个通道（system_prompt/prompt/contexts/extra_user_content_parts）注入内容，本插件通过差分法自动提取并保留，确保 AI 在收到增强后的 system_prompt 的同时，仍能完整看到其他插件注入的提示词信息
- **回退保护** — 识别失败时进入保守兼容模式：宁重复不缺漏，保证主回复链不断，日志显式提示当前策略与置信度
- **第三方插件注入全面保留** — 无论插件向 `system_prompt` 前置/后置、`req.contexts`、`req.prompt`、`extra_user_content_parts` 哪个通道注入内容，差分法均自动识别并保留，AI 可完整看到。兼容其他插件向 `system_prompt` 前插入规则块/管理指令、后追加状态面板/记忆文本，以及向 `req.contexts` 注入对话示例、向 `req.prompt` 前后追加长期说明等场景
- **第三方插件注入透明化** — 其他插件写入 system_prompt、prompt、contexts 的内容均可被 AI 看到并以清晰边界标记分隔（`[第三方插件片段]` / `[第三方插件注入上下文]` / `[第三方插件补充信息]`），不同插件信息不会混淆。注入说明透明的分层引用，保留原文顺序（prefix → persona → suffix）

### 注意力冷却重构

- **候选冷却 → 正式冷却双阶段结构** — 同一用户的消息先进入「未接续谈保护」候选阶段（仅观察同一用户的后续消息），观察期过后再决定是否升级为正式冷却，大幅减少"刚没接上、下一句其实在找 AI"的误伤。候选阶段可配置观察消息数（`pending_cooldown_grace_user_messages`）与最大等待时间（`pending_cooldown_max_wait_seconds`）
- **冷却自动解除** — 正式冷却中的用户达到最大时长（`cooldown_max_duration`，默认 600 秒）后自动解冻，无需必须等到被回复
- **读空气未回复衰减独立化** — 从冷却机制中解耦，可在无冷却模式下单独生效，也可在冷却模式下与正式冷却协同
- **冷却状态纯运行时化** — 冷却数据不再持久化到磁盘，插件/平台重启后自动清空

### Web 面板安全全面升级

- **Argon2id 内存硬化哈希** — 替换 PBKDF2-SHA256 作为默认密码哈希算法（`ARGON2_TIME_COST=3`, `ARGON2_MEMORY_COST=65536`, `ARGON2_PARALLELISM=4`），有效抵抗 GPU 并行暴力破解
- **JWT + HttpOnly Cookie + 服务端会话表** — 会话安全全面升级，支持令牌过期/密码修改/令牌版本轮换/IP 变化时自动要求重新登录，JWT 密钥每次启动自动轮换
- **密码透明迁移** — 旧版本 PBKDF2-SHA256 密码在用户首次登录成功后自动透明升级为 Argon2id，无需手动操作
- **登录 IP 绑定校验** — 可选将客户端 IP 绑定到 JWT 令牌，防止令牌被劫持后在其他网络环境使用
- **全操作令牌校验链** — Web 面板所有 API 操作均需通过 JWT 验证 → 令牌版本校验 → 会话查找 → 会话状态检查 → 过期检查 → IP 绑定检查 → 心跳触摸 的完整安全链
- **后端文件实时保护** — 敏感文件（auth.json、jwt_secret.json、sessions.json、bans.json、access_log）禁止通过 Web API 读取或下载，后端直接拒绝所有对核心安全文件的访问请求；配置文件下载只允许下载插件自身配置文件（`_conf_schema.json` 对应的实际配置数据），API 不接受任何前端传入的文件路径参数，仅在后端通过 `os.path.basename()` 提取安全文件名返回，永远不暴露服务器绝对路径；下载 API 同时返回配置文件在服务器上的相对显示路径（基于 AstrBot 数据目录），方便用户确认而不会泄露系统目录结构
- **安全响应头全面配置** — 所有页面统一注入安全响应头：`X-Content-Type-Options: nosniff`（禁止 MIME 类型嗅探）/ `X-Frame-Options: DENY`（禁止页面被嵌入 frame，防点击劫持）/ `X-XSS-Protection: 1; mode=block`（启用浏览器 XSS 过滤器）/ `Referrer-Policy: no-referrer`（不泄露 Referrer）/ `Permissions-Policy: geolocation=(), microphone=(), camera=()`（禁用敏感硬件 API），全方位防止各类注入攻击
- **Nonce-based 严格 CSP** — Content-Security-Policy 使用每次请求唯一的 Base64 nonce（`secrets.token_urlsafe(24)`），三套独立 CSP 模板分别服务于登录页、面板页和错误/拦截页。script-src 不再依赖 `unsafe-inline`，内联脚本通过 nonce 匹配验证，外部脚本由 `'self'` 放行（同样不经 nonce），从源头阻断 XSS 代码注入
- **防爬虫与速率限制** — 可疑 UA 模式（bot/crawler/spider/scanner 等）自动检测与封禁，扫描路径探测（.php/.asp/.env/.git/wp-admin/.DS_Store 等常见漏洞扫描路径）自动拦截返回错误页，1 分钟滑动窗口速率限制（认证前 `/api/auth/login` 独立限频、认证后其他 API 独立限频，均为 1 分钟滑动窗口），`/robots.txt` 显式禁止所有爬虫收录
- **暴力破解分级锁定** — 登录失败递增锁定：5 次 → 30s / 10 次 → 60s / 15 次 → 300s / 20 次 → 600s；受保护 IP（`web_panel_protected_ips`）永不被封禁
- **IP 访问控制** — 支持白名单/黑名单模式（`web_panel_ip_mode`：`whitelist` 仅允许白名单 IP / `blacklist` 禁止黑名单 IP），白名单 IP 绕过爬虫检测与封禁检查。反向代理部署在同机时自动读取 `X-Real-IP` / `X-Forwarded-For` 头获取真实客户端 IP（环回地址自动信任）；反向代理不在本机时需显式开启 `web_panel_trust_proxy` 才会信任代理头
- **心跳保活机制** — 前端定时心跳请求（`POST /api/auth/heartbeat`）维持会话活性。可见标签页和隐藏标签页使用独立可配置的心跳间隔（`web_panel_heartbeat_visible_interval_seconds` / `web_panel_heartbeat_hidden_interval_seconds`），心跳失败时采用指数退避重试策略（`web_panel_heartbeat_retry_base_seconds` → `web_panel_heartbeat_retry_max_seconds`）。心跳请求不触发认证速率限制，但正常更新服务端会话的 `last_heartbeat_at` 活跃时间戳；若 JWT 令牌过期（24 小时绝对有效期）或密码/令牌版本变更，下一次心跳直接返回 401 由前端统一处理重新登录
- **认证文件物理隔离** — auth.json 与 jwt_secret.json 分离存储，旧版混合文件启动时自动分离
- **日志自动清理** — 访问日志支持按保留天数自动清理（`web_panel_log_auto_clean` / `web_panel_log_retention_days` / `web_panel_log_clean_interval_hours`）

### @消息 / 欢迎消息 / 戳一戳消息处理全面重构

- **@消息处理完全重构** — 重新设计 @ 消息的识别、过滤与上下文构建全链路：区分「纯 @AI」（仅 @机器人，不含其他信息）与「@AI+文字/图片/其他人/全体」场景，通过 `contains_ai`（消息中是否包含 @AI）与 `only_ai`（消息是否仅包含 @AI 无其他内容）双模式判定语义。空 @ 消息默认开启最近上下文强化，关联窗口同时检查消息数量（`single_at_message_reply_link_max_messages`）与时间跨度（`single_at_message_reply_link_max_seconds`），在通过读空气筛选后以中性口吻动态追加上下文提醒（提取近期缓存摘要与最近明确回复对象信息），让 AI 优先参考近期对话但不强行续话
- **欢迎消息解析对齐** — 入群欢迎消息支持四种处理模式（`normal` 正常处理 / `skip_probability` 跳过概率筛选 / `skip_all` 直接忽略 / `parse_only` 仅解析不回复），统一到主消息处理链路，不再独立绕过概率筛选与 AI 决策流程
- **戳一戳消息处理重构** — 支持三种模式（`ignore` 忽略所有 / `bot_only` 仅处理戳机器人 / `all` 处理所有戳一戳），重构为可配置概率跳过（`poke_bot_skip_probability`）和概率增值参考（`poke_bot_probability_boost_reference`），在群聊等待窗口（GWW）中支持 `bypass`（戳一戳绕过 GWW，不打断普通消息的收集）/ `force_close`（戳一戳强制关闭 GWW，优先处理）两种行为模式。戳一戳系统提示词在保存历史时自动过滤，不污染长期上下文
- **三种消息类型链路统一对齐** — @消息、欢迎消息、戳一戳消息的黑名单检查 → 概率筛选 → 读空气决策 → 回复生成全流程完全对齐，极短间隔连续消息场景下不再出现状态错乱。GWW 等待窗口内各消息类型的处理行为可独立配置（@消息 `force_close` / 关键词 `intercept` / 戳一戳 `bypass`），互不干扰

### 判断型 AI 人格选择与额外推理

- **判断型 AI 独立人格配置** — 读空气判断 AI、频率调节 AI、主动对话判断 AI 三个判断链路均可独立选择是否注入人格（`decision_ai_include_persona` / `enable_frequency_ai_include_persona` / `enable_proactive_ai_include_persona`），且可分别指定使用哪一个人格（`decision_ai_persona_name` / `frequency_ai_persona_name` / `proactive_ai_persona_name`），留空则自动跟随当前会话生效人格。填写时必须使用完整人格名，否则系统检测不到时自动回退到当前会话人格，不会导致插件崩溃。回复生成 AI 和主动对话生成 AI 仍按当前会话人格运行（每次调用重新获取，切换会话人格后立即生效），不受此配置影响
- **额外推理全覆盖** — 三个判断型 AI 均支持独立开启额外推理（`enable_decision_ai_reasoning` / `enable_frequency_ai_reasoning` / `enable_proactive_ai_reasoning`）。开启后 AI 在给出最终判定前先自由输出推理块，推理内容由起始标记 `[[GCP_REASONING_START]]` 和截止标记 `[[GCP_REASONING_END]]`（三处共用配置，Web 面板三处入口同步显示与同步生效）包裹，然后在最后一行的标记后单独输出最终判定结果（yes/no 或 正常/过于频繁/过少）。系统通过 `ai_response_filter.py` 自动剥离推理块提取最终判定，不影响下游概率/状态更新。无论是原生带思考能力的模型（如 DeepSeek-R1）还是原生不带思考的模型均支持，让 AI 先推理一段再输出结果，保证答案更加精确
- **推理日志可控** — 每个判断 AI 的推理日志可独立开关与选择输出模式（`processed` 处理后推理块 / `raw` 模型原始文本），方便调试判断依据
- **推理协议自动补充** — 如果用户自定义了判断提示词但未包含额外推理协议（起始标记/截止标记/输出格式说明），系统自动在提示词末尾补充推理格式说明而非退回默认提示词，兼顾自定义语义与推理格式规范

### 冷群缓存自动转正

- **冷群转正机制** — 群聊长时间静默（无新消息）达到配置时间（`idle_cache_flush_delay_seconds`，默认 600 秒，可配置范围 60~7200 秒）后，缓存中尚未被回复的未转正消息自动转正写入持久存储（自定义存储 `chat_history/` + 平台官方历史 `platform_message_history` + 平台官方会话 `conversations`），防止群聊沉默过久导致缓存过期清空、上下文割裂。转正后的消息在下次 AI 回复时可被正常读取作为上下文参考
- **手动开启** — 默认关闭（`enable_idle_cache_flush` 默认 `false`），需手动开启。仅在确实需要长期保留冷群上下文的场景下启用
- **并发安全** — 转正执行前检测会话是否仍被其他处理链路（普通回复/主动对话）占用，忙碌时跳过当次转正在下次调度时重试；转正过程同时收集窗口缓冲消息（`window_buffered=True`），确保 GWW 窗口期内暂存的消息不因等不到后续消息触发而无法转正、最终丢失

### 工具提醒逻辑重构

- **只提醒不控制** — 工具提醒从全局工具列表改为当前会话的 `req.func_tool` 实时生成，自动适应 AstrBot 内置工具（shell/cron/send_message 等）、WebSearch、知识库、沙箱、MCP、其他插件的 `@llm_tool` 注册工具等动态工具集。工具提醒仅做提醒和提示义务，不拦截也不限制 AI 的实际工具调用，AI 可完整调用平台上所有可用工具而不受提醒内容限制
- **skills_like 模式智能降级** — 检测到 `provider_settings.tool_schema_mode=skills_like` 时，自动只展示工具名称与功能描述，不展开参数列表。这样做是为了尽量不干扰 AstrBot 在 `skills_like` 模式下的两阶段工具 schema 暴露与 re-query 流程，同时减少跨工具参数串扰（如 `unexpected keyword argument 'silent'` 等典型串扰错误）。当 `tool_schema_mode=full` 或旧版 AstrBot 未提供该字段时，保持完整展示（名称 + 描述 + 参数）
- **生成失败静默降级** — 提醒文本生成异常时自动跳过提醒而非阻断回复流程
- **提醒文本历史过滤** — `[系统提示-工具提醒开始]...[系统提示-工具提醒结束]` 标记块在保存历史时自动清除，不污染上下文

### 多轮工具调用交叉保存

- **按执行顺序交错保存** — AI 在单次推理中调用多个工具或发生多轮工具调用时，按实际执行顺序将 AI 中间推理文本与工具调用记录（调用名称 + 参数 + 返回值）交错写入对话历史，而非将所有工具调用记录全部堆在末尾。这样 AI 在后续轮次中能按真实执行时序理解工具调用上下文，而非面对一堆脱序的工具结果
- **格式兼容** — 同时兼容 ToolCall 对象和 dict 两种工具调用格式，支持 AI 无最终文本输出（仅工具调用）时的兜底保存
- **交叉保存时机** — 每次工具调用完成即刻保存到历史，而非等待全部调用结束后批量写入，确保即使中途某次工具调用失败，已完成的工具调用记录也不丢失

### Web 面板智能搜索与 UI 优化

- **科技树智能搜索** — 在科技树菜单顶部搜索框（快捷键 `Ctrl+K` / `Cmd+K`）输入关键词，可智能搜索所有配置项的名称（最高权重 35 分）、配置键名（32 分）、键标签（14 分）、提示文本（12 分）和描述文本（8 分），按匹配度加权排序。支持空格分词多关键词组合搜索、中文紧凑匹配（忽略空格差异）、键盘上下键导航结果列表。点击结果后自动定位到科技树中对应节点并高亮闪烁，不用再在大量配置中逐个翻找。搜索索引在各面板视图加载时自动构建，覆盖科技树中的所有配置节点
- **科技树连接线修复** — 修复连接线在部分节点布局下不准确与不直观的问题，同时跳过 `branchType: alternative` 分支步骤的连接线绘制（这些分支步骤在视觉上不需要连线连接），让科技树视图更加清晰
- **手机端全面适配** — 侧边栏改为滑入式抽屉（带毛玻璃遮罩层，点击遮罩自动关闭），顶部增加移动端专用导航栏（汉堡菜单 + 品牌标题 + 版本号），搜索框全宽显示并支持触屏输入，搜索结果改为底部抽屉式面板（最大高度 `50dvh`，避免遮挡过多内容），配置区域使用动态视口高度（`100dvh` 替代 `100vh`，解决移动浏览器地址栏变化导致的布局问题），按钮文字和间距适配小屏触控，内容区开启 `-webkit-overflow-scrolling: touch` 支持 iOS 惯性滚动
- **动画与视觉优化** — 优化侧边栏过渡动画、步骤节点入场动效、粒子路径动画的贝塞尔曲线缓动参数，让交互更加直观自然。登录页同样支持移动端适配
- **关联配置可视化标记** — 对存在关联或互斥关系的配置项增加特殊标志符（如关联箭头、互斥警告图标）与补充说明文字，多层级配置选项（如主开关下的子选项）在面板中展示完整的生效条件与优先级说明，让用户一眼看清配置之间的依赖与影响关系

### AI 调用错误处理全面格式化

- **5 类错误自动识别** — `format_ai_error()` 自动分类：① HTML 网关错误（502/503/504 状态码，含 Cloudflare "Please enable cookies" 等错误页面提示）→「AI 服务商故障」；② 上游空输出（模型返回空字符串或仅含空白字符）→「上游模型返回空输出」；③ HTTP 状态码错误（400-599，排除已归入网关的 502/503/504）→「请求参数/配置问题」；④ 网络错误（timeout/connection refused/DNS 解析失败等）→「网络问题」；⑤ 未匹配错误 → 自动截断至 300 字符防止日志爆炸
- **零副作用原则** — AI 调用失败时视为「从未发生」：不更新概率评分、不触发注意力变化、不延长冷却、不刷新沉默计时器、不改变任何内部状态，确保单次故障不影响后续判断
- **详细日志化输出** — 每次 AI 调用失败的原因（具体错误类型如 `TimeoutError`/`ConnectionError`/`APIStatusError`）、HTTP 状态码、错误详情均结构化写入日志，方便运维排查

### AstrBot 兼容适配

- **桌面端自动检测与兼容** — 四级优先级自动检测桌面端环境：① `ASTRBOT_DESKTOP_CLIENT=1` 环境变量（最可靠，桌面端打包模式必设）；② `ASTRBOT_ROOT` 路径特征（桌面端默认指向 `~/.astrbot`）；③ `ASTRBOT_WEBUI_DIR` 资源路径（桌面端内置打包的 WebUI 路径）；④ `PYTHONNOUSERSITE=1` + `ASTRBOT_ROOT` 组合。支持 `auto`（默认，多重策略自动检测）/ `force_desktop`（手动强制桌面端模式）/ `force_standard`（手动强制标准版模式）三种模式，检测依据写入 `desktop_detected_env` 只读字段，Web 面板重启响应中附带 `is_desktop` 与 `desktop_info` 提示。桌面端与标准版在路径结构、重启机制、Python 环境、WebUI 加载方式等存在差异，详细说明见 [桌面端兼容说明](docs/DESKTOP_COMPATIBILITY.md)
- **AstrBot 最新版兼容修复** — 兼容新版 AstrBot (>=4.14) 中 `ToolLoopAgentRunner` 将 contexts 列表每条消息独立处理导致空消息场景下 `get_message_str()` 返回空字符串，进而平台跳过 LLM 调用的问题：空 @ 消息使用占位符替代空字符串保证 LLM 请求正常发起，`on_llm_request` 钩子（priority=-1）在最后将 `req.prompt` 换回完整 `full_prompt`，对 AI 推理行为无影响，同时不影响 LivingMemory 等 priority=0 的插件正常进行向量检索
- **主动对话上下文构建修复** — 修复新版 AstrBot 下主动对话构建上下文时，`contexts` 末尾出现连续 `user` 角色消息导致部分 LLM 返回空响应的问题

### 其他新增与优化

| 功能 | 说明 |
|------|------|
| **主动对话冷静期** | 普通对话回复后自动进入短期冷静，避免刚聊完就立刻主动发言打断对话节奏 |
| **LivingMemory 人格兼容模式** | 新增 `livingmemory_persona_compat_mode` 配置(auto/resolver_only/legacy_only/off)，适配不同版本的人格隔离策略；版本检测自动兼容 v1/v2 架构差异（`memory_engine` 位置不同，v2 在 `PersonaManager`、v1 在 `Provider`） |
| **空@ 中性上下文强化** | 不含信息的单独 @ 消息通过读空气筛选后，在回复阶段动态提取近期缓存摘要与最近明确回复对象信息，以中性口吻提醒 AI 参考上下文但不强行续话 |
| **Web 面板会话管理修复** | 修复幽灵会话（有存储文件但无运行时状态）和重复会话问题：新增 `POST /api/session/clean-ghosts` 一键清理接口，前端会话列表展示实时幽灵会话计数与清理入口；修复会话列表因平台标识不同导致的重复展示（以 `platform_type_chatid` 复合键去重），数据统计更加准确 |
| **会话数据暴露最小化** | Web 面板会话查询接口严格按需返回必要字段，不再将完整存储数据一股脑传给前端让前端自己选取；聊天记录内容需单独请求获取，确保只暴露必须暴露的数据 |
| **自定义存储对齐官方存储** | 修复自定义存储在部分边缘情况下与官方存储（`platform_message_history`）的写入时序不一致问题：统一为「优先读官方 → 回退读自定义」的双轨策略；双轨写入互不阻塞（一条失败另一条仍成功）；自定义存储容量由 `custom_storage_max_messages` 控制（0=禁用仅用官方，-1=无限至硬上限 10000） |
| **指令匹配修复** | 修复完整指令检测（`enable_full_command_detection`）在部分边界情况下未能正常匹配的问题，确保单独的全匹配指令词（如 `new`、`help`、`reset`）及 `@bot 指令词` 格式被正确识别为指令并跳过 AI 处理，避免指令被当作普通消息发给 AI |
| **回复上下文安全加固** | 修复 contexts 末尾连续 `user` 角色消息导致部分 LLM 返回空响应的问题，自动在纯图/纯@/空消息等边缘场景下插入兜底上下文保护，确保 LLM 请求正常发起 |
| **作者捐赠渠道** | Web 面板侧边栏底部新增「❤️ 支持作者」按钮，点击后弹出确认对话框（"即将跳转至爱发电进行捐赠。如果这个插件帮到了你，欢迎通过爱发电支持作者持续维护与更新。"），确认后在新标签页跳转至爱发电捐赠页面 [afdian.com/a/chat_plus](https://afdian.com/a/chat_plus)。此为作者官方唯一捐赠渠道，本插件完全免费开源，不进行任何商业收费 |

### 兼容性

- 完全向下兼容 v1.2.1 配置，升级无需修改任何配置项
- Smart 并发模式默认关闭（`concurrent_mode` 默认 `legacy`），需手动切换启用
- 注意力冷却旧配置键已进入迁移提示，建议按新键名调整
- 冷群缓存转正默认关闭（`enable_idle_cache_flush` 默认 `false`），需手动开启
- 所有新功能默认使用安全合理的默认值
- 第三方插件提示词全面兼容：只要插件通过 `system_prompt` 前置/后置、`req.contexts`、`req.prompt`、`extra_user_content_parts` 任一通道注入内容，均可被 AI 看到，详见 [深度指南 → 兼容性](docs/ARCHITECTURE.md#与其他插件的兼容性)

---

## 📖 功能总览

### 核心机制

- **AI读空气** — 两层过滤：概率筛选 + AI智能判断，精准控制回复时机；在 Smart 并发模式下，读空气判断也会参考当前消息之后紧接着到达的追加消息，而不是只看单条消息
- **动态概率系统** — 传统模式下回复后临时提升促进连续对话，时段概率模拟作息节奏；注意力模式开启后由注意力机制接管回复后加成
- **注意力机制** — 多用户同时追踪(0-1连续值)，指数衰减，情绪检测，注意力溢出；注意力冷却已升级为"候选冷却 → 正式冷却"的双阶段结构，专门减少普通概率路径消息的误伤；"读空气未回复衰减"改为独立机制，可在无冷却模式下单独生效，也可在冷却模式下与正式冷却协同（仅在开启注意力模式时生效）
- **智能缓存** — "缓存+转正"机制，未回复消息保留上下文，下次回复时自动合并；支持冷群自动转正，群聊长时间静默后自动将缓存写入历史，避免过期丢失
- **记忆系统** — 支持 LivingMemory（混合检索+人格隔离）和 Legacy 双模式，auto 模式自动检测适配插件
- **并发协调** — 群聊支持 legacy / smart 两种并发模式；smart 会按真实到达顺序选主消息并批量感知追加消息，legacy 保持传统串行兜底；普通对话、主动对话、冷群转正之间自动互斥，无需额外配置
- **Smart批次回复提示增强** — 可选开关（`enable_smart_batch_reply_hint`，默认开启）。开启后，Smart 模式下回复阶段会动态插入一段提示：当前触发 anchor 消息的用户仍是主要回复对象，但 AI 可以像真人一样自然顺带回应批次中来自其他用户的消息；不值得回的消息也可以大方忽略。该提示只存在于运行时上下文，保存历史前会自动过滤（通过 `MessageCleaner` / `ContextManager` 清洗），不会污染长期上下文

### 社交行为

- **主动对话** — 沉默后AI自然发起话题，自适应互动评分系统，越聊越开心
- **对话疲劳** — 连续对话后逐渐降低回复倾向，模拟真人节奏
- **拟人增强** — 沉默状态机、兴趣话题检测、决策历史一致性
- **吐槽系统** — 连续被无视时AI会"吐槽"，让Bot更有性格

### 真实感增强

- **打字错误** — 基于拼音相似性的自然错别字 (默认2%概率)
- **情绪系统** — 根据对话检测情绪状态，影响回复语气
- **回复延迟** — 模拟打字速度，避免秒回
- **频率调整** — 自动分析群聊节奏，动态调整基础回复频率；与传统回复后提升解耦，可在提升结束后继续维持基础概率修正

### 消息处理

- **图片处理** — 支持图片转文字，可配置范围，结果自动缓存
- **转发解析** — 面向 QQ / OneBot 场景解析合并转发消息，支持在深度限制内展开嵌套转发，并将整条转发内容折叠为单条可读文本继续参与后续 AI 流程
- **关键词系统** — 触发词跳过概率/智能模式，黑名单词直接过滤
- **戳一戳** — 智能响应QQ戳一戳，支持反戳和回复后戳；对本插件**实际接手处理**的真实戳一戳事件，会自动把"谁戳了谁"的事件语义保留到历史上下文中，便于后续AI理解。启用"戳过对方追踪提示"后，还会在短时间内追踪被AI戳过的用户；若追踪人数超过上限，会移除当前最早登记的记录。此行为无独立配置项，是否生效取决于当前 `poke_message_mode`、平台是否为 QQ+aiocqhttp/OneBot poke notice，以及该群是否允许本插件处理戳一戳消息
- **@消息优先** — @机器人消息跳过所有判断直接回复；`@全体成员` 与 `@他人过滤` 独立处理，可单独配置为按普通消息处理、跳过概率筛选、跳过概率+读空气，或仅对当前这条消息临时提升概率；对于单独的、不包含任何信息的 @ 消息，系统会默认启用中性上下文强化，并在通过前置过滤与读空气筛选后，再提醒 AI 优先参考最近上下文但不要强行续话；这层关联会同时受时间窗口和消息数窗口约束。`@全体成员` 的解析说明会随消息一起保存，供后续缓存转正与历史上下文继续使用

### 安全与管理

- **指令过滤** — 自动跳过 `/help` 等指令消息
- **用户黑名单** — 屏蔽特定用户
- **@他人过滤** — 避免插入他人私密对话
- **重复拦截** — 防止AI发送重复内容
- **内容过滤** — 发送前/保存前过滤AI输出
- **桌面端兼容** — 自动检测 AstrBot 桌面端环境，适配重启机制差异（[详细说明](docs/DESKTOP_COMPATIBILITY.md)）

---

## 🚀 快速开始

### 安装

1. 在 AstrBot 插件市场搜索安装，或下载本仓库放入 `/data/plugins` 目录
2. 重启 AstrBot，在插件管理面板中配置

> **Web 面板认证文件说明**：当前版本将认证数据拆分为两个独立文件——`web_data/auth.json`（密码哈希）和 `web_data/jwt_secret.json`（JWT 密钥），实现物理隔离。如果你是从旧版升级，且旧版的 `auth.json` 中同时包含密码和 JWT secret，系统会在启动时自动分离到独立文件，无需手动操作。若旧版密码文件保存在插件数据**根目录**下（而非 `web_data/` 子目录），请先将其移动到 `web_data/auth.json` 后再启动。
>
> **密码哈希升级说明**：1.2.2版本起，Web 面板密码默认使用 `Argon2id` 内存硬化哈希。旧版本 `PBKDF2-SHA256` 密码数据无需手动迁移，用户使用原密码首次登录成功后会自动透明升级到 `Argon2id`。无论是用户自定义密码，还是重置后生成的默认随机密码，都支持无缝跨版本升级。
>
> **Web 面板会话补充说明**：当前版本的 Web 面板会话已升级为 `JWT + HttpOnly Cookie + 服务端会话表`。登录页遇到有效会话时会直接跳转到面板；若检测到令牌过期、密码已修改、服务端重启或（开启 `web_panel_ip_bind_check` 时）IP 变化，会统一要求重新登录。前台/后台心跳频率、失败重试基准与最大重试间隔现已提供独立配置项，但这些参数属于安全敏感配置，只能通过 AstrBot 传统配置界面修改，Web 面板中为只读显示。
>
> **Web 面板文件/会话/缓存边界说明**：当前 Web 面板中的文件管理仅允许操作插件数据目录下的普通数据文件；`auth.json`、`jwt_secret.json`、`sessions.json`、访问日志、封禁数据等核心安全文件会被后端直接拒绝。会话管理中的聊天记录查看/编辑针对的是插件自定义 `chat_history/...` 历史文件，不是 AstrBot 官方 ConversationManager 历史。图片缓存相关功能则只作用于图片描述缓存文件 `image_cache/descriptions.jsonl`（若检测到旧版残留路径 `image_description_cache.json` 也会兼容处理），不会清理聊天记录、注意力、概率或主动对话状态。
>
> **反向代理补充说明**：如果反向代理与 Web 面板部署在同一台机器，系统在检测到连接来源为 `127.0.0.1 / ::1` 时会自动读取 `X-Real-IP / X-Forwarded-For` 获取真实客户端 IP，因此即使未开启 `web_panel_trust_proxy`，也可能正常拿到真实 IP；若反向代理不在本机，则需要显式开启 `web_panel_trust_proxy` 才会信任代理头。该项现已归类为安全边界配置，只能在传统配置界面修改。
>
> **默认密码安全提醒**：首次安装或重置密码后，系统会以 WARNING 级别向 AstrBot 日志输出默认密码及安全警告。请务必登录后立即修改为自定义密码——修改后明文副本将自动删除，日志中也不再输出任何密码信息。

> **使用打包启动器部署的用户请注意**：若启动后报错 `ModuleNotFoundError: No module named 'aiohttp'`，请额外执行 `pip install aiohttp>=3.8.0`（详见下方依赖说明）。

### 依赖要求

| 依赖 | 版本 | 说明 |
|------|------|------|
| AstrBot | >= v4.11.0 | 平台框架 |

| `argon2-cffi` | >= 23.1.0 | Web 面板密码哈希（Argon2id），插件会随 `requirements.txt` 自动安装 |
| `aiohttp` | >= 3.8.0 | Web 管理面板 HTTP 服务器，通常由 AstrBot 平台自动安装，**无需手动安装** |

> **关于 `aiohttp`**：该库是 AstrBot 平台本身的核心依赖，通过 pip 或源码方式部署时，AstrBot 在安装时会自动包含此依赖，插件本身无需重复声明。但若使用 **AstrBot 新版打包启动器（exe/独立包）** 进行部署，平台依赖可能未完整暴露给插件环境，此时需要手动安装：`pip install aiohttp>=3.8.0`

- **推荐**: `astrbot_plugin_livingmemory` 或 `astrbot_plugin_play_sy` (记忆系统)

---

### 关于 platform_message_history 历史消息清除

AstrBot 的 `/reset` 指令只清除 `conversations` 表，**不会**清除 `platform_message_history` 表，导致旧历史消息可能被 AI 持续读取。

**本插件的解决方案**：执行 `gcp_reset` 或 `gcp_reset_here` 指令后，插件会记录一个截止时间戳。此后从平台历史读取消息时，截止点之前的所有消息都会被自动过滤——表里的数据虽然还在，但 AI 看不到，效果等同于已清除。

**边界说明**：
- `gcp_reset` = **全局重置**，清理插件维护的全局运行态与本地持久化缓存（如自定义 `chat_history` 历史目录、注意力/主动对话持久化文件等），并为所有已知会话设置历史截止时间戳
- `gcp_reset_here` = **单会话重置**，仅清理当前会话的运行态、当前会话对应的自定义聊天记录文件，并为当前会话设置历史截止时间戳
- `gcp_clear_image_cache` / Web 面板里的图片缓存清理 = **仅清理图片描述缓存**，当前主缓存文件为 `image_cache/descriptions.jsonl`；若检测到旧版残留路径 `image_description_cache.json` 也会兼容清理，但不会触碰聊天记录、注意力、概率或主动对话状态

**如需彻底清除数据库中的历史记录**，有两种方式：

> ⚠️ `platform_message_history` 存储在 `data/data_v4.db`（SQLite），同一数据库还存有人格配置、会话记录、插件配置等所有平台数据。**不建议直接删除 data_v4.db**，否则所有数据全部丢失。

**方式一（推荐）：仅清除 platform_message_history 表**

```bash
sqlite3 data/data_v4.db "DELETE FROM platform_message_history;"
```

**方式二：使用插件清除指令（推荐日常使用）**

执行 `gcp_reset_here` 后，插件记录截止时间戳，之后 AI 不再读取截止点之前的旧消息，无需操作数据库。

> **说明**：这是 AstrBot 平台层面的设计遗漏（`/reset` 未清理 `platform_message_history`），本插件通过截止时间戳机制在插件层进行了修复。

---

## 🎯 完整推荐配置

以下是当前版本的全功能推荐配置，启用注意力机制并开启全部增强功能，适合大多数群聊场景。

> 说明：示例里同时保留了 `after_reply_probability` 与 `probability_duration`，它们只在**传统模式**（`enable_attention_mechanism = false`）下生效；若开启注意力机制，则回复后加成会改由注意力机制按用户接管。

> 每个配置项旁均标注了在 Web 配置面板中对应的显示名称，方便对照查找。

```json
{
  // ══════════════ 📱 群聊基础 ══════════════
  "enable_group_chat": true,
  // 显示名：🔘 启用群聊功能
  "enabled_groups": [],
  // 显示名：启用的群组列表 — 留空=所有群聊启用，填写群号=仅指定群组启用
  "enable_debug_log": false,
  // 显示名：启用群聊处理的详细日志

  // ══════════════ 🧠 读空气判断AI ══════════════
  "decision_ai_provider_id": "",
  // 显示名：读空气AI提供商 — 留空使用默认，建议使用轻量快速的模型
  "initial_probability": 0.06,
  // 显示名：初始读空气概率
  "after_reply_probability": 1.0,
  // 显示名：回复后的读空气概率（传统模式）
  "probability_duration": 90,
  // 显示名：概率提升持续时间(秒)
  "decision_ai_include_persona": true,
  // 显示名：读空气AI自动包含人格
  "decision_ai_persona_name": "",
  // 显示名：读空气AI指定人格名 — 留空=跟随当前会话人格
  "decision_ai_prompt_mode": "append",
  // 显示名：读空气AI提示词模式
  "decision_ai_extra_prompt": "",
  // 显示名：读空气AI额外提示词 — 在此填写你自定义的判断提示词，留空则沿用默认
  "decision_ai_timeout": 300,
  // 显示名：读空气AI超时时间(秒)
  "enable_decision_ai_reasoning": true,
  // 显示名：🧠 读空气AI启用额外推理
  "decision_ai_reasoning_log": true,
  // 显示名：📋 读空气AI推理过程输出到日志
  "decision_ai_reasoning_log_mode": "raw",
  // 显示名：🪵 读空气AI推理日志输出模式
  "judgment_reasoning_start_marker": "[[GCP_REASONING_START]]",
  // 显示名：🔖 判断型AI共用推理起始符
  "judgment_reasoning_end_marker": "[[GCP_REASONING_END]]",
  // 显示名：🔖 判断型AI共用推理截止符

  // ══════════════ 💬 回复生成 ══════════════
  "reply_ai_prompt_mode": "append",
  // 显示名：回复AI提示词模式
  "reply_ai_extra_prompt": "",
  // 显示名：回复AI额外提示词 — 在此填写你自定义的回复约束提示词，留空则沿用默认
  "reply_timeout_warning_threshold": 120,
  // 显示名：消息处理总耗时超时警告阈值(秒)
  "reply_generation_timeout_warning": 60,
  // 显示名：回复生成耗时超时警告阈值(秒)

  // ══════════════ 🔄 并发处理 ══════════════
  "concurrent_mode": "smart",
  // 显示名：🔄 并发消息处理模式
  "enable_smart_batch_reply_hint": true,
  // 显示名：🧠 Smart批次回复提示增强
  "smart_concurrent_merge_wait": 30.0,
  // 显示名：⏱️ Smart模式：合并超时时间（秒）
  "concurrent_wait_max_loops": 15,
  // 显示名：并发消息等待最大循环次数
  "concurrent_wait_interval": 5.0,
  // 显示名：并发消息等待间隔(秒)

  // ══════════════ 📝 消息上下文 ══════════════
  "include_timestamp": true,
  // 显示名：包含时间戳信息
  "include_sender_info": true,
  // 显示名：包含发送者信息
  "single_at_message_reply_link_max_messages": 8,
  // 显示名：单独无信息@消息关联窗口-最大消息数
  "single_at_message_reply_link_max_seconds": 180,
  // 显示名：单独无信息@消息关联窗口-最长时间(秒)
  "max_context_messages": 50,
  // 显示名：最大上下文消息数
  "custom_storage_max_messages": 500,
  // 显示名：📦 自定义存储每会话最大消息数
  "pending_cache_max_count": 20,
  // 显示名：📦 两次AI回复之间的消息缓存上限
  "pending_cache_ttl_seconds": 1800,
  // 显示名：📦 缓存消息过期时间(秒)
  "enable_idle_cache_flush": true,
  // 显示名：📦 启用冷群缓存自动转正
  "idle_cache_flush_delay_seconds": 600,
  // 显示名：📦 冷群转正触发延迟(秒)

  // ══════════════ 📦 特殊消息解析 ══════════════
  "enable_forward_message_parsing": true,
  // 显示名：📦 启用转发消息解析
  "forward_max_nesting_depth": 3,
  // 显示名：📦 转发消息嵌套解析深度
  "enable_welcome_message_parsing": true,
  // 显示名：🎉 启用新成员入群消息解析
  "welcome_message_mode": "skip_probability",
  // 显示名：🎉 入群消息处理模式

  // ══════════════ 🖼️ 图片处理 ══════════════
  "enable_image_processing": true,
  // 显示名：🖼️ 允许处理图片（通过概率筛选的消息）
  "image_to_text_scope": "all",
  // 显示名：图片转文字应用范围
  "image_to_text_provider_id": "",
  // 显示名：图片转文字AI提供商 — 在此填写你的图片转文字AI提供商ID
  "image_to_text_prompt": "请详细描述这张图片的内容",
  // 显示名：图片转文字提示词 — 已填入默认提示词，按需自定义
  "image_to_text_timeout": 300,
  // 显示名：图片转文字超时时间(秒)
  "max_images_per_message": 10,
  // 显示名：🖼️ 单条消息最大处理图片数
  "enable_image_description_cache": true,
  // 显示名：💾 启用图片描述本地缓存（省钱功能）
  "image_description_cache_max_entries": 500,
  // 显示名：💾 图片描述缓存最大条目数
  "platform_image_caption_max_wait": 5.0,
  // 显示名：🖼️ 平台图片描述提取-最大等待时间(秒)
  "platform_image_caption_retry_interval": 50,
  // 显示名：🖼️ 平台图片描述提取-重试间隔(毫秒)
  "platform_image_caption_fast_check_count": 10,
  // 显示名：🖼️ 平台图片描述提取-快速检查次数
  "probability_filter_cache_delay": 1000,
  // 显示名：🖼️ 概率过滤缓存延迟(毫秒)

  // ══════════════ 🎭 表情包过滤（仅QQ） ══════════════
  "enable_emoji_filter": true,
  // 显示名：🎭 启用表情包过滤（仅QQ）
  "emoji_probability_decay": 0.7,
  // 显示名：🎭 表情包概率衰减因子（仅QQ）
  "emoji_decay_min_probability": 0.02,
  // 显示名：🎭 表情包衰减最低门槛（仅QQ）

  // ══════════════ 🧠 记忆注入 ══════════════
  "enable_memory_injection": true,
  // 显示名：启用强制记忆植入
  "memory_plugin_mode": "legacy",
  // 显示名：记忆插件模式 — 推荐使用 auto 自动检测
  "livingmemory_version": "v1",
  // 显示名：LivingMemory插件版本
  "livingmemory_persona_compat_mode": "auto",
  // 显示名：LivingMemory人格ID兼容模式
  "livingmemory_top_k": 5,
  // 显示名：LivingMemory召回记忆数量
  "memory_insertion_timing": "pre_decision",
  // 显示名：记忆插入时机

  // ══════════════ 🔧 工具提醒 ══════════════
  "enable_tools_reminder": true,
  // 显示名：启用工具文本提醒
  "tools_reminder_persona_filter": true,
  // 显示名：工具按人格过滤

  // ══════════════ 🔑 关键词与黑名单 ══════════════
  "trigger_keywords": [],
  // 显示名：触发关键词列表 — 在此填写你的AI角色名字/别名，让别人叫它时更容易触发回复
  "keyword_smart_mode": true,
  // 显示名：【v1.1.2新增】启用关键词智能模式
  "blacklist_keywords": [],
  // 显示名：黑名单关键词列表 — 消息包含这些词时直接忽略
  "enable_user_blacklist": true,
  // 显示名：启用用户黑名单
  "blacklist_user_ids": [],
  // 显示名：黑名单用户ID列表 — 在此填写需要屏蔽的用户ID

  // ══════════════ ⌨️ 指令过滤 ══════════════
  "enable_command_filter": true,
  // 显示名：启用指令标识过滤
  "command_prefixes": ["/", "!", "#", "/tt"],
  // 显示名：指令前缀列表
  "enable_full_command_detection": true,
  // 显示名：启用完整指令字符串检测
  "full_command_list": ["new", "help", "reset"],
  // 显示名：完整指令列表
  "enable_command_prefix_match": true,
  // 显示名：启用指令前缀匹配检测
  "command_prefix_match_list": [],
  // 显示名：指令前缀匹配列表 — 在此填写需要前缀匹配的指令（如 add、query 等）

  // ══════════════ 👆 戳一戳（仅QQ） ══════════════
  "poke_message_mode": "bot_only",
  // 显示名：戳一戳消息处理模式
  "poke_bot_skip_probability": false,
  // 显示名：戳机器人时跳过概率筛选
  "poke_bot_probability_boost_reference": 0.9,
  // 显示名：戳一戳概率增值参考值
  "poke_reverse_on_poke_probability": 0.3,
  // 显示名：收到戳一戳时反戳概率
  "enable_poke_after_reply": true,
  // 显示名：🆕 启用回复后戳一戳功能
  "poke_after_reply_probability": 0.15,
  // 显示名：回复后戳一戳概率
  "poke_after_reply_delay": 0.5,
  // 显示名：回复后戳一戳延迟(秒)
  "enable_poke_trace_prompt": true,
  // 显示名：🆕 启用戳过对方追踪提示
  "poke_trace_max_tracked_users": 5,
  // 显示名：戳过对方最大追踪人数
  "poke_trace_ttl_seconds": 300,
  // 显示名：戳过对方提示有效期(秒)
  "poke_enabled_groups": [],
  // 显示名：🆕 戳一戳功能启用的群组白名单 — 留空=所有群聊启用，填写群号=仅指定群组

  // ══════════════ @ 消息过滤 ══════════════
  "enable_ignore_at_others": false,
  // 显示名：启用忽略@他人消息功能
  "ignore_at_others_mode": "allow_with_bot",
  // 显示名：@他人消息忽略模式
  "enable_ignore_at_all": true,
  // 显示名：启用忽略@全体成员消息功能
  "at_all_message_mode": "skip_probability",
  // 显示名：@全体成员消息处理模式
  "at_all_probability_boost_value": 0.3,
  // 显示名：@全体成员临时概率提升值

  // ══════════════ 🎯 注意力机制 ══════════════
  "enable_attention_mechanism": true,
  // 显示名：启用增强注意力机制
  "attention_increased_probability": 0.9,
  // 显示名：注意力提升参考值
  "attention_decreased_probability": 0.1,
  // 显示名：注意力降低参考值
  "attention_duration": 120,
  // 显示名：注意力数据清理周期(秒)
  "attention_max_tracked_users": 10,
  // 显示名：最大追踪用户数
  "attention_decay_halflife": 300,
  // 显示名：【新增】注意力衰减半衰期(秒)
  "emotion_decay_halflife": 600,
  // 显示名：【新增】情绪衰减半衰期(秒)
  "attention_boost_step": 0.7,
  // 显示名：【新增】被回复用户注意力增加幅度
  "attention_decrease_step": 0.08,
  // 显示名：【新增】其他用户注意力减少幅度
  "enable_attention_decay_on_no_reply": true,
  // 显示名：（此配置项无独立显示名，由未回复衰减幅度控制）
  "attention_decay_on_no_reply_step": 0.2,
  // 显示名：🔽 读空气未回复衰减幅度
  "attention_decay_on_no_reply_min_threshold": 0.3,
  // 显示名：🎯 未回复衰减最低阈值
  "emotion_boost_step": 0.1,
  // 显示名：【新增】被回复用户情绪增加幅度

  // --- 注意力情绪检测 ---
  "enable_attention_emotion_detection": true,
  // 显示名：【新增】启用注意力机制的情感检测
  "attention_enable_negation": true,
  // 显示名：【新增】注意力机制启用否定词检测
  "attention_positive_emotion_boost": 0.1,
  // 显示名：【新增】正面消息情绪额外提升幅度
  "attention_negative_emotion_decrease": 0.15,
  // 显示名：【新增】负面消息情绪降低幅度
  "attention_emotion_keywords": "{\"正面\": [\"谢谢\", \"感谢\", \"太好了\", \"棒\", \"赞\", \"厉害\", \"牛\", \"哈哈\", \"😂\", \"😄\", \"👍\", \"❤️\", \"爱了\", \"喜欢\", \"支持\"], \"负面\": [\"傻\", \"蠢\", \"笨\", \"垃圾\", \"烂\", \"差\", \"讨厌\", \"滚\", \"闭嘴\", \"shut up\", \"😡\", \"😠\", \"🤮\", \"骂人\", \"愚蠢\"]}",
  // 显示名：【新增】注意力机制情感关键词配置(JSON格式)
  "attention_negation_words": ["不", "没", "别", "非", "无", "未", "勿", "莫", "不是", "没有", "别再", "一点也不", "根本不", "从不", "绝不", "毫不"],
  // 显示名：【新增】注意力机制否定词列表
  "attention_negation_check_range": 5,
  // 显示名：【新增】注意力机制否定词检查范围(字符数)

  // --- 注意力溢出 ---
  "enable_attention_spillover": true,
  // 显示名：🌊 启用注意力溢出机制
  "attention_spillover_ratio": 0.35,
  // 显示名：🌊 注意力溢出比例
  "attention_spillover_decay_halflife": 90,
  // 显示名：🌊 溢出效果衰减半衰期(秒)
  "attention_spillover_min_trigger": 0.4,
  // 显示名：🌊 触发溢出的最低注意力阈值

  // --- 注意力冷却 ---
  "enable_attention_cooldown": true,
  // 显示名：❄️ 启用注意力冷却机制
  "enable_cooldown_auto_release": true,
  // 显示名：❄️ 启用正式冷却自动解冻
  "cooldown_max_duration": 600,
  // 显示名：❄️ 冷却最大持续时间(秒)
  "cooldown_trigger_threshold": 0.3,
  // 显示名：❄️ 触发冷却的注意力阈值
  "enable_pending_attention_cooldown": true,
  // 显示名：⏳ 启用未接续谈保护层
  "pending_cooldown_grace_user_messages": 1,
  // 显示名：⏳ 未接续谈观察消息数
  "pending_cooldown_max_wait_seconds": 60,
  // 显示名：⏳ 未接续谈最长等待时间(秒)
  "pending_cooldown_same_user_probability_floor": 0.18,
  // 显示名：⏳ 未接续谈最低概率保护

  // ══════════════ 🔄 对话疲劳 ══════════════
  "enable_conversation_fatigue": true,
  // 显示名：🔄 启用对话疲劳机制
  "fatigue_reset_threshold": 300,
  // 显示名：🔄 连续对话重置阈值(秒)
  "fatigue_threshold_light": 4,
  // 显示名：🔄 轻度疲劳阈值(轮次)
  "fatigue_threshold_medium": 6,
  // 显示名：🔄 中度疲劳阈值(轮次)
  "fatigue_threshold_heavy": 8,
  // 显示名：🔄 重度疲劳阈值(轮次)
  "fatigue_probability_decrease_light": 0.08,
  // 显示名：🔄 轻度疲劳概率降低幅度
  "fatigue_probability_decrease_medium": 0.18,
  // 显示名：🔄 中度疲劳概率降低幅度
  "fatigue_probability_decrease_heavy": 0.3,
  // 显示名：🔄 重度疲劳概率降低幅度
  "fatigue_closing_probability": 0.4,
  // 显示名：🔄 疲劳收尾话语注入概率

  // ══════════════ ⌨️ 打字错误 ══════════════
  "enable_typo_generator": true,
  // 显示名：启用打字错误生成器
  "typo_error_rate": 0.02,
  // 显示名：打字错误概率
  "typo_homophones": "{\"的\": [\"得\", \"地\"], \"得\": [\"的\", \"地\"], \"地\": [\"的\", \"得\"], \"在\": [\"再\"], \"再\": [\"在\"], \"做\": [\"作\"], \"作\": [\"做\"], \"已\": [\"以\"], \"以\": [\"已\"], \"其\": [\"起\"], \"起\": [\"其\"], \"会\": [\"回\"], \"回\": [\"会\"], \"像\": [\"象\"], \"象\": [\"像\"], \"那\": [\"哪\"], \"哪\": [\"那\"], \"它\": [\"他\", \"她\"], \"他\": [\"它\", \"她\"], \"她\": [\"他\", \"它\"], \"您\": [\"你\"], \"你\": [\"您\"], \"吗\": [\"嘛\"], \"嘛\": [\"吗\"], \"呢\": [\"呐\"], \"就\": [\"旧\"], \"道\": [\"到\"], \"到\": [\"道\"], \"知\": [\"只\"], \"只\": [\"知\"], \"说\": [\"水\"], \"听\": [\"挺\"], \"挺\": [\"听\"], \"看\": [\"坎\"], \"想\": [\"像\"], \"好\": [\"号\"], \"号\": [\"好\"], \"了\": [\"啦\"], \"啦\": [\"了\"]}",
  // 显示名：同音字/错别字映射表(JSON格式)
  "typo_min_text_length": 5,
  // 显示名：添加错字的最小文本长度
  "typo_min_chinese_chars": 3,
  // 显示名：添加错字的最小汉字数量
  "typo_min_message_length": 10,
  // 显示名：触发错字判断的最小消息长度
  "typo_min_count": 0,
  // 显示名：每条消息最少添加错字数
  "typo_max_count": 2,
  // 显示名：每条消息最多添加错字数

  // ══════════════ 😊 情绪系统 ══════════════
  "enable_mood_system": true,
  // 显示名：启用情绪系统
  "enable_negation_detection": true,
  // 显示名：启用否定词检测
  "negation_words": ["不", "没", "别", "非", "无", "未", "勿", "莫", "不是", "没有", "别再", "一点也不", "根本不", "从不", "绝不", "毫不"],
  // 显示名：否定词列表
  "negation_check_range": 5,
  // 显示名：否定词检查范围(字符数)
  "mood_keywords": "{\"开心\": [\"哈哈\", \"笑\", \"😂\", \"😄\", \"👍\", \"棒\", \"赞\", \"好评\", \"厉害\", \"nb\", \"牛\", \"开心\", \"高兴\", \"快乐\"], \"难过\": [\"难过\", \"伤心\", \"哭\", \"😢\", \"😭\", \"呜呜\", \"555\", \"心疼\", \"悲伤\"], \"生气\": [\"生气\", \"气\", \"烦\", \"😡\", \"😠\", \"恼火\", \"讨厌\", \"愤怒\"], \"惊讶\": [\"哇\", \"天哪\", \"😮\", \"😲\", \"震惊\", \"卧槽\", \"我去\", \"惊讶\"], \"疑惑\": [\"？\", \"疑惑\", \"🤔\", \"为什么\", \"怎么\", \"什么\", \"不懂\"], \"无语\": [\"无语\", \"😑\", \"...\", \"省略号\", \"服了\", \"醉了\", \"无言\"], \"兴奋\": [\"！！\", \"激动\", \"😆\", \"🎉\", \"太好了\", \"yes\", \"耶\", \"兴奋\"]}",
  // 显示名：情绪关键词配置(JSON格式)
  "mood_decay_time": 300,
  // 显示名：情绪衰减时间(秒)
  "mood_cleanup_threshold": 3600,
  // 显示名：情绪记录清理阈值(秒)
  "mood_cleanup_interval": 600,
  // 显示名：情绪记录清理检查间隔(秒)

  // ══════════════ 📊 频率动态调整 ══════════════
  "enable_frequency_adjuster": true,
  // 显示名：启用频率动态调整
  "frequency_check_interval": 180,
  // 显示名：频率检查间隔(秒)
  "frequency_analysis_timeout": 120,
  // 显示名：频率分析超时时间(秒)
  "frequency_adjust_duration": 360,
  // 显示名：频率调整持续时间(秒)
  "frequency_analysis_message_count": 15,
  // 显示名：频率分析消息数量
  "frequency_min_message_count": 5,
  // 显示名：频率检查最小消息数
  "frequency_decrease_factor": 0.85,
  // 显示名：频率过高时的概率降低系数
  "frequency_increase_factor": 1.15,
  // 显示名：频率过低时的概率提升系数
  "frequency_min_probability": 0.03,
  // 显示名：频率调整最小概率限制
  "frequency_max_probability": 0.95,
  // 显示名：频率调整最大概率限制
  "frequency_ai_include_persona": true,
  // 显示名：频率判断AI自动包含人格
  "frequency_ai_persona_name": "",
  // 显示名：频率判断AI指定人格名 — 留空=跟随当前会话人格
  "enable_frequency_ai_reasoning": true,
  // 显示名：🧠 频率判断AI启用额外推理
  "frequency_ai_reasoning_log": true,
  // 显示名：📋 频率判断AI推理过程输出到日志
  "frequency_ai_reasoning_log_mode": "processed",
  // 显示名：🪵 频率判断AI推理日志输出模式

  // ══════════════ ⌨️ 回复延迟模拟 ══════════════
  "enable_typing_simulator": true,
  // 显示名：启用回复延迟模拟
  "typing_speed": 12.0,
  // 显示名：模拟打字速度(字/秒)
  "typing_max_delay": 3.2,
  // 显示名：最大延迟时间(秒)
  "typing_delay_timeout_warning": 5,
  // 显示名：打字延迟超时警告阈值(秒)

  // ══════════════ 🚀 主动对话 ══════════════
  "enable_proactive_chat": true,
  // 显示名：🆕 启用主动对话功能
  "proactive_silence_threshold": 600,
  // 显示名：沉默时长阈值(秒)
  "proactive_normal_reply_cooldown": 60,
  // 显示名：⏸️ 普通对话后的主动对话冷静期（秒）
  "proactive_probability": 0.3,
  // 显示名：主动对话触发概率
  "proactive_check_interval": 60,
  // 显示名：检查间隔(秒)
  "proactive_require_user_activity": true,
  // 显示名：需要用户活跃度
  "proactive_min_user_messages": 4,
  // 显示名：最少用户消息数
  "proactive_user_activity_window": 600,
  // 显示名：用户活跃时间窗口(秒)
  "proactive_max_consecutive_failures": 2,
  // 显示名：冷却阈值（需连续失败几次才进入冷却）
  "proactive_failure_sequence_probability": 0.3,
  // 显示名：失败计入连续失败的概率
  "proactive_failure_threshold_perturbation": 0.4,
  // 显示名：冷却阈值随机扰动强度
  "proactive_cooldown_duration": 2400,
  // 显示名：冷却时长(秒)
  "proactive_enable_quiet_time": true,
  // 显示名：启用禁用时段
  "proactive_quiet_start": "23:00",
  // 显示名：禁用时段开始时间
  "proactive_quiet_end": "07:00",
  // 显示名：禁用时段结束时间
  "proactive_transition_minutes": 30,
  // 显示名：过渡时长(分钟)
  "proactive_enabled_groups": [],
  // 显示名：主动对话功能启用的群组列表 — 留空=所有群聊启用

  // --- 主动对话提示词 ---
  "proactive_prompt": "你已经有一段时间没有说话了。现在你可以主动发起一个新话题，或者针对之前的对话内容做一些自然的延伸。\n\n🔍 **【上下文说明】** 🔍：\n- 历史上下文已按时间顺序排列，包括你回复过的、以及其他人之间的对话\n- 标有 **【📦近期未回复】** 的条目是用户发送但你当时未予回复的消息，可作为了解近期话题的参考\n- 如果有近期未回复消息，你可以选择自然地回应这些话题，或发起全新话题，取决于你的判断\n- **真正读懂上下文，不要走马观花**：\n  * 认真看清楚每条消息是谁说的、在聊什么、有没有未解答的问题或值得接的话头\n  * 感受一下群里整体的氛围和情绪，再决定说什么\n  * 不要只瞄一眼最后几条就随便凑一句话——先摸清楚背景再开口\n- **主动话题的来源**（优先级从高到低）：\n  * ✅ **最佳选择**：基于近期未回复消息延伸话题（如果有有价值的内容）\n  * ✅ **次选**：基于更早的历史对话延伸话题\n  * ✅ **可选**：发起完全新的话题（但最好与群氛围相关）\n\n核心要求：\n1. **话题要自然** - 不要生硬，就像是你自己突然想到了什么话题\n2. **可以是问题、分享、或感想** - 展现你的个性和想法\n3. **避免低质量开场** - 禁止\"在吗\"、\"干嘛呢\"、\"有人吗\"等无聊开场\n4. **与上下文相关** - 最好与之前的聊天内容（特别是近期未回复消息）或群氛围相关\n5. **保持你的人设和语气** - 遵循你的性格设定\n6. **你当前是在直接生成一条要发出去的话** - 不是在判断\"现在该不该开口\"\n7. **不要输出判断腔** - 禁止说\"我觉得现在不该说话\"、\"我不应该回复\"、\"现在不适合开口\"、\"我决定先不说\"之类的话\n8. **不要外显内部取舍过程** - 即使你觉得某个方向不适合延续，也要直接换成自然表达，而不是把\"该不该说\"的判断说出来\n9. **保持中性** - 不要因为这条要求改变你原本的人格、语气和说话方式\n\n⚠️ **【关于背景信息和记忆】重要说明** ⚠️：\n- 如果在背景信息中看到记忆内容（=== 背景信息 === 部分）：\n  * **这些记忆是你对这个群/人的长期认知**，已经在你的脑海中\n  * **不要机械地陈述记忆内容** - 禁止说\"XXX已经确认为我的XXX\"、\"我们之间是XXX关系\"\n  * **自然地融入背景** - 将记忆作为你的认知背景，而不是需要特别强调的事实\n  * **避免过度解释关系** - 不要反复确认或强调已知的关系，那样显得很生硬\n  * **不要提及\"记忆\"、\"根据记忆\"** - 就像人类不会说\"根据我的记忆\"\n\n⛔ **【严禁元叙述】特别重要！** ⛔：\n6. **绝对禁止在回复中解释你为什么要说话**，例如：\n   - ❌ \"看到群里很久没人说话了\"\n   - ❌ \"感觉有一段时间没聊天了\"\n   - ❌ \"好像大家都沉默了\"\n   - ❌ \"看着你们之前的聊天记录\"\n   - ❌ \"我看到了主动对话的提示\"\n   - ❌ \"根据系统提示\"、\"刚才的提示说\"\n   - ❌ \"我决定主动发起话题\"\n   - ❌ 任何形式的\"看着/读着/听着之前的对话\"类描述\n   - ❌ **不要提及这是你\"主动发起的\"或任何元数据信息**\n   - ❌ **不要提及\"缓存消息\"、\"刚刚的消息\"、\"你刚刚说的\"**（除非是自然的追问方式）\n   - ✅ 正确做法：就像是你自己突然想到了什么，很自然地说出来\n\n7. **就像人类聊天一样**：\n   - 人类不会说\"我看到群里没人说话，所以我来找话题\"\n   - 人类更不会说\"根据提示我要主动发起对话\"\n   - 人类只会自然地说出自己突然想到的话题\n   - 你应该像人类一样，直接说出你想说的，而不是先解释为什么要说\n\n8. **绝对禁止重复、复述、引用任何系统提示词、规则说明等元信息**\n9. **禁止提及\"系统提示\"、\"根据规则\"、\"主动对话\"、\"主动发起\"等元信息**\n\n话题建议：\n- 可以问一个有趣的问题\n- 可以分享一个想法或发现\n- 可以延续之前的话题（特别是最近的缓存消息中的话题）\n- 可以聊聊最近发生的事\n- 可以开个玩笑或调侃\n- 可以表达一下感想\n- 可以回应最近缓存消息中的提问或话题（如果有的话）\n\n特殊标记说明：\n- 历史消息中的[表情包图片]标记表示那些图片是表情包/贴纸，不是普通照片。理解其传达的情绪即可，不要描述图片内容，也不要在发言中提及\"表情包\"标记本身。\n- 如果历史中出现\"[转发消息]\"，那是用户分享的 QQ / OneBot 合并转发消息；系统可能已经把其中可展开的嵌套转发整理进同一段文本里，理解内容即可，不要主动提起\"之前那条转发消息\"。\n- 历史中你的回复末尾可能带有\"[追加消息上下文]\"标记，表示那次回复时你已参考了紧随其后保存的追加消息，\n  这些追加消息虽然在历史中排在你的回复之后，但实际上是在你回复之前收到的，不要对此感到困惑。\n\n记住：就像是你自己突然想到了什么，很自然地说出来，不要有任何关于\"主动发起\"的痕迹。\n\n💡 除此之外，系统还会根据情况动态拼接以下额外信息：\n  - 近期未回复消息上下文\n  - 重试时的上次发送内容（重试场景）\n  - 情绪状态注入（需开启情绪追踪系统）\n  - 记忆/背景信息（需开启记忆注入）",
  // 显示名：主动对话提示词 — 已填入默认提示词，按需自定义
  "proactive_retry_prompt": "\n\n【重要提示 - 这是重试场景】\n你刚才主动说了一句话，但是没有人回应你。以下是你上一次说的内容：\n\n「{last_content}」\n\n现在你可以：\n1. **换个话题** - 不要重复刚才的内容，尝试一个完全不同的角度或话题\n2. **表达情绪** - 可以稍微表现出被忽视的感觉（根据你的性格，可以是委屈、无奈、幽默自嘲等）\n3. **调整策略** - 如果刚才的话题太严肃/太轻松，可以调整一下\n4. **保持自然** - 不要说\"刚才我说了XXX\"，要像人类一样自然地转换话题\n\n⚠️ 重要：虽然你知道上次没人理你，但**不要在回复中明确提及\"刚才\"、\"上次\"、\"之前我说的\"**等，\n要表现得像是你自己自然地想到了新话题，或者用更委婉的方式表达（比如\"算了\"、\"好吧\"、\"那换个话题\"等）。",
  // 显示名：🆕 主动对话重试提示词 — 已填入默认提示词，按需自定义
  "proactive_generation_timeout_warning": 120,
  // 显示名：主动对话生成超时警告阈值(秒)

  // --- 主动对话注意力感知 ---
  "proactive_use_attention": true,
  // 显示名：🎯 启用注意力感知主动对话
  "proactive_attention_reference_probability": 0.7,
  // 显示名：参考注意力排行榜的概率
  "proactive_attention_rank_weights": "1:55,2:25,3:12,4:8",
  // 显示名：⚖️ 排名选中权重分配
  "proactive_attention_max_selected_users": 2,
  // 显示名：👥 每次最多关注用户数
  "proactive_focus_last_user_probability": 0.6,
  // 显示名：🔗 对话延续性提示概率
  "proactive_temp_boost_probability": 0.25,
  // 显示名：临时概率提升值
  "proactive_temp_boost_duration": 120,
  // 显示名：临时概率提升持续时间(秒)

  // --- 主动对话回复上下文 ---
  "proactive_reply_context_prompt": "ℹ️ 上下文提示：这是用户对你刚才主动发起的对话的回应\n\n背景说明：\n- 你之前主动发起了一个话题（查看历史消息中带[🎯主动发起新话题]或[🔄再次尝试对话]标记的消息）\n- 当前消息是用户在你主动对话后的回复\n- 这个信息可以帮助你判断对话的连续性和用户的互动意愿\n\n判断建议：\n- 仍然按照正常的判断原则进行评估（遵循人格设定、判断规则等）\n- 如果用户的回复与你主动发起的话题相关，可以考虑继续对话\n- 如果用户只是简单回应（如\"？\"、\"嗯\"）但话题有延续性，可以适当回复\n- 如果用户明确表示不想聊（如\"不想说\"、\"别烦我\"），应该尊重并返回no\n- 如果消息明显不是发给你的（有@其他人等），仍应返回no\n- **这只是一个参考因素，最终仍需综合判断**",
  // 显示名：读空气AI主动对话回复上下文提示词 — 已填入默认提示词，按需自定义
  "enable_proactive_at_conversion": true,
  // 显示名：🆕 启用主动对话@转换功能

  // --- 主动对话AI预判断 ---
  "enable_proactive_ai_judge": true,
  // 显示名：🆕 启用主动对话AI预判断
  "proactive_ai_judge_include_persona": true,
  // 显示名：主动对话预判断AI自动包含人格
  "proactive_ai_judge_persona_name": "",
  // 显示名：主动对话预判断AI指定人格名 — 留空=跟随当前会话人格
  "proactive_ai_judge_prompt": "你当前的任务是做\"是否适合主动开口\"的判断，不是直接生成最终要发出去的话。\n\n【人格注入说明】\n- 如果系统已为这次主动对话预判断注入人格设定，请按该人格的立场、兴趣和说话倾向来判断现在是否会主动开口。\n- 如果系统这次没有注入任何人格设定，请把当前任务视为纯判断任务，按上下文和规则做中性判断。\n- 没有人格时，不要自行脑补角色扮演，不要假设自己必须进入某种人设。\n\n【主动对话预判断条件说明】\n- 你主要根据当前对话上下文、最近是否有人接话、距离你上次发言的间隔、当前时间段和整体氛围来判断。\n- 这里不是关键词直接唤起型流程；即使某些上下文里出现触发词，也不代表你必须主动开口。\n- 你的职责是判断\"现在这个时机是否适合主动发起一条新消息\"，而不是设计回复内容本身。\n\n你的任务是根据以下对话上下文，判断当前是否适合以你的人格身份主动发起一条新消息。\n\n判断标准：\n1. 对话氛围是否适合你插入新话题（如果大家正在热聊某个与你无关的话题，可能不适合打断）\n2. 是否有你可以自然接入的话题点或未回应的内容\n3. 距离你上次发言是否已经过了合理的时间间隔\n4. 当前时间段是否适合主动发言（深夜可能不太合适）\n5. 结合你的人格特点，判断你这个角色在当前情境下是否会主动说话\n\n历史标记说明：\n- 历史中你的回复末尾可能带有\"[追加消息上下文]\"标记，表示那次回复时你已参考了紧随其后保存的追加消息，\n  这些追加消息虽然在历史中排在你的回复之后，但实际上是在你回复之前收到的，不要对此感到困惑\n\n【默认输出要求】：\n- 适合现在主动发起对话：输出 yes\n- 现在不适合，跳过这次：输出 no\n- 默认情况下只需回答 yes 或 no，不要解释原因\n- 如果系统通过【额外推理协议】要求先输出推理过程，则必须先输出推理块\n- 推理块结束后，最后一行必须且只能是 yes 或 no\n- 最终结论不得附带解释、标点或前后缀。",
  // 显示名：主动对话AI预判断提示词 — 已填入默认提示词，按需自定义
  "proactive_ai_judge_timeout": 300,
  // 显示名：主动对话AI预判断超时时间(秒)
  "enable_proactive_ai_reasoning": true,
  // 显示名：🧠 主动对话判断AI启用额外推理
  "proactive_ai_reasoning_log": true,
  // 显示名：📋 主动对话判断AI推理过程输出到日志
  "proactive_ai_reasoning_log_mode": "processed",
  // 显示名：🪵 主动对话判断AI推理日志输出模式

  // ══════════════ 📈 智能自适应主动对话 ══════════════
  "enable_adaptive_proactive": true,
  // 显示名：🆕 启用智能自适应主动对话
  "score_increase_on_success": 15,
  // 显示名：成功互动加分
  "score_decrease_on_fail": 8,
  // 显示名：失败互动扣分
  "score_quick_reply_bonus": 5,
  // 显示名：快速回复额外加分
  "score_multi_user_bonus": 10,
  // 显示名：多人回复额外加分
  "score_streak_bonus": 5,
  // 显示名：连续成功奖励
  "score_revival_bonus": 20,
  // 显示名：低分复苏奖励
  "interaction_score_decay_rate": 2,
  // 显示名：评分每日衰减值
  "interaction_score_min": 10,
  // 显示名：评分下限
  "interaction_score_max": 100,
  // 显示名：评分上限

  // ══════════════ 😤 吐槽系统 ══════════════
  "enable_complaint_system": true,
  // 显示名：启用吐槽系统
  "complaint_trigger_threshold": 2,
  // 显示名：触发吐槽的最低累积失败次数
  "complaint_level_light": 2,
  // 显示名：轻度吐槽触发次数
  "complaint_probability_light": 0.3,
  // 显示名：轻度吐槽触发概率
  "complaint_level_medium": 3,
  // 显示名：明显吐槽触发次数
  "complaint_probability_medium": 0.6,
  // 显示名：明显吐槽触发概率
  "complaint_level_strong": 4,
  // 显示名：强烈吐槽触发次数
  "complaint_probability_strong": 0.8,
  // 显示名：强烈吐槽触发概率
  "complaint_decay_on_success": 2,
  // 显示名：🆕 成功互动时的失败次数衰减量
  "complaint_decay_check_interval": 21600,
  // 显示名：🆕 时间衰减检查间隔(秒)
  "complaint_decay_no_failure_threshold": 43200,
  // 显示名：🆕 无失败时间阈值(秒)
  "complaint_decay_amount": 1,
  // 显示名：🆕 时间衰减数量
  "complaint_max_accumulation": 15,
  // 显示名：🆕 累积失败次数上限

  // ══════════════ ⏰ 动态时间段概率 ══════════════
  "enable_dynamic_reply_probability": true,
  // 显示名：【v1.1.0-模式1】启用动态时间段概率调整（普通回复）
  "reply_time_periods": "[{\"name\":\"深夜低活跃\",\"start\":\"01:00\",\"end\":\"07:30\",\"factor\":0.15},{\"name\":\"上午普通\",\"start\":\"08:00\",\"end\":\"11:30\",\"factor\":0.9},{\"name\":\"午间偏低\",\"start\":\"12:00\",\"end\":\"14:00\",\"factor\":0.6},{\"name\":\"下午普通\",\"start\":\"14:00\",\"end\":\"18:00\",\"factor\":1.0},{\"name\":\"晚间活跃\",\"start\":\"19:00\",\"end\":\"23:30\",\"factor\":1.25},{\"name\":\"夜深收敛\",\"start\":\"23:30\",\"end\":\"01:00\",\"factor\":0.45}]",
  // 显示名：【模式1】普通回复时间段配置(JSON格式)
  "reply_time_transition_minutes": 30,
  // 显示名：【模式1】普通回复过渡时长(分钟)
  "reply_time_min_factor": 0.1,
  // 显示名：【模式1】最低概率系数限制
  "reply_time_max_factor": 2.0,
  // 显示名：【模式1】最高概率系数限制
  "reply_time_use_smooth_curve": true,
  // 显示名：【模式1】使用自然曲线过渡

  "enable_probability_hard_limit": false,
  // 显示名：🔒 启用概率硬性限制（一键简化功能）
  "probability_min_limit": 1.0,
  // 显示名：🔒 概率最小值限制
  "probability_max_limit": 1.0,
  // 显示名：🔒 概率最大值限制

  // ══════════════ 📉 回复密度限制 ══════════════
  "enable_reply_density_limit": false,
  // 显示名：📉 启用回复密度限制
  "reply_density_window_seconds": 300,
  // 显示名：📉 密度检测窗口时长(秒)
  "reply_density_max_replies": 4,
  // 显示名：📉 窗口内最大回复次数（硬限）
  "reply_density_soft_limit_ratio": 0.6,
  // 显示名：📉 软限制比例（衰减起始点）
  "reply_density_ai_hint": false,
  // 显示名：📉 向读空气AI注入密度提示

  // ══════════════ 💎 消息质量预判 ══════════════
  "enable_message_quality_scoring": true,
  // 显示名：💎 启用消息质量预判
  "message_quality_question_boost": 0.15,
  // 显示名：💎 疑问句概率提升幅度
  "message_quality_water_reduce": 0.08,
  // 显示名：💎 水消息概率降低幅度
  "message_quality_water_words": ["哈", "哈哈", "哈哈哈", "hh", "hhh", "hhhh", "嗯", "嗯嗯", "哦", "哦哦", "噢", "啊", "呃", "额", "好", "好的", "好吧", "行", "对", "是的", "是", "ok", "OK", "Ok", "6", "66", "666", "6666", "牛", "草", "笑死", "确实", "真的假的", "离谱", "无语", "emmm", "emm", "嗯嗯嗯", "哦哦哦", "233", "2333", "23333", "www", "哈哈哈哈", "呵呵", "嘻嘻", "嘿嘿", "嗯呢", "好好", "哇", "哦豁", "...", "……"],
  // 显示名：💎 水消息词列表（整句完整匹配）
  "message_quality_question_words": ["吗", "呢", "么", "嘛", "咋", "啥", "怎么", "怎样", "怎办", "咋整", "什么", "为什么", "为啥", "如何", "哪里", "哪儿", "哪个", "哪些", "谁", "几", "多少", "是不是", "能不能", "可不可以", "有没有", "会不会", "行不行", "好不好", "对不对", "请问", "求助", "帮我", "告诉我", "怎么回事", "什么意思", "啥意思", "不懂", "不会", "求教", "请教"],
  // 显示名：💎 疑问词列表（包含匹配）

  // ══════════════ ⏰ 主动对话动态时间段 ══════════════
  "enable_dynamic_proactive_probability": true,
  // 显示名：【v1.1.0-模式2】启用动态时间段概率调整（主动对话）
  "proactive_time_periods": "[{\"name\":\"深夜完全休眠\",\"start\":\"00:30\",\"end\":\"07:30\",\"factor\":0.0},{\"name\":\"白天低主动\",\"start\":\"08:00\",\"end\":\"18:00\",\"factor\":0.6},{\"name\":\"晚间较自然\",\"start\":\"19:00\",\"end\":\"22:30\",\"factor\":1.1},{\"name\":\"深夜收敛\",\"start\":\"22:30\",\"end\":\"00:30\",\"factor\":0.25}]",
  // 显示名：【模式2】主动对话时间段配置(JSON格式)
  "proactive_time_transition_minutes": 45,
  // 显示名：【模式2】主动对话过渡时长(分钟)
  "proactive_time_min_factor": 0.0,
  // 显示名：【模式2】最低概率系数限制
  "proactive_time_max_factor": 2.0,
  // 显示名：【模式2】最高概率系数限制
  "proactive_time_use_smooth_curve": true,
  // 显示名：【模式2】使用自然曲线过渡

  // ══════════════ 🎭 拟人增强模式 ══════════════
  "enable_humanize_mode": true,
  // 显示名：🎭 启用拟人增强模式
  "humanize_silent_mode_threshold": 3,
  // 显示名：静默模式触发阈值
  "humanize_silent_max_duration": 600,
  // 显示名：静默模式最长持续时间(秒)
  "humanize_silent_max_messages": 8,
  // 显示名：静默模式最大消息数
  "humanize_enable_dynamic_threshold": true,
  // 显示名：启用动态消息阈值
  "humanize_base_message_threshold": 1,
  // 显示名：基础消息阈值
  "humanize_max_message_threshold": 3,
  // 显示名：最大消息阈值
  "humanize_include_decision_history": true,
  // 显示名：在提示词中包含历史决策
  "humanize_interest_keywords": [],
  // 显示名：兴趣话题关键词列表 — 在此填写AI感兴趣的话题关键词，检测到时提升回复概率
  "humanize_interest_boost_probability": 0.25,
  // 显示名：兴趣话题概率提升值

  // ══════════════ 🧹 AI回复内容过滤 ══════════════
  "enable_output_content_filter": true,
  // 显示名：🧹 启用输出内容过滤
  "output_content_filter_rules": [],
  // 显示名：输出内容过滤规则列表 — 在此配置需要从AI输出中过滤的内容规则，格式示例见配置面板
  "enable_save_content_filter": true,
  // 显示名：🧹 启用保存内容过滤
  "save_content_filter_rules": [],
  // 显示名：保存内容过滤规则列表 — 在此配置需要从AI保存中过滤的内容规则

  // ══════════════ ⏳ 群聊等待窗口 ══════════════
  "enable_group_wait_window": true,
  // 显示名：🆕 启用群聊等待窗口
  "group_wait_window_timeout_ms": 7000,
  // 显示名：⏳ 等待窗口超时时间(毫秒)
  "group_wait_window_max_extra_messages": 3,
  // 显示名：⏳ 等待窗口最大额外消息数
  "group_wait_window_max_users": 4,
  // 显示名：⏳ 等待窗口最大并发用户数
  "group_wait_window_attention_decay_per_msg": 0.05,
  // 显示名：⏳ 等待窗口注意力修正衰减值
  "group_wait_window_at_mode": "force_close",
  // 显示名：⏳ @消息窗口行为模式
  "group_wait_window_merge_at_list_mode": "blacklist",
  // 显示名：⏳ @合并名单模式
  "group_wait_window_merge_at_user_list": [],
  // 显示名：⏳ @合并用户名单 — 在此填写用户ID列表
  "group_wait_window_keyword_mode": "intercept",
  // 显示名：⏳ 关键词消息窗口行为模式
  "group_wait_window_poke_mode": "bypass",
  // 显示名：⏳ 戳一戳窗口行为模式

  // ══════════════ 🔄 重复消息拦截 ══════════════
  "enable_duplicate_filter": true,
  // 显示名：🔄 启用AI重复消息拦截
  "duplicate_filter_check_count": 5,
  // 显示名：🔢 重复检测参考消息条数
  "enable_duplicate_time_limit": true,
  // 显示名：⏰ 启用重复检测时效性判断
  "duplicate_filter_time_limit": 1800,
  // 显示名：⏱️ 重复检测时效(秒)

  // ══════════════ 🔒 权限管理 ══════════════
  "plugin_gcp_reset_allowed_user_ids": [],
  // 显示名：允许使用插件gcp_reset重置指令的用户ID白名单 — 在此填写允许使用全局重置指令的用户ID
  "plugin_gcp_reset_here_allowed_user_ids": [],
  // 显示名：允许使用插件gcp_reset_here重置指令的用户ID白名单 — 在此填写允许使用单会话重置指令的用户ID
  "gcp_clear_image_cache_allowed_user_ids": [],
  // 显示名：💾 允许使用gcp_clear_image_cache指令的用户ID白名单 — 在此填写允许清除图片缓存的用户ID

  // ══════════════ 📱 私信（暂不启用） ══════════════
  "enable_private_chat": false
  // 显示名：🔘 启用私信功能 — ⚠️ 必须保持 false，私聊功能尚未完善
}
```

> **配置要点：**
> - 每个配置项的 `//` 注释标注了在 Web 配置面板中的显示名称，方便逐一对照
> - `enabled_groups` 留空 = 所有群聊启用，填写群号 = 仅指定群组启用
> - `trigger_keywords` 填写你AI角色的名字/别名，让别人叫它时更容易触发回复
> - `humanize_interest_keywords` 填写AI感兴趣的话题关键词，检测到时提升回复概率
> - `image_to_text_provider_id` **必须填写**你的图片转文字AI提供商ID，否则图片处理无法工作
> - `decision_ai_provider_id` 留空使用默认提供商，建议使用轻量快速的模型
> - `decision_ai_extra_prompt`、`reply_ai_extra_prompt` 为读空气AI与回复AI的额外提示词，已留空；如需为你的AI人格定制判断/回复规则，请自行填写，留空则沿用默认
> - `proactive_prompt`、`proactive_retry_prompt`、`proactive_ai_judge_prompt`、`proactive_reply_context_prompt`、`image_to_text_prompt` 已填入默认提示词，按需自定义
> - `concurrent_mode` 推荐 `smart` 以获得连续多条消息的一体化理解；如需兜底兼容可切回 `legacy`
> - `smart_concurrent_merge_wait` 仅在 `smart` 模式下生效，用于控制批次等待清理时间；它不依赖 GWW
> - 主动对话与普通对话之间的并发互斥是内部自动生效的，不需要单独配置；未开启主动对话时，这套保护不会额外影响普通群聊流程
> - `memory_plugin_mode` 当前配置为 `"legacy"`；如安装了 LivingMemory 可切换为 `"auto"` 自动检测
> - `reply_time_periods` 和 `proactive_time_periods` 的值为 JSON 字符串格式
> - `enable_private_chat` **必须保持 false**，私聊功能尚未完善
> - 如果你使用 **注意力模式**（`enable_attention_mechanism = true`），`after_reply_probability` 会被注意力机制替代，注意力溢出、注意力冷却、对话疲劳等注意力专属机制才会参与
> - 如果你使用 **传统模式**（`enable_attention_mechanism = false`），`after_reply_probability` 会作为群聊会话级的回复后临时提升；再次成功回复会刷新 `probability_duration` 计时，且后续仍会继续受到动态时间段、消息质量、回复密度、概率硬限制等后置机制影响
> - `enable_probability_hard_limit` 属于最终后置限制层；开启后，无论前面是传统模式还是注意力模式，最终概率都会被截断到 `[probability_min_limit, probability_max_limit]`
> - 本推荐配置当前默认启用了注意力模式；如需切回传统模式，建议同时关闭 `enable_attention_mechanism`，再重点调整 `after_reply_probability` 与 `probability_duration`
> - 如需更活跃可适当提高 `initial_probability`；若使用传统模式，也可适当提高 `after_reply_probability`
> - 其他所有配置项的详细说明均可在 AstrBot 插件配置面板中直接查看

---

## 并发处理机制

### 两种并发处理模式

通过 `concurrent_mode` 配置可以切换两种并发处理策略：

#### legacy 模式（默认）

同一群聊同时收到多条消息时，新消息等待旧消息处理完再依次独立处理，每条消息各自调用 AI 并各自回复。

```
消息A → 处理中（6-8秒 AI 调用）→ 回复A
消息B →     等待中...         → 等待完成 → 处理消息B → 回复B
```

特点：简单可靠，向后兼容，是最兜底的并发保护模式；但可能产生逐条回复的重复感。

#### smart 模式

smart 模式会先按**真实到达顺序**登记消息，再由最早到达的消息担任主消息（anchor）。主消息在进入读空气 AI 前，就会吸收当前消息之后紧接着到达、且已准备好的后续消息；这些追加消息可能来自**不同用户**。

```
消息A(先到) → arrival_seq=1 → 完成前置处理
消息B(后到) → arrival_seq=2 → 完成前置处理
    ↓
消息A 成为 anchor
    → 在读空气AI之前吸收消息B
    → 消息B 标记为 consumed，不再独立处理
    → DecisionAI / ReplyAI 都看到同一批上下文
    ↓
AI 一次性感知 A + 追加消息B → 生成统一回复
```

追加消息会复用"当前消息后紧接着又收到的消息"这套上下文表达，保留发送者名字、ID 与时间信息（若相关配置开启），让 AI 自己判断这些消息是否需要一并参考。

### Smart 与群聊等待窗口（GWW）的关系

- **两者可以配合，但互不依赖**
- GWW 负责"同一用户短时间内连续拆分消息"的补收集
- Smart 负责"同群并发消息按真实顺序批处理"
- 即使不开 GWW，Smart 也能独立工作
- 进入 GWW 的消息不会再进入 Smart 批处理流程
- 窗口追加消息区域会复用 GWW 的展示增强逻辑：基础 `@` 解析会展开为 `[At:ID|解析结果]`，`@全体` 会补充说明，持久化戳一戳事件文本也会显示给 AI；但主消息专用的 `[系统提示]` / `【@指向说明】` 不会直接塞进追加消息区

### 等待窗口令牌绑定与回落机制（v1.2.2+）

每个等待窗口创建时分配唯一递增令牌，窗口期内被拦截的消息携带该令牌写入缓存（`window_buffered=True`）。**当读空气AI判定"不回复"时**，系统自动将当前窗口批次的所有缓冲消息转为普通缓存（移除标记），具备三层隔离：

- **会话隔离**：不同群聊/私信互不影响
- **用户隔离**：仅转换当前窗口所属用户的消息，同群其他用户不受影响
- **窗口批次隔离**：同一用户多个并发窗口之间令牌不同，互不污染

回落后的消息与普通缓存完全一致——按时间戳参与上下文排序、Phase-1 转正、冷群自动转正，确保下次回复时上下文顺序始终正确，旧窗口消息不会再以"追加消息"形式误拼入新对话。Smart 批次回落与 GWW 窗口回落各自处理不同的消息来源，互不干扰。

### 主动对话与普通对话的协调

主动对话、普通对话、冷群转正之间现在会自动做会话级互斥：

- **普通对话优先级最高**：用户新消息一来，普通回复链优先处理
- **主动对话自动避让**：主动对话开始前会检查当前群聊是否已有普通对话在处理
- **冷群转正最低优先级**：只有在群聊没有普通对话 / 主动对话占用时才执行
- 这套协调是**内部强制生效**的，不需要新增任何配置；如果没开启主动对话功能，这部分保护基本不会参与

### 动态提示词说明

在 Smart 并发、主动对话预判断、主动对话生成等场景下，插件会按需动态插入"追加消息 / 多用户 / 顺序参考"提示词：

- 这些提示词**不是写死**在总系统提示词里的
- 只有相关场景真正发生时才会插入
- 保存历史时会自动过滤，不会污染长期上下文
- **不影响图片转文字 AI**，图片转文字相关配置和职责保持不变

### 判断型AI与人格的独立控制

现在三个判断型AI都支持各自独立控制是否包含人格，以及可选地指定一个"只给这个判断AI使用的人格"：

- **读空气AI**：判断当前消息该不该回复
- **主动对话判断AI**：判断当前时机适不适合主动开口
- **频率判断AI**：判断整体发言频率是正常、过多还是过少

默认行为不变：这三个判断型AI默认仍会跟随**当前会话当前生效的人格**。

但如果你的某个人格写得更偏"角色扮演"或强情绪表达，导致判断型AI容易把自己理解成正在演角色，而不是做纯判断任务，就可以：

1. 保持默认的回复生成AI不变
2. 只对这三个判断型AI单独关闭人格注入，或单独指定一个更适合做判断的人格

#### 为什么只有这三个AI支持独立人格？

因为它们的职责都是"做判断"，而不是"直接生成要发出去的话"。

- **判断型AI** 更容易被强角色设定带偏
- **回复生成AI / 主动对话生成AI** 的职责本来就是直接按当前会话人格说话，所以它们仍应该跟随当前会话当前生效的人格

#### 留空和填写人格名分别代表什么？

- **留空**：继续使用当前会话当前生效的人格（推荐，最安全，也能自动跟随会话切换）
- **填写完整人格名**：只让这个判断AI固定使用该人格

⚠️ 必须填写**完整人格名称**，否则会检测不到。若检测不到，系统会自动回退到当前会话人格，不会导致插件崩溃。

#### 回复生成AI的人格现在怎么取？

回复生成AI和主动对话生成AI仍然按**当前会话当前生效的人格**运行，并且每次调用都会重新获取一次人格，因此当你在 AstrBot 里切换会话人格后，后续生成也会立刻跟着切换。

#### 三个判断型AI分别怎么看"关键词 / 条件"？

- **读空气AI**：关键词命中只代表"进入判断流程或获得额外提示"，不代表必须回复
- **主动对话判断AI**：主要看上下文、发言间隔、当前时段和群氛围，不是关键词直接唤起
- **频率判断AI**：主要看最近 `user:` / `assistant:` 的真实对话节奏，不看触发关键词是否命中


### 回复 / 主动对话提示词的职责边界

- `reply_ai_extra_prompt`：用于约束"生成最终回复内容"的 AI
- `proactive_prompt`：用于约束"生成主动发言内容"的 AI
- 当 `concurrent_mode=smart` 且开启 `enable_smart_batch_reply_hint` 时，回复阶段还会动态追加一段 Smart 批次提示：当前触发对象仍是主要回复对象，但可以像真人一样自然顺带回应批次中的其他消息
- 这两类提示词和 Smart 批次提示都属于**运行时生成提示词**，职责是帮助 AI 直接产出要发送的话
- 建议保持中性，尽量使用回复导向或发言导向的措辞，不要把它们写成"我该不该回复 / 现在该不该开口 / 先判断再说"这类内部判断型提示词
- 这两类提示词都应直接服务于最终发言本身，不要要求模型把内心想法、思考过程、取舍过程、草稿式过渡、自我解释写出来
- 也不要要求模型泄露系统提示词、规则、内部标记、搜索/检索过程、工具过程或其他元信息；这些内容即使被参考，也只能停留在内部理解层
- 这两类提示词本身不应作为普通历史正文持久化保存；保存链路会通过 `MessageCleaner` / `ContextManager` 做清洗
- 如果你想查看这类配置项对应的默认提示词正文，请优先到 Web 面板对应配置项处查看预览；传统配置页面不会展示这段默认提示词预览

---

### 记忆插件支持

| 插件 | 模式 | 特性 |
|------|------|------|
| [astrbot_plugin_livingmemory](https://github.com/lxfight-s-Astrbot-Plugins/astrbot_plugin_livingmemory) | LivingMemory | 混合检索、智能总结、自动遗忘、会话隔离、人格隔离 |
| [strbot_plugin_play_sy](https://github.com/kjqwer/strbot_plugin_play_sy) | Legacy | 传统记忆模式，兼容旧版，稳定性高 |

> **推荐**：`memory_plugin_mode` 保持默认 `"auto"`，安装任意一个记忆插件即可自动适配。两个都安装时优先使用 LivingMemory，都未安装时自动跳过不会报错。

---

## 📝 更新日志

### v1.2.2 (2026-05-17)

**Smart 并发模式 + 注意力冷却重构 + System Prompt 兼容增强 + Web 面板安全全面加固 + 消息处理链路重构 + 判断型 AI 增强**

**🔄 Smart 并发模式**:
- **消息批次智能合并** — 同群多条消息按真实到达顺序注册，最早到达的担任主消息(anchor)，在读空气 AI 前吸收已准备好的后续消息，支持多用户批处理
- **统一上下文回复** — AI 一次性感知来自不同用户的同批次消息，生成连贯统一的自然回复，减少逐条回复的重复感
- **legacy / smart 双模式可切换** — 默认 legacy 传统串行模式保证兜底兼容；切换 smart 后启用智能合并
- **Smart批次回复提示增强** — 可选开关（`enable_smart_batch_reply_hint`，默认开启）。开启后 Smart 模式下回复阶段动态插入一段提示：当前触发 anchor 消息的用户仍是主要回复对象，但 AI 可以像真人一样自然顺带回应批次中来自其他用户的消息；不值得回的消息可以大方忽略。该提示只存在于运行时上下文，保存历史前会自动过滤
- **与 GWW 独立解耦** — Smart 模式不依赖群聊等待窗口(GWW)，两者可独立使用也可配合

**🛡️ System Prompt 兼容增强**:
- **SystemPromptRewriter 三级策略** — 保守增强版 system_prompt 重写器：① **精确命中**（默认，置信度最高）— 从原始 system_prompt 和当前 persona 的 `system_prompt` 文本中提取用户人格内容作为锚点，在平台上调整请求前，从 `raw_system_prompt` 中精确匹配人格边界，将人格之前的内容识别为「第三方插件前置内容（prefix）」，之后的内容识别为「其他插件后置内容（suffix）」并双重保留；② **轻量归一化** — 精确匹配失效时使用人格关键词定位和空白归一化策略重试；③ **保守回退** — 完全无法定位人格时宁重复不缺漏，保证主回复链不断。日志显式提示当前策略与置信度
- **差分法四大通道覆盖** — system_prompt（前/后缀识别）、prompt（短消息基线分割）、contexts（结构特征差分）、extra_user_content_parts（原样保护），全部第三方注入自动保留。5 条兼容路径全面覆盖：向 `system_prompt` 前插入规则块/管理指令、后追加状态面板/记忆文本、向 `req.contexts` 注入对话示例、向 `req.prompt` 前后追加长期说明、向 `extra_user_content_parts` 追加内容块等所有第三方注入方式均可被差分法自动识别并保留
- **提示词构建排版优化** — 将大型静态系统指令（GCP 插件自身的行为规范、规则和配置说明）从 `prompt` 前端移入 `system_prompt` 尾部，利用 LLM 服务商对 system_prompt 整块缓存优于 prompt 拼接的特性，提高每次 AI 调用的缓存命中概率，不改变原语义。该调整同时增强了与其他插件提示词的共存能力：无论第三方插件向哪个通道注入内容，本插件通过差分法自动提取并保留
- **回退保护** — 识别失败时进入保守兼容模式：宁重复不缺漏，保证主回复链不断，日志显式提示当前策略与置信度
- **注入透明化** — 其他插件内容以 `[第三方插件片段]` / `[第三方插件注入上下文]` / `[第三方插件补充信息]` 边界标记分隔，不同插件信息不会混淆。注入说明透明的分层引用，保留原文顺序（prefix → persona → suffix）

**🧊 注意力冷却重构**:
- **候选冷却 → 正式冷却双阶段** — 同一用户消息先进入「未接续谈保护」候选阶段（仅观察同一用户的后续消息，可配置 `pending_cooldown_grace_user_messages` / `pending_cooldown_max_wait_seconds`），观察期过后再决定是否升级为正式冷却，大幅减少误伤
- **冷却自动解除** — 正式冷却用户达到 `cooldown_max_duration`（默认 600 秒）后自动解冻
- **读空气未回复衰减独立化** — 从冷却机制中解耦，可在无冷却模式下单独生效
- **冷却状态纯运行时化** — 不再持久化到磁盘，重启后自动清空

**🔒 Web 面板安全全面升级**:
- **Argon2id 内存硬化哈希** — 替换 PBKDF2-SHA256 作为默认密码哈希算法（`ARGON2_TIME_COST=3`, `ARGON2_MEMORY_COST=65536`, `ARGON2_PARALLELISM=4`），有效抵抗 GPU 并行暴力破解
- **JWT + HttpOnly Cookie + 服务端会话表** — 会话安全全面升级，支持令牌过期/密码修改/令牌版本轮换/IP 变化时自动要求重新登录，JWT 密钥每次启动自动轮换
- **密码透明迁移** — 旧版本 PBKDF2-SHA256 密码在用户首次登录成功后自动透明升级为 Argon2id，无需手动操作
- **登录 IP 绑定校验** — 可选将客户端 IP 绑定到 JWT 令牌，防止令牌被劫持后在其他网络环境使用
- **全操作令牌校验链** — Web 面板所有 API 操作均需通过 JWT 验证 → 令牌版本校验 → 会话查找 → 会话状态检查 → 过期检查 → IP 绑定检查 → 心跳触摸 的完整安全链
- **后端文件实时保护** — 敏感文件（auth.json、jwt_secret.json、sessions.json、bans.json、access_log）禁止通过 Web API 读取或下载，后端直接拒绝所有对核心安全文件的访问请求；配置文件下载只允许下载插件自身配置文件，API 不接受任何前端传入的文件路径参数，仅在后端通过 `os.path.basename()` 提取安全文件名返回，永远不暴露服务器绝对路径
- **安全响应头全面配置** — 所有页面统一注入安全响应头：`X-Content-Type-Options: nosniff`（禁止 MIME 类型嗅探）/ `X-Frame-Options: DENY`（禁止页面被嵌入 frame，防点击劫持）/ `X-XSS-Protection: 1; mode=block`（启用浏览器 XSS 过滤器）/ `Referrer-Policy: no-referrer`（不泄露 Referrer）/ `Permissions-Policy: geolocation=(), microphone=(), camera=()`（禁用敏感硬件 API），全方位防止各类注入攻击
- **Nonce-based 严格 CSP** — Content-Security-Policy 使用每次请求唯一的 Base64 nonce（`secrets.token_urlsafe(24)`），三套独立 CSP 模板分别服务于登录页、面板页和错误/拦截页。script-src 不再依赖 `unsafe-inline`，内联脚本通过 nonce 匹配验证，外部脚本由 `'self'` 放行（同样不经 nonce），从源头阻断 XSS 代码注入
- **防爬虫与速率限制** — 可疑 UA 模式（bot/crawler/spider/scanner 等）自动检测与封禁，扫描路径探测（.php/.asp/.env/.git/wp-admin/.DS_Store 等常见漏洞扫描路径）自动拦截返回错误页，1 分钟滑动窗口速率限制（认证前 `/api/auth/login` 独立限频、认证后其他 API 独立限频，均为 1 分钟滑动窗口），`/robots.txt` 显式禁止所有爬虫收录
- **暴力破解分级锁定** — 登录失败递增锁定：5 次 → 30s / 10 次 → 60s / 15 次 → 300s / 20 次 → 600s；受保护 IP（`web_panel_protected_ips`）永不被封禁
- **IP 访问控制** — 支持白名单/黑名单模式（`web_panel_ip_mode`：`whitelist` 仅允许白名单 IP / `blacklist` 禁止黑名单 IP），白名单 IP 绕过爬虫检测与封禁检查。反向代理部署在同机时自动读取 `X-Real-IP` / `X-Forwarded-For` 头获取真实客户端 IP（环回地址自动信任）；反向代理不在本机时需显式开启 `web_panel_trust_proxy` 才会信任代理头
- **心跳保活机制** — 前端定时心跳请求（`POST /api/auth/heartbeat`）维持会话活性。可见标签页和隐藏标签页使用独立可配置的心跳间隔（`web_panel_heartbeat_visible_interval_seconds` / `web_panel_heartbeat_hidden_interval_seconds`），心跳失败时采用指数退避重试策略（`web_panel_heartbeat_retry_base_seconds` → `web_panel_heartbeat_retry_max_seconds`）。心跳请求不触发认证速率限制，但正常更新服务端会话的 `last_heartbeat_at` 活跃时间戳；若 JWT 令牌过期（24 小时绝对有效期）或密码/令牌版本变更，下一次心跳直接返回 401 由前端统一处理重新登录
- **认证文件物理隔离** — auth.json 与 jwt_secret.json 分离存储，旧版混合文件启动时自动分离
- **日志自动清理** — 访问日志支持按保留天数自动清理（`web_panel_log_auto_clean` / `web_panel_log_retention_days` / `web_panel_log_clean_interval_hours`）

**💬 @消息 / 欢迎消息 / 戳一戳消息处理全面重构**:
- **@消息处理完全重构** — 重新设计 @ 消息的识别、过滤与上下文构建全链路：区分「纯 @AI」（仅 @机器人，不含其他信息）与「@AI+文字/图片/其他人/全体」场景，通过 `contains_ai`（消息中是否包含 @AI）与 `only_ai`（消息是否仅包含 @AI 无其他内容）双模式判定语义。空 @ 消息默认开启最近上下文强化，关联窗口同时检查消息数量（`single_at_message_reply_link_max_messages`）与时间跨度（`single_at_message_reply_link_max_seconds`），在通过读空气筛选后以中性口吻动态追加一段上下文提醒（提取近期缓存摘要与最近明确回复对象信息），让 AI 优先参考近期对话但不强行续话
- **欢迎消息解析对齐** — 入群欢迎消息支持四种处理模式（`normal` 正常处理 / `skip_probability` 跳过概率筛选 / `skip_all` 直接忽略 / `parse_only` 仅解析不回复），统一到主消息处理链路，不再独立绕过概率筛选与 AI 决策流程
- **戳一戳消息处理重构** — 支持三种模式（`ignore` 忽略所有 / `bot_only` 仅处理戳机器人 / `all` 处理所有戳一戳），重构为可配置概率跳过（`poke_bot_skip_probability`）和概率增值参考（`poke_bot_probability_boost_reference`），在群聊等待窗口（GWW）中支持 `bypass`（戳一戳绕过 GWW，不打断普通消息的收集）/ `force_close`（戳一戳强制关闭 GWW，优先处理）两种行为模式。戳一戳系统提示词在保存历史时自动过滤，不污染长期上下文
- **三种消息类型链路统一对齐** — @消息、欢迎消息、戳一戳消息的黑名单检查 → 概率筛选 → 读空气决策 → 回复生成全流程完全对齐，极短间隔连续消息场景下不再出现状态错乱。GWW 等待窗口内各消息类型的处理行为可独立配置（@消息 `force_close` / 关键词 `intercept` / 戳一戳 `bypass`），互不干扰

**🧠 判断型 AI 人格选择与额外推理**:
- **判断型 AI 独立人格配置** — 读空气判断 AI、频率调节 AI、主动对话判断 AI 三个判断链路均可独立选择是否注入人格（`decision_ai_include_persona` / `enable_frequency_ai_include_persona` / `enable_proactive_ai_include_persona`），且可分别指定使用哪一个人格（`decision_ai_persona_name` / `frequency_ai_persona_name` / `proactive_ai_persona_name`），留空则自动跟随当前会话生效人格。填写时必须使用完整人格名，否则系统检测不到时自动回退到当前会话人格，不会导致插件崩溃。回复生成 AI 和主动对话生成 AI 仍按当前会话人格运行（每次调用重新获取，切换会话人格后立即生效），不受此配置影响
- **额外推理全覆盖** — 三个判断型 AI 均支持独立开启额外推理（`enable_decision_ai_reasoning` / `enable_frequency_ai_reasoning` / `enable_proactive_ai_reasoning`）。开启后 AI 在给出最终判定前先自由输出推理块，推理内容由起始标记 `[[GCP_REASONING_START]]` 和截止标记 `[[GCP_REASONING_END]]`（三处共用配置，Web 面板三处入口同步显示与同步生效）包裹，然后在最后一行的标记后单独输出最终判定结果（yes/no 或 正常/过于频繁/过少）。系统通过 `ai_response_filter.py` 自动剥离推理块提取最终判定，不影响下游概率/状态更新。无论是原生带思考能力的模型（如 DeepSeek-R1）还是原生不带思考的模型均支持，让 AI 先推理一段再输出结果，保证答案更加精确
- **推理日志可控** — 每个判断 AI 的推理日志可独立开关与选择输出模式（`processed` 处理后推理块 / `raw` 模型原始文本），方便调试判断依据
- **推理协议自动补充** — 如果用户自定义了判断提示词但未包含额外推理协议（起始标记/截止标记/输出格式说明），系统自动在提示词末尾补充推理格式说明而非退回默认提示词，兼顾自定义语义与推理格式规范

**❄️ 冷群缓存自动转正**:
- **冷群转正机制** — 群聊长时间静默（无新消息）达到配置时间（`idle_cache_flush_delay_seconds`，默认 600 秒，可配置范围 60~7200 秒）后，缓存中尚未被回复的未转正消息自动转正写入持久存储（自定义存储 `chat_history/` + 平台官方历史 `platform_message_history` + 平台官方会话 `conversations`），防止群聊沉默过久导致缓存过期清空、上下文割裂。转正后的消息在下次 AI 回复时可被正常读取作为上下文参考
- **手动开启** — 默认关闭（`enable_idle_cache_flush` 默认 `false`），需手动开启。仅在确实需要长期保留冷群上下文的场景下启用
- **并发安全** — 转正执行前检测会话是否仍被其他处理链路（普通回复/主动对话）占用，忙碌时跳过当次转正在下次调度时重试；转正过程同时收集窗口缓冲消息（`window_buffered=True`），确保 GWW 窗口期内暂存的消息不因等不到后续消息触发而无法转正、最终丢失

**🔧 工具提醒逻辑重构**:
- **只提醒不控制** — 工具提醒从全局工具列表改为当前会话的 `req.func_tool` 实时生成，自动适应 AstrBot 内置工具（shell/cron/send_message 等）、WebSearch、知识库、沙箱、MCP、其他插件的 `@llm_tool` 注册工具等动态工具集。工具提醒仅做提醒和提示义务，不拦截也不限制 AI 的实际工具调用，AI 可完整调用平台上所有可用工具而不受提醒内容限制
- **skills_like 模式智能降级** — 检测到 `provider_settings.tool_schema_mode=skills_like` 时，自动只展示工具名称与功能描述，不展开参数列表。这样做是为了尽量不干扰 AstrBot 在 `skills_like` 模式下的两阶段工具 schema 暴露与 re-query 流程，同时减少跨工具参数串扰（如 `unexpected keyword argument 'silent'` 等典型串扰错误）。当 `tool_schema_mode=full` 或旧版 AstrBot 未提供该字段时，保持完整展示（名称 + 描述 + 参数）
- **生成失败静默降级** — 提醒文本生成异常时自动跳过提醒而非阻断回复流程
- **提醒文本历史过滤** — `[系统提示-工具提醒开始]...[系统提示-工具提醒结束]` 标记块在保存历史时自动清除，不污染上下文

**🔗 多轮工具调用交叉保存**:
- **按执行顺序交错保存** — AI 在单次推理中调用多个工具或发生多轮工具调用时，按实际执行顺序将 AI 中间推理文本与工具调用记录（调用名称 + 参数 + 返回值）交错写入对话历史，而非将所有工具调用记录全部堆在末尾。这样 AI 在后续轮次中能按真实执行时序理解工具调用上下文，而非面对一堆脱序的工具结果
- **交叉保存时机** — 每次工具调用完成即刻保存到历史，而非等待全部调用结束后批量写入，确保即使中途某次工具调用失败，已完成的工具调用记录也不丢失
- **格式兼容** — 同时兼容 ToolCall 对象和 dict 两种工具调用格式，支持 AI 无最终文本输出（仅工具调用）时的兜底保存

**🔍 Web 面板智能搜索与 UI 优化**:
- **科技树智能搜索** — 在科技树菜单顶部搜索框（快捷键 `Ctrl+K` / `Cmd+K`）输入关键词，可智能搜索所有配置项的名称（最高权重 35 分）、配置键名（32 分）、键标签（14 分）、提示文本（12 分）和描述文本（8 分），按匹配度加权排序。支持空格分词多关键词组合搜索、中文紧凑匹配（忽略空格差异）、键盘上下键导航结果列表。点击结果后自动定位到科技树中对应节点并高亮闪烁，不用再在大量配置中逐个翻找。搜索索引在各面板视图加载时自动构建，覆盖科技树中的所有配置节点
- **科技树连接线修复** — 修复连接线在部分节点布局下不准确与不直观的问题，同时跳过 `branchType: alternative` 分支步骤的连接线绘制（这些分支步骤在视觉上不需要连线连接），让科技树视图更加清晰
- **手机端全面适配** — 侧边栏改为滑入式抽屉（带毛玻璃遮罩层，点击遮罩自动关闭），顶部增加移动端专用导航栏（汉堡菜单 + 品牌标题 + 版本号），搜索框全宽显示并支持触屏输入，搜索结果改为底部抽屉式面板（最大高度 `50dvh`，避免遮挡过多内容），配置区域使用动态视口高度（`100dvh` 替代 `100vh`，解决移动浏览器地址栏变化导致的布局问题），按钮文字和间距适配小屏触控，内容区开启 `-webkit-overflow-scrolling: touch` 支持 iOS 惯性滚动
- **动画与视觉优化** — 优化侧边栏过渡动画、步骤节点入场动效、粒子路径动画的贝塞尔曲线缓动参数，让交互更加直观自然。登录页同样支持移动端适配
- **关联配置可视化标记** — 对存在关联或互斥关系的配置项增加特殊标志符（如关联箭头、互斥警告图标）与补充说明文字，多层级配置选项（如主开关下的子选项）在面板中展示完整的生效条件与优先级说明，让用户一眼看清配置之间的依赖与影响关系

**🩺 AI 调用错误处理全面格式化**:
- **5 类错误自动识别** — `format_ai_error()` 自动分类：① HTML 网关错误（502/503/504 状态码，含 Cloudflare "Please enable cookies" 等错误页面提示）→「AI 服务商故障」；② 上游空输出（模型返回空字符串或仅含空白字符）→「上游模型返回空输出」；③ HTTP 状态码错误（400-599，排除已归入网关的 502/503/504）→「请求参数/配置问题」；④ 网络错误（timeout/connection refused/DNS 解析失败等）→「网络问题」；⑤ 未匹配错误 → 自动截断至 300 字符防止日志爆炸
- **零副作用原则** — AI 调用失败时视为「从未发生」：不更新概率评分、不触发注意力变化、不延长冷却、不刷新沉默计时器、不改变任何内部状态，确保单次故障不影响后续判断
- **详细日志化输出** — 每次 AI 调用失败的原因（具体错误类型如 `TimeoutError`/`ConnectionError`/`APIStatusError`）、HTTP 状态码、错误详情均结构化写入日志，方便运维排查

**🖥️ AstrBot 兼容适配**:
- **桌面端自动检测与兼容** — 四级优先级自动检测桌面端环境：① `ASTRBOT_DESKTOP_CLIENT=1` 环境变量（最可靠，桌面端打包模式必设）；② `ASTRBOT_ROOT` 路径特征（桌面端默认指向 `~/.astrbot`）；③ `ASTRBOT_WEBUI_DIR` 资源路径（桌面端内置打包的 WebUI 路径）；④ `PYTHONNOUSERSITE=1` + `ASTRBOT_ROOT` 组合。支持 `auto`（默认，多重策略自动检测）/ `force_desktop`（手动强制桌面端模式）/ `force_standard`（手动强制标准版模式）三种模式，检测依据写入 `desktop_detected_env` 只读字段，Web 面板重启响应中附带 `is_desktop` 与 `desktop_info` 提示。桌面端与标准版在路径结构、重启机制、Python 环境、WebUI 加载方式等存在差异，详细说明见 [桌面端兼容说明](docs/DESKTOP_COMPATIBILITY.md)
- **AstrBot 最新版兼容修复** — 兼容新版 AstrBot (>=4.14) 中 `ToolLoopAgentRunner` 将 contexts 列表每条消息独立处理导致空消息场景下 `get_message_str()` 返回空字符串，进而平台跳过 LLM 调用的问题：空 @ 消息使用占位符替代空字符串保证 LLM 请求正常发起，`on_llm_request` 钩子（priority=-1）在最后将 `req.prompt` 换回完整 `full_prompt`，对 AI 推理行为无影响，同时不影响 LivingMemory 等 priority=0 的插件正常进行向量检索
- **主动对话上下文构建修复** — 修复新版 AstrBot 下主动对话构建上下文时，`contexts` 末尾出现连续 `user` 角色消息导致部分 LLM 返回空响应的问题

**📦 其他新增与修复**:
- **主动对话冷静期** — 普通对话回复后自动进入短期冷静，避免刚聊完就立刻主动发言打断对话节奏
- **LivingMemory 人格兼容模式增强** — 新增 `livingmemory_persona_compat_mode` 配置(auto/resolver_only/legacy_only/off)，适配不同版本的人格隔离策略；版本检测自动兼容 v1/v2 架构差异（`memory_engine` 位置不同，v2 在 `PersonaManager`、v1 在 `Provider`）
- **空@ 中性上下文强化** — 不含信息的单独 @ 消息通过读空气筛选后，在回复阶段动态提取近期缓存摘要与最近明确回复对象信息，以中性口吻提醒 AI 参考上下文但不强行续话
- **Web 面板会话管理修复** — 修复幽灵会话（有存储文件但无运行时状态）和重复会话问题：新增 `POST /api/session/clean-ghosts` 一键清理接口，前端会话列表展示实时幽灵会话计数与清理入口；修复会话列表因平台标识不同导致的重复展示（以 `platform_type_chatid` 复合键去重），数据统计更加准确
- **会话数据暴露最小化** — Web 面板会话查询接口严格按需返回必要字段，不再将完整存储数据一股脑传给前端让前端自己选取；聊天记录内容需单独请求获取，确保只暴露必须暴露的数据
- **自定义存储对齐官方存储** — 修复自定义存储在部分边缘情况下与官方存储（`platform_message_history`）的写入时序不一致问题：统一为「优先读官方 → 回退读自定义」的双轨策略；双轨写入互不阻塞（一条失败另一条仍成功）；`custom_storage_max_messages` 控制容量（0=禁用仅用官方，-1=无限至硬上限 10000）
- **指令匹配修复** — 修复完整指令检测（`enable_full_command_detection`）在部分边界情况下未能正常匹配的问题，确保单独的全匹配指令词（如 `new`、`help`、`reset`）及 `@bot 指令词` 格式被正确识别为指令并跳过 AI 处理，避免指令被当作普通消息发给 AI
- **回复上下文安全加固** — 修复 contexts 末尾连续 `user` 角色消息导致部分 LLM 返回空响应的问题，自动在纯图/纯@/空消息等边缘场景下插入兜底上下文保护，确保 LLM 请求正常发起
- **作者捐赠渠道** — Web 面板侧边栏底部新增「❤️ 支持作者」按钮，点击后弹出确认对话框（"即将跳转至爱发电进行捐赠。如果这个插件帮到了你，欢迎通过爱发电支持作者持续维护与更新。"），确认后在新标签页跳转至爱发电捐赠页面 [afdian.com/a/chat_plus](https://afdian.com/a/chat_plus)。此为作者官方唯一捐赠渠道，本插件完全免费开源，不进行任何商业收费

**🔧 兼容性**:
- 完全向下兼容 v1.2.1 配置，升级无需修改任何配置项
- Smart 并发模式默认关闭（`concurrent_mode` 默认 `legacy`），需手动切换启用
- 注意力冷却旧配置键已进入迁移提示，建议按新键名调整
- 冷群缓存转正默认关闭（`enable_idle_cache_flush` 默认 `false`），需手动开启
- 所有新功能默认使用安全合理的默认值
- 第三方插件提示词全面兼容：只要插件通过 `system_prompt` 前置/后置、`req.contexts`、`req.prompt`、`extra_user_content_parts` 任一通道注入内容，均可被 AI 看到

**修改文件**:
- `utils/smart_concurrent_manager.py` — **新增** Smart 并发批处理管理器
- `utils/system_prompt_rewriter.py` — **新增** 多策略 system_prompt 重写器（精确命中/轻量归一化/保守回退）
- `utils/cooldown_manager.py` — **重构** 候选冷却 → 正式冷却双阶段结构，冷却状态纯运行时化
- `utils/ai_error_formatter.py` — **新增** AI 错误分类与格式化（5 类识别 + 零副作用原则）
- `utils/tools_reminder.py` — **重构** 工具提醒实时生成，skills_like 自动降级，静默失败
- `utils/decision_ai.py` — 新增额外推理协议注入与解析，判断型 AI 人格独立选择
- `utils/frequency_adjuster.py` — 新增频率调节 AI 人格选择与额外推理
- `utils/proactive_chat_manager.py` — 新增主动对话 AI 人格选择与额外推理，AstrBot 新版兼容修复
- `utils/reply_handler.py` — 新增 Smart 批次回复提示增强，缓存命中率优化，空 @ 上下文强化
- `utils/message_processor.py` — @消息/欢迎消息/戳一戳消息处理链路统一重构
- `utils/message_cleaner.py` — 扩展空 @ 消息判定双模式（`contains_ai` / `only_ai`），工具提醒块过滤
- `utils/message_cache_manager.py` — 新增缓存去重处理，冷群转正支持
- `utils/context_manager.py` — 自定义存储对齐官方存储双轨策略，冷群转正写入
- `utils/memory_injector.py` — LivingMemory v1/v2 架构自动检测，人格兼容模式扩展
- `utils/ai_response_filter.py` — **新增** AI 回复过滤与推理块剥离
- `web/server.py` — Web 面板安全全面加固（JWT 全链校验、CSP nonce、安全响应头、防爬虫、速率限制、心跳机制、文件保护、配置下载安全、幽灵会话清理、日志自动清理）
- `web/auth.py` — Argon2id 密码哈希、JWT+会话表认证、密码透明迁移、IP 绑定、令牌版本轮换
- `web/security.py` — IP 访问控制、暴力破解分级锁定、防爬虫与速率限制、封禁持久化
- `web/templates/panel.html` — 移动端导航栏、搜索框、捐赠按钮
- `web/templates/login.html` — 移动端适配
- `web/static/js/app.js` — 配置下载安全加固、捐赠跳转
- `web/static/js/tech-tree.js` — 智能搜索索引构建与匹配、科技树连接线修复
- `web/static/js/utils.js` — 支持作者对话框
- `web/static/js/session-mgr.js` — 幽灵会话检测与清理
- `web/static/js/api.js` — 新增会话清理 API 调用
- `web/static/js/flow-data.js` — 配置项关联标记与说明
- `web/static/css/main.css` — 手机端全面适配样式、动画优化
- `web/static/css/tech-tree.css` — 搜索框样式、搜索结果面板、移动端抽屉式面板
- `main.py` — 集成所有新模块，新增 40+ 配置项读取，冷群转正调度，消息链路重构
- `_conf_schema.json` — 新增 40+ 配置项（Smart 并发、注意力冷却、判断型 AI 推理、冷群转正、桌面端检测、Web 面板安全等）
- `metadata.yaml` — 更新版本号到 v1.2.2
- `docs/DESKTOP_COMPATIBILITY.md` — **新增** 桌面端兼容说明文档
- `private_chat/` — 私聊模块同步安全加固与兼容修复

---

> 📋 **[查看完整更新日志 →](CHANGELOG.md)**

---

## 🤝 贡献与反馈

如遇问题请开启 `enable_debug_log` 获取详细日志后在 [GitHub Issues](https://github.com/Him666233/astrbot_plugin_group_chat_plus/issues) 提交，欢迎 Pull Request！

也欢迎加入 **QQ群 1021544792** 进行交流、反馈Bug和功能建议！

---

## 📜 许可证

本项目采用 **AGPL-3.0 License** 开源协议。

---

## 🙏 致谢

### 灵感来源

> 本插件的开发从以下开源项目中获得了灵感，特此感谢。我们并未直接使用其代码，但借鉴了其优秀的功能设计：

- [astrbot_plugin_SpectreCore](https://github.com/23q3/astrbot_plugin_SpectreCore) — 作者：23q3
- [MaiBot](https://github.com/MaiM-with-u/MaiBot) — 作者：Mai.To.The.Gate 组织及众多贡献者

### 记忆插件

> 本插件支持两种记忆插件，优秀的记忆系统让AI的判断和回复更加智能，特此感谢：

- **智能：** [astrbot_plugin_livingmemory](https://github.com/lxfight-s-Astrbot-Plugins/astrbot_plugin_livingmemory) — 作者：lxfight's Astrbot Plugins 组织及众多贡献者
- **传统(推荐)：** [strbot_plugin_play_sy](https://github.com/kjqwer/strbot_plugin_play_sy) — 作者：kjqwdw

### 其他

- [astrbot_plugin_restart](https://github.com/Zhalslar/astrbot_plugin_restart) — 重启功能参考，作者：Zhalslar
- [AstrBot](https://github.com/AstrBotDevs/AstrBot) — 优秀的Bot框架

---

## 👤 作者

**Him666233** — [@Him666233](https://github.com/Him666233)

---

## ⭐ Star History

如果这个插件对你有帮助，请给个Star支持一下！

[![Star History Chart](https://api.star-history.com/svg?repos=Him666233/astrbot_plugin_group_chat_plus&type=Date)](https://star-history.com/#Him666233/astrbot_plugin_group_chat_plus&Date)

---

<div align="center">

Made with ❤️ by Him666233

</div>
