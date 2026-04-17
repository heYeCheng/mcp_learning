# 需求文档：交易逻辑驱动的智能选股系统

> **Version**: 1.3
> **Date**: 2026-04-16
> **Status**: DRAFT
> **Branch**: main
> **Repo**: ZhuLinsen/daily_stock_analysis
>
> **整合来源**:
> - `heyecheng-main-design-20260414-222300.md` (Doc 1, APPROVED)
> - `heyecheng-main-design-20260415-080000.md` (Doc 2, REVIEW FINDINGS)
> - `ceo-plans/2026-04-14-sector-logic-engine.md` (CEO Plan)
> - 2026-04-16 office-hours 补充澄清
>
> **冲突裁决**: 所有矛盾以本文件为准。本文件基于 `heyecheng-main-design-consolidation-20260416.md` 的已决事项。

---

## 一、系统定位

### 1.1 系统名称

**交易逻辑驱动的智能选股系统**（Trading Logic-Driven Smart Stock Selection System）

系统本质上是一个**选股系统**，而非纯粹的认知工具。它既帮助用户理解市场逻辑（认知价值），也输出具体的股票推荐列表和操作建议（决策价值）。

### 1.2 核心使命

> 确保用户不受个股波动影响，能理性持仓或空仓，而不会情绪化交易。

解决 A 股散户的三个核心痛点：
1. **错过入场** — 看到逻辑切换时已经大涨
2. **被噪音震出** — 分不清是逻辑反转还是量化噪音
3. **信息过载** — 新闻太多，无法提炼出驱动行情的**那一个**主导逻辑

### 1.3 核心哲学：跟随不预测

系统基于当前可观测信号给出建议，**绝不做未来走势的点位预测**。跟随的核心是量价交易的波段操作。

- ✅ "当前信号显示 XX，建议做 YY" — 这是观察-响应
- ✅ "strength declining，建议减仓" — 这是对当前状态的响应
- ❌ "预计将涨到 XX 价位" — 这是点位预测，系统不做
- ❌ "目标价 XX 元" — 这是点位预测，系统不做

个股 T+N 能涨到哪里或跌到哪里，只有神才能知道。我们不是神。

### 1.4 交易风格

- **波段交易**：持仓天~周级别
- **不是** T+0/T+1 日内交易
- 扫描频率：**收盘后每日一次**

### 1.5 系统边界

| 本系统（选股系统） | 择时系统（另一个系统） |
|---|---|
| 选出股票 | 基于个股在不同板块的角色细化买卖时机 |
| 五维雷达图评分 | 区分龙头/中军/跟风的入场时机 |
| 基础操作建议（方向/仓位/止损条件） | 具体买卖点判断 |
| 每日自动分析 top200 + 用户自选 | 盘中实时信号 |

---

## 二、三层独立评分体系

### 2.0 架构总览

系统采用**三层独立评分架构**。每层有独立的评分维度、独立的雷达图、独立的数据模型。仅在综合决策（选股推荐）时，三层分数按权重组合。

```
┌─────────────────────────────────────────────────────────────┐
│  宏观层 (Macro Layer)                                        │
│  评分：macro_thesis_score                                    │
│  雷达图：流动性 / 政策方向 / 经济周期                          │
│  输出：当前宏观环境状态 + 对各板块的差异化影响                  │
└────────────────────┬────────────────────────────────────────┘
                     │ macro_context（全局注入）
                     │ sector_macro_impact（差异化影响，LLM 解读）
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  板块层 (Sector Layer)                                       │
│  评分：sector_thesis_score / sector_price_score              │
│  雷达图：逻辑面 / 基本面 / 技术面 / 资金面 / 情绪面            │
│  输出：板块主导逻辑 + 强度趋势 + 翻转预警                      │
└────────────────────┬────────────────────────────────────────┘
                     │ sector_dominant_logic
                     │ sector_logic_strength
                     │ sector_macro_adjustment
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  个股层 (Stock Layer)                                        │
│  评分：stock_thesis_score / stock_price_score                │
│  雷达图：逻辑面 / 基本面 / 技术面 / 资金面 / 情绪面            │
│  输出：个股推荐 + 操作建议                                    │
└────────────────────┬────────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  综合决策层 (Composite Selection)                             │
│  f(宏观, 板块, 个股) → 重点关注 / 观察名单 / 其余              │
└─────────────────────────────────────────────────────────────┘
```

### 2.0.1 关键术语与评分关系

- `macro_thesis_score`：宏观层环境健康度，决定系统是否可以给出较强推荐。
- `sector_thesis_score`：板块五维雷达总体评分，反映板块当前基本面、资金面、情绪等整体健康度。
- `sector_logic_strength`：板块主导逻辑强度，反映交易逻辑证据链是否成立、逻辑是否稳定。
- `sector_macro_adjustment`：宏观层对板块的差异化修正项，仅用于最终推荐加权，不直接修改 `sector_logic_strength`。
- `stock_thesis_score`：个股五维雷达综合评分，反映个股逻辑、基本面、技术、资金、情绪的综合判断。
- `stock_price_score`：个股价格行为评分，反映市场对个股当前趋势和价量行为的评价。
- `logic_strength`：单个交易逻辑的强度分数，纯粹反映逻辑自身证据链，不包含价格预测。
- `model_consistency_score`：LLM 多次运行一致性评分，用于衡量 AI 结论稳定性，并映射为最终的 `confidence`。

### 2.1 宏观层（Macro Layer）

#### 2.1.1 宏观环境判断

宏观层评估**五个维度**，覆盖领先指标、同步指标和滞后指标，以捕捉宏观拐点：

| 维度 | 评分要素 | 数据源 | 指标类型 |
|---|---|---|---|
| **流动性环境** | M1-M2 剪刀差（领先3-6月）、Shibor 期限结构、社融存量增速、Shibor-Hibor 利差 | 央行、Tushare cn_m/sf_month/shibor/hibor | 领先+同步 |
| **经济周期位置** | PMI 领先指数（新订单-库存）、PMI 库存周期、PMI 分行业景气度 | 统计局、Tushare cn_pmi | 领先+同步 |
| **通胀与成本** | PPI-CPI 剪刀差、PPI 产业链传导、PMI 价格指数 | 统计局、Tushare cn_cpi/cn_ppi | 同步+滞后 |
| **政策方向** | 高层会议定调、部委表态、产业政策密集度、实体融资成本 | 政府文件、部委网站、新华社 | 同步 |
| **全球联动** | 美国宏观（Fed Rate、10Y Treasury、ISM PMI、非农）、Polymarket 预测、关税风险 | Fed、BLS、Polymarket | 领先+同步 |

**核心改进**：
1. **领先指标优先**：M1-M2 剪刀差领先股市 3-6 个月，PMI 新订单-库存差领先经济周期 2-3 个月
2. **衍生指标**：剪刀差、期限结构、增速趋势等二阶指标，比单点数据更能反映拐点
3. **时间序列分析**：12 个月滚动窗口，计算趋势动量、拐点检测、周期相位
4. **经济周期四象限**：根据增长+流动性定位当前周期位置（复苏/过热/滞胀/衰退）

**输出**：`MacroContext` 记录，包含：
- `macro_thesis_score`（0-1）：宏观环境整体健康度
- `macro_state`：复苏 / 过热 / 滞胀 / 衰退（四象限分类，替代原三分类）
- `macro_radar`：{流动性环境: 0-10, 经济周期位置: 0-10, 通胀与成本: 0-10, 政策方向: 0-10, 全球联动: 0-10}
- `leading_signals`：领先指标拐点预警列表（如 "M1-M2 剪刀差连续 3 月收窄，预示 2-3 月后流动性收紧"）
- `cycle_position`：当前经济周期四象限坐标 {growth_momentum: -1~+1, liquidity_momentum: -1~+1}
- `trend_analysis`：各维度 12 月趋势（increasing/stable/declining）+ 拐点时间戳

**频率**: 每周更新一次（宏观变化缓慢，不需要每日更新）+ 重大事件触发立即重跑（Fed/PBOC 决策、Polymarket >20% 变化）。

#### 2.1.2 宏观→板块差异化映射

宏观环境对不同板块的影响方向、程度各不相同。系统通过以下机制处理：

1. **板块敏感度配置表**：每个板块预定义对**五个宏观维度**的敏感度（-1.0 ~ +1.0），并细化到**指标级别**
   
   **示例：黄金板块**
   - 流动性环境：M1-M2 剪刀差 +0.9（剪刀差扩大=流动性宽松=黄金受益）、Shibor 期限结构 +0.7
   - 经济周期位置：PMI 领先指数 -0.5（经济过热=黄金避险需求下降）
   - 通胀与成本：PPI-CPI 剪刀差 +0.6（通胀预期上升=黄金保值需求上升）
   - 政策方向：+0.3（政策宽松间接利好）
   - 全球联动：Fed Rate -0.8（美联储加息=美元走强=黄金承压）、Polymarket 地缘风险 +0.9
   
   **示例：AI/算力板块**
   - 流动性环境：M1-M2 剪刀差 +0.6、社融存量增速 +0.7（流动性宽松=科技估值扩张）
   - 经济周期位置：PMI 新订单 +0.5（需求扩张=算力投资增加）
   - 通胀与成本：PPI-CPI 剪刀差 -0.3（成本上升压缩利润）
   - 政策方向：+0.9（产业政策直接驱动）
   - 全球联动：ISM PMI +0.6（美国科技需求）、关税风险 -0.7
   
   **示例：银行板块**
   - 流动性环境：M1-M2 剪刀差 -0.4（流动性过松=息差收窄）、Shibor 期限结构 +0.5（期限利差扩大=银行利润增加）
   - 经济周期位置：PMI 领先指数 +0.7（经济扩张=信贷需求增加）
   - 通胀与成本：PPI-CPI 剪刀差 +0.3（通胀温和上升利好）
   - 政策方向：+0.6（货币政策直接影响）
   - 全球联动：Fed Rate +0.4（美联储加息=中美利差扩大=人民币稳定）

2. **LLM 宏观解读**：每日收盘后，LLM 在最新可用宏观数据快照基础上重新解读宏观形势，生成以下输出。宏观原始指标以每周更新为主，翻译成板块影响时可在当天重新判读。
   ```
   宏观解读报告:
   - 当前宏观状态: 复苏期（增长动能 +0.6, 流动性动能 +0.4）
   - 领先信号: M1-M2 剪刀差连续 3 月收窄（-2.1% → -3.5%），预示 2-3 月后流动性收紧
   - 周期位置: PMI 新订单-库存差 +3.2（扩张期），PMI 库存周期处于主动补库存阶段
   - 受益板块排序: AI算力(+0.9, 政策+流动性双驱动) > 新能源车(+0.7, 补库存周期) > 消费(+0.5, 复苏期) > ...
   - 受损板块排序: 黄金(-0.6, 避险需求下降) > 银行(-0.4, 息差收窄预期) > 地产(-0.3, 政策未明显放松) > ...
   - 拐点预警: 若 M1-M2 剪刀差继续收窄至 -4% 以下，建议 1 个月内逐步降低科技板块仓位
   ```

3. **宏观调整分计算**：`sector_macro_adjustment = Σ(indicator_impact × indicator_sensitivity) / N`
   - 指标级别加权：每个维度下的多个指标分别计算影响，再加权平均
   - 范围：-0.2 ~ +0.2（作用程度不大，但方向明确）
   - 该调整分在综合决策时加权到板块总评中，不直接修改板块自身 sector_logic_strength
   
   **计算示例（黄金板块）**：
   ```
   流动性环境影响 = (M1-M2剪刀差影响 +0.3 × 敏感度 +0.9) + (Shibor期限结构影响 +0.2 × 敏感度 +0.7) = +0.41
   经济周期影响 = (PMI领先指数影响 +0.5 × 敏感度 -0.5) = -0.25
   通胀成本影响 = (PPI-CPI剪刀差影响 +0.4 × 敏感度 +0.6) = +0.24
   政策方向影响 = +0.1 × +0.3 = +0.03
   全球联动影响 = (Fed Rate影响 -0.3 × 敏感度 -0.8) + (地缘风险 +0.6 × 敏感度 +0.9) = +0.78
   
   sector_macro_adjustment = (+0.41 - 0.25 + 0.24 + 0.03 + 0.78) / 5 = +0.24 → 截断至 +0.2
   ```

### 2.2 板块层（Sector Layer）

#### 2.2.1 板块五维雷达图

每个板块有独立的五维雷达图评分：

| 维度 | 评分要素 | 计算方式 |
|---|---|---|
| **板块逻辑面** | 主导逻辑 logic_strength + 逻辑趋势 | 由 TradingLogics 计算得出（见 2.2.2） |
| **板块基本面** | 板块整体盈利增速、估值分位、景气度 | 板块成分股财务指标聚合 + 行业景气指数 |
| **板块技术面** | 板块指数趋势、量价配合、支撑/阻力 | 板块指数 K 线技术分析 |
| **板块资金面** | 板块资金净流入/流出、北向持仓变化 | 板块资金流向聚合 |
| **板块情绪面** | 板块新闻热度、社交媒体讨论度 | FinBERT 聚合 + 搜索指数 |

**评分输出**：
- `sector_radar`：{logic: 0-10, fundamental: 0-10, technical: 0-10, capital_flow: 0-10, sentiment: 0-10}
- `sector_thesis_score`（0-1）：综合五维雷达图，加权计算
- `sector_price_score`（0-1）：板块指数价格行为评分

**决策矩阵**（与个股层一致）：

| | sector_price_score 高 | sector_price_score 低 |
|---|---|---|
| **sector_thesis_score 高** | 推荐板块 | 观察板块 |
| **sector_thesis_score 低** | 跳过板块 | 不参与板块 |

#### 2.2.2 板块交易逻辑追踪

**核心原则**: Strength 纯粹评估**逻辑本身的因果链条是否成立**，与市场表现（量价/资金）无关。市场表现属于板块雷达图的技术面和资金面维度。

**工作流程**:
1. AI 识别逻辑类型（产业趋势/政策驱动/供需周期/流动性/事件驱动/...）
2. AI 根据逻辑类型**自动生成**该逻辑的关键评估维度（因果链条的关键节点）
3. 系统爬取对应数据源验证每个维度
4. AI 验证逻辑真实性并评估强度

**示例**:

```
猪周期逻辑 → 自动生成评估维度:
  供给端: 能繁母猪存栏量(0-10), 仔猪出栏量(0-10), 产能利用率(0-10)
  需求端: 消费量趋势(0-10), 季节性因素(0-10), 替代品价格(0-10)
  价格周期: 生猪价格位置(0-10), 成本-利润周期(0-10)
  → 加权总分 = logic_strength

AI算力逻辑 → 自动生成评估维度:
  需求验证: 云厂商资本开支增速(0-10), 模型规模增长(0-10)
  供给验证: 产能扩张计划(0-10), 交付周期(0-10), 技术路线稳定性(0-10)
  竞争格局: 市占率变化(0-10), 新进入者威胁(0-10)
  → 加权总分 = logic_strength

加息逻辑 → 自动生成评估维度:
  政策信号: 央行表态(0-10), 利率决议(0-10)
  数据支撑: CPI/PPI(0-10), 就业数据(0-10), M2(0-10)
  传导机制: 债券收益率(0-10), 资金成本变化(0-10)
  → 加权总分 = logic_strength
```

**框架缓存策略**: 评估框架按逻辑类型（产业趋势/政策驱动/供需周期等）缓存，同类型板块共享同一套框架模板。仅在以下情况重新生成：
1. 发现新的逻辑类型（不在预定义目录中）
2. 现有框架连续 5 日无法解释板块价格行为（框架质量下降）
3. 用户手动触发重新生成

按逻辑类型缓存后，实际每日框架生成约 10 次（按逻辑类型数），而非 20 次（按板块数），大幅降低 LLM 调用成本。

#### 2.2.3 逻辑类目全集与风险模板

系统预定义以下逻辑类型，每种类型附带**通用风险模板**。风险因素用于自动扫描和强度降级。AI 可以发现并新增新类目，人工定期清理合并重复类目。

##### 2.2.3.1 逻辑类型目录

| # | 逻辑类型 | 核心特征 | 典型持续时间 | 代表场景 |
|---|---|---|---|---|
| 1 | **产业趋势** | 产业长期发展方向性变化 | 数月至数年 | AI算力爆发、固态电池突破、创新药出海 |
| 2 | **政策驱动** | 政府政策直接驱动板块逻辑 | 数周至数月 | 光伏补贴、房地产放松、行业整顿 |
| 3 | **供需周期** | 供给侧或需求侧周期性波动 | 数月 | 猪周期、面板周期、航运运价周期 |
| 4 | **流动性** | 资金环境变化驱动估值重估 | 数周至数月 | 降息降准、北向资金大幅流入/流出、M2 扩张 |
| 5 | **事件驱动** | 突发性事件短期影响板块 | 数日至2周 | 地缘冲突（美伊战争）、突发并购、自然灾害 |
| 6 | **估值重构** | 市场对该资产的估值体系发生切换 | 数周至数月 | 超跌反弹、PE/PB 重构、外资定价权转移 |
| 7 | **成本反转** | 核心原材料或产品成本趋势反转 | 数月至季度 | 锂矿价格暴跌、海运成本暴涨、能源价格反转 |
| 8 | **技术革命** | 颠覆性技术改变产业竞争格局 | 数月至数年 | AI 大模型突破、光刻技术迭代、自动驾驶落地 |
| 9 | **竞争格局变化** | 行业竞争结构发生根本变化 | 数月 | 龙头合并、反垄断处罚、新玩家颠覆格局 |
| 10 | **制度变革** | 交易制度或规则变化影响估值 | 数周至数月 | 注册制实施、T+0 试点、涨跌停规则修改 |

##### 2.2.3.1.1 逻辑分类判定规则

- **产业趋势**：仅限于需求/供给变化和产业长期结构性扩张，不含单纯政策刺激或估值事件。
- **技术革命**：仅限于技术本身引发产业格局改变，例如新技术使整个行业进入新周期。
- **政策驱动**：仅限于财政、补贴、行政政策直接触发板块上涨或下行，不包括交易规则变化。
- **制度变革**：仅限于交易制度、监管规则或市场机制变化，例如涨跌停、注册制、T+0、交易费用。
- **估值重构**：仅限于市场对估值体系的重新定价，而非基本面本身变化。
- **流动性**：仅限于资金环境变化对整个资产定价的影响，不包括个别行业供需逻辑。

##### 2.2.3.2 各类型风险模板

每种逻辑类型对应一组通用风险因素。当 AI 检测到风险信号时，自动触发排查并降低逻辑强度（详见 2.2.6 风险自动扫描机制）。

**1. 产业趋势 — 风险模板**:
| 风险因素 | 信号来源 | 触发后动作 |
|---|---|---|
| 需求不及预期 | 云厂商资本开支数据、下游订单、销量数据 | 降低需求验证维度分数 → 降低 logic_strength |
| 技术路线被替代 | 学术论文、专利、竞品发布 | 降低技术路线稳定性分数 → 降低 logic_strength |
| 竞争格局恶化 | 市场份额变化、新进入者、价格战 | 降低竞争格局分数 → 降低 logic_strength |
| 供给超预期 | 产能投产数据、扩产公告 | 降低供需平衡预期 → 降低 logic_strength |
| 产业链中断 | 供应链数据、海关数据、物流数据 | 标记供应链风险 → 降低 logic_strength |

**2. 政策驱动 — 风险模板**:
| 风险因素 | 信号来源 | 触发后动作 |
|---|---|---|
| 政策方向反转 | 政府文件、部委表态、高层会议 | 直接降低 policy 维度分数 → 可能触发翻转 |
| 执行力度不及预期 | 地方配套政策、资金到位、实施进度 | 降低执行确认分数 → 降低 logic_strength |
| 被更高层政策否决 | 国务院/中央文件覆盖部委政策 | 直接触发翻转检测 |
| 政策窗口期结束 | 政策文件明确有效期、阶段性目标达成 | 降低政策持续性分数 → 降低 logic_strength |
| 国际政策对抗 | 制裁、关税、出口管制 | 标记外部风险 → 降低 logic_strength |

**3. 供需周期 — 风险模板**:
| 风险因素 | 信号来源 | 触发后动作 |
|---|---|---|
| 周期提前到来 | 产能去化加速、库存提前见底 | 调整周期相位判断 → 更新 logic_strength |
| 周期延后 | 产能去化慢于预期、库存去化放缓 | 降低周期确定性分数 → 降低 logic_strength |
| 新产能打破平衡 | 新增产能投产、海外进口增加 | 降低供需缺口预期 → 降低 logic_strength |
| 需求端结构性变化 | 消费习惯改变、替代品渗透 | 降低需求维度分数 → 降低 logic_strength |
| 外部冲击打断周期 | 疫情、战争、自然灾害 | 标记周期暂停 → logic_strength 暂降 |

**4. 流动性 — 风险模板**:
| 风险因素 | 信号来源 | 触发后动作 |
|---|---|---|
| 流动性收紧 | 央行操作（MLF/SLF/逆回购）、利率上升 | 直接降低流动性分数 → 可能触发翻转 |
| 资金转向其他资产 | 资金流向数据、跨市场比较 | 降低资金流入预期 → 降低 logic_strength |
| 外资大幅流出 | 北向资金数据、汇率变动 | 降低外资维度分数 → 降低 logic_strength |
| 信用环境恶化 | 社融数据、信用利差、违约事件 | 降低信用扩张预期 → 降低 logic_strength |
| 汇率剧烈波动 | 汇率数据、外汇储备 | 标记外部流动性风险 → 降低 logic_strength |

**5. 事件驱动 — 风险模板**:
| 风险因素 | 信号来源 | 触发后动作 |
|---|---|---|
| 事件快速解决 | 和平协议、谈判成功、危机解除 | 直接降低事件强度 → 可能触发翻转（如美伊冲突缓和） |
| 影响被稀释 | 市场注意力转移、更大事件出现 | 降低事件关注度分数 → 降低 logic_strength |
| 被更大事件覆盖 | 新突发事件强度 > 当前事件 | 事件层降级 → 标记被覆盖 |
| 事件升级失控 | 冲突扩大、危机加深 | 更新事件强度 → 可能增强或减弱（取决于事件性质） |
| 事件证伪 | 最初信息被证明不准确 | 直接标记逻辑失效 → status = "dead" |

**6. 估值重构 — 风险模板**:
| 风险因素 | 信号来源 | 触发后动作 |
|---|---|---|
| 估值修复完成 | PE/PB 回到历史均值或分位数 | 降低重构空间 → 降低 logic_strength |
| 市场拒绝重估 | 资金不流入、估值继续压缩 | 直接触发翻转检测 |
| 基本面继续恶化拖累估值 | 财报数据、盈利预警 | 降低基本面支撑分数 → 降低 logic_strength |
| 估值锚点变化 | 无风险利率变化、风险溢价变化 | 重新计算合理估值区间 → 更新 logic_strength |
| 流动性收紧压制估值 | 利率数据、资金面数据 | 标记流动性风险 → 降低 logic_strength |

**7. 成本反转 — 风险模板**:
| 风险因素 | 信号来源 | 触发后动作 |
|---|---|---|
| 成本趋势反转 | 原材料价格数据、大宗商品价格 | 直接降低成本反转分数 → 可能触发翻转 |
| 成本下降被需求下降抵消 | 销量数据、利润数据 | 降低净效应预期 → 降低 logic_strength |
| 成本下降传导不畅 | 毛利率数据、定价权变化 | 降低传导效率分数 → 降低 logic_strength |
| 替代品成本更低 | 替代技术成本数据 | 降低成本优势预期 → 降低 logic_strength |
| 成本下降速度不及预期 | 产能利用率、成本曲线 | 降低时间性预期 → 降低 logic_strength |

**8. 技术革命 — 风险模板**:
| 风险因素 | 信号来源 | 触发后动作 |
|---|---|---|
| 技术路线失败 | 学术论文撤回、产品失败、测试未通过 | 直接降低技术可行性分数 → 可能触发翻转 |
| 商业化不及预期 | 产品销量、收入数据、用户增长 | 降低商业化进度分数 → 降低 logic_strength |
| 监管限制技术应用 | 政策文件、监管表态 | 标记监管风险 → 降低 logic_strength |
| 竞争者技术超越 | 竞品发布、专利对比 | 降低技术领先分数 → 降低 logic_strength |
| 技术被快速迭代 | 新版本发布、性能提升数据 | 降低技术壁垒分数 → 降低 logic_strength |

**9. 竞争格局变化 — 风险模板**:
| 风险因素 | 信号来源 | 触发后动作 |
|---|---|---|
| 新进入者颠覆格局 | 新玩家融资、产品发布、市场份额 | 降低格局确定性分数 → 降低 logic_strength |
| 龙头地位动摇 | 龙头财报、市场份额变化、管理层变动 | 降低龙头确认分数 → 降低 logic_strength |
| 反垄断/反不正当竞争 | 监管文件、处罚公告 | 标记政策风险 → 降低 logic_strength |
| 行业合并改变格局 | 合并公告、反垄断审查 | 重新评估格局 → 更新 logic_strength |
| 海外竞争者进入 | 外资进入公告、进口数据 | 降低国产优势分数 → 降低 logic_strength |

**10. 制度变革 — 风险模板**:
| 风险因素 | 信号来源 | 触发后动作 |
|---|---|---|
| 制度变革延迟 | 政策文件延期、试点推迟 | 降低制度变革确定性 → 降低 logic_strength |
| 制度执行偏离预期 | 实施细则与预期不符 | 降低制度有效性分数 → 降低 logic_strength |
| 市场适应不良 | 交易量变化、流动性数据 | 降低制度正面效应预期 → 降低 logic_strength |
| 制度被叫停或修改 | 监管公告、政策调整 | 直接触发翻转检测 |
| 国际规则变化影响 | WTO/国际组织文件 | 标记外部制度风险 → 降低 logic_strength |

#### 2.2.4 多层逻辑架构

```
宏观层（大逻辑）
  → 流动性环境、政策方向、经济周期
  → 持续时间: 数月至数年 | 影响范围: 全市场或多板块

行业层（中逻辑 / 主体层）
  → 产业趋势、供需格局、政策驱动
  → 持续时间: 数周至数月 | 影响范围: 特定板块

事件层（小逻辑）
  → 短期催化、突发事件、情绪波动
  → 持续时间: 数日至2周 | 影响范围: 个股或子板块

关系:
  大逻辑套中逻辑，中逻辑套小逻辑
  小逻辑可能成长为中逻辑，中逻辑可能升级为大逻辑
  大逻辑变化缓慢，小逻辑变化快
  当大逻辑和小逻辑冲突 → 短期小逻辑主导，中长期大逻辑回归
```

#### 2.2.5 排查清单（Issue Queue）

当风险自动扫描（2.2.6）触发风险因素后，系统自动将该逻辑加入排查清单。排查清单是用户可见的每日检查项汇总。

**触发条件**: 任一风险模板中的风险因素被信号源匹配并确认。

**清单条目格式**:
```
{板块名称} | {逻辑ID} | {风险因素} | {触发信号摘要} | {自动动作: logic_strength降X分} | {建议: 观察/减仓/离场}
```

**生命周期**:
- 新触发 → 加入清单，标记 `status = "active"`
- 连续 3 日未出现新风险信号 → 自动标记 `status = "monitoring"`
- 逻辑 logic_strength 恢复到触发前水平或逻辑进入 `dead` 状态 → 自动移出清单

**展示**: 在 Dashboard 中以列表形式展示，按风险严重程度（logic_strength 降幅 × 逻辑当前强度）排序。

#### 2.2.6 风险自动扫描机制

当系统识别到风险信号时，按以下机制自动处理：

1. **AI 自动扫描**: 每个交易日收盘后，系统自动对所有活跃逻辑扫描其对应的风险因素信号源
2. **信号匹配**: 将扫描结果与风险模板中的信号源比对，判断是否触发某个风险因素
3. **自动降级**: 触发风险因素后，自动降低对应评估维度的分数 → 重新计算 logic_strength
4. **排查清单**: 触发风险后自动加入排查清单（见 2.2.5），供用户查看
5. **翻转检测**: 如果 logic_strength 下降触发翻转阈值（dominant logic_strength < 0.3 或新逻辑 > dominant × 0.8），自动标记翻转信号

**示例**: 美伊战争逻辑 → 风险因素"事件快速解决" → AI 扫描到和平协议签署新闻 → 自动降低事件强度 → 触发排查 → 如强度降至阈值以下 → 标记翻转信号

#### 2.2.7 交易逻辑完整生命周期

每个交易逻辑（TradingLogic）经历完整的生命周期管理。生命周期采用**循环迭代模型**，允许逻辑在确认后继续追踪或新逻辑被发现：

```
                    ┌─────────────────────────────────────┐
                    │                                     │
                    ▼                                     │
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  发现逻辑    │─▶│  追踪强度    │─▶│  监控拐点    │─▶│  确认切换    │
│  Discovery   │  │  Tracking   │  │  Monitoring  │  │ Confirmation│
└─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘
       │                │                │                 │
       │                │                │                 │
       ▼                ▼                ▼                 ▼
  AI 综合多源数据    每日计算 logic_strength  检测关键信号       新逻辑确认（右侧）
  识别主导逻辑      主导/次要权重        政策转向/成本突破   或前兆确认（左侧）
                    更新 logic_strength_trend 量价异动/龙头信号   输出操作建议


循环路径:
  确认后同一逻辑持续 ────────────▶ 回到 追踪强度（同一逻辑继续）
  确认新逻辑出现 ────────────────▶ 回到 发现逻辑（新逻辑生命周期开始）
  监控发现信号但不足以确认 ──────▶ 回到 追踪强度（继续观察）
```

**每个阶段详细定义**:

##### 阶段 1: 发现逻辑（Discovery）

- **触发条件**: AI 扫描到新的信息模式（新闻/研报/政策/供应链数据中出现新的主导叙事）
- **输入**: 多源数据流（新闻、政策文件、研报、供应链信号、社交媒体情绪）
- **处理**:
  1. 按板块分组信息
  2. 识别每个板块内的叙事聚类
  3. 判断哪个叙事是当前主导逻辑
  4. 生成逻辑 ID、分类、描述、证据链
- **输出**: 新 `TradingLogic` 记录，`status = "emerging"`
- **质量门槛**: 至少一个高可信度证据源 + 一个中可信度源交叉验证

##### 阶段 2: 追踪强度（Tracking）

- **频率**: 每日收盘后
- **处理**:
  1. 更新该逻辑的所有评估维度分数（按逻辑类型的评估框架）
  2. 计算加权 logic_strength（0-1），计算公式：`logic_strength = weighted_average(dimension_scores) / 10.0`
  3. 计算 rolling 3 日 strength_trend（increasing/stable/declining）：
     - `increasing`: 连续 3 日 logic_strength 累计增加 > 0.05
     - `declining`: 连续 3 日 logic_strength 累计减少 > 0.05
     - `stable`: 3 日内累计变化 < 0.05
  4. 更新证据源权重（新证据加入、旧证据权重衰减）
  5. 执行风险自动扫描（见 2.2.6）
- **与 alphaear-signal-tracker 状态映射**:
  - Strengthened → strength_trend = increasing
  - Weakened → strength_trend = declining
  - Falsified → status = dead 或 fading
  - Unchanged → strength_trend = stable
- **状态变迁**:
  - `emerging` → `dominant`: logic_strength >= 0.5 且 logic_thesis_score >= 0.5
  - `dominant` → `secondary`: logic_strength 降至 0.3-0.5 或被新逻辑接近
  - `secondary` → `fading`: logic_strength < 0.3 且 declining
  - `fading` → `dead`: 逻辑证伪或被明确替代

##### 阶段 3: 监控拐点（Monitoring）

- **持续执行**: 与追踪强度并行
- **监控信号**:
  - **政策转向信号**: 政策文件变化、部委表态变化
  - **成本突破信号**: 关键原材料/产品成本突破阈值
  - **量价异动信号**: 板块成交量/价格异常波动
  - **龙头订单信号**: 中军/龙头公司订单、业绩、产能变化
  - **券商评级变动**: 集中上调或下调评级
  - **风险因素触发**: 风险模板中的风险信号被扫描到
- **拐点分类**:
  - **左侧信号**: 逻辑即将翻转的前兆（强度尚未变化但信号已出现）
  - **右侧信号**: 逻辑已经开始翻转（强度已变化、新逻辑 logic_strength 上升）
- **输出**: `signal_events` 列表更新，如为左侧信号标记 `mode = "left_side"`

##### 阶段 4: 确认切换（Confirmation）

- **触发条件**（满足任一）:
  - 当前 dominant logic_strength < 0.3（逻辑瓦解）
  - 新逻辑 logic_strength > dominant × 0.8（新逻辑接近超越）
  - 价格行为与当前主导逻辑方向连续 3 日背离
- **确认流程**:
  1. 收集翻转触发信号（2+ 条件满足）
  2. 生成 `LogicFlipEvent` 记录
  3. 计算翻转置信度
  4. 标记 `mode`（left_side = 信号确认中 / right_side = 趋势已确认）
  5. 输出操作建议（含 invalidation 条件）
- **输出**: `LogicFlipEvent` 记录，旧逻辑 `status` 更新，新逻辑 `status = "dominant"`

##### 阶段 5: 输出决策（Output）

- **板块K线标注**: 将逻辑区间以彩色条带标注在板块K线图上（见 2.2.9 K线可视化）
- **板块逻辑面评分** = 主导逻辑的 logic_strength × 0.6 + 次要逻辑加权 × 0.4
- **板块操作建议**: 方向（看多/看空/观望）+ 仓位（轻仓/半仓/重仓）+ 止损条件

#### 2.2.8 SectorLogic（板块整体评分）

一个板块可能有 N 个并发 TradingLogics。SectorLogic 是板块整体的评分，综合所有 TradingLogics：

```
sector_logic_strength = Σ(each_logic.logic_strength × weight_by_status)

其中权重:
  dominant 逻辑: weight = 0.6
  第一次要逻辑: weight = 0.25
  其余逻辑: weight = 0.15 平分
```

SectorLogic 输出：
- `sector_logic_strength`（0-1）：板块整体逻辑强度
- `sector_dominant_logic_id`：当前主导逻辑 ID
- `sector_logic_change_detected`（bool）：是否有新逻辑出现或翻转
- `sector_all_logics`：该板块所有活跃 TradingLogics 的列表

#### 2.2.9 K 线逻辑标注与回测可视化

##### 视图设计

系统提供**双视图切换**模式：

**简化视图**（默认，快速浏览）:
- 仅在逻辑翻转处加竖线标记 + 简短标签（如 "困境反转→政策补贴"）
- K线主体不受遮挡，适合快速查看逻辑与价格的对应关系
- 翻转标记颜色区分翻转类型（dominant_change=红色, dominant_collapse=橙色, new_emergence=绿色）

**详细视图**（深度分析）:
- K线上方彩色条带覆盖不同逻辑区间，条带上显示逻辑名称
- K线下方强度曲线（每日 logic_strength 值连线）
- 翻转处加标记图标（⚡ 闪电标记）
- 点击条带显示该逻辑的完整证据链
- 条带颜色对应逻辑类型（产业趋势=蓝色, 政策驱动=绿色, 供需周期=黄色, 流动性=紫色, 事件驱动=红色, 估值重构=青色, 成本反转=棕色, 技术革命=品红, 竞争格局变化=深绿, 制度变革=灰色）

##### K线回测模式 — 历史回放

- 选择一个日期范围作为回放区间
- 系统显示当时的逻辑标注，叠加在历史实际K线上
- 可拖动时间轴，观察逻辑如何在历史中演变
- 与实际股价对照验证（系统当时的判断 vs 实际发生了什么）
- 支持操作：
  - [◀ 上一天] / [下一天 ▶]: 逐日移动回放位置
  - [▶ 自动播放]: 按日自动播放逻辑演变过程
  - [跳转到翻转点]: 快速跳到最近的逻辑翻转位置
- 回测时显示：
  - 系统当时的逻辑判断（标注在K线上）
  - 系统当时给出的操作建议
  - 后续实际价格走势（从回放位置到今天的真实走势）
  - 事后验证：如果按系统建议操作，理论收益是多少

##### K线数据结构

```
K线逻辑标注数据:
{
  "sector": "CPO/光通信模块",
  "period_start": "2025-01-01",
  "period_end": "2026-04-14",
  "logic_intervals": [
    {
      "logic_id": "logic_2025_01_cpo_cost_benefit",
      "title": "成本>收益亏损逻辑",
      "category": "成本反转",
      "start_date": "2025-01-15",
      "end_date": "2025-04-10",
      "status": "dead",
      "max_strength": 0.72,
      "color": "#8B4513"  // 棕色 = 成本反转
    },
    {
      "logic_id": "logic_2025_04_pv_subsidy",
      "title": "政策补贴+困境反转逻辑",
      "category": "政策驱动",
      "start_date": "2025-04-12",
      "end_date": "2025-08-20",
      "status": "dead",
      "max_strength": 0.85,
      "color": "#228B22"  // 绿色 = 政策驱动
    }
  ],
  "flip_events": [
    {
      "date": "2025-04-12",
      "flip_type": "dominant_change",
      "from": "成本>收益亏损逻辑",
      "to": "政策补贴+困境反转逻辑",
      "marker": "⚡"
    }
  ]
}
```

### 2.3 个股层（Stock Layer）

#### 2.3.1 个股池

- **扫描范围**: 每日成交额 top200 + 用户自选个股
- **扫描频率**: 每个交易日收盘后一次
- **扫描池说明**: 仅对进入扫描池的个股进行后续评分，不做更大范围的全市场预先过滤
- **不做前置过滤**：进入扫描池的所有个股进入五维评分流程

#### 2.3.2 个股五维雷达图

每只股票有独立的五维雷达图评分：

| 维度 | 评分要素 | 计算方式 |
|---|---|---|
| **个股逻辑面** | 个股与所属板块逻辑的一致性 + 个股自身的催化事件 | 板块 logic_strength × 一致性系数(0-1) + 个股催化剂加分 |
| **个股基本面** | 财务指标 + 行业地位 + 成长性 + 估值 + 风险 + Buffett 定性补充 | PE/PB/ROE/营收增速/现金流 + 护城河类型/趋势 + 管理质量 |
| **个股技术面** | 个股趋势方向、量价配合、支撑/阻力位、动量强度 | 个股 K 线技术分析 |
| **个股资金面** | 个股主力资金流向、北向持仓变化、融资融券、大单流向 | 个股资金流向数据 |
| **个股情绪面** | FinBERT 个股情绪评分 + 个股新闻热度 + 投资者情绪指标 | FinBERT -1.0 ~ +1.0 映射到 0-10 + 搜索指数 |

**评分输出**：
- `stock_radar`：{logic: 0-10, fundamental: 0-10, technical: 0-10, capital_flow: 0-10, sentiment: 0-10}
- `stock_thesis_score`（0-1）：五维加权综合评分
- `stock_price_score`（0-1）：个股价格行为评分

**决策矩阵**：

| | stock_price_score 高 | stock_price_score 低 |
|---|---|---|
| **stock_thesis_score 高** | 推荐个股 | 观察个股（逻辑对但市场没跟） |
| **stock_thesis_score 低** | 跳过（市场在交易但逻辑不清） | 不参与 |

### 2.4 综合决策层（Composite Selection）

#### 2.4.1 三层分数如何组合

综合决策层独立于三层评分系统，负责将宏观/板块/个股三层分数组合为最终推荐：

```
推荐分数 = f(macro_thesis_score, sector_logic_strength, stock_thesis_score, sector_macro_adjustment)
```

**组合方式**:

1. **宏观开关**: 如果 `macro_thesis_score < 0.3`（宏观环境极度恶化），系统整体降低推荐强度，所有股票最多进入"观察名单"
2. **板块筛选**: 按 `sector_logic_strength` 排序，选出 top5 板块作为重点推荐板块；`sector_thesis_score` 仍作为板块内部健康度参考，但主导逻辑决定优先级。
3. **个股加权**: 个股推荐分数 = `stock_thesis_score × 0.5 + sector_logic_strength × 0.3 + sector_macro_adjustment × 0.2`
   - 其中 `sector_logic_strength` 表示板块逻辑本身力量，`sector_macro_adjustment` 表示当前宏观对该板块的额外加成或减持。
4. **分层展示**:
   - **重点关注**: 推荐分数 > 0.7 且五维雷达图无明显短板（最低维度 ≥ 5）
   - **观察名单**: 推荐分数 0.5-0.7 或存在单一维度短板
   - **其余**: 推荐分数 < 0.5，可展开查看

#### 2.4.2 操作建议生成

**格式**: 方向（看多/看空/观望）+ 仓位建议（轻仓/半仓/重仓）+ 止损条件（基于量价信号描述，不给具体价位）

**示例**:
- "看多，轻仓试探，若跌破前低或量能连续萎缩则离场"
- "观望，逻辑面模糊，不建议参与"
- "看多但需等待，技术面尚未确认，待放量突破后再入场"

**不做**: 不给具体入场价位、目标价、止损价。符合"跟随不预测"原则。

#### 2.4.3 推荐结果展示

分三层展示：
- **重点关注**: 推荐分数高、五维雷达图各维度都强的股票
- **观察名单**: 部分维度强但有短板的股票（如逻辑强但技术面未确认）
- **其余**: 可展开查看但不突出展示

---

## 三、A 股微结构约束

系统需要知晓以下约束，以便正确给出操作建议：

| 约束 | 影响 |
|---|---|
| T+1 | 买入后当日无法卖出，系统给出的操作建议必须考虑隔日风险 |
| 涨跌停 ±10% | 主板涨跌停限制，创业板/科创板 ±20% — 逻辑确认后可能出现连续涨停无法买入 |
| 集合竞价 | 9:15-9:25 集合竞价期间信号价值高，但不可执行 |
| 停牌 | 个股停牌期间无法交易，逻辑变更需要事后确认 |

---

## 四、数据模型

### 4.1 MacroContext（宏观环境记录）

```json
{
  "date": "2026-04-14",
  "macro_thesis_score": 0.72,
  "macro_state": "复苏",
  "cycle_position": {
    "growth_momentum": 0.6,
    "liquidity_momentum": 0.4,
    "quadrant": "复苏期"
  },
  "macro_radar": {
    "liquidity_environment": 7.5,
    "economic_cycle_position": 6.8,
    "inflation_and_cost": 5.2,
    "policy_direction": 7.0,
    "global_linkage": 6.5
  },
  "leading_signals": [
    {
      "indicator": "M1-M2 剪刀差",
      "current_value": -3.5,
      "trend": "收窄",
      "duration_months": 3,
      "prediction": "预示 2-3 月后流动性收紧",
      "confidence": 0.75
    },
    {
      "indicator": "PMI 新订单-库存差",
      "current_value": 3.2,
      "trend": "扩张",
      "duration_months": 2,
      "prediction": "经济处于主动补库存阶段，持续 3-4 月",
      "confidence": 0.68
    }
  ],
  "trend_analysis": {
    "liquidity_environment": {
      "trend": "declining",
      "momentum": -0.15,
      "inflection_point": "2026-02-15",
      "rolling_12m_data": [7.8, 7.9, 8.1, 7.9, 7.7, 7.5, 7.3, 7.2, 7.0, 6.8, 6.9, 7.5]
    },
    "economic_cycle_position": {
      "trend": "increasing",
      "momentum": 0.22,
      "inflection_point": "2025-12-20",
      "rolling_12m_data": [5.2, 5.3, 5.5, 5.8, 6.0, 6.2, 6.4, 6.5, 6.6, 6.7, 6.8, 6.8]
    }
  },
  "derived_indicators": {
    "m1_m2_scissors": {
      "current": -3.5,
      "prev_month": -2.8,
      "prev_quarter": -1.2,
      "trend": "收窄",
      "interpretation": "M1 增速低于 M2，企业活期存款减少，流动性收紧信号"
    },
    "ppi_cpi_scissors": {
      "current": 1.8,
      "prev_month": 2.1,
      "prev_quarter": 2.5,
      "trend": "收窄",
      "interpretation": "PPI-CPI 剪刀差收窄，上游成本压力向下游传导减弱，企业利润改善"
    },
    "shibor_term_structure": {
      "slope": 0.85,
      "prev_month": 0.92,
      "interpretation": "期限利差收窄，短期流动性偏紧预期"
    },
    "social_financing_growth": {
      "stock_yoy": 9.2,
      "prev_month": 9.5,
      "prev_quarter": 10.1,
      "trend": "放缓",
      "interpretation": "社融存量增速放缓，信用扩张动能减弱"
    }
  },
  "data_sources": {
    "china": {
      "m0": 93000.0,
      "m1": 575100.0,
      "m2": 2080900.0,
      "m1_yoy": 5.0,
      "m2_yoy": 10.1,
      "m1_m2_scissors": -5.1,
      "dr007": 1.85,
      "mlf_rate": 2.3,
      "shibor_overnight": 1.52,
      "shibor_3m": 2.04,
      "shibor_1y": 2.66,
      "social_financing_stock": 365.77,
      "social_financing_stock_yoy": 9.2,
      "pmi": 49.8,
      "pmi_new_orders": 51.2,
      "pmi_inventory": 48.0,
      "pmi_new_orders_inventory_diff": 3.2,
      "cpi_yoy": 0.3,
      "ppi_yoy": -2.1,
      "ppi_cpi_scissors": -2.4
    },
    "us": {
      "fed_funds_rate": 5.25,
      "treasury_10y": 4.35,
      "ism_pmi": 48.5,
      "nonfarm_payrolls": 175000,
      "unemployment_rate": 3.9
    },
    "global": {
      "polymarket": {
        "us_china_tariffs": 0.35,
        "fed_rate_cut_2026q2": 0.62
      },
      "geopolitical_risk": "normal",
      "tariff_risk": "elevated"
    }
  },
```

### 4.2 SectorMacroImpact（宏观→板块差异化影响）

```json
{
  "date": "2026-04-14",
  "macro_state_summary": "复苏期（增长动能 +0.6, 流动性动能 +0.4），但领先指标显示流动性拐点临近",
  "cycle_position": {
    "quadrant": "复苏期",
    "growth_momentum": 0.6,
    "liquidity_momentum": 0.4
  },
  "leading_signals_summary": "M1-M2 剪刀差连续 3 月收窄，预示 2-3 月后流动性收紧；PMI 新订单-库存差扩张，经济处于主动补库存阶段",
  "sector_impacts": [
    {
      "sector": "AI/算力",
      "LLM_interpretation": "复苏期+政策双驱动，AI 为政策重点扶持方向，但需警惕流动性拐点",
      "LLM_impact_score": 0.85,
      "indicator_breakdown": {
        "liquidity_environment": {
          "m1_m2_scissors": {"impact": 0.3, "sensitivity": 0.6, "contribution": 0.18},
          "social_financing_growth": {"impact": 0.2, "sensitivity": 0.7, "contribution": 0.14},
          "shibor_term_structure": {"impact": 0.1, "sensitivity": 0.4, "contribution": 0.04}
        },
        "economic_cycle_position": {
          "pmi_leading_index": {"impact": 0.5, "sensitivity": 0.5, "contribution": 0.25}
        },
        "inflation_and_cost": {
          "ppi_cpi_scissors": {"impact": -0.2, "sensitivity": -0.3, "contribution": 0.06}
        },
        "policy_direction": {"impact": 0.8, "sensitivity": 0.9, "contribution": 0.72},
        "global_linkage": {
          "ism_pmi": {"impact": 0.4, "sensitivity": 0.6, "contribution": 0.24},
          "tariff_risk": {"impact": -0.3, "sensitivity": -0.7, "contribution": 0.21}
        }
      },
      "sector_macro_adjustment": 0.18,
      "rank": 1,
      "risk_warning": "流动性拐点临近，建议 1 个月内关注 M1-M2 剪刀差变化，若继续收窄至 -4% 以下，逐步降低仓位"
    },
    {
      "sector": "新能源车",
      "LLM_interpretation": "补库存周期+政策支持，但成本压力仍存",
      "LLM_impact_score": 0.7,
      "indicator_breakdown": {
        "liquidity_environment": {
          "m1_m2_scissors": {"impact": 0.3, "sensitivity": 0.5, "contribution": 0.15}
        },
        "economic_cycle_position": {
          "pmi_leading_index": {"impact": 0.5, "sensitivity": 0.7, "contribution": 0.35},
          "pmi_inventory_cycle": {"impact": 0.6, "sensitivity": 0.8, "contribution": 0.48}
        },
        "inflation_and_cost": {
          "ppi_cpi_scissors": {"impact": -0.2, "sensitivity": -0.5, "contribution": 0.10}
        },
        "policy_direction": {"impact": 0.6, "sensitivity": 0.7, "contribution": 0.42}
      },
      "sector_macro_adjustment": 0.15,
      "rank": 2
    },
    {
      "sector": "黄金",
      "LLM_interpretation": "复苏期避险需求下降，但地��风险仍支撑",
      "LLM_impact_score": -0.3,
      "indicator_breakdown": {
        "liquidity_environment": {
          "m1_m2_scissors": {"impact": 0.3, "sensitivity": 0.9, "contribution": 0.27}
        },
        "economic_cycle_position": {
          "pmi_leading_index": {"impact": 0.5, "sensitivity": -0.5, "contribution": -0.25}
        },
        "inflation_and_cost": {
          "ppi_cpi_scissors": {"impact": -0.2, "sensitivity": 0.6, "contribution": -0.12}
        },
        "global_linkage": {
          "fed_funds_rate": {"impact": 0.2, "sensitivity": -0.8, "contribution": -0.16},
          "geopolitical_risk": {"impact": 0.3, "sensitivity": 0.9, "contribution": 0.27}
        }
      },
      "sector_macro_adjustment": -0.06,
      "rank": 12
    },
    {
      "sector": "银行",
      "LLM_interpretation": "复苏期信贷需求增加，但息差收窄预期",
      "LLM_impact_score": -0.2,
      "indicator_breakdown": {
        "liquidity_environment": {
          "m1_m2_scissors": {"impact": 0.3, "sensitivity": -0.4, "contribution": -0.12},
          "shibor_term_structure": {"impact": 0.1, "sensitivity": 0.5, "contribution": 0.05}
        },
        "economic_cycle_position": {
          "pmi_leading_index": {"impact": 0.5, "sensitivity": 0.7, "contribution": 0.35}
        },
        "policy_direction": {"impact": 0.4, "sensitivity": 0.6, "contribution": 0.24}
      },
      "sector_macro_adjustment": -0.04,
      "rank": 15
    }
  ]
}
```

### 4.3 TradingLogic（交易逻辑）

```json
{
  "sector": "CPO/光通信模块",
  "sector_code": "880792",
  "logic_id": "logic_2026_04_cpo_ai_demand",
  "title": "AI算力基础设施需求爆发",
  "description": "海外云厂商资本开支持续高增长，国内算力规划落地，CPO作为光通信核心环节直接受益于算力需求扩张",
  "category": "产业趋势",
  "identified_date": "2026-03-15",

  "logic_thesis_score": 0.85,
  "logic_price_score": 0.72,

  "logic_strength": 0.72,
  "logic_strength_framework": {
    "logic_type": "产业趋势",
    "dimensions": [
      {"name": "需求验证", "score": 8, "data_source": "云厂商资本开支"},
      {"name": "供给验证", "score": 7, "data_source": "产能扩张计划"},
      {"name": "竞争格局", "score": 9, "data_source": "市占率变化"}
    ]
  },
  "logic_strength_trend": "increasing",

  "evidence_sources": [
    {"source": "news_article_123", "weight": 0.3, "summary": "三大云厂商Q1资本开支同比+40%", "credibility": "high"},
    {"source": "research_report_456", "weight": 0.4, "summary": "券商深度报告：AI算力链景气度分析", "credibility": "high"},
    {"source": "supply_chain_signal", "weight": 0.3, "summary": "中际旭创订单排满至Q3", "credibility": "medium"}
  ],
  "status": "dominant"
}
```

### 4.4 SectorLogic（板块整体评分）

```json
{
  "sector": "CPO/光通信模块",
  "sector_code": "880792",
  "date": "2026-04-14",
  "sector_logic_strength": 0.68,
  "sector_dominant_logic_id": "logic_2026_04_cpo_ai_demand",
  "sector_logic_change_detected": false,
  "sector_all_logics": [
    {"logic_id": "logic_2026_04_cpo_ai_demand", "logic_strength": 0.72, "status": "dominant", "weight": 0.6},
    {"logic_id": "logic_2026_04_cpo_competition", "logic_strength": 0.55, "status": "secondary", "weight": 0.25},
    {"logic_id": "logic_2026_03_cpo_valuation", "logic_strength": 0.42, "status": "fading", "weight": 0.15}
  ],
  "sector_radar": {
    "logic": 8.2,
    "fundamental": 7.5,
    "technical": 7.0,
    "capital_flow": 6.8,
    "sentiment": 7.2
  },
  "sector_thesis_score": 0.74,
  "sector_price_score": 0.68,
  "sector_macro_adjustment": 0.15,
  "issue_queue": []
}
```

### 4.5 SectorLogicTimeline（板块逻辑时间线）

```json
{
  "sector": "CPO/光通信模块",
  "sector_code": "880792",
  "date": "2026-04-14",
  "active_logics": [
    {"logic_id": "logic_2026_04_cpo_ai_demand", "logic_strength": 0.72, "status": "dominant"},
    {"logic_id": "logic_2026_04_cpo_competition", "logic_strength": 0.55, "status": "secondary"},
    {"logic_id": "logic_2026_03_cpo_valuation", "logic_strength": 0.42, "status": "fading"}
  ],
  "dominant_logic": "logic_2026_04_cpo_ai_demand",
  "logic_change_detected": false,
  "macro_context": "流动性宽松，政策偏暖，经济周期弱复苏",
  "signal_events": []
}
```

### 4.6 StockRadar（个股五维雷达图）

```json
{
  "stock_code": "300502",
  "stock_name": "新易盛",
  "date": "2026-04-14",
  "stock_thesis_score": 0.82,
  "stock_price_score": 0.75,
  "stock_radar": {
    "logic": 8.5,
    "fundamental": 7.8,
    "technical": 7.2,
    "capital_flow": 8.0,
    "sentiment": 7.6
  },
  "operation_suggestion": {
    "direction": "看多",
    "position": "轻仓",
    "stop_condition": "若跌破前低或量能连续萎缩则离场"
  },
  "tier": "重点关注",
  "sector_ref": "CPO/光通信模块",
  "sector_logic_strength_ref": 0.68,
  "stock_recommend_score": 0.78
}
```

### 4.7 LogicFlipEvent（逻辑翻转事件）

```json
{
  "sector": "光伏",
  "flip_type": "dominant_change",
  "old_dominant": "成本>收益亏损逻辑",
  "new_dominant": "政策补贴+困境反转逻辑",
  "confidence": 0.78,
  "mode": "right_side",
  "trigger_signals": [
    "政府发布2026年光伏补贴细则",
    "行业龙头成本跌破关键心理价位后快速回升",
    "券商集体上调评级"
  ],
  "detected_at": "2026-04-12",
  "action_hint": {
    "mode": "right_side",
    "certainty": "medium",
    "suggestion": "新逻辑已确认但仍需观察2-3日。中等仓位试探，跌破支撑位止损。",
    "invalidation": "若板块跌回支撑位以下，反转逻辑被证伪，应立即退出"
  },
  "validation": {
    "backtest_result": "若该次翻转被正确捕捉，理论上可获+15%收益",
    "actual_result": "flip后5日实际涨幅+12.3%"
  }
}
```

### 4.8 数据质量处理

- **矛盾数据**（同一板块两份报告说相反逻辑）: 标记 `logic_thesis_score = MIN(logic_thesis_score, 0.4)`，等待第三源确认
- **证据源权威性分层**: 官方文件/券商报告 > 主流财经媒体 > 自媒体/论坛 > 匿名/无来源
- **单一低可信度源**不足以建立 dominant logic（需至少一个高可信度源 + 一个中可信度源交叉验证）
- **AI 合成失败**（LLM 返回空/乱码/无法提取）: 降级为 `status = "unknown"`，dashboard 显示 "当前板块逻辑不明确 — 不建议基于该板块盲目交易"

---

## 五、中军定义与识别

### 5.1 定义

**中军 = 行业龙头**，由研报/研究确认（不是简单市值排名）。

### 5.2 识别方式

- **Phase 1**: 手动标记
- **Phase 2**: AI 通过研报分析识别

### 5.3 中军切换

行业龙头可能发生变化（技术路线变化、竞争格局变化）。中军变更由**择时系统**追踪和触发，本系统仅使用当前中军信息。

- **接口契约**: 本系统需要一个明确的输入字段，如 `current_sector_leaders` 或 `sector_leader_stock`，用于标记当前中军个股与行业龙头。
- **降级策略**: 若择时系统暂不可用，本系统仍可基于板块内市值/研报标签做弱化版本的辅助判断，但不将其作为核心逻辑面评分。

### 5.4 多板块映射

个股属于多个板块的复杂性由**择时系统**处理。本系统取所属**最强板块**的逻辑得分作为逻辑面评分。

---

## 六、基本面分析

### 6.1 数据输入

三管齐下：

- **结构化数据**: 通过 API（如 Tushare/AKShare）拉取 PE/PB/ROE/营收增速/现金流等量化指标
- **AI 读研报**: AI 读卖方研报原文，提取定性判断（行业地位、竞争格局、技术壁垒、成长预期等）
- **Buffett 定性补充**: 基于 Buffett skill 的护城河框架（五类护城河：无形资产/成本优势/转换成本/网络效应/有效规模）和管理质量评估，对个股进行定性判断。该补充不直接改变数值化的 `stock_thesis_score` 计算公式，但可作为强否决信号和定性标签，用于风险提示和重点关注过滤。具体作用：
  1. 快速否决：如果护城河持续收窄或管理诚信存疑，该个股应从“重点关注”中剔除或降级到“观察名单”。
  2. 定性标签：在个股详情页展示护城河类型、护城河趋势（widening/stable/narrowing）、管理质量评级。
  3. 透明提示：当定性判断与量化评分出现冲突时，界面/报告需明确说明“量化评分高，但定性护城河或管理质量存在风险”。

两者结合形成基本面雷达图维度的评分。

### 6.2 数据源选型（待验证）

| 数据类型 | 候选数据源 | 状态 |
|---|---|---|
| 行情数据（成交额/价格/量） | 东方财富/AKShare/Tushare | 已有（data_provider） |
| 财报数据（PE/PB/ROE/现金流） | Tushare/AKShare | 待验证 |
| 研报数据 | 萝卜投研/慧博/Tushare 研报接口 | 待验证 |
| 新闻舆情 | Tavily/SerpAPI | 已有 |
| 政策文件 | gov.cn/部委 RSS | 待验证 |
| 资金流向 | 东方财富/Tushare | 待验证 |
| 情绪数据 | 雪球/淘股吧 | 待验证 |

### 6.3 中文数据源采集风险

gov.cn、东方财富、同花顺、雪球等网站反爬严重。需评估：
- 是否有现成的付费数据 API（Tushare Pro、AKShare、JQData 等）
- 反爬绕过方案（代理、无头浏览器、官方 API）
- 数据更新频率是否满足每日扫描需求

---

## 七、系统架构

### 7.1 总体架构

```
                          ┌─────────────────────────────────┐
                          │   Sector Logic Engine (SLE)     │
                          │         (standalone core)       │
                          ├─────────────────────────────────┤
                          │                                 │
┌─────────────────┐      │   ┌─────────┐    ┌───────────┐  │
│ Multi-Source    │─────▶│   │ Logic   │───▶│ Logic     │  │
│ Collectors      │      │   │ Registry│    │ Tracker   │  │
│                 │      │   │(truth   │    │(strength  │  │
│ • News crawler  │      │   │ source) │    │ over time)│  │
│ • Report parser │      │   └────┬────┘    └─────┬─────┘  │
│ • Policy monitor│      │        │               │         │
│ • Supply chain  │      │        ▼               ▼         │
│ • Social sentiment│    │   ┌────────────────────────┐    │
│ • DSA data_provider│  │   │   Synthesis Engine     │    │
└─────────────────┘      │   │ (LLM-powered analysis) │    │
                          │   │                       │    │
                          │   │ Input: multi-source    │    │
                          │   │ Output: logic JSON     │    │
                          └───┴───┬───┬───┬─────────┬──┘
                                  │   │   │         │
                    ┌─────────────┘   │   │         │
                    ▼                 ▼   ▼         ▼
              ┌────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
              │ Dashboard  │ │ Deep     │ │ Alert    │ │ DSA      │
              │ (K-line +  │ │ Report   │ │ System   │ │ Analysis │
              │ Logic      │ │ Generator│ │ (flip    │ │ Pipeline │
              │ overlay)   │ │          │ │ events)  │ │ consumer │
              └────────────┘ └──────────┘ └──────────┘ └──────────┘
                                  │
                                  ▼
                          ┌──────────────────┐
                          │ Stock Selection  │
                          │ Pipeline         │
                          ├──────────────────┤
                          │ • top200 scanner │
                          │ • Radar scoring  │
                          │ • Operation rec  │
                          │ • Tier display   │
                          └──────────────────┘
```

### 7.2 模块架构

| Module | Path | Responsibility | Standalone? |
|---|---|---|---|
| `sector_logic/` | New standalone package | Core logic registry, timeline tracking | Yes |
| `sector_logic/collectors/` | New | Multi-source data collection | Yes |
| `sector_logic/analysis/` | New | LLM-powered synthesis and logic extraction | Yes |
| `sector_logic/models/` | New | Logic data models + schemas | Yes |
| `src/stock_selection/` | New | Top200 scanner, radar scoring, recommendations | Yes |
| `apps/dsa-web/src/views/logic-tracker/` | New in DSA web | Dashboard: K-line + logic overlay + radar | Consumer |
| `apps/dsa-web/src/components/radar-chart/` | New in DSA web | Radar chart component | Consumer |
| `api/logic/` | New API endpoints | Logic query, timeline, alerts | Consumer |
| `api/selection/` | New API endpoints | Stock recommendations, radar data | Consumer |
| `data_provider/` | Existing DSA | Reuse for price/volume data | Contributor |

### 7.3 漏斗筛选架构

```
全市场 A 股
    │
    ▼
[漏斗层 1: 成交额过滤]
    → 成交额 top200 + 用户自选
    │
    ▼
[漏斗层 2: 五维评分]
    → 每只股票计算五维雷达图
    │
    ▼
[漏斗层 3: 决策矩阵]
    → Thesis × Price 四象限分类
    │
    ▼
[漏斗层 4: 分层展示]
    → 重点关注 / 观察名单 / 其余
```

---

## 八、LLM 合成引擎

### 8.1 验证与回退机制

1. **Schema validation**: 每个 LLM 输出用 Pydantic 模型验证。解析失败 → 重试一次 → 仍失败 → `status = "unknown"`
2. **Evidence check**: LLM 声明逻辑但零证据源 → `logic_thesis_score = 0.2` → `status = "unknown"`
3. **Cross-run consistency**: 两天用不同 prompt 运行两次。结果一致 → `model_consistency_score` += 0.1；不一致 → `model_consistency_score` -= 0.2。该字段用于衡量 AI 结论稳定性，并映射到最终 `confidence`。不应直接改变 `logic_strength`。
4. **Price validation**: LLM 识别主导逻辑后，检查板块价格趋势是否一致。连续 >2 天方向矛盾 → `price_validation_flag` 触发，降低最终 `confidence`；这属于验证/一致性信号，不直接修改 `logic_strength`。
5. **Manual override**: 用户可覆盖任何 AI 生成的逻辑（`source = "human_override"`, credibility = 用户定义）
6. **Fallback chain**: LLM 成功 → 结构化 JSON。LLM 失败 → 重试一次 → 仍失败 → `status = "unknown"`，dashboard 显示"当前板块逻辑不明确"

### 8.2 Prompt 策略

**Stage 1 — 逻辑提取**:
给定板块 X 在 [T-7, T] 日期范围内的所有文章/报告/数据：
1. 当前主导交易逻辑是什么？
2. 什么证据支持（按可信度排序）？
3. 次要逻辑有哪些？
4. 是否有新兴或衰退信号？

**Stage 2 — 逻辑强度计算**:
给定板块 X 的 N 个逻辑：
1. 根据证据量、来源可信度、价格行为确认计算相对强度
2. 输出：逻辑 ID → 强度分数 (0-1)，趋势方向

### 8.3 Strength 动态框架生成 Prompt

对每个逻辑类型，系统需自动生成评估维度。Prompt 核心逻辑：
1. 识别该逻辑类型的因果链条
2. 确定链条上的关键验证节点
3. 映射每个节点到可获取的数据源
4. 生成评分模板

---

## 九、Phase 实施计划

### Phase 1 — Logic Registry + 手动输入（MVP, ~1-2 周）

- 定义核心数据模型（`TradingLogic`, `SectorTimeline`, `LogicFlipEvent`, `StockRadar`）
- 构建简单注册系统（SQLite 或 JSON 文件）
- 手动逻辑输入 UI（用户输入："光伏当前主导逻辑=困境反转, logic_strength=0.8"）
- K 线时间线叠加，用彩色条带显示逻辑区间
- Dashboard MVP：2-3 个板块的当前逻辑 + 强度（用户已回测的板块）
- **目标**: 验证数据模型和 UI，证明"这能让我交易得更好吗？"使用手动数据

### Phase 2 — AI 合成引擎（右侧交易, ~2-4 周）

- **多源采集器（Phase 2a）**:
  - 最小可行集：1) DSA 现有新闻搜索（Tavily/SerpAPI），2) 政策 RSS（gov.cn、部委网站），3) 财经新闻 API（东方财富/同花顺 RSS）
  - Phase 2b 后期：社交情绪（雪球/淘股吧）、供应链数据
- **LLM 合成引擎**:
  - 输入：板块 X 在 [T-7, T] 范围内的所有文章/报告/数据
  - Stage 1 — 逻辑提取
  - Stage 2 — 动态框架生成 + 强度计算
  - 必须输出符合 `TradingLogic` schema 的结构化 JSON
  - 回退：连续 2 次 LLM 合成失败 → "unknown regime" 标志 + 最近已知有效逻辑
- **翻转检测**: dominant logic_strength < 0.3 或新逻辑 logic_strength > dominant × 0.8
- 支持**右侧交易**：趋势已建立，AI 比共识更快识别逻辑

### Phase 2.5 — 宏观层增强（本次优化重点, ~30-60 分钟）

**优先级**: P0（与 Phase 2 并行或紧随其后）

**范围**: 完整五维度宏观框架 + 衍生指标 + 趋势分析

**具体任务**:
1. **数据采集扩展** (~15 分钟):
   - MacroCollector 添加 M1 数据采集（Tushare cn_m API）
   - 添加社融存量同比计算（已有 sf_month API）
   - 添加 PMI 详细子指标采集（cn_pmi API，50+ 字段）
   - 添加 Hibor 数据采集（hibor API，跨境流动性指标）
   - 添加 CPI/PPI 详细分项（cn_cpi/cn_ppi API）

2. **衍生指标计算** (~10 分钟):
   - M1-M2 剪刀差 = M1_yoy - M2_yoy
   - PPI-CPI 剪刀差 = PPI_yoy - CPI_yoy
   - Shibor 期限结构斜率 = (Shibor_1y - Shibor_overnight) / 365
   - 社融存量增速 = (当月社融存量 - 去年同期) / 去年同期
   - PMI 领先指数 = PMI_new_orders - PMI_inventory
   - Shibor-Hibor 利差 = Shibor_overnight - Hibor_overnight

3. **时间序列分析引擎** (~15 分钟):
   - 12 个月滚动窗口数据存储
   - 趋势判断：连续 3 月同向变化 > 阈值 → increasing/declining
   - 拐点检测：趋势方向改变 + 变化幅度 > 阈值
   - 动量计算：(当前值 - 3月前值) / 3月前值

4. **经济周期四象限分类** (~10 分钟):
   - 增长动能 = f(PMI 领先指数, 社融增速, 工业增加值)
   - 流动性动能 = f(M1-M2 剪刀差, Shibor 期限结构, DR007)
   - 四象限映射：
     - 复苏期：增长↑ + 流动性↑
     - 过热期：增长↑ + 流动性↓
     - 滞胀期：增长↓ + 流动性↓
     - 衰退期：增长↓ + 流动性↑（反常规，需警惕）

5. **Skill 文件更新** (~10 分钟):
   - `macro/evaluation-framework.json` → 5 维度
   - `macro/derived-indicators-config.json` → 新建
   - `macro/trend-analysis-config.json` → 新建
   - `macro/sector-sensitivity-config.json` → 指标级别细化

**验证标准**:
- MacroCollector 能成功采集所有新增数据源
- 衍生指标计算结果与手工计算一致（误差 < 0.1%）
- 12 月滚动窗口能正确识别历史拐点（回测 2023-2025 数据）
- 四象限分类与实际经济周期吻合度 > 80%

**交付物**:
- 更新后的 `macro_collector.py`（+200 行）
- 新增 `macro_analyzer.py`（衍生指标 + 趋势分析，~150 行）
- 更新后的 4 个 skill 文件
- 单元测试覆盖所有衍生指标计算（~50 行）
- **翻转检测**: dominant logic_strength < 0.3 或新逻辑 logic_strength > dominant × 0.8
- 支持**右侧交易**：趋势已建立，AI 比共识更快识别逻辑

### Phase 3 — 选股管线 + 左侧信号 + 完整 UI（~3-4 周）

- **top200 扫描引擎**: 收盘后自动获取成交额排名，进入评分流程
- **五维雷达图评分**: 每只股票完整评分
- **操作建议引擎**: 方向 + 仓位 + 止损条件生成
- **分层展示 UI**: 重点关注 / 观察名单 / 其余
- **雷达图可视化**: 前端图表组件（优先 recharts，如复杂则切 echarts）
- **响应式 Dashboard**: 移动端友好
- **左侧信号检测**:
  - 每个逻辑类别的预定义触发器目录：政策转向信号、成本突破信号、量价异动信号、龙头订单信号、券商评级变动
  - 触发器触发 → 增加新兴逻辑强度 → 在主导变化前提醒用户
- **回测框架**: 回测历史翻转 vs 价格行动，校准阈值
- **告警系统**: 翻转时推送通知，附带操作提示和失效条件
- **深度研究报告生成**: 每周板块总结

### Phase 4 — DSA 集成 + 优化（~1-2 周）

- DSA 分析管线消费逻辑数据 — 将逻辑上下文注入个股分析
- "该股当前服从板块 XX 的 YY 逻辑"注入到股票报告
- 机器人/通知包含逻辑翻转告警及每日分析
- 板块到个股逻辑偏离检测："板块逻辑向上，但个股价格向下 — 是否基本面出问题？"

---

## 十、板块分类体系

| 级别 | 示例 |
|---|---|
| 一级行业 | 光伏, CPO/光通信, 半导体, 新能源车, 医药, 消费, ... |
| 二级概念 | AI 算力, 储能, 氢能, 固态电池, 创新药, ... |
| 三级个股 | 具体个股从属于二级概念从属于一级行业 |

每个板块可以有 N 个并发逻辑，但只有 1-2 个主导。

---

## 十一、LLM 调用成本估算

系统涉及大量 LLM 调用：

| 环节 | 频率估算 | 模型建议 | Phase 2.5 增量 |
|---|---|---|---|
| 宏观环境判断（每周 1 次） | ~1 次/周 | 大模型（GPT-4/Claude 级别） | +0（频率不变） |
| **宏观衍生指标计算** | ~1 次/周 | **无需 LLM**（纯数学计算） | **+0 LLM 调用** |
| **宏观趋势分析** | ~1 次/周 | **无需 LLM**（时间序列算法） | **+0 LLM 调用** |
| **宏观四象限分类** | ~1 次/周 | **无需 LLM**（规则引擎） | **+0 LLM 调用** |
| 宏观→板块差异化映射（LLM 解读） | ~1 次/天 | 大模型 | +0（频率不变，但输入更丰富） |
| 板块逻辑追踪（~20 板块 × 每日 1 次） | ~20 次/天 | 大模型（GPT-4/Claude 级别） | +0 |
| 动态评估框架生成（按逻辑类型缓存） | ~10 次/天 | 大模型 | +0 |
| 个股基本面分析（200 只 × 每日 1 次） | ~200 次/天 | 中小模型（可批量/缓存） | +0 |
| 逻辑匹配与推荐生成 | ~200 次/天 | 中小模型 | +0 |
| 排查清单触发 | 不确定 | 大模型（按需） | +0 |

**Phase 2.5 成本影响分析**:
- **LLM 调用次数**: 无增加（衍生指标、趋势分析、四象限分类均为纯计算，不需要 LLM）
- **计算成本**: 增加约 5-10 秒/周（12 个月滚动窗口计算 + 衍生指标）
- **存储成本**: 增加约 50KB/周（12 个月历史数据 × 20 个指标）
- **LLM 输入 token**: 宏观→板块映射环节增加约 500-800 tokens（更丰富的宏观上下文），但输出 token 不变

**优化后估计**: 考虑宏观每周更新（非每日）、框架缓存（按逻辑类型而非按板块）、批量处理后约 230-250 次 LLM 调用/天，其中大模型约 30-35 次/天。**Phase 2.5 不增加 LLM 调用次数**。

**成本控制策略（已细化）**:
- 宏观环境判断每周一次，而非每日
- **衍生指标与趋势分析使用纯数学计算，不调用 LLM**（关键优化点）
- 评估框架按逻辑类型缓存，同类型板块共享模板（见 2.2.2）
- 个股基本面分析可批量处理而非逐只
- 中小模型可用于情绪评分、基础数据提取等不需要深度推理的环节
- **12 个月滚动窗口数据缓存在 DataStore，避免重复计算**

---

## 十二、A 股量化机构参考

### High-Flyer（幻方量化）演进路径

- 2016: 传统多因子价量模型
- 2017: 深度学习全面替代手工因子
- 2019+: Ensemble 架构，多模型集成
- 创始人梁文锋: "2017年后很难发现真正创新的因子"

### 风控共识

- 单笔风险 1-2% 账户资金
- 组合总风险 4-8%
- Pyramiding（加仓确认的趋势），不 averaging down（摊薄亏损仓位）
- 论证失效 → 移入观察名单，不死扛

### Confidence 独立评分的行业依据

- Robeco 2025: 独立策略 IR=0.61/0.54，组合后 IR=0.88
- Vantage Protocol: 五门独立子系统全部通过才下单
- QuantInsti: F-Score/G-Score 独立于价格计算

### 波段选股漏斗架构参考

- SSRN Paper (Verma, Gupta & Gupta): "Selection of Market Sector Trend and Sub-Selection of Stocks for Swing Trades"
- 标准流程: 板块筛选 → 基本面筛选 → 技术确认 → 多因子复合评分 → 仓位管理

---

## 十三、成功标准

1. 能在趋势确认后 48 小时内识别 5+ 个板块的主导交易逻辑
2. 逻辑强度追踪器正确标记 ≥60% 的主要逻辑翻转（用 2025-2026 数据回测）
3. 用户能看到 K 线 + 逻辑叠加图后立刻回答"这段行情在交易什么？"
4. 系统通过标记"unknown regime"每月至少阻止一次"盲做"
5. 同时支持左侧（前兆捕捉）和右侧（趋势确认）模式
6. 每日 top200 扫描在收盘后 2 小时内完成
7. 推荐列表覆盖至少 3-5 只重点关注股票
8. **【Phase 2.5 新增】宏观领先指标能提前 1-2 个月预警流动性拐点**（回测验证：M1-M2 剪刀差领先股市 3-6 月的准确率 ≥ 70%）
9. **【Phase 2.5 新增】经济周期四象限分类与实际周期吻合度 ≥ 80%**（对照统计局/央行事后定性）
10. **【Phase 2.5 新增】板块宏观敏感度调整能解释 ≥ 50% 的板块轮动现象**（回测 2023-2025 板块表现）

---

## 十四、风险与缓解

| 风险 | 可能性 | 影响 | 缓解措施 |
|---|---|---|---|
| LLM 幻觉（编造合理逻辑） | 高 | 高 | 每个逻辑必须引用具体证据源。Schema 验证。价格对齐检查。 |
| 翻转信号过于自信 | 中 | 高 | 带明确方法论的 confidence 评分。翻转需满足 2+ 条件。左侧信号标记为"信号确认中"而非"逻辑已切换"。 |
| 数据管线脆弱 | 高 | 中 | 每个采集器独立容错。单个采集器失败不停止合成。Dashboard 显示数据源健康状态。 |
| 黑天鹅事件 | 低 | 高 | confidence < 0.3 时系统标记"unknown regime"。"看不懂不盲做"护栏强制执行。 |
| **【Phase 2.5 新增】衍生指标计算错误** | 中 | 高 | 单元测试覆盖所有衍生指标。与手工计算对照验证。误差阈值 < 0.1%。 |
| **【Phase 2.5 新增】领先指标失效（市场结构变化）** | 中 | 中 | 每季度回测领先指标有效性。若准确率 < 60% 持续 2 季度，触发人工审查。 |
| **【Phase 2.5 新增】12 月滚动窗口数据缺失** | 低 | 中 | 数据缺失时使用可用最长窗口（最短 6 月）。标记数据质量降级。 |
| Strength 系统性偏差 | 中 | 高 | 前 2 周人工校准。若 LLM 与用户评估差异持续 > 0.15，标记"强度校准不充分"，降低 confidence。 |
| 中文数据采集不稳定 | 高 | 高 | 多数据源 fallback 机制。单一数据源失败不影响整体流程。评估付费 API 替代方案。 |
| LLM 调用成本过高 | 中 | 中 | 大小模型分级使用。缓存可复用分析结果。个股批量处理。 |

---

## 十五、待决事项（需在实现阶段细化）

### 15.1 技术验证项

| # | 事项 | 负责人 | 优先级 |
|---|---|---|---|
| T1 | 中文数据采集可行性 PoC（东方财富/雪球/gov.cn） | 待定 | P0 |
| T2 | 财报数据获取渠道确认（Tushare/AKShare/Wind） | 待定 | P0 |
| T3 | 研报数据获取渠道确认（萝卜投研/慧博/Tushare） | 待定 | P0 |
| T4 | LLM 调用成本精确估算（按模型分级） | 待定 | P1 |
| T5 | 200 只 × 每日分析的计算成本评估 | 待定 | P1 |

### 15.2 设计细化项

| # | 事项 | 状态 |
|---|---|---|
| D1 | 各逻辑类型的评估维度模板（AI 自动生成的起点规则） | 待实现 |
| D2 | 事件层（小逻辑）升级为行业层的具体条件 | 待实现 |
| D3 | 阈值校准方案（基于回测：dominant/分歧/翻转触发/strength_trend） | 待实现 |
| D4 | 雷达图各维度的具体子指标和评分规则 | 待实现 |
| D5 | 操作建议的 LLM prompt 模板（方向/仓位/止损条件的格式约束） | 待实现 |
| D6 | 推荐结果的 UI/UX 设计（列表 vs 报告 vs 精选粒度） | 待实现 |
| D7 | 中军识别的操作标准（市占率/营收/技术领先/品牌认知？） | 待实现 |
| D8 | ~~宏观 context 的注入格式和更新频率~~ | 已定（见 2.1.1，每周更新，SectorMacroImpact 数据模型见 4.2） |

### 15.3 校准阈值列表

以下阈值初始值为拍脑袋估计，需通过回测校准：

| 阈值 | 初始值 | 用途 |
|---|---|---|
| dominant 阈值 | logic_thesis_score >= 0.5 | 标记主导逻辑 |
| 分歧阈值 | gap < 0.15 | 双逻辑接近时的分歧标志（指 logic_thesis_score 差值 < 0.15） |
| 翻转触发 1 | dominant logic_strength < 0.3 | 主导逻辑瓦解 |
| 翻转触发 2 | new logic logic_strength > dominant × 0.8 | 新逻辑接近超越 |
| logic_strength_trend | rolling 3 日 | 强度趋势计算窗口（±0.05 判定 increasing/declining） |
| confidence 映射值 | 推荐=0.9, 观察=0.5, 跳过=0.3, 不参与=0.1 | 决策矩阵离散映射值（见 2.4.1） |

---

## 十六、NOT in scope（明确不在本系统范围内）

- **择时系统**: 基于个股在不同板块角色（龙头/中军/跟风）的具体买卖时机判断 — 由另一个系统处理
- **日内交易**: T+0/T+1 盘中实时信号和交易
- **具体价位预测**: 入场价、目标价、止损价
- **港股/美股**: 当前仅 A 股，跨市场扩展已 defer
- **盘中实时扫描**: 收盘后每日一次，不需要盘中
- **Kronos 预测注入操作建议**: Kronos (alphaear-predictor) 的预测作为独立参考视图展示，不影响系统生成的操作建议（方向/仓位/止损条件）。符合"跟随不预测"原则。

---

## 十七、与现有 DSA 基础设施的复用关系

| DSA 现有模块 | 本系统复用方式 | Phase 2.5 增强 |
|---|---|---|
| `data_provider/efinance_fetcher.py` (Priority 0) | 行情数据（成交额/价格/量） | 无变化 |
| `data_provider/akshare_fetcher.py` (Priority 1) | 备选行情数据 | 无变化 |
| `data_provider/tushare_fetcher.py` (Priority 2) | 财报/研报数据（待评估） | **新增宏观数据采集**（cn_m/sf_month/cn_pmi/cn_cpi/cn_ppi/shibor/hibor） |
| `src/core/pipeline.py` | 分析管线编排模式 | 无变化 |
| `src/agent/` | LLM 调用框架 | 无变化 |
| `src/notification/` | 告警通知推送 | **新增宏观拐点预警** |
| `src/repositories/` | 数据存储模式 | **新增 12 月滚动窗口存储** |
| `src/schemas/` | 数据校验模式 | **新增 MacroContext/DerivedIndicators schema** |
| `api/` | FastAPI 路由模式 |
| `apps/dsa-web/` | 前端框架、组件复用 |

### 17.1 与 AlphaEar Skill 生态的复用关系

| AlphaEar Skill | 本系统复用方式 |
|---|---|
| `alphaear-stock` | 股票搜索（模糊匹配）、历史价格获取（OHLCV）、基本面数据（PE/市值） |
| `alphaear-news` | 新闻采集（cls/weibo/华尔街见闻）、统一趋势报告、Polymarket 预测市场数据 |
| `alphaear-search` | 多引擎搜索（Jina/DDG/Baidu）、本地 RAG 搜索（daily_news 数据库）、搜索缓存 |
| `alphaear-sentiment` | FinBERT 情绪评分（-1.0 ~ +1.0）、LLM 情绪分析 |
| `alphaear-signal-tracker` | 信号生命周期追踪（Strengthened/Weakened/Falsified 映射到本系统状态机） |
| `alphaear-reporter` | 信号聚类、分段报告生成、图表配置生成（Phase 3 深度报告生成复用） |
| `alphaear-logic-visualizer` | Draw.io XML 生成（用于逻辑链可视化，独立于 K 线可视化） |
| `alphaear-predictor` | Kronos 预测作为独立参考视图，不注入操作建议（见 16 节 NOT in scope） |
| `alphaear-deepear-lite` | DeepEar Lite 信号作为额外数据源输入 |
| `buffett` | 基本面定性补充（护城河类型/趋势、管理质量、快速否决） |

---

## 十八、版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.0 | 2026-04-16 | 初始版本 — 整合三份设计文档 + office-hours 补充，以 consolidation 文档为准裁决冲突 |
| 1.1 | 2026-04-16 | 新增 10 类逻辑类型及风险模板；新增风险自动扫描机制；完善交易逻辑完整生命周期（5阶段+循环）；新增 K 线逻辑标注与回测可视化（双视图+历史回放）；补充 K 线逻辑标注数据结构 |
| 1.2 | 2026-04-16 | 修复 2.2.4 排查清单缺失；新增动态评估框架缓存策略（按逻辑类型缓存，~10次/天）；修正 2.3 板块前置过滤逻辑（板块决定入选范围）；新增 Buffett 定性补充到基本面分析；修正 confidence 术语定义（离散映射值）；新增情绪面 FinBERT 评分映射；新增 alphaear-signal-tracker 状态映射；新增 Kronos 边界声明（独立参考视图，不注入建议）；更新 LLM 调用成本估算（250-300次/天）；新增 17.1 AlphaEar Skill 生态复用关系表 |
| 1.3 | 2026-04-16 | 第四章数据模型全面重构：新增 4.1 MacroContext 数据模型；新增 4.2 SectorMacroImpact 数据模型；新增 4.4 SectorLogic 数据模型；原 4.1-4.5 重编号为 4.3-4.8；所有字段使用前缀命名（logic_thesis_score, logic_price_score, logic_strength, logic_strength_trend, sector_thesis_score, sector_price_score, sector_logic_strength, stock_thesis_score, stock_price_score, stock_radar, stock_recommend_score）；数据质量处理中 thesis_score 引用更新为 logic_thesis_score；LLM 验证机制中 thesis_score 引用更新为 logic_thesis_score；第十一章 LLM 成本估算更新（宏观每周更新非每日、大模型~30-35次/天、总调用~230-250次/天） |
| 1.4 | 2026-04-17 | **宏观层全面增强（Phase 2.5）**：2.1.1 宏观环境判断从 3 维度扩展到 5 维度（流动性环境/经济周期位置/通胀与成本/政策方向/全球联动），新增领先指标（M1-M2 剪刀差、PMI 领先指数）、衍生指标（PPI-CPI 剪刀差、Shibor 期限结构、社融增速）、时间序列分析（12 月滚动窗口、拐点检测、趋势动量）、经济周期四象限分类（复苏/过热/滞胀/衰退）；2.1.2 板块敏感度配置细化到指标级别，新增指标级别加权计算示例；4.1 MacroContext 数据模型扩展（新增 cycle_position、leading_signals、trend_analysis、derived_indicators）；4.2 SectorMacroImpact 数据模型扩展（新增 indicator_breakdown、risk_warning）；九章新增 Phase 2.5 实施计划（30-60 分钟，5 个子任务）；十一章 LLM 成本估算新增 Phase 2.5 影响分析（无 LLM 调用增加，衍生指标为纯计算）；十三章成功标准新增 3 条宏观层验证标准；十四章风险与缓解新增 3 条 Phase 2.5 相关风险；十七章 DSA 复用关系新增 Phase 2.5 增强列 |
