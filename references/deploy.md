# 部署你自己的临时邮箱实例

本 skill 是客户端，需要一个 [cloudflare_temp_email](https://github.com/dreamhunter2333/cloudflare_temp_email) 实例作服务端。全程不需要传统服务器，只用 Cloudflare 免费服务。

## 架构

```
发件方 → 你的域名 (Cloudflare Email Routing, catch-all)
       → Email Worker 的 email() 处理器
       ├─ 存入 D1 数据库（raw_mails 表，原始 MIME）
       └─ 可选：message.forward() 转发到个人邮箱留档
查询方 → https://mail.你的域名/api/mails (HTTP API，即本 skill 读的接口)
       └─ 网页版：同一 Worker 返回前端静态资源
```

- Email Routing 只负责路由（决定"发给谁的邮件交给谁处理"），不存邮件。
- Worker 负责收下邮件：存 D1 + 转发，两者不冲突。
- AI 读邮件 = 主动轮询 HTTP API，不是推送。

## 部署步骤概要

1. 一个域名，接入 Cloudflare（免费计划即可），开启 Email Routing。
2. 按官方文档部署 Worker + D1：
   - `vitepress-docs/docs/zh/guide/cli/d1.md`（建库建表）
   - `vitepress-docs/docs/zh/cli.md`（wrangler deploy）
3. `wrangler.toml` 关键配置：
   - `DOMAINS` / `DEFAULT_DOMAINS`：你的邮箱域名
   - `JWT_SECRET`：随机长字符串（泄露后所有地址凭据作废）
   - `PASSWORDS`：站点访问密码（即本 skill config.json 里的 `password`）
   - `PREFIX`：地址前缀（如 `"tmp"`）
   - 可选 `FORWARD_ADDRESS_LIST`：来信转发到个人邮箱留档
   - `[assets]`：绑定前端 dist 目录，网页 + API 同域
4. Cloudflare 控制台把 Email Routing 的 catch-all 规则指向该 Worker。
5. 自定义域名绑定 Worker（如 `mail.你的域名`）。

## 部署后验证

```bash
# 生成地址（返回 jwt）
curl -s -X POST "https://mail.你的域名/api/new_address" \
  -H "x-custom-auth: <PASSWORDS之一>" -H "Content-Type: application/json" \
  -H "User-Agent: Mozilla/5.0" -d '{}'
# 用真实邮箱发一封信到该地址，然后：
curl -s "https://mail.你的域名/api/mails?limit=5&offset=0" \
  -H "x-custom-auth: <PASSWORDS之一>" -H "Authorization: Bearer <jwt>" \
  -H "User-Agent: Mozilla/5.0"
```

看到 `"count": 1` 即链路通。

## 常见坑

- `/api/mails` 必须 `limit`(1-100) 和 `offset` 都传，否则 400。
- 读信必须带该地址的 JWT，光有站点密码不够（站点密码只是全局网关 + 建址权限）。
- 转发目的地（如 Gmail）需先在 Cloudflare Email Routing 里验证。
- Python urllib 默认 UA 会被 Cloudflare 拦（403, error 1010），务必带正常 UA。
