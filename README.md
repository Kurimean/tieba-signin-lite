# tieba-signin-lite

基于 https://github.com/LuoSue/TiebaSignIn-1 的 MIT 许可接口逻辑改写。仅用于本人账号，并遵守服务条款。

## 部署

1. Settings → Secrets and variables → Actions → New repository secret，添加 `BDUSS`（主账号）。如需第二个本人账号，添加 `BDUSS_SECOND`，保留原 `BDUSS`；不配置第二个账号也可运行。不要把凭证写入文件、命令行、issue 或聊天。
2. Actions → Daily task → Run workflow。只在默认分支运行。默认每天 UTC 22:30，即北京时间/马来西亚时间 06:30（可能延迟）。
3. 公开仓库可能在 60 天无仓库活动后停止定时工作流，需人工重新启用。没有保活插件。

离线测试：`python3 -B -m unittest -q test_signin test_private_run`。
