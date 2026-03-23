可以，而且用 **Hugging Face access token** 这条路是能做的；但要先说明一个关键限制：**HF 目前我能确认有可直接读的 paper page 和部分 JSON 接口，但我没有找到一个“官方文档清楚写明的、可按标题直接返回 JSON 的 papers 搜索 API”**。我能确认的是：HF 的 Paper Pages 官方支持按**论文名或完整 arXiv id**在主页面搜索；单篇论文页的路由是 `/papers/<arxiv_id>`；并且至少有一个公开 JSON 端点 `/api/daily_papers?date=...`，返回里直接带 `githubRepo`、`projectPage`、`paper.id`、`paper.title` 等字段。([Hugging Face][1])

所以，**纯 HF 的最实用方案**是：

**标题/关键词 → `https://huggingface.co/papers?q=...` 搜到论文页 → 进入 `https://huggingface.co/papers/<arxiv_id>` → 抽取 GitHub 链接。**
如果你已经知道 arXiv id，那就更简单，直接访问 `/papers/<arxiv_id>`。HF 官方文档明确说主 Papers 页面可以搜论文名或完整 arXiv id，也明确给了 `hf.co/papers/xxxx.yyyyy` 这种路由格式；而实际论文页上确实会展示 `GitHub` 按钮。([Hugging Face][1])

另外，**access token 的申请很简单**：登录 HF 后到 **Settings → Access Tokens → New token**，创建一个 User Access Token 即可。官方文档写明可以创建 token，并选择角色；你的这个场景只做读取，`read` 就够了。([Hugging Face][2])

你这个需求，我建议直接按下面两种方式做。

---

## 方案 1：已知 arXiv ID，直接查代码

这是最稳的。

### curl

```bash
curl -L \
  -H "Authorization: Bearer $HF_TOKEN" \
  -H "User-Agent: paper-code-finder/1.0" \
  "https://huggingface.co/papers/2503.19108"
```

然后在返回的 HTML 里找 `https://github.com/...`。
之所以这样做，是因为 HF 的论文页本身就会展示 GitHub 链接；例如 `2503.19108` 这个页面上就有 `GitHub` 按钮，而且页面正文里也能看到代码链接。([Hugging Face][3])

### Python

```python
import re
import requests
from bs4 import BeautifulSoup

HF_TOKEN = "hf_xxx"
HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "User-Agent": "paper-code-finder/1.0",
}

def get_github_from_arxiv_id(arxiv_id: str) -> str | None:
    url = f"https://huggingface.co/papers/{arxiv_id}"
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()

    html = resp.text

    # 先用正则快速扫一遍
    m = re.search(r'https://github\.com/[^\s"<>]+', html)
    if m:
        return m.group(0)

    # 再用 HTML 解析兜底
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("https://github.com/"):
            return href

    return None

print(get_github_from_arxiv_id("2503.19108"))
```

---

## 方案 2：只有论文标题，先搜 HF Papers，再进详情页

HF 官方文档说主 Papers 页面支持搜**论文名**或**完整 arXiv id**；而实际站点上也确实有 `q` 查询参数形式的页面，比如 `/papers?q=API`。所以你可以先请求搜索页，再提取第一个匹配的 `/papers/<id>` 链接，最后再按上面的方式抓 GitHub。([Hugging Face][1])

### Python

```python
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

HF_TOKEN = "hf_xxx"
HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "User-Agent": "paper-code-finder/1.0",
}

def search_paper_page_by_title(title: str) -> str | None:
    url = f"https://huggingface.co/papers?q={quote(title)}"
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # 找形如 /papers/2503.19108 的链接
    candidates = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if re.fullmatch(r"/papers/\d{4}\.\d{4,5}(v\d+)?", href):
            candidates.append("https://huggingface.co" + href)

    return candidates[0] if candidates else None

def get_github_from_paper_page(paper_url: str) -> str | None:
    resp = requests.get(paper_url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    html = resp.text

    m = re.search(r'https://github\.com/[^\s"<>]+', html)
    if m:
        return m.group(0)

    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("https://github.com/"):
            return href
    return None

title = "Your ViT is Secretly an Image Segmentation Model"
paper_url = search_paper_page_by_title(title)
github_url = get_github_from_paper_page(paper_url) if paper_url else None

print("paper_url =", paper_url)
print("github_url =", github_url)
```

---

## 方案 3：如果你刚好知道日期，可以直接走 JSON

我能确认 HF 有公开 JSON 端点：

```bash
https://huggingface.co/api/daily_papers?date=YYYY-MM-DD
```

这个返回里直接有：

* `paper.id`
* `paper.title`
* `githubRepo`
* `projectPage`
* `githubStars`

比如我查到的一个样例里，JSON 里就直接出现了 `githubRepo: "https://github.com/tue-mps/eomt"`。所以如果你的目标论文在那天的 daily papers 列表中，这条是最省事的。([Hugging Face][4])

### Python

```python
import requests

HF_TOKEN = "hf_xxx"
HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "User-Agent": "paper-code-finder/1.0",
}

def find_code_from_daily_papers(date_str: str, title: str):
    url = f"https://huggingface.co/api/daily_papers?date={date_str}"
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    for item in data:
        paper = item.get("paper", {})
        if paper.get("title", "").strip().lower() == title.strip().lower():
            return {
                "paper_id": paper.get("id"),
                "title": paper.get("title"),
                "github_repo": paper.get("githubRepo"),
                "project_page": paper.get("projectPage"),
            }
    return None
```

---

## 你要注意的两个坑

第一，**HF 上的 GitHub 链接不是对所有论文都一定有**。我查到的实际 JSON 里有 `githubRepoAddedBy: "user"`，论文页社区区块里也能看到提交者补充的 `Code:` 链接，这说明它很多时候是**社区/提交者添加**的，不是“HF 自动保证全量覆盖”。所以：**查不到，不一定是没有代码，也可能是 HF 这边没挂出来。**([Hugging Face][4])

第二，**HF 这套更偏“paper page + 关联 artifacts”**。官方文档强调的是：Paper Pages 用来聚合与论文相关的 **models、datasets、Spaces**；如果仓库 README 里引用了 paper，HF 会抽 arXiv id 并把这些 artifacts 关联到 paper page。换句话说，HF 很适合当“论文中枢页”，但它不是一个专门做“全网 GitHub 实现映射”的数据库。([Hugging Face][1])

---

## 我给你的实际建议

如果你坚持 **只用 Hugging Face + access token**，就这样做：

1. 先创建一个 `read` token。([Hugging Face][2])
2. **优先用 arXiv id**，直接请求 `https://huggingface.co/papers/<arxiv_id>`。 ([Hugging Face][1])
3. 如果只有标题，就请求 `https://huggingface.co/papers?q=<标题>`，先拿到 paper page。([Hugging Face][1])
4. 进入 paper page 后抽取 `github.com/...`。
5. 如果没有 GitHub，再看页面下方的 **Models citing this paper / Spaces citing this paper**，有时这些 HF repo 的 README 里会再带出原始代码仓库。([Hugging Face][3])

如果你愿意，我下一条直接给你一份**可运行的完整 Python 脚本**，输入“论文标题或 arXiv id”，输出“HF paper 链接 + GitHub 代码链接”。

[1]: https://huggingface.co/docs/hub/paper-pages "Paper Pages · Hugging Face"
[2]: https://huggingface.co/docs/hub/en/security-tokens?utm_source=chatgpt.com "User access tokens - Hugging Face"
[3]: https://huggingface.co/papers/2503.19108 "Paper page - Your ViT is Secretly an Image Segmentation Model"
[4]: https://huggingface.co/api/daily_papers?date=2025-03-31 "huggingface.co"
