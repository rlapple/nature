import os
from openai import OpenAI


SUMMARY_PROMPT = """
你是一名学术期刊编辑，请为以下 Nature Research Article 撰写【中文论文导读】：

【论文标题】
{title}

【论文摘要】
{abstract}

要求：
1. 150–250 字
2. 学术、客观、克制，不使用宣传性语言
3. 包含：
   - 研究背景
   - 核心发现
   - 方法或机制亮点
   - 学术意义
4. 不逐句翻译摘要，而是重组表达
"""
# Please install OpenAI SDK first: `pip3 install openai`



client = OpenAI(
    api_key=os.environ.get('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com")




def summarize_with_llm(title: str, main_content: str) -> str:
    if not main_content.strip():
        return ""

    prompt = SUMMARY_PROMPT.format(title=title, abstract=main_content)

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role":"user","content":prompt}],
        temperature=0.3,
        stream=False
    )

    return response.choices[0].message.content.strip()

def translate_with_llm(text: str, target_language: str = "Chinese") -> str:
    if not text.strip():
        return ""

    prompt = f"请将论文的标题翻译成{target_language}：\n\n{text}"

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role":"user","content":prompt}],
        temperature=0.3,
        stream=False
    )

    return response.choices[0].message.content.strip()


CATEGORIES = [
    "Biology",
    "Materials Science",
    "Computer Science",
    "Physics",
    "Chemistry",
    "Medicine",
    "Earth & Environment",
    "Other"
]



def classify_paper_with_llm(title: str, abstract: str) -> str:
    prompt = f"""
你是一名学术期刊编辑。

请将下列论文【且仅能】归类到以下学科之一：
- Biology
- Materials Science
- Computer Science
- Physics
- Chemistry
- Medicine
- Earth & Environment
- Other

【论文标题】
{title}

【论文摘要】
{abstract[:1500]}

要求：
1. 只输出学科英文名
2. 不要输出解释
"""

    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0
    )

    return resp.choices[0].message.content.strip()

