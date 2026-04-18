# Face Ground Truth And Resolution Handling

## Key Distinction
- 六张脸的心理学“真值”是稳定的，定义在共享的 0–10 空间。
- 所有和坐标点有关的绘图与统计检验，都应先放缩到共享的 0–10 空间中完成。
- 任何像素坐标、`true_leftBar` / `true_rightBar`、`F*X` / `F*Y`、或 400×400 坐标，都不是原始实验里的唯一真值，而是某种显示尺度下的派生表示。
- 因此，分析时不能把一个固定的像素模板直接当作所有被试、所有日期、所有任务的真实坐标。

## Canonical Ground Truth
仓库里的稳定真值来源于 `scripts/analysis_common.py`：
- `FACE_TRUE_RAW`：六张脸在共享 0–10 空间中的 canonical coordinates。
- `FACE_TRUE_400`：把同一组真值映射到 400×400 参考框后的派生坐标，仅用于兼容旧图形或中间转换，不是默认分析空间。

### Raw 0–10 Coordinates

| Face | Ability | Warmth |
| :--- | ---: | ---: |
| F1 | 2.416 | 4.788 |
| F2 | 2.789 | 7.765 |
| F3 | 6.426 | 8.527 |
| F4 | 8.817 | 6.716 |
| F5 | 4.894 | 2.020 |
| F6 | 7.659 | 3.185 |

## What `FACE_TRUE_400` Means
- `FACE_TRUE_400` 是把 0–10 空间线性映射到 400×400 的 legacy reference frame。
- 它适合：
  - 兼容旧版脚本或历史图形；
  - 在需要复现既有 400×400 参考框时作为中间表示；
  - 辅助检查线性映射是否正确。
- 它不等同于：
  - 某个具体被试当天实验界面的真实像素位置；
  - EP / CT / PD 原始文件里直接记录到的 `true_*` 坐标；
  - 所有任务共享的唯一屏幕分辨率模板。
- 只要进入跨被试绘图、汇总或检验，默认应回到共享的 0–10 空间。

## Resolution And Task-Specific Rules

### EP Task
- EP 原始任务中的目标条长度来自公式：`facebar = round((facevalue / 10) * squareSidePx)`。
- 因此，同一组 0–10 真值在不同 `squareSidePx` 下会对应不同的像素坐标。
- `scripts/proc1_eptask_learning_analysis.py` 会根据记录下来的 `true_leftBar` / `true_rightBar` 反推 `squareSidePx`。
- 不同被试、不同日期可能使用不同屏幕分辨率，因此 EP 的 `squareSidePx` 需要按“被试 × 日期”推断，而不是全局固定。
- 已知同一被试的 EP task day 3 与其后立即完成的任务处在同一个屏幕配置块中，因此 day 3 推断出的 `squareSidePx` 可作为后续任务的缩放依据。
- 当前 EP 分析输出 `results/proc1_eptask_learning_analysis/tables/subject_date_square_side_summary.csv` 会记录每个被试日期的 `best_integer_square_side`；已观测到的值并不唯一，而是至少包括：
  - `218`
  - `313`
  - `373`
  - `374`
  - `400`
- 所以 EP 的像素真值必须按“被试 × 日期（必要时到文件）”推断，不能直接硬编码为固定 400×400 像素坐标。

### CT Task
- CT 原始 `true_leftBar` / `true_rightBar` 在不同 cohort 中会变化。
- 当前分析脚本 `scripts/proc5_cttask_position_analysis.py` 的做法不是直接假设固定像素真值，而是：
  - 先用每名被试原始文件里的 `true_leftBar` / `true_rightBar`；
  - 结合对应 session 的 `squareSidePx` 做缩放；
  - 最后统一映射回共享的 0–10 空间做比较和统计。

### PD Task
- PD 分析中的真实几何关系来自 EP/MR 学到的 face coordinates，而不是 PD 旧模板。
- `PD_RECORDED_FACE_TRUE_400` 只用于推断每个被试记录坐标对应的方框尺度。
- 推断出被试特异尺度之后，应把坐标统一放缩回 0–10 空间，再与 canonical truth 比较。

### MR Task
- MR 数据里实际重建矩形的长宽由 `WarmthRange` / `AbilityRange`（或 legacy `Xrange` / `Yrange`）决定。
- 如需投射到 400×400，那只是中间转换；最终跨被试绘图和检验仍应回到 0–10 空间。

## Practical Rule For Documentation And Analysis
- 讨论“真实脸位置”时，默认指 `FACE_TRUE_RAW` 对应的共享心理空间真值。
- 需要做统一比较图或统计检验时，默认使用共享的 0–10 空间。
- 只有在兼容旧图或检查映射过程时，才使用 `FACE_TRUE_400` 作为中间参考。
- 需要解释原始任务文件中的像素坐标时，必须额外说明对应的 `squareSidePx`、轴长度或被试特异映射。
- 不要把 canonical 400×400 坐标写成“实验真实分辨率坐标”。

## Recommended References
- `scripts/analysis_common.py`：canonical truth constants。
- `scripts/proc1_eptask_learning_analysis.py`：EP 的 `squareSidePx` 推断与学习轨迹分析。
- `results/proc1_eptask_learning_analysis/tables/subject_date_square_side_summary.csv`：当前已审计到的方框尺寸分布。
- `scripts/proc5_cttask_position_analysis.py`：CT 的个体线性映射逻辑。
- `scripts/proc4_pdtask_analysis.py`：PD 的个体尺度归一化逻辑。

## Related Docs
- `docs/architecture.md`
- `docs/pdtask-main-effect.md`
- `docs/analysis-roadmap.md`
