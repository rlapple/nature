# Nature Research Articles 月度抓取与导出

## 功能简介
- 抓取 Nature（`/nature/research-articles`）列表页的论文条目
- 支持：
  - 默认抓取**当前月**
  - 或通过参数指定月份（`YYYY-MM`）
- 对每篇论文：
  - 抽取 Abstract + 正文首段（按当前实现）
  - 调用 LLM：学科分类、标题翻译、中文导读生成
- 按学科分组导出 Markdown：`nature_{YYYY-MM}.md`

## 部署环境
- Python：建议 3.10+（代码使用了 `str | None` 类型注解）
- 依赖安装（项目根目录执行）：
  ```bash
  pip install -r requirement.txt
  ```

> 备注：依赖文件名是 `requirement.txt`（不是常见的 `requirements.txt`）。

## 运行命令
### 1) 默认抓取当前月
```bash
python main.py
```

### 2) 指定月份（YYYY-MM）
```bash
python main.py --month 2025-12
```

### 3) 限制最多扫描页数（安全上限）
```bash
python main.py --month 2025-12 --max-pages 50
```

## 输出
- 运行结束后会在当前目录生成：
  - `nature_{YYYY-MM}.md`

## 环境变量（必须先自行定义）
本项目通过 `llm.py` 调用 DeepSeek（OpenAI SDK 兼容接口），需要你本地先设置：
- `DEEPSEEK_API_KEY`

示例：

**Windows PowerShell**
```powershell
$env:DEEPSEEK_API_KEY="your_key_here"
python main.py --month 2025-12
```

**Windows CMD**
```bat
set DEEPSEEK_API_KEY=your_key_here
python main.py --month 2025-12
```

**macOS / Linux (bash/zsh)**
```bash
export DEEPSEEK_API_KEY="your_key_here"
python main.py --month 2025-12
```
