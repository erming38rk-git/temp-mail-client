# temp-mail-client

通用临时邮箱收码 skill：配合自部署的 [cloudflare_temp_email](https://github.com/dreamhunter2333/cloudflare_temp_email) 实例，让 AI 自动生成一次性收件地址、轮询读取验证码、完成注册/登录，不让用户手动转述邮件。

## 安装

```bash
git clone https://github.com/erming38rk-git/temp-mail-client.git
cp temp-mail-client/config.example.json temp-mail-client/scripts/config.json
```

然后编辑 `scripts/config.json`：

| 字段 | 说明 |
|---|---|
| `base_url` | 你的实例地址，如 `https://mail.你的域名` |
| `password` | 站点访问密码（wrangler.toml 的 PASSWORDS） |
| `register_password` | 可选：注册外部账号时统一使用的密码 |
| `address` / `jwt` | 留空，首次跑 `new` 自动写入 |

验证：`python scripts/tempmail.py new` 返回一个 tmp 开头的地址即为成功。

## 命令

```bash
python scripts/tempmail.py new [名字]   # 新建一次性地址
python scripts/tempmail.py code         # 最新邮件里的验证码
python scripts/tempmail.py check        # 最新几封 + 验证码
python scripts/tempmail.py mails -n 20  # 邮件列表
python scripts/tempmail.py read 17      # 按 id 看全文
python scripts/tempmail.py address      # 当前地址
python scripts/tempmail.py password     # 注册外部账号的统一密码
```

详细服务端部署见 [references/deploy.md](references/deploy.md)。

> 本仓库无任何硬编码地址/密钥，可放心公开使用。
