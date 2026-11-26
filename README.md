# tieba-signin-lite

基于 https://github.com/LuoSue/TiebaSignIn-1 的 MIT 许可接口逻辑改写。仅用于本人账号，并遵守服务条款。

## 部署

1. Settings → Secrets and variables → Actions → New repository secret，添加 `BDUSS`（主账号）。如需第二个本人账号，添加 `BDUSS_SECOND`，保留原 `BDUSS`；不配置第二个账号也可运行。不要把凭证写入文件、命令行、issue 或聊天。
2. Actions → Daily task → Run workflow。只在默认分支运行。默认每天 UTC 22:30，即北京时间/马来西亚时间 06:30（可能延迟）。
3. 公开仓库可能在 60 天无仓库活动后停止定时工作流，需人工重新启用。没有保活插件。

## 安全边界

无 pip 依赖、第三方 Actions、通知、缓存、上传产物或自动更新。仅向代码内三个固定百度 HTTPS 接口请求，证书验证开启，不跟随重定向或环境代理。凭证只在签到步骤注入；公开日志仅输出 Task completed. 或 Task incomplete.，子进程输出被丢弃。每次签到步骤固定约 600 秒，两个隔离的 300 秒窗口依次执行（每个真实签到最多 280 秒，超时按失败处理）。第二账号未配置时仍填充第二窗口，同一凭证不会重复执行；仅输出所有已配置账号的汇总状态，缓解通过运行时间推测关注数量的风险。GitHub 自身仍公开运行时间、状态与仓库信息，取消任务、系统故障、外部签到记录等仍可能泄漏信息。GitHub Runner 与百度可接触凭证，不能保证绝对匿名或零风险。任何有仓库写权限的人都可能修改未来运行代码；不要授予陌生人写权限。遇到异常停止，不尝试绕过验证。HTTPS 接口已通过单个真实账号测试；双账号固定窗口通过离线验证后仍需真实运行验证，接口可能变更；若失败，请检查贴吧 App 并手动处理，不要公开原始响应。若怀疑泄漏，撤销登录会话并删除 Secret。

离线测试：`python3 -B -m unittest -q test_signin test_private_run`。
