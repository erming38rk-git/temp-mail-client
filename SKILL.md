---
name: temp-mail-client
description: 通用临时邮箱收码 skill：配合自部署的 cloudflare_temp_email 实例，让 AI 自动生成一次性收件地址、轮询读取验证码、完成注册/登录，不让用户手动转述邮件。当用户要收验证码、临时邮箱、一次性邮箱，或提到 tempmail/temp-mail、用临时地址注册网站时使用。需要先在同目录 scripts/config.json 配置 base_url/password（参考 config.example.json）。
---

# temp-mail-client（通用版）

配合自部署的 [cloudflare_temp_email](https://github.com/dreamhunter2333/cloudflare_temp_email) 实例使用。核心目标：**AI 自己生成一次性地址、自己读验证码、继续完成注册/登录，全程不让用户手动转述邮件。**

## 首次配置（一次性）

1. 按 `references/deploy.md` 部署自己的实例（或用已有的）。
2. 复制 `config.example.json` 为 `scripts/config.json`，填入 `base_url` 和 `password`；可选填 `register_password`（注册外部账号统一密码）。
3. 首次运行 `python scripts/tempmail.py new` 会自动生成地址和 JWT 并写入配置。

## 工作流（每个任务一个随机地址）

```bash
python "<本技能目录>/scripts/tempmail.py" new          # 随机地址（服务器自动加前缀）
python "<本技能目录>/scripts/tempmail.py" new github   # 指定名
python "<本技能目录>/scripts/tempmail.py" code         # 轮询最新验证码（每 10-20 秒一次）
python "<本技能目录>/scripts/tempmail.py" check        # 最新几封 + 验证码
python "<本技能目录>/scripts/tempmail.py" address      # 当前地址
python "<本技能目录>/scripts/tempmail.py" read 17      # 按 id 看完整正文
python "<本技能目录>/scripts/tempmail.py" password     # 注册外部账号要用的统一密码
```

流程：`new` 生成地址 → 填进要注册的网站（账号密码用 `password` 命令的输出，不要自拟）→ 轮询 `code`（最多 2-3 分钟）→ 拿到验证码继续操作。没收到就如实回报，不要猜。

## 注册外部账号的密码约定（重要）

用本技能的邮箱注册任何外部网站/服务时，**账号密码一律用 `password` 命令输出的值**（`config.json` 的 `register_password`），不要自己另设密码，也不要随机生成。

- 原因：账号是用户的，AI 自拟的密码用户之后登不进去。
- 没配 `register_password` 时，直接问用户要统一密码，同样不许自拟。
- 注册完成后告诉用户「网站 + 邮箱地址」，不要在回复里重复密码本身。

## 远程/无脚本环境：直接用 HTTP API

任何能发 HTTP 请求的环境都能用，无需本技能脚本：

```bash
# 1. 生成地址（name 留空=随机）
curl -s -X POST "<base_url>/api/new_address" \
  -H "x-custom-auth: <password>" -H "Content-Type: application/json" \
  -H "User-Agent: Mozilla/5.0 tempmail/1.0" \
  -d '{"name":""}'
# 返回 {"address":"...","jwt":"..."}

# 2. 读邮件（用返回的 jwt；limit 1-100，offset 必填）
curl -s "<base_url>/api/mails?limit=5&offset=0" \
  -H "x-custom-auth: <password>" -H "Authorization: Bearer <jwt>" \
  -H "User-Agent: Mozilla/5.0 tempmail/1.0"

# 3. 某封完整内容：GET <base_url>/api/mail/<id>（请求头同上）
```

要点：
- 缺 `x-custom-auth` 或 `Authorization` → 401。
- 必须带正常 User-Agent（默认 UA 可能被 Cloudflare 拦成 403）。
- 一个 JWT 只能读一个地址；`raw` 字段是原始 MIME，解析找 4-8 位验证码。
- JWT 长期有效（除非服务端更换 JWT_SECRET）。
- 注册账号的密码用用户给的统一密码，不要自拟。

## 安全

- `scripts/config.json` 含密码和 JWT，**不要提交到任何仓库**（.gitignore 已排除）。
- 给远程 AI 用时优先让它每次随机生成新地址+JWT，用完废弃；不要共享固定 JWT。
