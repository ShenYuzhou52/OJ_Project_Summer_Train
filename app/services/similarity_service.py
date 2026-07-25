"""
代码相似度检测服务
使用 AST 分析方式对 Python 代码进行相似度计算，核心方式是解析 Python 抽象语法树（AST）后再比较结构。
数据库操作委托给 similarity_repo。
"""
import ast
import uuid
import itertools
from app.repositories import similarity_repo, submission_repo
from app.utils.time_utils import now_utc


def strip_comments_and_blanks(code: str) -> str:
    """使用 tokenize 正确删除注释和空行"""
    import tokenize
    import io

    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(code).readline))
        # 过滤掉 COMMENT token，保留其余
        filtered = [tok for tok in tokens if tok.type != tokenize.COMMENT]
        cleaned = tokenize.untokenize(filtered)
    except tokenize.TokenizeError:
        # tokenize 失败，回退到简单去空行
        cleaned = code

    # 去除空行
    lines = [line for line in cleaned.split('\n') if line.strip()]
    return '\n'.join(lines)


def normalize_variable_names(tree: ast.AST) -> ast.AST:
    """将变量名统一替换为通用名称，降低变量名不同对结果的影响"""
    class NameNormalizer(ast.NodeTransformer):
        def __init__(self):
            self.name_map = {}
            self.counter = 0

        def _get_normalized(self, name):
            import keyword
            if name in dir(__builtins__) or keyword.iskeyword(name):
                return name
            if name not in self.name_map:
                self.name_map[name] = f"var_{self.counter}"
                self.counter += 1
            return self.name_map[name]

        def visit_Name(self, node):
            node.id = self._get_normalized(node.id)
            return self.generic_visit(node)

        def visit_FunctionDef(self, node):
            node.name = self._get_normalized(node.name)
            for arg in node.args.args:
                arg.arg = self._get_normalized(arg.arg)
            return self.generic_visit(node)

        def visit_arg(self, node):
            node.arg = self._get_normalized(node.arg)
            return self.generic_visit(node)

    normalizer = NameNormalizer()
    return normalizer.visit(tree)


def get_ast_structure(code: str) -> str:
    """获取代码的 AST 结构化表示"""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        # 解析失败，回退到 token 方法
        return strip_comments_and_blanks(code)

    tree = normalize_variable_names(tree)
    return ast.dump(tree)


def calculate_similarity(code_a: str, code_b: str) -> float:
    """
    计算两份代码的相似度 (0~1)
    使用 AST 结构化比较 + 序列相似度
    """
    clean_a = strip_comments_and_blanks(code_a)
    clean_b = strip_comments_and_blanks(code_b)

    if not clean_a and not clean_b:
        return 1.0
    if not clean_a or not clean_b:
        return 0.0

    struct_a = get_ast_structure(clean_a)
    struct_b = get_ast_structure(clean_b)

    from difflib import SequenceMatcher
    matcher = SequenceMatcher(None, struct_a, struct_b)
    return round(matcher.ratio(), 4)


async def run_similarity_check(problem_id: str, submission_ids: list[str]) -> list[dict]:
    """
    对给定的 submission_id 列表进行两两相似度检测
    返回所有配对的相似度报告
    """
    # 获取所有提交的源码
    submissions = {}
    for sid in submission_ids:
        sub = await submission_repo.get_submission_by_id(sid)
        if sub and sub["problem_id"] == problem_id:
            submissions[sid] = sub["source_code"]

    if len(submissions) < 2:
        return []

    # 两两比较
    reports = []
    pairs = list(itertools.combinations(submissions.keys(), 2))

    for sid_a, sid_b in pairs:
        similarity = calculate_similarity(submissions[sid_a], submissions[sid_b])
        report_id = str(uuid.uuid4())
        created_at = now_utc()

        report = {
            "id": report_id,
            "problem_id": problem_id,
            "submission_a": sid_a,
            "submission_b": sid_b,
            "similarity": similarity,
            "method": "ast",
            "created_at": created_at,
        }
        reports.append(report)

        # 通过 repo 层保存到数据库
        await similarity_repo.save_similarity_report(report)

    return reports


async def get_similarity_reports(problem_id: str) -> list[dict]:
    """获取某题目的所有相似度报告（委托给 repo 层）"""
    return await similarity_repo.get_similarity_reports(problem_id)