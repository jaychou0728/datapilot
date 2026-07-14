import json
import duckdb
import pandas as pd
import numpy as np
from app.data.duckdb_manager import DuckDBManager
from app.ai.deepseek_client import DeepSeekClient
from app.model.cleaning import CleaningIssue, CleanResult

class CleaningService:
    def __init__(self, db_path: str, table_name: str):
        self.db_path = db_path
        self.table_name = table_name
        self._backup_df: pd.DataFrame | None = None
        self.ai = DeepSeekClient()

    def _get_df(self) -> pd.DataFrame:
        mgr = DuckDBManager(self.db_path)
        return pd.DataFrame(mgr.query(f"SELECT * FROM {self.table_name}", limit=1000000))

    def _query(self, sql: str) -> list[dict]:
        mgr = DuckDBManager(self.db_path)
        return mgr.query(sql, limit=1000000)

    def scan(self) -> list[CleaningIssue]:
        """Rule-based scan, kept as fallback."""
        df = self._get_df()
        issues = []

        dup_count = df.duplicated().sum()
        if dup_count > 0:
            dup_samples = df[df.duplicated(keep=False)].head(3).to_dict(orient="records")
            issues.append(CleaningIssue(
                type="duplicate", count=int(dup_count),
                sample=dup_samples, severity="high"
            ))

        for col in df.columns:
            null_count = df[col].isnull().sum()
            if null_count > 0:
                issues.append(CleaningIssue(
                    type="null", column=col, count=int(null_count),
                    severity="high" if null_count / len(df) > 0.3 else "medium"
                ))

        for col in df.select_dtypes(include=["object"]).columns:
            mask = df[col].astype(str).str.strip() != df[col].astype(str)
            ws_count = mask.sum()
            if ws_count > 0:
                bad = df[mask].head(3)[col].tolist()
                issues.append(CleaningIssue(
                    type="whitespace", column=col, count=int(ws_count),
                    sample=bad, severity="low"
                ))

        for col in df.select_dtypes(include=["object"]).columns:
            non_null = df[col].dropna()
            if len(non_null) == 0:
                continue
            converted = pd.to_numeric(non_null, errors="coerce")
            fail_count = converted.isnull().sum()
            if 0 < fail_count < len(non_null):
                bad = non_null[converted.isnull()].head(3).tolist()
                issues.append(CleaningIssue(
                    type="type_mismatch", column=col, count=int(fail_count),
                    sample=bad, severity="medium"
                ))

        for col in df.select_dtypes(include=[np.number]).columns:
            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            outlier_mask = (df[col] < lower) | (df[col] > upper)
            if outlier_mask.sum() > 0:
                bad = df[outlier_mask].head(3)[col].tolist()
                issues.append(CleaningIssue(
                    type="outlier", column=col, count=int(outlier_mask.sum()),
                    sample=bad, severity="low"
                ))

        return issues

    def _build_profile(self) -> dict:
        """Build comprehensive data profile for AI analysis."""
        mgr = DuckDBManager(self.db_path)
        table_info = mgr.get_table_info("data")
        columns = mgr.get_columns("data")
        total_rows = mgr.query("SELECT COUNT(*) AS cnt FROM data")[0]["cnt"]

        col_stats = []
        for info in table_info:
            col = info["column_name"]
            dtype = info["dtype"]
            null_count = info["null_count"]
            samples = info.get("sample_values", [])[:5]

            is_numeric = any(t in dtype.upper() for t in ["INT", "FLOAT", "DOUBLE", "BIGINT", "DECIMAL"])
            quoted = f'"{col}"'

            stat = {"column": col, "dtype": dtype, "null_count": null_count, "samples": samples}

            if is_numeric:
                nums = mgr.query(f"SELECT MIN({quoted}) AS mn, MAX({quoted}) AS mx, ROUND(AVG({quoted}),2) AS av, ROUND(STDDEV({quoted}),2) AS sd, COUNT(DISTINCT {quoted}) AS uniq FROM data WHERE {quoted} IS NOT NULL")
                if nums:
                    stat.update(nums[0])
                # Detect if this looks like a year column
                s = nums[0] if nums else {}
                if s.get("mn", 0) >= 1900 and s.get("mx", 0) <= 2100 and s.get("uniq", 0) <= 30:
                    stat["likely_year"] = True
                stat["numeric"] = True
            else:
                unique = mgr.query(f"SELECT COUNT(DISTINCT {quoted}) AS cnt FROM data")[0]["cnt"]
                stat["unique_count"] = unique
                if unique <= 15:
                    dist = mgr.query(f"SELECT {quoted} AS v, COUNT(*) AS c FROM data WHERE {quoted} IS NOT NULL GROUP BY {quoted} ORDER BY c DESC")
                    stat["distribution"] = [{"value": r["v"], "count": r["c"]} for r in dist]
                # Detect potential issues
                if samples:
                    sample_strs = [str(s) for s in samples]
                    # Currency detection
                    if any("CNY" in s or "¥" in s or "$" in s or "USD" in s for s in sample_strs):
                        stat["looks_like_currency"] = True
                    # Detect mixed case issues
                    lowered = [s.lower().strip() for s in sample_strs if isinstance(s, str)]
                    if len(set(lowered)) < len(sample_strs):
                        stat["case_inconsistency"] = True
                stat["numeric"] = False

            col_stats.append(stat)

        sample_rows = mgr.query("SELECT * FROM data LIMIT 25")

        return {
            "total_rows": total_rows,
            "total_columns": len(columns),
            "columns": columns,
            "column_stats": col_stats,
            "sample_rows": sample_rows,
        }

    async def ai_analyze(self) -> dict:
        """AI-powered data quality analysis with concrete fix suggestions."""
        profile = self._build_profile()
        profile_json = json.dumps(profile, ensure_ascii=False, default=str)

        prompt = f"""你是数据清洗专家。根据以下数据画像，找出数据质量问题，给出具体修复方案。

## 数据画像
{profile_json}

## 要求
对每个问题输出一个 JSON 对象（只返回 JSON 数组）：
[
  {{
    "title": "问题简短标题（中文，10字内）",
    "description": "用通俗语言解释问题，引用数据中的具体例子",
    "severity": "high|medium|low",
    "affected_columns": ["列名"],
    "affected_rows_estimate": 数字,
    "fix_description": "修复方案的一句话说明",
    "operation": "操作名（从下方列表选）",
    "params": {{}}
  }}
]

## 可用操作（必须从以下列表中选择，不要自己发明）
### clean_currency — 清理货币字符串转数字
   params: {{"column": "列名"}}
   说明: 自动去除 CNY/USD/$/¥/€ 前缀、逗号、空格，转为纯数字

### extract_number — 从字符串中提取数字
   params: {{"column": "列名", "units": ["可选的后缀列表如 inches GB g mAh"]}}
   说明: 从 "6.1 inches" "6GB" "174g" 中提取数字部分

### normalize_case — 统一大小写
   params: {{"column": "列名", "mode": "upper|lower|title"}}
   说明: 解决 POCO vs Poco 这类问题

### drop_column — 删除冗余列
   params: {{"column": "列名"}}

### rename_column — 重命名列
   params: {{"old_name": "旧名", "new_name": "新名"}}

### drop_outliers — 标记异常值为空
   params: {{"column": "列名", "min": 下限, "max": 上限}}
   说明: 如重量>500g异常、年份>2025异常

### deduplicate — 删除完全重复的行
   params: {{}}

### trim_strings — 去除所有文本列的前后空格
   params: {{}}

### fill_nulls — 填充空值
   params: {{"column": "列名", "strategy": "mean|median|mode|drop"}}

## 检查要点
- 货币/价格列带CNY/$/¥前缀 → clean_currency
- 数值带单位(g, GB, inches, mAh) → extract_number
- 大小写不一致 → normalize_case
- 处理器的中英文列信息重复 → drop_column 删除其一
- CPU品牌/系列/层级都冗余 → drop_column
- 异常值年份>2024、重量>500g → drop_outliers
- 重复行 → deduplicate
- 空值 → fill_nulls

只返回 JSON 数组。"""

        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        response = await self.ai.chat([
            {"role": "system", "content": "你是数据清洗专家。只输出合法 JSON 数组。"},
            {"role": "user", "content": prompt},
        ], temperature=0.2)

        text = response.strip()
        if text.startswith("```json"):
            text = text.split("```json")[1].split("```")[0].strip()
        elif text.startswith("```"):
            text = text.split("```")[1].split("```")[0].strip()

        try:
            suggestions = json.loads(text)
            return {"suggestions": suggestions, "profile_summary": f"共{profile['total_rows']}行{profile['total_columns']}列"}
        except json.JSONDecodeError:
            return {"suggestions": [], "raw_response": text, "profile_summary": ""}

    async def ai_execute(self, approved_operations: list[dict]) -> CleanResult:
        """Execute approved AI-suggested cleaning operations (safe Python implementation)."""
        df = self._get_df()
        self._backup_df = df.copy()
        rows_before = len(df)
        changes = []

        for op in approved_operations:
            if not op or not isinstance(op, dict):
                continue
            action = op.get("operation", "")
            params = op.get("params", {})
            col = params.get("column", "")

            try:
                if action == "clean_currency" and col and col in df.columns:
                    s = df[col].astype(str)
                    for prefix in ["CNY ", "CNY", "USD ", "USD", "$", "¥", "€", "£", "￥"]:
                        s = s.str.replace(prefix, "", regex=False)
                    s = s.str.replace(",", "", regex=False).str.replace(" ", "", regex=False).str.strip()
                    df[col] = pd.to_numeric(s, errors="coerce")
                    changes.append(f"清理货币列'{col}' → 数字")

                elif action == "extract_number" and col and col in df.columns:
                    s = df[col].astype(str)
                    units = params.get("units", [])
                    for u in units:
                        s = s.str.replace(str(u), "", regex=False)
                    s = s.str.strip()
                    df[col] = pd.to_numeric(s, errors="coerce")
                    changes.append(f"提取列'{col}'中的数字")

                elif action == "normalize_case" and col and col in df.columns:
                    mode = params.get("mode", "upper")
                    if mode == "upper":
                        df[col] = df[col].astype(str).str.strip().str.upper()
                    elif mode == "lower":
                        df[col] = df[col].astype(str).str.strip().str.lower()
                    elif mode == "title":
                        df[col] = df[col].astype(str).str.strip().str.title()
                    changes.append(f"统一列'{col}'大小写为{mode}")

                elif action == "drop_column" and col and col in df.columns:
                    df = df.drop(columns=[col])
                    changes.append(f"删除列'{col}'")

                elif action == "rename_column":
                    old = params.get("old_name", "")
                    new = params.get("new_name", "")
                    if old and new and old in df.columns:
                        df = df.rename(columns={old: new})
                        changes.append(f"重命名'{old}' → '{new}'")

                elif action == "drop_outliers" and col and col in df.columns:
                    lo = params.get("min")
                    hi = params.get("max")
                    mask = pd.Series(True, index=df.index)
                    if lo is not None:
                        mask = mask & (df[col] >= lo)
                    if hi is not None:
                        mask = mask & (df[col] <= hi)
                    n_outliers = (~mask).sum()
                    df.loc[~mask, col] = None
                    changes.append(f"标记列'{col}'异常值 {n_outliers} 个为 NULL")

                elif action == "deduplicate":
                    n = df.duplicated().sum()
                    if n > 0:
                        df = df.drop_duplicates()
                        changes.append(f"删除重复行 {n} 条")

                elif action == "trim_strings":
                    count = 0
                    for c in df.select_dtypes(include=["object"]).columns:
                        old = df[c].astype(str)
                        new = old.str.strip()
                        changed = (old != new).sum()
                        if changed > 0:
                            df[c] = new
                            count += changed
                    changes.append(f"去除 {count} 个文本值的前后空格")

                elif action == "fill_nulls" and col and col in df.columns:
                    strategy = params.get("strategy", "mean")
                    null_count = df[col].isnull().sum()
                    if null_count > 0:
                        if strategy == "drop":
                            df = df.dropna(subset=[col])
                            changes.append(f"删除列'{col}'空值所在行 {null_count} 行")
                        elif strategy == "median" and pd.api.types.is_numeric_dtype(df[col]):
                            df[col] = df[col].fillna(df[col].median())
                            changes.append(f"用中位数填充列'{col}'")
                        elif strategy == "mode":
                            m = df[col].mode()
                            df[col] = df[col].fillna(m[0] if len(m) > 0 else "未知")
                            changes.append(f"用众数填充列'{col}'")
                        else:  # mean
                            if pd.api.types.is_numeric_dtype(df[col]):
                                df[col] = df[col].fillna(df[col].mean())
                                changes.append(f"用均值填充列'{col}'")
                            else:
                                m = df[col].mode()
                                df[col] = df[col].fillna(m[0] if len(m) > 0 else "未知")
                                changes.append(f"用众数填充列'{col}'")
                else:
                    changes.append(f"跳过未知操作: {action}")
            except Exception as e:
                changes.append(f"操作 '{action}' 失败: {str(e)[:80]}")

        # Write cleaned data back to DuckDB
        mgr = DuckDBManager(self.db_path)
        mgr.overwrite_table(df, self.table_name)

        return CleanResult(
            rows_before=rows_before,
            rows_after=len(df),
            changes=changes,
            can_undo=True,
        )

    def execute(self, actions: list[str], fill_strategy: str = "mean") -> CleanResult:
        df = self._get_df()
        self._backup_df = df.copy()
        rows_before = len(df)
        changes = []

        if "deduplicate" in actions:
            n = df.duplicated().sum()
            if n > 0:
                df = df.drop_duplicates()
                changes.append(f"删除重复行 {n} 条")

        if "trim_whitespace" in actions:
            for col in df.select_dtypes(include=["object"]).columns:
                df[col] = df[col].astype(str).str.strip()
            changes.append("去除文本前后空格")

        if "fill_null" in actions:
            for col in df.columns:
                if df[col].isnull().sum() > 0:
                    if fill_strategy == "drop":
                        df = df.dropna(subset=[col])
                        changes.append(f"删除列'{col}'空值所在行")
                    elif pd.api.types.is_numeric_dtype(df[col]):
                        val = df[col].mean() if fill_strategy == "mean" else df[col].median()
                        df[col] = df[col].fillna(val)
                        changes.append(f"用{fill_strategy}填充列'{col}'")
                    else:
                        mode_val = df[col].mode()
                        fill_val = mode_val[0] if len(mode_val) > 0 else "未知"
                        df[col] = df[col].fillna(fill_val)
                        changes.append(f"用众数填充列'{col}'")

        if "fix_types" in actions:
            for col in df.select_dtypes(include=["object"]).columns:
                try:
                    df[col] = pd.to_datetime(df[col])
                    changes.append(f"列'{col}'转换为日期类型")
                except (ValueError, TypeError):
                    converted = pd.to_numeric(df[col], errors="coerce")
                    if converted.notna().sum() > len(df) * 0.8:
                        df[col] = converted
                        changes.append(f"列'{col}'转换为数字类型")

        if "remove_outliers" in actions:
            for col in df.select_dtypes(include=[np.number]).columns:
                q1, q3 = df[col].quantile(0.25), df[col].quantile(0.75)
                iqr = q3 - q1
                lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
                n = ((df[col] < lower) | (df[col] > upper)).sum()
                if n > 0:
                    df = df[(df[col] >= lower) & (df[col] <= upper)]
                    changes.append(f"移除列'{col}'异常值 {n} 条")

        mgr = DuckDBManager(self.db_path)
        mgr.overwrite_table(df, self.table_name)
        return CleanResult(
            rows_before=rows_before,
            rows_after=len(df),
            changes=changes,
            can_undo=True,
        )

    def undo(self) -> bool:
        if self._backup_df is None:
            return False
        mgr = DuckDBManager(self.db_path)
        mgr.overwrite_table(self._backup_df, self.table_name)
        self._backup_df = None
        return True
