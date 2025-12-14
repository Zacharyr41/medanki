import re


class TagBuilder:
    def sanitize(self, text: str) -> str:
        result = re.sub(r'[\'\":]', '', text)
        result = re.sub(r'\s+', '_', result)
        return result

    def build_mcat_tag(self, path: str) -> str:
        parts = [p.strip() for p in path.split('>')]
        sanitized = [self.sanitize(p) for p in parts]
        return "#MCAT::" + "::".join(sanitized)

    def build_usmle_tag(self, step: str, *categories: str) -> str:
        parts = [self.sanitize(c) for c in categories]
        return f"#AK_{step}_v12::" + "::".join(parts)

    def build_source_tag(self, source_name: str) -> str:
        sanitized = self.sanitize(source_name)
        return f"#Source::MedAnki::{sanitized}"

    def build_hierarchical_tag(self, parts: list[str]) -> str:
        if not parts:
            return ""
        return "#" + "::".join(parts)
