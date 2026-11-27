# D09 模型可见轻量接口候选

基于 D08 已验证代码与证据提交 9aa011d72d257f974f70a16fe34fba0551eb0358。新增只读紧凑接口，不增加执行权限；旧 UI structuredContent 不变，旧详情默认 app-only，可显式回退。状态/结果 JSON UTF-8 字节预算600/1500，超预算返回错误；不是 Token 上限证明。增量内容 SHA256 非持久 revision；日志分页仅事件类型与时间/游标，不返回任意文件、用户 prompt 或原始输出。实际宿主是否遵守 visibility 未验证，非安全边界。D10 进一步版本化，D16 优化数据库聚合查询。测试待 CI；真实模型/宿主 NOT_RUN。


## D09 补测
初次 [Run 45938576927](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45938576927) 四环境 PASS。补充正向操作状态与当前结果绑定：Python 在原子写入后发布 turn + SHA256，Node 只读取精确状态绑定的 artifact；旧记录无引用时返回不可用，不以扫描旧目录冒充当前结果。校验 ID/session/exit/task status、大小、链接路径；不承诺对恶意本地同权限并发改写的 OS 级隔离。补测含运行中、内容篡改、错误身份、过大、缺失 turn、链接/junction。真实模型/宿主仍未测。复检待执行。

## D09 补测最终候选结果
[Run 45940757723](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45940757723) completed/success，tested commit `99c0e5544bf03c1702fee7b7deb1a196b9fba502`。Ubuntu (140314263163)、Windows Server x64 (140314263322)、macOS (140314263379)、Windows 11 ARM64 (140314263404) 四个 job 全部成功。正向操作状态、当前 artifact SHA256/身份、running/stale/missing/oversized/identity/link 拒绝及实际 Mock run/resume 结果引用验证均通过；累计回归和两种 Windows 安装生命周期通过。真实模型调用 0；真实 Antigravity 可见性/UI、实际 Token、真实宿主及前置正式合并仍 BLOCKED。旧数据无 result_ref 不推断；日志只返回事件元数据；内容哈希不是持久 revision。D09 候选可作为 D10 基础，PR #11 Draft，未合并。
