# 一键部署 Package 交付规范

用户要求“一键部署”“完整 Package”“可移交目录”或包含完整 Skill 的成品时读取本文件。Package 默认是当前工作区中的普通目录；用户明确要求压缩或发布时才生成归档或上传。

## 必须包含

1. `skill/[skill-name]/`，保存完整 `SKILL.md`、`agents/`、`scripts/`、`references/` 和实际使用的 `assets/`，排除 `__pycache__`、`.pyc` 与临时日志。
2. `project/`，保存可运行的 WebBook、工具、派生分析、Agent Knowledge Base、复现清单和用户要求保留的本地原始证据。
3. 一键安装入口，检测 Codex、Cindy 与 Claude 的现有技能目录；安装同名 Skill 前先做带时间戳的可恢复备份。
4. 一键启动入口，从 Package 自身路径启动服务，不依赖原工作区的绝对路径。
5. 一键验证入口，检查必需文件、Skill frontmatter、项目自检、发布边界、知识库和 Package 哈希。
6. `package-manifest.json` 与 `package-files.sha256`，记录版本、生成时间、文件数、大小、排除项和逐文件 SHA-256。
7. 根目录用户说明，写清系统要求、双击顺序、目录结构、移动 Package 后是否需要重新安装快捷方式，以及本地专有材料不得公开上传。
8. Agent 访问层：`llms.txt`、OpenAPI、统一查询核心、CLI、HTTP 和 stdio MCP；安装状态记录 Package/KB 路径，移动后重跑安装器即可刷新。

## 体积与证据选择

先统计源工作区各一级目录的文件数和大小。保留支撑学习、运行、复现和继续分析的唯一副本。排除生成期 SubAgent/Goal 隔离工作区、浏览器缓存、Python 缓存、重复构建和能够从清单稳定重建的临时文件。

用户要求完整原始数据时，保留隔离提取物、活动视图、解析索引、工具链和必要二进制分析工程。不得把原游戏安装目录、账号数据、密钥、PAK 源归档或用户未授权材料偷偷复制进 Package。Package 含提取游戏材料时，在根说明和安装界面标记“仅供本地合法学习，不得公开分发”。

默认优先生成 `learning` profile：Skill、WebBook、公开证据页、AKB、Agent 访问层与运行脚本；排除 Ghidra 工程、完整工具链和原始提取副本。只有用户明确要求可复现研究材料时生成 `research` profile，在 learning 唯一副本之外增加必要分层提取物、工具链与二进制分析工程。两个 profile 都禁止 `.internal/`。

## 安装行为

Project 默认原地运行，避免一键安装再次复制数 GB 数据。安装脚本只部署 Skill、创建本地快捷方式并记录当前 Package 路径。Package 移动后，用户重新运行安装入口即可刷新快捷方式。

安装脚本不得静默删除同名 Skill。先把旧目录移动到同一技能根下的时间戳备份，再复制新 Skill。自定义测试根或 `-NoShortcut`、`-NoLaunch` 参数用于隔离验证，成品测试不能修改真实用户技能目录。

## 成品验证

从 Package 目录自身执行以下检查：

- Skill 通过 `quick_validate.py` 或等价 frontmatter/资源检查。
- 安装脚本部署到临时技能根，目标文件与 Package Skill 一致。
- 启动器能够取得本地 HTTP 200，默认页非空。
- Project、学习 Wiki、Agent Knowledge Base 与浏览器回归通过。
- 哈希清单覆盖全部交付文件，仅排除清单自身与运行时状态文件。
- Package 中不含 `.hgoal`、`.git`、`__pycache__`、`.pyc`、临时端口文件和内部凭据。
- Package 中不含 `.internal`、独立审查、生成日志或旧稿；验证器不得把这些文件纳入哈希后误判为合法交付。
- llms、OpenAPI、CLI、HTTP 与 MCP 从 Package 自身路径完成同源查询回归；MCP 使用隔离运行时，stdout 无日志污染。
- 离线运行时必须在 manifest 声明精确支持的 Python/平台组合；安装器对不在 wheelhouse 覆盖范围内的版本提前给出明确错误，不能笼统承诺“更高版本”。

任何一项失败都修复成品后重新生成哈希。源工作区曾经通过验证，不能替代 Package 自身验证。
