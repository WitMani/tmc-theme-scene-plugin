# 正式游玩交付契约

来源：2026-09-17用户要求“最后产出要和现在一样是有正式游玩界面的，端到端”。流水线默认保留当前7格托盘/同类三消/180秒/静态载具可收集；默认216实例、每种3的倍数。独立Stage1/Stage2调用仍保持原范围。

## 开工前

定位当前安装的tmc-vehicle-motion技能并读取，不硬编码缓存版本。检查其doctor、playable-deliver、playable-gallery及Playwright/Chromium。缺少完整游玩工具时先报告阻碍，不先生成一批图片再发现无法交付。数量规划记录count_multiple=3及gameplay_basis；明确用户选择其他玩法时另记覆盖，现有三消导出器不能冒充支持其他游戏。

## 完成顺序

1. 每seed完成布局post/render/scene-review/validate，必须精确计划数量与sceneCompletion.ok=true。
2. `scripts/tmc-motion playable-deliver --run-dir <run> --title <主题名称> --mode static`。此命令读取已审核静态layout，不使用残留motion文件，验证每类可收集实例为3的倍数，生成单文件playable.html、item_placements.csv，执行实际浏览器功能测试，保存绑定文件哈希的playable-delivery.json。输入、HTML或测试变化使交付状态失效。
3. 实际查看playable-test.png（测试会重开后截图）；可用且未受策略阻止时在当前浏览器检查页面尺寸、点击与入口。浏览器策略阻止时如实报告，不绕过；已运行的独立自动测试与视觉截图可作为已完成的验证，但不得声称已在受阻浏览器中检查。
4. `scripts/tmc-motion playable-gallery --batch-dir <batch> --title <主题名称> --recommended <seed>`。生成index.html，只给当前验证有效的候选显示开始游玩。失败候选明确未完成；部分完成不能报告全部完成。
5. 最终主链接为推荐游玩页和index.html。背景PNG、素材、layout.json、效果图仍保留；seed-gallery只做附加效果比较。

## 必备界面与验证

清晰主题标题、画面、目标进度、托盘、倒计时、暂停/继续、重开、缩放/平移、明确胜负反馈；叠放收取遵循先上层后底座。测试必须覆盖真实鼠标三消、叠放顺序、通关、托盘溢出、重开恢复、暂停冻结、恢复、超时失败及无页面错误。透明命中与画家层级沿用现有引擎。测试不得因重复命中同一叠放角色而假报托盘失败；失败或skipped均不算通过。

静态模式是明确的游戏呈现选择，不等于车辆运动通过；页面显示静态可收集。不为静态界面擅改已审核布局或缩小资产。

用户明确要求车辆运动：先motion-plan、查看路线、motion-validate零硬问题，再playable-deliver --mode motion；无合格路线时保留失败证据，预算内按原流程修复，不自动降级静态、不放宽轨道/道路、不要自写动画绕过运动模型。
