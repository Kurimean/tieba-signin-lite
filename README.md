# tieba-signin-lite

基于 https://github.com/LuoSue/TiebaSignIn-1 的 MIT 许可接口逻辑改写。仅用于本人账号，并遵守服务条款。

## 部署

1. Settings → Secrets and variables → Actions → New repository secret，添加 `BDUSS`（主账号）。如需第二个本人账号，添加 `BDUSS_SECOND`，保留原 `BDUSS`；不配置第二个账号也可运行。不要把凭证写入文件、命令行、issue 或聊天。
2. Actions → Daily task → Run workflow。默认勾选 fast_validation，要求两个不同的凭证，不执行隐私填充等待，并仅公开汇总错误分类；取消勾选可执行正常隐私模式。只在默认分支运行。默认每天 UTC 22:30，即北京时间/马来西亚时间 06:30（可能延迟）。
3. 公开仓库可能在 60 天无仓库活动后停止定时工作流，需人工重新启用。没有保活插件。

离线测试：`python3 -B -m unittest -q test_signin test_private_run test_validate_run`。快速验证保留请求间隔与每账号 900 秒实际执行上限，但真实执行时间公开，可能泄漏间接信息；正式定时签到使用两个各 930 秒的固定时间窗口（合计约 31 分钟），避免过早终止关注贴吧较多的账号。
