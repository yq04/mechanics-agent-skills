# Mechanics Agent Skills 任务交接文档 (HANDOFF.md)

> 本文档面向完全没有上下文的新会话/接手 Agent，详尽记录本项目的任务目标、全部已交付成果、当前状态与遗留事项、下一步实施建议，以及极为惨痛的实战踩坑与硬性行为纪律。

---

## 一、 我们在做什么任务 (Task & Project Scope)

### 1.1 项目定位与核心目标
- **项目仓库**：https://github.com/yq04/mechanics-agent-skills
- **工作区根目录**：`D:\1_Research\AI_Workspace\mechanics-agent-skills`
- **核心使命**：将原本零散、简陋的学术检索脚本，升级打造为一个**生产级、证据驱动、完全开源（MIT 友好）且零外部硬性运行依赖**的力学学术全生命周期 Agent 技能生态（**Mechanics Agent Skills Suite**）。
- **专业领域**：固体力学（Solid Mechanics）、断裂力学（Fracture Mechanics）、线/非线性弹性力学（Elasticity）以及应用数学（Applied Mathematics）。
- **通用性原则（重要边界）**：该技能库**面向全学科与广大力学研究者通用**，绝对不可污染进用户个人子项目的专属数值求解代码（例如 `LBM_Fabrikant` 的特定网格算子）；但必须吸收其严密的力学证据规范、符号定义以及学术严谨性契约。

### 1.2 借鉴的顶级网络开源项目与协议红线
在架构设计中深入调研并解构了三大开源标杆项目，并制定了严密的协议防火墙：
1. **`academic-research-skills` (ARS v3.22.0)**：
   - *借鉴思想*：三层引文定位与虚假引用审计、科学完整性门禁（Scientific Integrity Gates G1~G7）、学者声音校准与去 AI 浮夸词。
   - *协议红线*：ARS 采用 **CC BY-NC 4.0** 协议！为保持本项目纯正宽松的 **MIT 商业友好许可**，**严禁直接复制、vendor 其任何源码或文本**。本项目所有诚信门禁与校准逻辑均进行完全独立的力学化原生实现（Clean-room Implementation）。
2. **`nature-skills` (19 个技能体系)**：
   - *借鉴思想*：出版级科学绘图契约（Nature 单双栏 85/175 mm 物理尺寸、Okabe-Ito 色弱友好配色、数据墨水比契约、渲染清单 Manifest）与论文多维路由润色。
   - *协议兼容*：Apache-2.0 协议，吸收其设计思想并具象化为力学专属图件（应力云图、无量纲 SIF 曲线等）。
3. **`AutoResearchClaw` (ARC, UNC)**：
   - *借鉴思想*：自主科研状态机流转（Idea -> 检索 -> 证据 -> 绘图 -> 润色 -> 审稿）与模拟审稿人反思反馈环（Reviewer Agent 驱动的 Revision Ledger）。
   - *协议兼容*：MIT 协议，状态流转与有界审稿台账机制已融入统一工作流编排。

### 1.3 本地科研项目的经验沉淀与注入
吸收了用户本地三大项目（`Develop_Research`、`LBM_Fabrikant`、`Mechanics`）的实战精髓：
- **符号纪律与物理护栏**：严格区分单侧位移 $w$ 与裂纹总开度 $\mathrm{COD} = 2w$、应力强度因子小 $k_I$ 与大 $K_I = \sqrt{\pi} k_I$、工程剪应变 $\gamma$ 与张量剪应变 $\varepsilon_{12}$；严禁 AI 擅自“纠错”。
- **证据分级与真实页码**：文献必须具备真实 DOI、PDF SHA-256 与真实页码/公式行号；无全文时必须诚实标记为摘要来源（`pdf_page: unknown`），严禁编造锚点。
- **基准独立性**：严格区分数值求解器的自一致性验证与真正独立的外部解析基准。

---

## 二、 已经完成了什么 (Completed Work)

经过两轮系统化建设（Phase 1~5 第一轮核心库与检索抽取，Phase 6~9 第二轮绘图、润色、模拟审稿与端到端编排），已全部落地为坚固的工程实现：

### 2.1 核心底层架构 (`src/mechanics_skills/`, v3.1.0)
- **零外部硬依赖**：基于 Python 标配库（`urllib`, `sqlite3`, `dataclasses`, `json`, `re` 等）实现全套能力，不强制要求安装第三方包；对 `httpx`（异步加速）、`pymupdf`（PDF 深度抽取）、`matplotlib`/`numpy`（出版绘图）提供自动降级与懒加载支持。
- **多数据源检索与适配器 (`providers/`)**：
  - `crossref.py`：严格遵守 mailto/User-Agent 礼貌池协议，自动指数退避重试。
  - `openalex.py`：遵守 OpenAlex 官方最新规范（`per_page<=100`，突破 100 自动游标分页，礼貌池 10 req/s）。
  - `arxiv.py`：修复历史版本的 HTTP/406 Accept 头部缺陷，改用强制 HTTPS + XML Atom 流解析。
  - `semantic_scholar.py` 与 `unpaywall.py`：实现合规的 OA 全文与开放访问链接探测。
- **力学 5D 筛选器 (`screening.py`)**：
  - 基于本构模型(C)、缺陷几何(G)、势函数表述(P)、输出物理量(O)、分析方法(M)五维力学特征的启发式评分。
- **引文滚雪球与主路径分析 (`citations.py`)**：
  - 支持正向/反向引用图 BFS 遍历与关键脉络拓扑主路径（Main Path Analysis）自动提取。
- **页码级证据抽取引擎 (`extraction.py`)**：
  - 抽取本构刚度/柔度张量（$C_{ijkl}, S_{ijkl}$）、能量释放率与应力强度因子（$J, G, K$）、复变势（Muskhelishvili, Stroh）与基准对比表；严格区分 `abstract` 与 `pdf_page` 真实锚点。
- **出版级力学绘图引擎 (`figure.py`)**：
  - 内置 5 种经典力学模板：应力云图 (`stress_contour`)、SIF 响应曲线 (`sif_curve`)、相互作用热图 (`interaction_heatmap`)、渐近解与全场对比 (`asymptotic_comparison`)、裂纹几何拓扑图 (`crack_geometry`)。
  - 严格锁定单栏 85 mm、双栏 175 mm 出版物理尺寸，采用 Okabe-Ito 色弱友好色盘，自动输出三格式（PDF/PNG/SVG）与数据/渲染清单（`figure.manifest.json`）。
- **学术润色与力学符号护栏 (`polishing.py`)**：
  - LaTeX 行内/行间公式、物理量单位、张量角标的不可动保护区。
  - 力学混淆护栏与 AI 机械套话清洗（彻底剥离 `delve`, `pivotal`, `testament`, `foster` 等）。
  - 章节专属性格校准（Introduction, Methods, Results, Discussion）。
- **模拟同行评审与五维健全性门禁 (`reviewer.py` & `integrity.py`)**：
  - 模拟 *JMPS*、*IJSS*、*EFM*、*Acta Mechanica Sinica* 顶级期刊审稿人的严苛审查。
  - 实现贯穿全链路的 **7 大科学诚信门禁 (G1~G7)**：
    * **G1**：数值与符号一致性（$\sqrt{\pi}$ 因子、单位量纲）
    * **G2**：引用与出处忠实度（防虚假引用、防摘要冒充全文）
    * **G3**：数据出处可溯性（图表必须绑定原始数据哈希）
    * **G4**：基准独立性（自洽测试与外部独立基准隔离）
    * **G5**：伪物理现象防范（网格畸变/奇异截断误差防假冒新机理）
    * **G6**：方法声明一致性（平面应变与平面应力、退化各向同性一致性核查）
    * **G7**：理论假设范围锁定（远场等效假设在近场极值下的边界锁定）
  - 输出结构化修订台账（`Revision Ledger`）。
- **轻量端到端工作流编排 (`workflow.py`)**：
  - 串联全生命周期：`search -> screen -> citations -> oa -> extract -> figure -> polish -> peer-review -> integrity -> handoff`。
  - 基于阶段哈希实现断点续跑（Resumable），产出完整的 `workflow.manifest.json`。

### 2.2 六大独立 Agent Skills（已规范化构建）
符合 Agent Skills 官方标准，每个目录均包含简明直观的 `SKILL.md`（含标准 frontmatter，<500 行）、`references/` 深度指南以及 `scripts/` 启动脚本：
1. **`mechanics-scoping-review`**：系统性文献检索、5D 初筛、引文主路径与 PRISMA 综述生成。
2. **`openalex-database`**：全球 2.5 亿学术图谱实体查询、通用引用与学者统计助手。
3. **`mechanics-evidence-extraction`**：力学本构、断裂参数、势表述的真实页码级提取与证据矩阵构建。
4. **`mechanics-figure`**：固体力学出版级绘图引擎（85/175mm、Okabe-Ito 色盘、清单契约）。
5. **`mechanics-paper-polishing`**：力学论文语言润色、公式完整性锁定、术语护栏与 AI 套话清洗。
6. **`mechanics-paper-reviewer`**：模拟顶刊审稿人意见、五维科学健全性审核与有界反思修订。

### 2.3 分发构建与全局同步
- 构建工具 `tools/build_skill_bundles.py`：自动将核心包打包为自包含的 `_vendor/mechanics_skills` 注入到各技能中。
- 独立分发物已成功产出在 `dist/skills/`（包含 6 个独立技能目录与 6 个 `.zip` 离线压缩包）。
- **已成功全量同步到宿主全局技能库**：`C:\Users\Administrator\.agents\skills\`。

### 2.4 测试套件与质量验证
- **测试覆盖率**：18 个测试文件、101 个测试用例，覆盖检索、缓存、ID 解析、提取、绘图、润色、评审、门禁、打包与工作流。
- **测试结果**：`pytest -q` 耗时约 6 秒，**101 passed, 0 failed, 100% 绿色全通**。

---

## 三、 当前卡在哪 / 遗留事项 (Current Status & Leftovers)

当前核心能力、CLI、测试套件、六大技能包与文档均已完成闭环：

1. **核心代码与六大技能已提交本地 Git**：
   - commit `8df1a5b`: `feat: implement v3.1.0 core mechanics skills suite with 6 skills and 7 integrity gates`
2. **README.md 与架构文档已补齐**：
   - README.md 已全面扩充为六技能体系、十项 CLI 命令、七大科学诚信门禁及出版级绘图契约。
   - `docs/architecture.md`（微内核 + 6 技能 + 7 门禁拓扑架构）、`docs/provider-policy.md`（各大学术 API 频率限制与调用规范）、`docs/distribution.md`（vendor 打包与全局同步）已全部完成。
3. **远端推送**：
   - 本地所有改动均已提交，等待用户最终确认后执行 `git push origin master`。

---

## 四、 下一步计划是什么 (Next Step Plan)

### 阶段 1：完善文档与外观呈现（已完成）
- [x] **更新 `README.md`**：101/101 tests 徽章、6 技能矩阵、10 项 CLI 速查表、7 门禁与工作流架构图、文档索引。
- [x] **补齐 `docs/` 核心设计文档**：
  - [x] `docs/architecture.md`
  - [x] `docs/provider-policy.md`
  - [x] `docs/distribution.md`

### 阶段 2：Git 清理与原子化提交（已完成）
- [x] 清理临时文件，配置 `.gitignore`（过滤 `artifacts/`, `dist/`, `build/`, `.pytest_cache/` 等）。
- [x] 完成核心功能提交：`feat: implement v3.1.0 core mechanics skills suite with 6 skills and 7 integrity gates`。
- [x] 完成文档与交接提交：`docs: update README, system architecture, provider policies, and distribution guide`。

### 阶段 3：远端同步与用户交付（当前阶段）
- [ ] 在得到用户明确指示后，执行 `git push origin master` 推送到 GitHub 远端仓库。
- [ ] 向用户总结完整交付报告。

---

## 五、 有哪些踩过的坑绝对不要再踩 (Hard Pitfalls & Lessons Learned)

> **⚠️ 以下 8 条为血泪换来的硬性闸门与教训，新会话绝对不可违背！**

### 1. 致命号池限制：严禁在 `functions__exec` 脚本中调用 `notify()` 或 `yield_control()`
- **事故机理**：本开发环境通过 CLIProxyAPI (CPA) 代理池驱动 Gemini 模型。底层协议严格要求每一次 `functionCall` 只能配对一次同 ID 的 `functionResponse`。如果在 JS 脚本执行中途调用 `notify(...)`，会向响应队列额外塞入一个中间包，导致下一次工具调用的 ID 配对发生队列错位，直接抛出无法恢复的 HTTP 400：`antigravity executor: invalid Gemini function call history: functionResponse.id does not match functionCall.id`。
- **后果**：该错误会被立刻写入 SQLite 数据库与 session jsonl，**导致整个会话永久报废，再也无法发起任何工具调用**！
- **铁律**：所有工具执行结果必须在 JS 脚本结束时通过**唯一次 `text(...)`** 输出，绝对不要在脚本内调用 `notify()`，也不要调用 `yield_control()`！

### 2. 算力与额度纪律：绝对不要滥用 `gpt-6-astra`
- **背景**：本机同时接入了 ChatGPT Plus (Astra) 与 Gemini 号池。Astra 额度极其宝贵且有严格周期限额。
- **铁律**：日常代码修改、写测试、运行命令、读写文档、普通子代理隔离等操作，**必须严格默认使用父会话模型或 `gemini-3.8-flash`**！只有当用户显式输入 `/astra-plan` 或明确要求“请让 Astra 进行深度架构规划/重大论证”时，才允许单次派发 `gpt-6-astra`，并且必须设置 `fork_turns: "3"` 或 `"none"`（严禁 fork `all`，否则上下文直接爆炸）。规划一旦写入 `task_plan.md`，Astra 必须立刻退出，后续具体实施全部交由 Gemini。

### 3. 多智能体协作纪律：长思考等待超时与 Turn 活跃维持
- **铁律**：调用 `wait_agent` 等待深度推理子代理时，超时时间 `timeout_ms` 推荐设置为 `180000` 到 `300000`（3~5 分钟），切忌使用 30s 等短超时进行轮询。
- **严禁无工具调用交还控制权**：当子代理还在后台运行且 `wait_agent` 发生超时唤醒时，如果主智能体仅回复纯文本而不发起下一次 `wait_agent` 调用，客户端会将当前 Turn 判定为结束（task_complete），导致前端过早把控制权扔给用户并频繁弹窗“› 继续！”。子代理未结束前，必须保持在循环中持续调用 `wait_agent`。

### 4. 测试命令与环境路径配置
- **踩坑**：在 Windows PowerShell 下直接敲 `pytest` 时，如果当前目录 `.` 没有在 `pythonpath` 中，由于 `tests/test_distribution.py` 引用了 `tools/build_skill_bundles.py`，会报 `ModuleNotFoundError: No module named 'tools'`。
- **已修复与防范**：已经在 `pyproject.toml` 中将 `.` 加入了 `pythonpath = [".", "src", ...]`。但为了最大程度的稳健性，在命令行建议优先使用 `python -m pytest -q`，它会自动将当前执行目录置入 `sys.path`。

### 5. 验证与审查节约准则 (Stop on Green)
- **踩坑**：模型容易陷入过度验证综合征——针对微小的局部改动，反复发散探索虚构的边缘场景，编写几十个无意义的测试用例，空耗数万 Token。
- **铁律**：遵循“按比例检验（Proportional Testing）”与“通过即止（Stop on Green）”。针对性测试 Exit 0 绿灯后立即收手，禁止无休止的自我重复验证。

### 6. 严守开源协议纯洁性：严禁混入 ARS 代码
- **背景**：参考的 `academic-research-skills` 是 **CC BY-NC 4.0** 协议，不可用于纯商业或宽松开源。
- **铁律**：严禁直接复制代码或文本！所有门禁（G1~G7）、审稿标准必须立足固体力学实际，独立自主编写。确保本项目始终保持纯正清白的 **MIT** 许可证，方便全世界研究者自由商用与二次开发。

### 7. 力学领域的数学物理符号护栏（严防 AI 瞎改公式）
- **学术重坑**：一般学术润色工具往往认为力学公式有“笔误”而自作聪明地修改：
  * 把单侧位移 $w$ 强制改成开度 $\mathrm{COD}$，或者把 $\mathrm{COD}$ 误当成单侧位移导致开度翻倍；
  * 把断裂力学中的应力强度因子小 $k_I$ 与大 $K_I$ 搞混（两者的定义差了 $\sqrt{\pi}$ 因子）；
  * 把工程剪应变 $\gamma_{xy}$ 与张量剪应变 $\varepsilon_{xy}$ 搞混（差了 2 倍）。
- **铁律**：润色工具必须严格保护 LaTeX 区域与符号映射表，遇有歧义时标记为 `unknown` 或生成修改建议，绝对不可在未经人工确认下自动篡改公式。

### 8. 严谨的学术证据定位（拒绝虚假页码）
- **踩坑**：历史早期代码中，如果某文献只查到了摘要没有全文 PDF，脚本顺手给填了 `pdf_page: 1`，造成了事实上的“伪造证据锚点”。
- **铁律**：在 `extraction.py` 与 `models.py` 中，必须严格区分 `abstract` 与 `pdf_page`。未读取真实 PDF 的证据，其页码必须忠实标记为 `unknown`，严禁伪造。

---

## 六、 常用命令与快速验证速查

新会话若需快速核验当前项目健康度，可直接运行以下命令：

```powershell
# 1. 运行完整测试集 (101 项测试全部通过)
python -m pytest -q

# 2. 检查统一 CLI 帮助信息
python -m mechanics_skills.cli --help

# 3. 运行端到端离线工作流验证
python -m mechanics_skills.cli workflow run --brief "crack interaction in elasticity" --output-dir artifacts/workflow-test

# 4. 重新打包 6 大技能包
python tools/build_skill_bundles.py --out dist/skills

# 5. 同步至全局技能库
python tools/build_skill_bundles.py --sync-global
```
