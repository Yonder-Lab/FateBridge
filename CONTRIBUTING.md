# 贡献指南

感谢您有兴趣为 FateBridge 做出贡献！本指南将帮助您了解如何参与项目开发。

## 目录

- [行为准则](#行为准则)
- [如何开始](#如何开始)
- [贡献方式](#贡献方式)
- [Pull Request 流程](#pull-request-流程)
- [编码规范](#编码规范)
- [提交信息规范](#提交信息规范)

---

## 行为准则

我们的社区致力于为所有人创建一个友好、有趣和包容的环境。

### 我们的承诺

我们作为贡献者和维护者承诺：

- 使用欢迎和包容的语言
- 尊重不同的观点和经验
- 接受建设性批评
- 关注对社区最好的事情
- 对其他社区成员表示同情

### 不可接受的行为

不可接受的行为包括：

- 使用带有性别、性取向、种族、宗教或残疾相关内容的语言或形象
- 人身攻击
- 骚扰或欺凌
- 发布他人私人信息而未获得明确许可
- 其他可能被认为不适当的行为

---

## 如何开始

### 第一步：Fork 仓库

```bash
# 访问 https://github.com/Yonder-Lab/FateBridge
# 点击右上角的 "Fork" 按钮
```

### 第二步：克隆您的 Fork

```bash
git clone https://github.com/YOUR_USERNAME/FateBridge.git
cd FateBridge
```

### 第三步：添加上游仓库

```bash
git remote add upstream https://github.com/Yonder-Lab/FateBridge.git
git fetch upstream
```

### 第四步：创建新分支

```bash
git checkout -b feature/your-feature-name
```

### 第五步：搭建开发环境

跑测试和格式化需要装上 dev 依赖。推荐用 [uv](https://docs.astral.sh/uv/)：

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

或者用 pip：

```bash
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

`[dev]` 里带了 pytest、black、isort、mypy，跟 CI 的四道门禁是对齐的。

### 第六步：进行更改

编辑文件，进行测试，确保您的更改正常工作。

### 第七步：提交更改

```bash
git add .
git commit -m "feat: Add your feature description"
```

### 第八步：推送到您的 Fork

```bash
git push origin feature/your-feature-name
```

### 第九步：创建 Pull Request

访问原始仓库，您应该会看到一个"创建 Pull Request"的按钮。

---

## 贡献方式

### 🐛 报告 Bug

如果您发现了 Bug：

1. **检查已有 Issues**：查看是否已有人报告过此问题
2. **提供详细信息**：
   - 清晰的描述
   - 重现步骤
   - 预期行为
   - 实际行为
   - 系统信息（OS、Python 版本等）
   - 错误消息或日志

3. **创建 Issue**：在 GitHub 上创建新的 Issue

示例：

```markdown
## Bug 报告

### 描述
当输入无效的出生日期（如 2 月 30 日）时，API 返回 500 错误而非 400 错误。

### 重现步骤
1. 向 `/api/calculate` 发送 POST 请求
2. 使用 birth_year=2000, birth_month=2, birth_day=30
3. 观察返回的错误

### 预期行为
应该返回 400 错误，提示"无效的出生日期"

### 实际行为
返回 500 Internal Server Error

### 环境
- OS: macOS 13.1
- Python: 3.10
- FateBridge: 0.1.0
```

---

### 💡 提议新功能

如果您有功能建议：

1. **创建 Issue** 标记为 `enhancement`
2. **描述用例**：说明新功能如何有用
3. **提供示例**：如果可能，给出使用示例
4. **讨论实现**：说明您的实现思路

示例：

```markdown
## 功能请求

### 描述
添加一个新的 API 端点，用于批量分析多个人的命理信息。

### 用例
用户想要同时分析一组人（如家族成员）的命理，而不是一个一个分析。

### 建议的 API
```
POST /api/batch-calculate
{
  "people": [
    { "name": "张三", "birth_year": 1990, ... },
    { "name": "李四", "birth_year": 1992, ... }
  ]
}
```

### 实现思路
- 创建新的端点处理
- 复用现有的 `calculate_destiny_analysis` 服务编排
- 返回结果数组
- 添加错误处理
```

---

### 📝 改进文档

文档改进对项目非常重要！

1. **找出不清晰的部分**：阅读文档，记下不理解的地方
2. **检查过期信息**：查找不再准确的内容
3. **改进示例**：改进或添加代码示例
4. **修复错别字**：纠正拼写错误

提交文档更改的 PR 时，请：

- 清晰地描述更改内容
- 说明为什么需要这个更改
- 提供在修改前后的对比

---

### 🔧 代码贡献

代码贡献应遵循以下步骤：

1. **选择问题**：在 Issues 中找到您感兴趣的问题
2. **评论表示您要处理**：让维护者知道您正在处理此问题
3. **遵循编码规范**：详见下面的"编码规范"部分
4. **编写测试**：为您的更改编写或更新测试
5. **更新文档**：更新相关的文档
6. **提交 PR**：按照 Pull Request 流程提交

---

## Pull Request 流程

### 提交前的检查清单

- [ ] 代码遵循项目编码规范
- [ ] 已运行测试：`pytest tests/`
- [ ] 代码已格式化：`black` 和 `isort`
- [ ] 类型检查通过：`mypy fatebridge/`
- [ ] 添加了新功能的测试
- [ ] 更新了相关文档
- [ ] 提交信息清晰和有描述性
- [ ] 没有合并冲突

### PR 描述模板

```markdown
## 描述
简要描述您的更改。

## 类型
- [ ] Bug 修复
- [ ] 新功能
- [ ] 文档改进
- [ ] 代码重构
- [ ] 测试

## 相关 Issue
修复 #（Issue 编号）

## 更改内容
- 更改 1
- 更改 2
- 更改 3

## 测试
描述您如何测试了这些更改。

## 截图（如适用）
如果有 UI 更改，请添加截图。

## 检查清单
- [ ] 本地测试通过
- [ ] 添加了测试覆盖
- [ ] 更新了文档
- [ ] 没有破坏性更改
```

---

## 编码规范

### Python 代码风格

遵循 [PEP 8](https://peps.python.org/pep-0008/)：

```python
# ✅ 好的代码
def analyze_compatibility(person1: PersonInfo, person2: PersonInfo) -> Dict:
    """分析两人的八字配合度。

    Args:
        person1: 第一人的个人信息
        person2: 第二人的个人信息

    Returns:
        包含配合度分析的字典
    """
    analysis1 = calculate_single_analysis(person1)
    analysis2 = calculate_single_analysis(person2)

    return calculate_compatibility(analysis1, analysis2)

# ❌ 避免
def analyze(p1, p2):
    a1 = calc(p1)
    a2 = calc(p2)
    return compat(a1, a2)
```

### Python 项目结构

```python
# fatebridge/core/example.py

"""Module docstring describing the module's purpose."""

from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class ExampleClass:
    """Class docstring."""

    def __init__(self):
        """Initialize the class."""
        pass

    def method(self, param: str) -> Dict:
        """Method docstring.

        Args:
            param: Parameter description

        Returns:
            Return value description

        Raises:
            ValueError: When validation fails
        """
        if not param:
            raise ValueError("param cannot be empty")

        return {}
```

### 注释和文档

```python
# ✅ 好的注释
# 基于日期差计算干支循环
# 1984-03-31 是甲子日，从此基准点开始计算
days_diff = (target_date - BASE_DAY_PILLAR_DATE).days
stem_index = (BASE_STEM + days_diff) % 10

# ❌ 坏的注释
# 计算差
days_diff = (target_date - BASE_DAY_PILLAR_DATE).days
# 模 10
stem_index = (BASE_STEM + days_diff) % 10
```

---

## 提交信息规范

遵循 [Conventional Commits](https://www.conventionalcommits.org/)：

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 类型

- `feat`: 新功能
- `fix`: 缺陷修复
- `docs`: 文档改进
- `style`: 代码风格（格式化等）
- `refactor`: 代码重构
- `perf`: 性能改进
- `test`: 测试相关
- `chore`: 构建、依赖等

### 示例

```bash
git commit -m "feat(api): Add batch analysis endpoint

- Create new /api/batch-calculate endpoint
- Support analyzing multiple people simultaneously
- Include error handling for invalid requests

Closes #42"
```

### 更多示例

```bash
# 新功能
git commit -m "feat(calendar): Add lunar calendar conversion

- Implement gregorian to lunar conversion
- Add validation for lunar dates"

# Bug 修复
git commit -m "fix(validation): Properly validate birth dates

- Check for invalid dates like Feb 30
- Return 400 instead of 500 for bad input"

# 文档改进
git commit -m "docs: Add API usage examples

- Add Python examples for all endpoints
- Add JavaScript examples
- Update error handling section"

# 代码重构
git commit -m "refactor(core): Extract calculation logic

- Move common calculation functions to helpers
- Reduce code duplication
- Improve maintainability"
```

---

## 审查过程

### 审查标准

我们在审查 PR 时检查：

- ✅ 代码质量和风格
- ✅ 测试覆盖率
- ✅ 文档更新
- ✅ 与现有代码的一致性
- ✅ 性能影响
- ✅ 安全问题

### 反馈和修改

如果审查者请求更改：

1. 进行请求的更改
2. 在本地测试
3. 推送更新
4. 再次请求审查

```bash
# 进行更改后
git add .
git commit -m "Address review comments"
git push origin feature/your-feature-name
```

---

## 常见问题

### Q: 如何保持我的 Fork 与上游同步？

```bash
git fetch upstream
git checkout main
git merge upstream/main
git push origin main
```

### Q: 我应该针对哪个分支创建 PR？

通常针对 `master` 分支。

### Q: 如何在本地运行测试？

```bash
pytest tests/ -v
```

### Q: 审查需要多长时间？

通常在 1-3 天内。对于复杂的更改可能需要更长时间。

---

## 获取帮助

- 📖 阅读 [DEVELOPMENT.md](docs/DEVELOPMENT.md)
- 🐛 查看已有的 Issues
- 💬 在 GitHub Discussions 中提问
- 📧 联系维护者

---

## 致谢

感谢所有为 FateBridge 做出贡献的人！

每一个贡献，无论大小，都帮助使这个项目变得更好。

---

祝开发愉快！🚀
