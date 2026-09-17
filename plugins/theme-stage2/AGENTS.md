# theme-stage2 开发约定

- 这是 Stage 2 独立插件；不要修改 Stage 1 插件或依赖原实验目录。
- 美术、选材、交付配置在 runtime/profiles/；用户原话与规范快照在 runtime/docs/，区分原文与解释。
- 默认一张Stage 1源图、22种独立素材（建筑8、道具6、载具3、角色5）和1张背景，仅交付PNG，不默认HTML、原图对照或回拼。
- 不将示例当成本次输入，不将合成测试通过记录当成美术验收。
- 修改脚本后验证行为；插件更新使用 plugin-creator 的缓存版本与重装流程，不手改 marketplace 配置。
