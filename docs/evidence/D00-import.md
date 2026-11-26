# D00 固定上游快照完整性证据

- 上游：Koala973/antigravity-lead-codex
- 上游 commit：`b6c36443e5a134ea36aa18dc171f312fdd54b5bc`
- 规划基线：`03b073d87b7431965072e8a061cadb4524d86c53`
- 导入 commit：`7f6bebddc5a895a1da707d66b187f2221a7cca3e`
- 导入 tree：`5ea8fdefb5e621d48df0b990d1dbf3c31a41d13c`
- 结果：45/45 文件路径映射、Blob SHA、mode 一致；0 不匹配；原规划文件除根 LICENSE 补充版权外在导入提交中字节不变。后续文档提交仅更新状态、来源和证据。
- 功能测试、Windows 实机、真实模型调用及性能基准：NOT_RUN（D00 不包含此项）。
- 未启用 CI、未改动上游业务源码、未合并 main。

| 上游路径 | 导入路径 | Git Blob SHA | Git mode |
|---|---|---|---|
| `.gitignore` | `.gitignore` | `c6195107517e3370bc06753c82b4e1a3a330f2f6` | `100644` |
| `CHANGELOG.md` | `CHANGELOG.md` | `edef39dbe7fea47670f19d07dd46dfc1a31f4403` | `100644` |
| `LICENSE` | `LICENSE.upstream` | `a03b68d32c3114a10062f77212f2c959f2129d7c` | `100644` |
| `README.md` | `README_UPSTREAM.md` | `ddaf2686800ebd96ae4fca733c53b72252015086` | `100644` |
| `README_EN.md` | `README_EN.md` | `92098f15d00fc4b227daeed7babfade4830e1a37` | `100644` |
| `docs/ARCHITECTURE.md` | `docs/ARCHITECTURE.md` | `63b39d4db55b5b4496f04598b6d3058eda99af5c` | `100644` |
| `docs/CAPABILITIES.md` | `docs/CAPABILITIES.md` | `07c671627877164b1b13ae6102a086df254026e5` | `100644` |
| `docs/DOCTOR.md` | `docs/DOCTOR.md` | `ea87bab305768b46845b42191f65bc26751a2f1c` | `100644` |
| `docs/workflows/ci.yml` | `docs/workflows/ci.yml` | `95237a18587c8e85f371fe7053d6e2ce4f8af275` | `100644` |
| `docs/workflows/release.yml` | `docs/workflows/release.yml` | `3e1d5b321405b5a5a17a5dfced0623da742ea5e4` | `100644` |
| `img/logo.svg` | `img/logo.svg` | `21fd335a6135d029b09e9fc651bb8e5cd6c1869c` | `100644` |
| `img/preview-console.svg` | `img/preview-console.svg` | `3fadd8a524eca46e892fb3db6c346ab376420c03` | `100644` |
| `img/showcase-live.jpg` | `img/showcase-live.jpg` | `d3bb2de8d4a7df16b9384e3dc2aa1bdfeb7d74c3` | `100644` |
| `img/showcase-subagents.jpg` | `img/showcase-subagents.jpg` | `5b7207fbd8eee072665e9d13ff6862363da7b836` | `100644` |
| `plugins/codex-auto-router/hooks.json` | `plugins/codex-auto-router/hooks.json` | `7aa985b5ff604e6a4c29fdd88e974bc21ad3879c` | `100644` |
| `plugins/codex-auto-router/hooks/allow_dispatch.py` | `plugins/codex-auto-router/hooks/allow_dispatch.py` | `7c5cb6292339f6e5e5f8f63ad33601b844442a5b` | `100755` |
| `plugins/codex-auto-router/plugin.json` | `plugins/codex-auto-router/plugin.json` | `e36a3f1dd88c8c7b8d7318988463d1068a7e567a` | `100644` |
| `plugins/codex-auto-router/rules/AGENTS.md` | `plugins/codex-auto-router/rules/AGENTS.md` | `a89aeb302fb191df1cff357c30ea35f37cc1e437` | `100644` |
| `plugins/codex-console/assets/logo.svg` | `plugins/codex-console/assets/logo.svg` | `21fd335a6135d029b09e9fc651bb8e5cd6c1869c` | `100644` |
| `plugins/codex-console/bin/run-server.sh` | `plugins/codex-console/bin/run-server.sh` | `1e94b4b817b774877a5a5afad29bd3ebbf5d3c93` | `100755` |
| `plugins/codex-console/dist/app.html` | `plugins/codex-console/dist/app.html` | `049db88b452fe7ed4e765fcfbb8ceda07077adad` | `100644` |
| `plugins/codex-console/mcp_config.json` | `plugins/codex-console/mcp_config.json` | `57d701e83ecd56389f3457eb47d6fd4c6c4f18bb` | `100644` |
| `plugins/codex-console/package-lock.json` | `plugins/codex-console/package-lock.json` | `489de3cc311ff985f960aa09a70b0fbb8c8dcab4` | `100644` |
| `plugins/codex-console/package.json` | `plugins/codex-console/package.json` | `993f605304dfa4148028dac582f2bdbbc8b1befe` | `100644` |
| `plugins/codex-console/plugin.json` | `plugins/codex-console/plugin.json` | `f7f7289197bc267365892f7ccdfad10e0d9c7c06` | `100644` |
| `plugins/codex-console/server/codex-store.mjs` | `plugins/codex-console/server/codex-store.mjs` | `25b9a0a0fdb766805a7686fa5144cea0a4243b80` | `100644` |
| `plugins/codex-console/server/console-db.mjs` | `plugins/codex-console/server/console-db.mjs` | `bdbd08cf975ff8f2ba51a8241613750607f0ff4f` | `100644` |
| `plugins/codex-console/server/index.mjs` | `plugins/codex-console/server/index.mjs` | `4eadeaa1c669162f3727d1498fa5f7bca90763d5` | `100644` |
| `plugins/codex-console/server/quota.mjs` | `plugins/codex-console/server/quota.mjs` | `2c8b6302fb6607d94c3c3d0a6b607e2b4b24b409` | `100644` |
| `plugins/codex-console/server/runner.mjs` | `plugins/codex-console/server/runner.mjs` | `30d32e12771391c19523a8a726cf43d4083d72b0` | `100644` |
| `plugins/codex-console/skills/codex-console/SKILL.md` | `plugins/codex-console/skills/codex-console/SKILL.md` | `d624989b1672d37d9b85786e29666fdee3cd4287` | `100644` |
| `plugins/codex-console/ui/app.html` | `plugins/codex-console/ui/app.html` | `2130a0faf11d3b31e1e92c06b1b94e77aafa98a2` | `100644` |
| `plugins/codex-console/ui/cat-pet.js` | `plugins/codex-console/ui/cat-pet.js` | `ac5533661a5ea50c7653f3227708c6c8672c7df6` | `100644` |
| `plugins/codex-console/ui/main.js` | `plugins/codex-console/ui/main.js` | `32baa8a770f21beeef370decf1c710ac7d157e1f` | `100644` |
| `plugins/codex-console/ui/styles.css` | `plugins/codex-console/ui/styles.css` | `10eaf3c4f9407f1794d5ea5bb35a19ee50158201` | `100644` |
| `plugins/codex-console/vite.config.mjs` | `plugins/codex-console/vite.config.mjs` | `c535149e61b6c783fffc6e671f35511a07356a29` | `100644` |
| `scripts/doctor.sh` | `scripts/doctor.sh` | `22e9ad1fa6fb18b02d00a463ed320b3792d78dfc` | `100755` |
| `scripts/install.sh` | `scripts/install.sh` | `9c6b9a9ca8e67b19e5d73f731a64a4694699bc18` | `100755` |
| `scripts/package-release.sh` | `scripts/package-release.sh` | `80a1c9f359ab15fb3e670ea39275c85022dc62f4` | `100755` |
| `scripts/privacy-check.sh` | `scripts/privacy-check.sh` | `4a3e402ff47dafdd6f234875f71d95dc36df1c0a` | `100755` |
| `skills/multi-agent-dispatch/SKILL.md` | `skills/multi-agent-dispatch/SKILL.md` | `d961c2dd9ce86b45245a563ded9e1da3ec6c4ccc` | `100644` |
| `skills/multi-agent-dispatch/resources/report_schema.json` | `skills/multi-agent-dispatch/resources/report_schema.json` | `36d5a817785eeaf04a972c5c363ab04beb5c482e` | `100644` |
| `skills/multi-agent-dispatch/scripts/dispatch.py` | `skills/multi-agent-dispatch/scripts/dispatch.py` | `2057553f544c0ef605eb2c9ad8ae0f8fb59df84a` | `100755` |
| `tests/test-mcp-console.mjs` | `tests/test-mcp-console.mjs` | `bc17beb142c435bd8b132f796fa072b987bb3a14` | `100644` |
| `tests/test_dispatch.py` | `tests/test_dispatch.py` | `a79b8122dbe611a93e67ec00cec3b454255846f3` | `100644` |

## 回滚
关闭未合并的 PR 即可保持 main 原样。若已由用户批准合并，使用正常 revert 撤销 D00 导入及状态记录，避免强推；保留原规划与提交历史。
