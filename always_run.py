import pathlib

script_directory = pathlib.Path(__file__).resolve().parent
civinsts = script_directory / "civil_institutions"
commons = script_directory / "civil-society" / "common"


###################
# PARADOX PARSER  #
###################
class ParadoxParser:
    """Recursive parser for Paradox Interactive game script files."""
    
    def __init__(self, text):
        self.text = text
        self.pos = 0
        self.length = len(text)
    
    def parse(self):
        """Parse the entire document and return the tree structure."""
        return self.parse_object()
    
    def current_char(self):
        """Get current character without advancing position."""
        if self.pos < self.length:
            return self.text[self.pos]
        return None
    
    def peek_char(self, offset=1):
        """Peek ahead at character."""
        if self.pos + offset < self.length:
            return self.text[self.pos + offset]
        return None
    
    def advance(self):
        """Move to next character."""
        self.pos += 1
    
    def skip_whitespace(self):
        """Skip whitespace and comments."""
        while self.pos < self.length:
            char = self.current_char()
            
            # Skip whitespace
            if char in ' \t\n\r':
                self.advance()
            # Skip line comments
            elif char == '#':
                while self.current_char() and self.current_char() != '\n':
                    self.advance()
            else:
                break
    
    def parse_string(self):
        """Parse a quoted string."""
        quote_char = self.current_char()
        self.advance()  # Skip opening quote
        
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
            self.advance()  # Skip closing quote
        
        return ''.join(result)
    
    def parse_identifier(self):
        """Parse an unquoted identifier or value."""
        result = []
        
        while self.current_char():
            char = self.current_char()
            
            # Stop at structural characters or whitespace
            if char in '{}=<>#\n\r\t ':
                break
            
            result.append(char)
            self.advance()
        
        return ''.join(result)
    
    def parse_value(self):
        """Parse a single value (string, number, identifier, or object)."""
        self.skip_whitespace()
        
        char = self.current_char()
        
        if char is None:
            return None
        
        # Quoted string
        if char in '"\'':
            return self.parse_string()
        
        # Nested object
        if char == '{':
            return self.parse_object()
        
        # Unquoted identifier or number
        return self.parse_identifier()
    
    def parse_object(self):
        """Parse an object (dictionary or list)."""
        self.skip_whitespace()
        
        items = []  # Track all items to detect structure
        
        # Handle opening brace if present
        if self.current_char() == '{':
            self.advance()
        
        while self.current_char():
            self.skip_whitespace()
            
            # Check for closing brace
            if self.current_char() == '}':
                self.advance()
                break
            
            # End of input
            if self.current_char() is None:
                break
            
            # Parse key
            key = self.parse_value()
            
            if key is None:
                break
            
            self.skip_whitespace()
            
            # Check for assignment operators
            char = self.current_char()
            
            if char in '=<>':
                # Handle operators like =, ==, <=, >=, etc.
                operator = char
                self.advance()
                
                # Check for compound operators
                if self.current_char() in '=<>':
                    operator += self.current_char()
                    self.advance()
                
                self.skip_whitespace()
                
                # Parse the value after the operator
                value = self.parse_value()
                
                # Store as key-value pair
                items.append({'key': key, 'value': value, 'has_operator': True})
            
            else:
                # No operator - just a standalone key
                items.append({'key': key, 'value': True, 'has_operator': False})
        
        # Now decide structure based on items
        if not items:
            return {}
        
        # Check if all items have operators (key=value pairs)
        all_have_operators = all(item['has_operator'] for item in items)
        none_have_operators = all(not item['has_operator'] for item in items)
        
        # Get all unique keys
        keys = [item['key'] for item in items]
        unique_keys = set(keys)
        has_duplicates = len(keys) != len(unique_keys)
        
        if all_have_operators and not has_duplicates:
            # All key=value pairs with unique keys -> simple dict
            result = {}
            for item in items:
                result[item['key']] = item['value']
            return result
        
        elif all_have_operators and has_duplicates:
            # Multiple key=value pairs, some keys repeated -> list of dicts
            result = []
            for item in items:
                result.append({item['key']: item['value']})
            return result
        
        elif none_have_operators:
            # All standalone keys -> dict with True values
            result = {}
            for item in items:
                if item['key'] in result:
                    # Convert to list for duplicates
                    if not isinstance(result[item['key']], list):
                        result[item['key']] = [result[item['key']]]
                    result[item['key']].append(True)
                else:
                    result[item['key']] = True
            return result
        
        else:
            # Mixed: some with operators, some without
            # Keep as dict but handle duplicates
            result = {}
            for item in items:
                if item['key'] in result:
                    # Convert to list if duplicate key
                    if not isinstance(result[item['key']], list):
                        result[item['key']] = [result[item['key']]]
                    result[item['key']].append(item['value'])
                else:
                    result[item['key']] = item['value']
            return result
class ParadoxWriter:
    """Converts parsed tree structure back to Paradox script format."""
    
    def __init__(self, indent_char='\t', indent_level=0):
        self.indent_char = indent_char
        self.indent_level = indent_level
    
    def write(self, tree):
        """Convert tree structure to Paradox script text."""
        # Check if tree is a dict at root level
        if isinstance(tree, dict):
            return self.write_dict(tree, self.indent_level, is_root=True)
        return self.write_value(tree, self.indent_level)
    
    def get_indent(self, level):
        """Get indentation string for given level."""
        return self.indent_char * level
    
    def needs_quotes(self, value):
        """Check if a value needs to be quoted."""
        if not isinstance(value, str):
            return False
        
        # Already has quotes
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            return False
        
        # Check for special characters that require quoting
        special_chars = ' \t\n\r{}=<>#'
        return any(char in value for char in special_chars)
    
    def format_value(self, value):
        """Format a single value for output."""
        if value is True:
            return ""  # Boolean True means just the key with no value
        elif value is None or value is False:
            return ""
        elif isinstance(value, str):
            if self.needs_quotes(value):
                # Escape quotes inside the string
                escaped = value.replace('"', '\\"')
                return f'"{escaped}"'
            return value
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, dict):
            return self.write_dict(value, self.indent_level, is_root=False)
        elif isinstance(value, list):
            return self.write_list(value, self.indent_level)
        else:
            return str(value)
    
    def write_dict(self, d, level, is_root=False):
        """Write a dictionary as a Paradox object."""
        if not d:
            return "{}"
        
        lines = []
        if not is_root:
            lines.append("{")
        
        for key, value in d.items():
            indent = self.get_indent(level + 1 if not is_root else level)
            
            # Format the key
            formatted_key = self.format_value(key) if not isinstance(key, str) or self.needs_quotes(key) else key
            
            if value is True:
                # Just the key, no value
                lines.append(f"{indent}{formatted_key}")
            elif isinstance(value, dict):
                # Nested object
                nested = self.write_dict(value, level + 1 if not is_root else level, is_root=False)
                lines.append(f"{indent}{formatted_key} = {nested}")
            elif isinstance(value, list):
                # Check if it's a list of dicts (multiple key-value pairs)
                if all(isinstance(item, dict) for item in value):
                    # List of dicts - write each dict directly without wrapping in { }
                    lines.append(f"{indent}{formatted_key} = {{")
                    for item in value:
                        # Write each dict's content directly
                        dict_lines = self.write_dict(item, level + 1 if not is_root else level, is_root=False).split('\n')
                        # Skip the outer { } and just use the content
                        for line in dict_lines[1:-1]:  # Skip first '{' and last '}'
                            lines.append(line)
                    lines.append(self.get_indent(level + 1 if not is_root else level) + "}")
                else:
                    # Regular list or mixed content
                    all_simple = all(isinstance(item, (bool, str, int, float)) or item is True for item in value)
                    
                    if all_simple and len(value) <= 3:
                        # Inline simple list
                        items = [self.format_value(item) for item in value if item is not True]
                        if items:
                            lines.append(f"{indent}{formatted_key} = {{ {' '.join(items)} }}")
                        else:
                            lines.append(f"{indent}{formatted_key} = {{}}")
                    else:
                        # Multi-line list
                        list_content = self.write_list(value, level + 1 if not is_root else level)
                        lines.append(f"{indent}{formatted_key} = {list_content}")
            else:
                # Simple key-value pair
                formatted_value = self.format_value(value)
                if formatted_value:
                    lines.append(f"{indent}{formatted_key} = {formatted_value}")
                else:
                    lines.append(f"{indent}{formatted_key}")
        
        if not is_root:
            lines.append(self.get_indent(level) + "}")
        return "\n".join(lines)
    
    def write_list(self, lst, level):
        """Write a list as a Paradox array."""
        if not lst:
            return "{}"
        
        # Check if all items are simple
        all_simple = all(isinstance(item, (bool, str, int, float)) or item is True for item in lst)
        
        if all_simple and len(lst) <= 3:
            # Inline for short simple lists
            items = [self.format_value(item) for item in lst if item is not True]
            return "{ " + " ".join(items) + " }"
        
        # Multi-line format
        lines = ["{"]
        
        for item in lst:
            indent = self.get_indent(level + 1)
            
            if isinstance(item, dict):
                nested = self.write_dict(item, level + 1, is_root=False)
                lines.append(f"{indent}{nested}")
            elif item is True:
                continue  # Skip boolean markers
            else:
                formatted = self.format_value(item)
                if formatted:
                    lines.append(f"{indent}{formatted}")
        
        lines.append(self.get_indent(level) + "}")
        return "\n".join(lines)
    
    def write_value(self, value, level):
        """Write any value type."""
        if isinstance(value, dict):
            return self.write_dict(value, level, is_root=False)
        elif isinstance(value, list):
            return self.write_list(value, level)
        else:
            return self.format_value(value)
def parse_file(filepath):
    """Parse a Paradox script file and return the tree structure."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    parser = ParadoxParser(content)
    return parser.parse()

def dict_to_paradox(tree, indent_char='\t'):
    """Convert a parsed tree structure back to Paradox script format."""
    writer = ParadoxWriter(indent_char=indent_char)
    return writer.write(tree)



def helper_get_root(tree):
    # this is the only key in the dict
    return next(iter(tree))

def helper_get_script_block(tree, block_name):
    root = helper_get_root(tree)
    block = tree[root].get(block_name, {})
    if not isinstance(block, list):
        block = [block]
    return block
    
def handle_institution_icon(trees):
    # each tree should have a name as root
    # and immediately inside it an "icon" key
    institution_icon_file = {}


    for tree in trees:
        root = helper_get_root(tree)
        icon = tree[root].get("icon", None)
        if icon:
            institution_icon_file[f"{root}_icon"] = [{
                "icon": f"\"{icon}\""
            }]

    return institution_icon_file

def handle_process(trees):
    process_file_monthly = []

    for tree in trees:
        root = helper_get_root(tree)
        process_file_monthly.append({
            "ciso_civsoc_process_tooling_handle_creation": [
                {"ci": root }
            ]
        })

    return {
        "ciso_civsoc_process_monthly": process_file_monthly
    }

def handle_setup(trees):
    init_global = []
    
    for tree in trees:
        root = helper_get_root(tree)
        init_global.append({
            "add_to_global_variable_list": [
                {"name": "ciso_civil_institutions" },
                {"target": f"flag:{root}"}
            ]
        })

    return {"ciso_init_civsoc_global": init_global}

def handle_sgui(trees):
    sgui_file = {}
    
    for tree in trees:
        root = helper_get_root(tree)
        visible = helper_get_script_block(tree, "visible")
        
        sgui_file[f"{root}_creation_trigger_sgui"] = [
            {"scope": "state"},
            {
                "is_shown": [{
                    "NOT": {
                        "is_target_in_variable_list": [
                            {"name": "ciso_civil_institutions"},
                            {"target": f"flag:{root}"}
                        ]
                    }
                }] + visible
            },
            {
                "is_valid": {
                    f"{root}_creation_trigger": "yes"
                }
            }
        ]
        
    
    return sgui_file


def handle_triggers(trees):
    triggers_file = {}
    
    for tree in trees:
        root = helper_get_root(tree)
        possible = helper_get_script_block(tree, "possible")

        triggers_file[f"{root}_creation_trigger"] = possible
    
    return triggers_file

def handle_files(files):
    trees = [parse_file(file) for file in files]

    # institutions
    institution_icon_folder = commons / "institutions"
    institution_icon_file = handle_institution_icon(trees)

    # process
    process_folder = commons / "scripted_effects"
    process_file = handle_process(trees)

    # setup
    setup_folder = commons / "scripted_effects"
    setup_file = handle_setup(trees)

    # sgui
    sgui_folder = commons / "scripted_guis"
    sgui_file = handle_sgui(trees)

    # triggers
    triggers_folder = commons / "scripted_triggers"
    triggers_file = handle_triggers(trees)

    write_handled_files(
        [institution_icon_folder, institution_icon_file, "CISO_civinsts.txt"],
        [process_folder, process_file, "CISO_process.txt"],
        [setup_folder, setup_file, "CISO_setup.txt"],
        [sgui_folder, sgui_file, "CISO_sguis.txt"],
        [triggers_folder, triggers_file, "CISO_triggers.txt"]
    )

def write_handled_files(*file_data):
    for folder, content, filename in file_data:
        folder.mkdir(parents=True, exist_ok=True)
        filepath = folder / filename
        paradox_text = dict_to_paradox(content, indent_char='\t')
        with open(filepath, 'w', encoding='utf-8') as f:
            # first write a paragraph comment
            # saying this file is autogenerated 
            # and should not be edited directly
            f.write("# This file is autogenerated by always_run.py\n")
            f.write("# Do not edit this file directly\n\n")
            f.write(paradox_text)


if __name__ == "__main__":
    files = list(civinsts.glob("*.txt"))
    handle_files(files)