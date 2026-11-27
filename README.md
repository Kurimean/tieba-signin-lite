# tieba-signin-lite

基于 https://github.com/LuoSue/TiebaSignIn-1 的 MIT 许可接口逻辑改写。仅用于本人账号，并遵守服务条款。

## 部署

1. Settings → Secrets and variables → Actions → New repository secret，添加 `BDUSS`（主账号）。如需第二个本人账号，添加 `BDUSS_SECOND`，保留原 `BDUSS`；不配置第二个账号也可运行。不要把凭证写入文件、命令行、issue 或聊天。
2. Actions → Daily task → Run workflow。默认勾选 fast_validation，要求两个不同的凭证，不执行隐私填充等待，并仅公开汇总错误分类；取消勾选可执行正常隐私模式。只在默认分支运行。默认每天 UTC 22:37，即北京时间/马来西亚时间 06:37（可能延迟）。
3. 公开仓库可能在 60 天无仓库活动后停止定时工作流，需人工重新启用。没有保活插件。

离线测试：`python3 -B -m unittest -q test_signin test_private_run test_validate_run test_verify_status test_batch_signin`。快速验证每账号上限 900 秒，不进行人为填充；真实执行时间公开，可能泄漏间接信息。正式签到采用一键签到接口，使用两个各 300 秒的固定隐私窗口（合计约 10 分钟），每账号工作上限 280 秒。

签到前使用只读接口核对状态及完整关注 ID 集合；仅当可签到贴吧全部报告已签到才跳过写入。如确认存在未签到贴吧，每账号最多提交一次一键签到请求。随后核验完整状态；若遭拒绝，不切换接口或重试；不完整、身份异常或状态不明不会被判作完成。公开日志仍只提供汇总结果，不记录贴吧名称、账号或凭证。

一键签到接口参考 https://github.com/lumina37/aiotieba 的公开实现，不引入第三方依赖，不关闭 TLS 证书验证。不需要新增凭证。
