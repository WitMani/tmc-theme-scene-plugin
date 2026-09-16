# 最终 C：英文基础模板

先选择用户提供的1–3张参考图；用户未提供图片时使用随技能打包的 assets/default-reference.png 一张。查看实际参考图后，填入编号与角色，再填写主题。所有候选共享这个基础段，最后按 candidates.md 添加各自差异段。本文模板完整包含最终C方案，不依赖旧技能目录或实验图片。

```text
Create one complete casual-game scene in the requested theme.

FIXED SCENE SCALE
Use square framing for a 4096 x 4096 delivery canvas. Ordinary characters have a visible height of about 128 pixels on that canvas, or 3.125% of scene height, with natural body and costume variation. This canvas-relative scale overrides conflicting character size in the references. Preserve recognizable small characters and coherent building-to-character proportions. Do not enlarge characters to fill empty space.

REFERENCE AND PRIORITIES
The clean reference group contains [N: 1, 2 or 3] images, followed by one script-generated camera-guide overlay of Reference 1 (image [N+1]), then the reviewed layout sketch for this candidate (image [N+2]). Reference 1 is the primary source for art style and proportions; other clean references supplement compatible shapes and structural details. The camera-guide image supplies projection guidance only; its annotations must agree with the declared camera and validated sketch; do not copy inconsistent projection directions from any reference. Follow any explicit roles below. The reference group is the reference for the drawing language, camera, shape proportions, character-to-building scale, structural detail density, and stylized surface treatment. Preserve its coherent game-asset appearance. Apply the fixed orthographic camera rule and the outline, palette, and material refinements below even where the references show perspective convergence, black contours, heavy dark colors, or strong highlights.
Reference roles and observed characteristics: [identify each input image in order, its role, common traits, and primary-image traits].

LAYOUT SKETCH ROLE
The last image is a validated world-coordinate orthographic spatial plan, NOT an art-style or architecture-shape reference. It uses neutral low-detail placement marks only. Do not inherit its box shape, flat geometric modeling, face shading, roof design or regularity. Preserve the clean style reference's rounded shapes, outline character, palette, texture budget and softness. Improving geometry must not harden shadows, increase plank lines, square off buildings or create a different rendering style. Follow its broad clickable placement zones, limited non-clickable environmental areas, major cluster positions and route connections. Interpret its region IDs and placeholders using this mapping: [actual sketch legend and region-to-theme mapping]. Preserve the shared orthographic camera. Render this arrangement using the clean references’ art style, proportions and detail budget. Do not copy sketch colors, labels, zone boundaries, placeholder boxes or legends into the finished scene.

THEME
Theme: [name and subtitle].
Buildings: [elements].
Characters: [elements].
Vehicles: [elements].
Props and environment: [elements].
World organization: [only the necessary theme-appropriate land, water, circulation and elevation design].

The theme may reshape the background, terrain, roads, waterways, parcels and building arrangement. Use the fixed elevated orthographic camera defined below and preserve the requested framing, not the exact reference terrain topology. Keep a consistent family of recognizable assets, readable gaps, appropriate repetition, and small character proportions. Retain meaningful architectural features and moderate rounded volume while controlling incidental decoration.

INTERACTION-LED TERRAIN ALLOCATION
Plan two spatial roles before arranging the scene. Clickable zones accommodate the intended clickable buildings, characters, vehicles and props, with readable spacing and placement room. These zones must occupy the clear majority of the scene and form generous usable parcels. Non-clickable zones contain environmental rocks, cliffs, landforms or other non-interactive scenery that establish the theme. Keep these zones a small supporting share, mainly along edges or in limited local accents. Avoid broad central cliffs, mountains or decorative water expanses that consume placement space or fragment it into narrow scraps.
Classify areas by intended interaction: water supporting clickable boats can be a clickable zone; purely scenic water is non-clickable. Preserve theme-appropriate infrastructure. Increase usable placement area and reduce environmental occupation while preserving reference-derived asset scales and moderate density. Maintain readable gaps instead of enlarging characters or packing objects into every opening. This is a spatial allocation rule, not an object-count quota or a pixel-fill target. Do not render zone labels, overlays or click boxes.

FIXED CAMERA
Use a fixed elevated oblique orthographic projection that shows both the tops and sides of objects. Parallel edges must not converge toward vanishing points, and comparable objects must remain approximately the same size regardless of distance. Keep exactly the same camera orientation and elevation angle across candidates A, B and C. Change layouts, not the viewing direction, camera tilt or perspective. Shared camera description: [actual declared camera copied verbatim across A/B/C: default azimuth 45 degrees and downward elevation 45 degrees, parallel orthographic projection, upright verticals, ground-axis screen slopes +0.707107 and -0.707107; not screen diagonals of 45 degrees].
CAMERA GUIDE ROLE
The declared camera and validated layout use one shared projection for ground, road widths, circular structures, bridges, rails and placement masses. At the default camera, a ground circle becomes an ellipse with minor/major ratio 0.707107. Use the camera-guide image's cyan and magenta lines only as matching approximate ground-axis reminders and yellow segments for upright height. No screen-space circles pasted onto oblique ground, no independent camera per building. Apply this camera consistently to wall bases, horizontal eaves, foundations, bridge decks and platforms. Pitched roof slopes are not ground-plane edges; naturally rotated objects need not align to the two guide axes but must share the same projection. The overlay does not lock terrain or layout. Use the clean original for art style; the script overlay supplies geometric annotations only. The lines are annotations only: remove ALL guide lines, grids, markers and labels from the finished scene.

GOOSE CHARACTER DESIGN — WHEN APPLICABLE
If the requested characters are geese, favor a chubby, big-round-headed goose design: a large rounded head, a plump compact feathered body, a short but recognizable goose neck, a simple readable goose beak, and small webbed feet. Use restrained costume and prop changes for different roles. Keep the same goose proportions across candidates. Avoid slender realistic geese or human-bodied characters. The enlarged head is an internal character proportion; keep the overall character small relative to buildings. Do not apply goose anatomy to themes that explicitly request other species.

COLOR-AWARE OUTLINES
Use clean, consistent outlines whose hues are derived from the neighboring fill colors. Prefer a moderately darker, chromatic shade of the local color family over uniform black contours. Choose a boundary color with enough contrast to separate adjacent objects. Keep outer contours readable and interior structural lines restrained. Do not remove outlines.

LIGHT, CHROMATIC PALETTE
Create a relaxed, light casual-game palette. Reduce the area occupied by heavy dark colors and achromatic extremes. Prefer softly tinted off-whites, colored light tones, and chromatic dark accents over large regions of pure white or pure black. Keep theme identity and clear hue/value separation. Preserve necessary small dark details such as eyes; do not wash out all contrast or desaturate the whole scene.

RESTRAINED MATERIAL RESPONSE
Reduce the strength and area of specular highlights and reflections. Favor softly matte or gently satin surfaces. Avoid white streaks, brushed-looking white marks, shiny rims, bright reflective edge trim, and aged ornamental material effects. Convey materials with color, a few structural marks, broad shading and gentle localized gradients. Preserve volume and identifying building details without adding realistic microtexture or flattening assets into bare geometric icons.

SCENE COHERENCE
Planned core prototypes and repeated instance targets: [actual authored scene-plan summary]. Preserve the necessary support infrastructure and its connectivity: [actual rail/water/road/bridge/platform requirements]. Density and composition objectives: [actual density intent and goals]. Railway tracks supporting selected trains must remain part of the terrain. Do not erase them as decorative railings. These plans guide composition; actual output must still be reviewed and counts are not guaranteed by this prompt.
Use theme-appropriate infrastructure. Boats belong in navigable water; land vehicles belong on ground routes; bridges connect reachable surfaces. Avoid arbitrary rivers in themes that do not support them. Keep the background calm and prevent foliage, debris and small decorations from overwhelming the asset silhouettes.

Maintain coherent large color fields and consistent lighting across the canvas. Follow the requested output framing and UI treatment; for scene-only output, include no UI, text, timers, buttons, borders or watermarks.
```

保持相同参考组；默认第一张主导，共性优先，不平均混合不兼容画风。干净原图只有一张时删除其他干净参考图的描述，但保留额外辅助线图及其用途。N表示干净原图数量，默认实际输入为N+2（干净图、辅助线图、当前草图）；填入真实编号。用户明确关闭辅助线或脚本失败已记录降级时删除派生图与CAMERA GUIDE ROLE相关句子，并沿用已审核草图的统一镜头，保留当前布局草图并重新填写其编号（N+1）。不要把占位符直接发给生成器。斑驳是后续事项，不视为已解决。

辅助线脚本与校验步骤见 [camera-guides.md](camera-guides.md)。默认图是实际图片输入，不是纯文本模式。使用默认图时 N=1，并在参考角色中说明它是内置河畔村落画风参考；不要继承其中人类角色，目标角色依主题定义。文件路径按 SKILL.md 所在目录解析，并通过图像工具的图片引用参数传入。

三个候选必须复用同一段具体镜头描述；不要给A/B/C分别设置不同的朝向或俯角。胖头鹅约束只在主题角色是鹅时适用，优先于参考图中的细长鹅或人类比例。
