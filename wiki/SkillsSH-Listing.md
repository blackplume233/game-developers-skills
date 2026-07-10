# skills.sh 收录与页面维护

## 适用范围

本流程用于个人或社区 GitHub 技能仓库的普通收录和页面分组，不申请 Official。
Official 面向技术产品的官方组织；根目录 `skills.sh.json` 不能授予该身份。

## 配置同步

在仓库根目录运行：

```bash
python skills/skill-management/skill-repo-manager/scripts/sync_skills_sh.py --write
python skills/skill-management/skill-repo-manager/scripts/sync_skills_sh.py --check
```

脚本扫描 `skills/<category>/<skill>/SKILL.md`，使用 frontmatter 的 `name` 生成分组，
并阻止重复技能名或配置漂移。提交前应人工确认标题、说明及页面 slug。

## 发布与发现

1. 同步 `README.md`、`WIKI.md`、相关 Wiki 页面和 `CHANGELOG.md`。
2. 完成版本检查和隐私审查。
3. 提交并推送根目录 `skills.sh.json`。
4. 运行 `npx skills add <owner>/<repo> --skill '*' -g -y` 触发匿名安装遥测。
5. 验证 CLI 发现数量、安装目录中的 `SKILL.md` 和 skills.sh 仓库页面。

skills.sh 页面存在缓存。推送或安装后未立即变化时，应记录触发时间并稍后复查，
不能立即判定失败，也不要通过重复安装伪造热度。

## 故障排查

- 页面不存在：确认仓库公开，并至少成功执行一次 Skills CLI 安装。
- 技能数量不完整：检查各技能是否存在合法 `SKILL.md` 和 `name`。
- 分组未更新：运行 `sync_skills_sh.py --check`，确认已推送默认分支并等待缓存刷新。
- CLI 与页面不一致：以 CLI 实际发现输出、公开默认分支和页面最终状态分别记录证据。
