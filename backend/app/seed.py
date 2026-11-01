"""初始化脚本：建表 + 管理员账号 + 演示题目 / 标签 / 题单。

用法：
    python -m app.seed          # 幂等：已存在的数据不会重复写入
    python -m app.seed --reset  # 先 drop 所有表再重建（危险，仅本地使用）
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from config import settings
from database import Base, SessionLocal, engine
from models import Problem, ProblemList, ProblemListItem, ProblemTag, SubQuestion, Tag, User
from security import hash_password

KNOWLEDGE_TAGS = [
    "程序阅读", "时间复杂度", "位运算", "递归", "排序", "图论",
    "动态规划", "字符串", "树", "数学", "进制", "数组",
]
SOURCE_TAGS = ["CSP-J真题", "CSP-S真题", "原创", "改编"]


def ensure_admin(db: Session) -> User:
    admin = db.scalar(select(User).where(User.username == settings.admin_username))
    if admin is None:
        admin = User(
            username=settings.admin_username,
            password_hash=hash_password(settings.admin_password),
            role="admin",
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        # 不在日志里打印密码：云平台的构建/运行日志对团队成员可见
        print(f"[seed] 管理员已创建：{settings.admin_username}（密码来自 ADMIN_PASSWORD 环境变量）")
        if settings.uses_placeholder_admin_password:
            print("[seed] 警告：当前使用占位管理员密码，请立即通过 python -m app.passwd 重置")
    elif admin.role != "admin":
        admin.role = "admin"
        db.commit()
    return admin


def ensure_tags(db: Session) -> dict[str, Tag]:
    mapping: dict[str, Tag] = {}
    for name in KNOWLEDGE_TAGS:
        tag = db.scalar(select(Tag).where(Tag.name == name))
        if tag is None:
            tag = Tag(name=name, category="知识点")
            db.add(tag)
            db.flush()
        mapping[name] = tag
    for name in SOURCE_TAGS:
        tag = db.scalar(select(Tag).where(Tag.name == name))
        if tag is None:
            tag = Tag(name=name, category="来源")
            db.add(tag)
            db.flush()
        mapping[name] = tag
    db.commit()
    return mapping


def single(title: str, stem: str, options: list[str], correct: str, analysis: str, *,
           source_tag: str = "original", year: int | None = None, exam: str | None = "CSP-J",
           answer_md: str = "") -> dict:
    keys = "ABCDEF"
    return {
        "title": title,
        "type": "single",
        "source_tag": source_tag,
        "source_year": year,
        "source_exam": exam,
        "content_md": stem,
        "answer_md": answer_md,
        "sub_questions": [
            {
                "content_md": "",
                "options": [{"key": keys[i], "text": text} for i, text in enumerate(options)],
                "correct_answer": correct,
                "analysis_md": analysis,
            }
        ],
    }


def big(title: str, ptype: str, stem: str, subs: list[dict], *,
        source_tag: str = "original", year: int | None = None, exam: str | None = "CSP-J",
        answer_md: str = "") -> dict:
    keys = "ABCDEF"
    normalized = []
    for i, sub in enumerate(subs, start=1):
        normalized.append(
            {
                "content_md": sub["q"],
                "options": [{"key": keys[j], "text": t} for j, t in enumerate(sub["options"])],
                "correct_answer": sub["a"],
                "analysis_md": sub.get("analysis", ""),
            }
        )
    return {
        "title": title,
        "type": ptype,
        "source_tag": source_tag,
        "source_year": year,
        "source_exam": exam,
        "content_md": stem,
        "answer_md": answer_md,
        "sub_questions": normalized,
    }


def build_problems() -> list[dict]:
    data: list[dict] = []

    # ---------------- 15 道单选（模拟考试正好用满） ----------------
    data.append(single(
        "字符溢出",
        "执行下面的 C++ 代码后，输出结果是（ ）。\n\n```cpp\n#include <iostream>\nusing namespace std;\nint main() {\n    char c = 127;\n    c = c + 1;\n    cout << (int)c << endl;\n    return 0;\n}\n```\n\n提示：`char` 是有符号 8 位整数。",
        ["127", "-128", "128", "0"],
        "B",
        "`char` 为 8 位有符号整数，范围 $-128 \\sim 127$。127 加 1 溢出后按补码回绕到 $-128$，输出 `-128`。",
        source_tag="real", year=2021, answer_md="答案：B。有符号整数溢出属于未定义行为，但常见平台按二进制补码回绕。",
    ))
    data.append(single(
        "循环时间复杂度",
        "下面代码段的时间复杂度是（ ）。\n\n```cpp\nint s = 0;\nfor (int i = 1; i <= n; i *= 2)\n    for (int j = 1; j <= n; j++)\n        s += i * j;\n```",
        ["$O(n)$", "$O(n \\log n)$", "$O(n^2)$", "$O(\\log n)$"],
        "B",
        "外层循环执行 $\\lfloor \\log_2 n \\rfloor + 1$ 次，内层每次执行 $n$ 次，总计 $O(n \\log n)$。",
        year=2022,
    ))
    data.append(single(
        "异或的性质",
        "已知 `x ^ y = 0b1011`，且 `x = 0b0110`，则 `y` 的二进制表示是（ ）。",
        ["0b1101", "0b0011", "0b1111", "0b1001"],
        "A",
        "异或满足 `y = (x ^ y) ^ x`，即 `0b1011 ^ 0b0110 = 0b1101`。",
        year=2020,
    ))
    data.append(single(
        "二叉树遍历",
        "某二叉树的先序遍历为 `A B D E C F`，中序遍历为 `D B E A C F`，则其后序遍历为（ ）。",
        ["D E B F C A", "D E B C F A", "E D B F C A", "D B E F C A"],
        "A",
        "由先序确定根 A；中序中 A 左侧 D B E 为左子树、右侧 C F 为右子树。左子树后序为 D E B，右子树后序为 F C，故整体为 `D E B F C A`。",
        year=2019,
    ))
    data.append(single(
        "出栈序列",
        "依次将 `1, 2, 3, 4, 5` 压栈，允许在任意时刻出栈，则下列哪个序列不可能是出栈序列（ ）。",
        ["2 3 4 1 5", "5 4 3 2 1", "3 1 2 4 5", "4 3 5 2 1"],
        "C",
        "若要 3 先出栈，则 1、2 必须在栈中；3 出栈后只能先出 2 再出 1，因此 `3 1 2 ...` 不可能。",
        year=2018,
    ))
    data.append(single(
        "稳定排序",
        "下列排序算法中，平均时间复杂度为 $O(n \\log n)$ 且稳定的是（ ）。",
        ["快速排序", "堆排序", "归并排序", "希尔排序"],
        "C",
        "归并排序平均与最坏均为 $O(n \\log n)$ 且稳定；快排、堆排不稳定，快排最坏 $O(n^2)$。",
        year=2021,
    ))
    data.append(single(
        "进制转换",
        "十进制数 $2024$ 的十六进制表示是（ ）。",
        ["0x7E8", "0x7D8", "0x7E0", "0x8E8"],
        "A",
        "$2024 = 7 \\times 256 + 14 \\times 16 + 8 = (7E8)_{16}$。",
        year=2024,
    ))
    data.append(single(
        "数组与指针",
        "下面代码输出（ ）。\n\n```cpp\nint a[5] = {1, 2, 3, 4, 5};\nint *p = a + 2;\ncout << *(p + 1) << \" \" << p[-1] << endl;\n```",
        ["4 2", "4 1", "3 2", "5 3"],
        "A",
        "`p` 指向 `a[2]`（值 3）。`*(p+1)` 即 `a[3]`=4；`p[-1]` 即 `a[1]`=2。",
        year=2020,
    ))
    data.append(single(
        "递归调用次数",
        "函数 `f(n)` 定义为：`n <= 1` 时返回 1，否则返回 `f(n-1) + f(n-2)`。`f(6)` 的值是（ ）。",
        ["8", "13", "21", "5"],
        "B",
        "数列为 1,1,2,3,5,8,13，`f(6)=13`。",
        year=2022,
    ))
    data.append(single(
        "最短路算法",
        "使用朴素 Dijkstra 算法求含 $n$ 个点、$m$ 条边的图（$m \\gg n$）的单源最短路，复杂度为（ ）。",
        ["$O(n)$", "$O(n^2)$", "$O(m \\log n)$", "$O(nm)$"],
        "B",
        "朴素 Dijkstra 每轮扫描全部顶点，共 $n$ 轮，复杂度 $O(n^2)$；堆优化版本为 $O((n+m)\\log n)$。",
        year=2023,
    ))
    data.append(single(
        "字符串比较",
        "`strcmp(\"csp\", \"csq\")` 的返回值（ ）。",
        ["大于 0", "等于 0", "小于 0", "不确定"],
        "C",
        "逐字符比较，第三位 `p < q`，故返回值小于 0。",
        year=2019,
    ))
    data.append(single(
        "区间贪心",
        "有 $n$ 个闭区间，要选出最多的互不重叠区间，正确的贪心策略是（ ）。",
        ["按左端点升序选", "按右端点升序选", "按区间长度升序选", "随机选后再调整"],
        "B",
        "按右端点升序，每次选择与前一个区间不重叠的最早结束区间，可用交换论证证明最优。",
        year=2023,
    ))
    data.append(single(
        "埃氏筛计数",
        "$100$ 以内的素数共有（ ）个。",
        ["23", "24", "25", "26"],
        "C",
        "100 以内素数共 25 个：2,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,73,79,83,89,97。",
        year=2021,
    ))
    data.append(single(
        "二分查找次数",
        "在长度为 $1024$ 的有序数组中做二分查找，最坏情况下需要比较（ ）次。",
        ["10", "11", "12", "1024"],
        "B",
        "每次比较后区间减半，$\\lceil \\log_2 1024 \\rceil = 10$，再加最后一次判定，最坏比较 11 次。",
        year=2022,
    ))
    data.append(single(
        "等比数列求和",
        "计算 $\\sum_{k=1}^{10} 2^k$ 的结果是（ ）。",
        ["1024", "2046", "2048", "4094"],
        "B",
        "$\\sum_{k=1}^{n} 2^k = 2^{n+1} - 2$，代入 $n=10$ 得 $2048-2=2046$。",
        year=2024,
    ))
    data.append(single(
        "结构体与内存对齐",
        "在 64 位环境下，下面结构体 `sizeof(S)` 通常是（ ）。\n\n```cpp\nstruct S {\n    char a;\n    int b;\n    char c;\n};\n```",
        ["6", "8", "12", "16"],
        "C",
        "`char` 占 1 字节，`int` 需 4 字节对齐：a 后有 3 字节填充，c 之后填充到 4 的倍数，共 $4+4+4=12$。",
        year=2023,
    ))

    # ---------------- 3 道阅读程序（各 3 小题） ----------------
    data.append(big(
        "阅读程序：循环累加与取模",
        "reading",
        "阅读下面的程序，回答后面的问题。\n\n```cpp\n#include <iostream>\nusing namespace std;\nint main() {\n    int n = 2024, s = 0, k = 0;\n    while (n > 0) {\n        s += n % 10;\n        n /= 10;\n        ++k;\n    }\n    cout << s << \" \" << k << endl;\n    return 0;\n}\n```\n\n提示：该程序统计十进制数的各位数字之和与位数。",
        [
            {"q": "程序的输出结果是（ ）。", "options": ["8 4", "10 4", "8 5", "2024 4"], "a": "A",
             "analysis": "$2+0+2+4=8$，共 4 位，输出 `8 4`。"},
            {"q": "将 `n /= 10` 改为 `n = n / 100` 后，`k` 的值变为（ ）。", "options": ["1", "2", "3", "4"], "a": "B",
             "analysis": "每次去掉两位，2024 → 20 → 0，循环 2 次，`k = 2`。"},
            {"q": "若把 `int` 改为 `long long`，程序行为（ ）。", "options": ["结果改变", "结果不变，但可处理更大整数", "编译错误", "死循环"], "a": "B",
             "analysis": "运算逻辑不变，仅取值范围变大，因此结果不变。"},
        ],
        year=2023, exam="CSP-J", source_tag="adapted",
    ))
    data.append(big(
        "阅读程序：递归与字符串",
        "reading",
        "阅读下面的程序，回答后面的问题。\n\n```cpp\n#include <string>\n#include <iostream>\nusing namespace std;\n\nstring rev(string s, int l, int r) {\n    if (l >= r) return s;\n    swap(s[l], s[r]);\n    return rev(s, l + 1, r - 1);\n}\n\nint main() {\n    string s = \"csp2024\";\n    cout << rev(s, 0, (int)s.size() - 1) << endl;\n    return 0;\n}\n```",
        [
            {"q": "程序的输出是（ ）。", "options": ["4202psc", "csp2024", "4202csp", "psc4202"], "a": "A",
             "analysis": "递归交换首尾字符，等价于整体反转，得 `4202psc`。"},
            {"q": "函数 `rev` 的递归调用次数是（ ）。", "options": ["3", "4", "5", "7"], "a": "B",
             "analysis": "长度 7，每层处理两个字符，共 $\\lfloor 7/2 \\rfloor = 3$ 次交换后 `l >= r`，调用 4 次（含最后一次返回）。"},
            {"q": "如果 `s` 的长度为偶数且为 $2k$，则交换的次数为（ ）。", "options": ["$k-1$", "$k$", "$2k$", "$k+1$"], "a": "B",
             "analysis": "长度为 $2k$ 时需交换 $k$ 对字符。"},
        ],
        year=2022, exam="CSP-S", source_tag="real",
    ))
    data.append(big(
        "阅读程序：数组排序与计数",
        "reading",
        "阅读下面的程序，回答后面的问题。\n\n```cpp\n#include <iostream>\n#include <algorithm>\nusing namespace std;\n\nint main() {\n    int a[8] = {5, 3, 5, 1, 3, 5, 7, 1};\n    sort(a, a + 8);\n    int cnt = 1, ans = 1;\n    for (int i = 1; i < 8; ++i) {\n        if (a[i] == a[i - 1]) ++cnt;\n        else cnt = 1;\n        ans = max(ans, cnt);\n    }\n    cout << a[0] << \" \" << ans << endl;\n    return 0;\n}\n```",
        [
            {"q": "程序的输出是（ ）。", "options": ["1 3", "1 5", "5 3", "1 8"], "a": "A",
             "analysis": "排序后数组为 1,1,3,3,5,5,5,7，最小值 1，最多重复 3 次，输出 `1 3`。"},
            {"q": "这段程序统计的是（ ）。", "options": ["最小值与最大出现次数", "最小值与数组长度", "最大值与最小值", "中位数与众数"], "a": "A",
             "analysis": "`ans` 记录最长连续相同元素个数，排序后即最大出现次数。"},
            {"q": "若把 `sort` 换成冒泡排序实现，程序的时间复杂度变为（ ）。", "options": ["$O(n)$", "$O(n \\log n)$", "$O(n^2)$", "$O(2^n)$"], "a": "C",
             "analysis": "冒泡排序为 $O(n^2)$，此处 $n=8$ 影响可忽略，但复杂度量级改变。"},
        ],
        year=2024, exam="CSP-J", source_tag="original",
    ))

    # ---------------- 2 道完善程序（各 5 小题） ----------------
    data.append(big(
        "完善程序：快速排序的分区",
        "completion",
        "下面的程序用快速排序将数组升序排列。请选出正确的填空。\n\n```cpp\nvoid quickSort(int a[], int l, int r) {\n    if (l >= r) return;\n    int pivot = a[(l + r) / 2];\n    int i = l, j = r;\n    while (i <= j) {\n        while (a[i] < pivot) ++i;      // ①\n        while (a[j] > pivot) --j;      // ②\n        if (i <= j) {\n            swap(a[i], a[j]);          // ③\n            ++i; --j;                  // ④\n        }\n    }\n    quickSort(a, l, j);                // ⑤\n    quickSort(a, i, r);\n}\n```",
        [
            {"q": "① 处循环 `while (a[i] < pivot) ++i;` 的作用是（ ）。", "options": ["找到左侧第一个不小于基准的元素", "找到最大值", "统计小于基准的个数", "删除元素"], "a": "A", "analysis": "让 `i` 向右移动直到遇到不小于基准的元素，等待交换。"},
            {"q": "② 处 `while (a[j] > pivot) --j;` 结束后，`a[j]` 的性质是（ ）。", "options": ["不大于基准", "大于基准", "等于基准", "不存在"], "a": "A", "analysis": "循环因 `a[j] <= pivot` 而停止，故 `a[j]` 不大于基准。"},
            {"q": "③ 处交换后执行 ④ 的原因是（ ）。", "options": ["避免死循环并使区间收缩", "恢复数组", "统计次数", "节省内存"], "a": "A", "analysis": "交换后两侧元素均已就位，指针各前进一格，保证 `i > j` 时退出，避免死循环。"},
            {"q": "⑤ 处递归调用 `quickSort(a, l, j)` 处理的是（ ）。", "options": ["不大于基准的左半部分", "右半部分", "整个数组", "中间元素"], "a": "A", "analysis": "此时 `j` 指向左段末尾，左段元素均不大于基准。"},
            {"q": "该实现在数组已有序时的时间复杂度为（ ）。", "options": ["$O(n \\log n)$", "$O(n)$", "$O(n^2)$", "$O(\\log n)$"], "a": "A", "analysis": "取中间元素作基准可避免最坏划分，有序数组仍能均分区间，保持 $O(n \\log n)$。"},
        ],
        year=2023, exam="CSP-S", source_tag="adapted",
    ))
    data.append(big(
        "完善程序：0/1 背包",
        "completion",
        "下面程序用动态规划求解 0/1 背包：`n` 件物品，容量 `W`，求最大价值。\n\n```cpp\ndp[0..W] = 0;\nfor (int i = 1; i <= n; ++i) {\n    for (int j = W; j >= w[i]; --j) {   // ①\n        dp[j] = max(dp[j], dp[j - w[i]] + v[i]);  // ②\n    }\n}\ncout << dp[W] << endl;                 // ③\n```",
        [
            {"q": "① 处容量循环必须从大到小的原因是（ ）。", "options": ["保证每件物品只被选一次", "提高速度", "防止下标越界", "便于输出"], "a": "A", "analysis": "逆序更新使 `dp[j-w[i]]` 仍是上一轮状态，避免同一物品被重复使用。"},
            {"q": "② 处 `dp[j]` 的含义是（ ）。", "options": ["前 i 件物品、容量为 j 时的最大价值", "容量为 j 时已选物品件数", "第 j 件物品的价值", "物品 i 的总体积"], "a": "A", "analysis": "`dp[j]` 表示处理到第 i 件物品时，容量 j 的最优价值。"},
            {"q": "若把 ① 的内层循环改为正序，则问题性质变为（ ）。", "options": ["完全背包", "多重背包", "分组背包", "仍是 0/1 背包"], "a": "A", "analysis": "正序会允许同一物品被多次选择，即完全背包。"},
            {"q": "③ 处输出的是（ ）。", "options": ["容量为 W 时的最大价值", "物品总数", "最小价值", "总体积"], "a": "A", "analysis": "`dp[W]` 即容量 W 的最优解。"},
            {"q": "该算法的时间复杂度是（ ）。", "options": ["$O(nW)$", "$O(nW^2)$", "$O(n^2)$", "$O(2^n)$"], "a": "A", "analysis": "外层 n 次、内层最多 W 次，总计 $O(nW)$。"},
        ],
        year=2024, exam="CSP-J", source_tag="original",
    ))
    return data


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admin = ensure_admin(db)
        tags = ensure_tags(db)

        existing = db.scalar(select(Problem.id).limit(1))
        if existing is not None:
            print("[seed] 题库中已有数据，跳过演示数据写入")
            return

        tag_lookup = {
            0: ["程序阅读", "进制"], 1: ["时间复杂度"], 2: ["位运算"], 3: ["树", "程序阅读"],
            4: ["数组", "程序阅读"], 5: ["排序"], 6: ["进制", "数学"], 7: ["数组", "程序阅读"],
            8: ["递归"], 9: ["图论", "时间复杂度"], 10: ["字符串"], 11: ["排序", "动态规划"],
            12: ["数学", "数组"], 13: ["程序阅读", "时间复杂度"], 14: ["数学"],
            15: ["程序阅读", "数组"], 16: ["程序阅读", "进制"], 17: ["递归", "字符串"],
            18: ["排序", "数组"], 19: ["排序", "程序阅读"], 20: ["动态规划", "程序阅读"],
        }
        created: list[Problem] = []
        for idx, item in enumerate(build_problems()):
            sub_items = item.pop("sub_questions")
            problem = Problem(
                title=item["title"],
                type=item["type"],
                source_tag=item.get("source_tag", "original"),
                source_year=item.get("source_year"),
                source_exam=item.get("source_exam"),
                content_md=item["content_md"],
                answer_md=item.get("answer_md", ""),
                status="approved",
                contributor_id=admin.id,
                reviewer_id=admin.id,
                reviewed_at=datetime.now(timezone.utc),
            )

            for order_no, sub in enumerate(sub_items, start=1):
                problem.sub_questions.append(
                    SubQuestion(
                        order_no=order_no,
                        content_md=sub["content_md"],
                        options_json=sub["options"],
                        correct_answer=sub["correct_answer"],
                        analysis_md=sub["analysis_md"],
                    )
                )
            names = tag_lookup.get(idx, [])
            category_tag = "CSP-J真题" if item.get("source_tag") == "real" and item.get("source_exam") == "CSP-J" else None
            for name in names:
                if name in tags:
                    problem.tag_links.append(ProblemTag(tag_id=tags[name].id))
            if category_tag and category_tag in tags:
                problem.tag_links.append(ProblemTag(tag_id=tags[category_tag].id))
            db.add(problem)
            created.append(problem)
        db.flush()

        # 演示学生账号与题单：默认关闭；开启时必须显式提供 DEMO_STUDENT_PASSWORD，
        # 避免任何「已知密码」账号随代码上线。
        if settings.seed_demo_student:
            if not settings.demo_student_password:
                print("[seed] 已开启 SEED_DEMO_STUDENT，但未设置 DEMO_STUDENT_PASSWORD，跳过演示学生账号")
            else:
                student = db.scalar(select(User).where(User.username == "student"))
                if student is None:
                    student = User(
                        username="student",
                        password_hash=hash_password(settings.demo_student_password),
                        role="user",
                    )
                    db.add(student)
                    db.flush()

                plist = ProblemList(
                    title="初赛必刷 10 题",
                    description="覆盖进制、位运算、排序、递归与程序阅读的基础题单。",
                    creator_id=student.id,
                    is_public=True,
                )
                db.add(plist)
                db.flush()
                for order_no, problem in enumerate(created[:10], start=1):
                    db.add(ProblemListItem(list_id=plist.id, problem_id=problem.id, order_no=order_no))

        db.commit()
        print(f"[seed] 已写入 {len(created)} 道演示题目、{len(tags)} 个标签")
        if settings.seed_demo_student and settings.demo_student_password:
            print("[seed] 演示学生账号：student（密码来自 DEMO_STUDENT_PASSWORD）")
    finally:
        db.close()


def reset() -> None:
    Base.metadata.drop_all(bind=engine)
    print("[seed] 已清空所有表")


if __name__ == "__main__":
    if "--reset" in sys.argv:
        reset()
    seed()
