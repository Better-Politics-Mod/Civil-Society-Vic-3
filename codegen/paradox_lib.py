import pathlib


class ParadoxParser:
    """Recursive parser for Paradox Interactive game script files."""

    def __init__(self, text):
        self.text = text
        self.pos = 0
        self.length = len(text)

    def parse(self):
        return self.parse_object()

    def current_char(self):
        if self.pos < self.length:
            return self.text[self.pos]
        return None

    def peek_char(self, offset=1):
        if self.pos + offset < self.length:
            return self.text[self.pos + offset]
        return None

    def advance(self):
        self.pos += 1

    def skip_whitespace(self):
        while self.pos < self.length:
            char = self.current_char()
            if char in ' \t\n\r':
                self.advance()
            elif char == '#':
                while self.current_char() and self.current_char() != '\n':
                    self.advance()
            else:
                break

    def parse_string(self):
        quote_char = self.current_char()
        self.advance()

        result = []
        while self.current_char() and self.current_char() != quote_char:
            if self.current_char() == '\\':
                self.advance()
                if self.current_char():
                    result.append(self.current_char())
                    self.advance()
            else:
                result.append(self.current_char())
                self.advance()

        if self.current_char() == quote_char:
            self.advance()

        return ''.join(result)

    def parse_identifier(self):
        result = []
        while self.current_char():
            char = self.current_char()
            if char in '{}=#\n\r\t ':
                break
            result.append(char)
            self.advance()
        return ''.join(result)

    def parse_comparison_or_value(self):
        first = self.parse_identifier()
        self.skip_whitespace()

        char = self.current_char()
        if char in '<>':
            operator = char
            self.advance()
            if self.current_char() == '=':
                operator += self.current_char()
                self.advance()
            self.skip_whitespace()
            second = self.parse_identifier()
            return f"{first}{operator}{second}"

        return first

    def parse_value(self):
        self.skip_whitespace()
        char = self.current_char()

        if char is None:
            return None
        if char in '"\'':
            return self.parse_string()
        if char == '{':
            return self.parse_object()
        return self.parse_comparison_or_value()

    def parse_object(self):
        self.skip_whitespace()
        items = []

        if self.current_char() == '{':
            self.advance()

        while self.current_char():
            self.skip_whitespace()

            if self.current_char() == '}':
                self.advance()
                break
            if self.current_char() is None:
                break

            key = self.parse_comparison_or_value()
            if key is None:
                break

            self.skip_whitespace()
            char = self.current_char()

            if char == '=':
                operator = char
                self.advance()
                if self.current_char() == '=':
                    operator += self.current_char()
                    self.advance()
                self.skip_whitespace()
                value = self.parse_value()
                items.append({'key': key, 'value': value, 'has_operator': True})
            else:
                items.append({'key': key, 'value': True, 'has_operator': False})

        if not items:
            return {}

        all_have_operators = all(item['has_operator'] for item in items)
        none_have_operators = all(not item['has_operator'] for item in items)
        keys = [item['key'] for item in items]
        has_duplicates = len(keys) != len(set(keys))

        if all_have_operators and not has_duplicates:
            return {item['key']: item['value'] for item in items}
        elif all_have_operators and has_duplicates:
            return [{item['key']: item['value']} for item in items]
        elif none_have_operators:
            result = {}
            for item in items:
                if item['key'] in result:
                    if not isinstance(result[item['key']], list):
                        result[item['key']] = [result[item['key']]]
                    result[item['key']].append(True)
                else:
                    result[item['key']] = True
            return result
        else:
            result = {}
            for item in items:
                if item['key'] in result:
                    if not isinstance(result[item['key']], list):
                        result[item['key']] = [result[item['key']]]
                    result[item['key']].append(item['value'])
                else:
                    result[item['key']] = item['value']
            return result


class ParadoxWriter:
    def __init__(self, indent_char='\t'):
        self.indent_char = indent_char

    def write(self, obj, indent_level=0):
        if obj is None:
            return ""
        if isinstance(obj, dict):
            return self._write_dict(obj, indent_level)
        elif isinstance(obj, list):
            return self._write_list(obj, indent_level)
        else:
            return self._write_value(obj)

    def _write_dict(self, d, indent_level):
        lines = []
        indent = self.indent_char * indent_level

        for key, value in d.items():
            if self._is_comparison(key):
                lines.append(f"{indent}{self._format_comparison(key)}")
                continue
            if isinstance(value, dict):
                lines.append(f"{indent}{key} = {{")
                lines.append(self._write_dict(value, indent_level + 1))
                lines.append(f"{indent}}}")
            elif isinstance(value, list):
                list_content = self._write_list(value, indent_level + 1)
                if list_content.strip():
                    lines.append(f"{indent}{key} = {{")
                    lines.append(list_content)
                    lines.append(f"{indent}}}")
            else:
                lines.append(f"{indent}{key} = {self._write_value(value)}")

        return '\n'.join(lines)

    def _write_list(self, lst, indent_level):
        lines = []
        indent = self.indent_char * indent_level

        for item in lst:
            if isinstance(item, dict):
                dict_content = self._write_dict(item, indent_level)
                if dict_content.strip():
                    lines.append(dict_content)
            elif isinstance(item, list):
                nested_content = self._write_list(item, indent_level)
                if nested_content.strip():
                    lines.append(nested_content)
            else:
                lines.append(f"{indent}{self._write_value(item)}")

        return '\n'.join(lines)

    def _write_value(self, value):
        if isinstance(value, bool):
            return "yes" if value else "no"
        elif isinstance(value, str):
            if ' ' in value or any(c in value for c in ['=', '{', '}', '#']):
                return f'"{value}"'
            return value
        elif isinstance(value, (int, float)):
            return str(value)
        else:
            return str(value)

    def _is_comparison(self, key):
        return any(op in key for op in ['>=', '<=', '!=', '>', '<', '='])

    def _format_comparison(self, key):
        for op in ['>=', '<=', '!=', '>', '<', '=']:
            if op in key:
                parts = key.split(op, 1)
                return f"{parts[0].strip()} {op} {parts[1].strip()}"
        return key


class ParadoxHelper:
    @staticmethod
    def parse_file(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return ParadoxParser(content).parse()

    @staticmethod
    def replace_leaves(tree, old_str, new_str):
        if isinstance(tree, dict):
            result = {}
            for key, value in tree.items():
                new_key = key.replace(old_str, new_str) if (isinstance(key, str) and key.strip() == old_str) else key
                result[new_key] = ParadoxHelper.replace_leaves(value, old_str, new_str)
            return result
        elif isinstance(tree, list):
            return [ParadoxHelper.replace_leaves(item, old_str, new_str) for item in tree]
        elif isinstance(tree, str):
            if tree.strip() == old_str:
                return tree.replace(old_str, new_str)
            return tree
        else:
            return tree

    @staticmethod
    def multi_replace_leaves(tree, pairs):
        for old_str, new_str in pairs:
            tree = ParadoxHelper.replace_leaves(tree, old_str, new_str)
        return tree

    @staticmethod
    def dict_to_paradox(tree, indent_char='\t'):
        writer = ParadoxWriter(indent_char=indent_char)
        return writer.write(tree)

    @staticmethod
    def get_root(tree):
        return next(iter(tree))

    @staticmethod
    def has_block(tree, block_name):
        root = ParadoxHelper.get_root(tree)
        return block_name in tree[root]

    @staticmethod
    def get_script_block(tree, block_name):
        root = ParadoxHelper.get_root(tree)
        block = tree[root].get(block_name, {})
        if not isinstance(block, list):
            block = [block]
        return block

    @staticmethod
    def write_handled_files(*file_data):
        for folder, content, filename in file_data:
            folder.mkdir(parents=True, exist_ok=True)
            filepath = folder / filename
            paradox_text = ParadoxHelper.dict_to_paradox(content, indent_char='\t')
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("# This file is autogenerated by always_run.py\n")
                f.write("# Do not edit this file directly\n\n")
                f.write(paradox_text)


class ParadoxLocWriter:
    def write(self, obj, language='english'):
        lines = [f"l_{language}:"]
        self._write_obj(obj, lines, prefix="")
        return '\n'.join(lines) + '\n'

    def _write_obj(self, obj, lines, prefix):
        if isinstance(obj, dict):
            for key, value in obj.items():
                full_key = f"{prefix}_{key}" if prefix else key
                self._write_obj(value, lines, full_key)
        elif isinstance(obj, list):
            for item in obj:
                self._write_obj(item, lines, prefix)
        else:
            value_str = str(obj) if not isinstance(obj, bool) else ("yes" if obj else "no")
            lines.append(f' {prefix}:0 "{value_str}"')
