import pathlib

script_directory = pathlib.Path(__file__).resolve().parent
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
class ParadoxHelper:
    @staticmethod
    def parse_file(filepath):
        """Parse a Paradox script file and return the tree structure."""
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        parser = ParadoxParser(content)
        return parser.parse()

    @staticmethod
    def dict_to_paradox(tree, indent_char='\t'):
        """Convert a parsed tree structure back to Paradox script format."""
        writer = ParadoxWriter(indent_char=indent_char)
        return writer.write(tree)

    @staticmethod
    def get_root(tree):
        # this is the only key in the dict
        return next(iter(tree))

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
                # first write a paragraph comment
                # saying this file is autogenerated 
                # and should not be edited directly
                f.write("# This file is autogenerated by always_run.py\n")
                f.write("# Do not edit this file directly\n\n")
                f.write(paradox_text)


from functools import wraps

###################
# BASE HANDLER    #
###################
def handler(folder_path, filename):
    """Decorator to register a handler method and its output configuration.
    
    Args:
        folder_path: Path object or lambda that takes commons and returns path
        filename: Name of the output file
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self):
            # Call the actual handler method
            content = func(self)
            
            # Resolve folder path (could be a lambda for dynamic paths)
            folder = folder_path(commons) if callable(folder_path) else folder_path
            
            # Return the triple expected by write_handled_files
            return [folder, content, filename]
        
        # Store metadata for registration
        if not hasattr(func, '_is_handler'):
            func._is_handler = True
            func._wrapper = wrapper
            func._folder_path = folder_path
            func._filename = filename
        
        return func
    return decorator
class HandlerMeta(type):
    """Metaclass to collect all handler methods and track output files globally."""
    
    # Class-level registry to track all output files across ALL handler classes
    _global_file_registry = {}
    
    def __new__(mcs, name, bases, namespace):
        cls = super().__new__(mcs, name, bases, namespace)
        
        # Collect all methods marked as handlers
        handlers = []
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            if hasattr(attr, '_is_handler') and hasattr(attr, '_wrapper'):
                handlers.append(attr._wrapper)
                
                # Register this output file globally
                folder_path = attr._folder_path
                filename = attr._filename
                
                # Create a unique key for this file
                # We'll resolve the path during class creation if possible
                if callable(folder_path):
                    # For lambdas, we can't resolve yet, use a placeholder
                    file_key = f"<dynamic>/{filename}"
                else:
                    file_key = str(Path(folder_path) / filename)
                
                # Check for duplicates
                if file_key in mcs._global_file_registry:
                    previous_class, previous_method = mcs._global_file_registry[file_key]
                    warnings.warn(
                        f"\n⚠️  DUPLICATE OUTPUT FILE DETECTED ⚠️\n"
                        f"File: {filename}\n"
                        f"Folder: {folder_path}\n"
                        f"First defined in: {previous_class}.{previous_method}()\n"
                        f"Also defined in: {name}.{attr_name}()\n"
                        f"The second handler will OVERWRITE the first!\n",
                        UserWarning,
                        stacklevel=2
                    )
                else:
                    # Register this file
                    mcs._global_file_registry[file_key] = (name, attr_name)
        
        cls.handlers = handlers
        return cls
class BaseHandler(metaclass=HandlerMeta):
    """Base class for all handlers with automatic handler registration."""
    
    def __init__(self, files):
        self.parse_and_update(files)
    
    def parse_and_update(self, files):
        self.trees = [ParadoxHelper.parse_file(file) for file in files]
        
        # Collect all handler outputs
        outputs = []
        for handler_wrapper in self.handlers:
            result = handler_wrapper(self)
            if result:
                outputs.append(result)
        
        # Write all files
        ParadoxHelper.write_handled_files(*outputs)



###################
# TYPE HANDLERS   #
###################
class CivInstHandler(BaseHandler):
    
    @handler(lambda c: c / "script_values", "CISO_values.txt")
    def handle_values(self):
        trees = self.trees
        values_file = {}
        
        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            me_weights = ParadoxHelper.get_script_block(tree, "measure_weights")
            values_file[f"{root}_me_weights"] = me_weights
            values_file[f"{root}_social_impact"] = ParadoxParser("""
                value = 0
                if = {
                    limit = {
                        has_variable = <<root>>_social_impact
                    }
                    value = var:<<root>>_social_impact
                }
            """.replace("<<root>>", root)).parse()
            values_file[f"{root}_avg_sqrt_weight"] = ParadoxParser("""
                value = 0
                every_in_global_list = {
                    variable = ciso_society_measures
                    save_temporary_scope_as = measure
                    prev = {
                        add = {
                            value = ciso_<<root>>_me_weights
                            if = {
                                limit = {
                                    ciso_<<root>>_me_weights > 0
                                }
                                pow = 0.5
                            }
                        }
                    }
                }
                divide = {
                    value = 0
                    every_in_global_list = {
                        variable = ciso_society_measures
                        add = 1
                    }
                    min = 1
                }
            """.replace("<<root>>", root)).parse()
            values_file[f"{root}_num_measures"] = ParadoxParser("""
                value = 0
                every_in_global_list = {
                    variable = ciso_society_measures
                    save_temporary_scope_as = measure
                    prev = {
                        add = {
                            value = 0
                            if = {
                                limit = {
                                    ciso_<<root>>_me_weights > 0
                                }
                                value = 1
                            }
                        }
                    }
                }
            """.replace("<<root>>", root)).parse()
        
        return values_file

    @handler(lambda c: c / "institutions", "CISO_civinsts.txt")
    def handle_institution_icon(self):
        trees = self.trees
        institution_icon_file = {}
        
        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            icon = tree[root].get("icon", None)
            if icon:
                institution_icon_file[f"{root}_icon"] = [{
                    "icon": f"\"{icon}\""
                }]

        return institution_icon_file

    @handler(lambda c: c / "scripted_effects", "CISO_process.txt")
    def handle_process(self):
        trees = self.trees
        process_file_monthly = []

        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            process_file_monthly.append({
                "ciso_civsoc_process_tooling_handle_creation": [
                    {"ci": root }
                ]
            })

        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            process_file_monthly.append({
                "ciso_calculate_allocation": [ { "ci": root } ]
            })

        return {
            "ciso_civsoc_process_monthly": [
                {"ciso_reset_all_measures_ci_invest": "yes"}
            ] + process_file_monthly
        }

    @handler(lambda c: c / "scripted_effects", "CISO_setup.txt")
    def handle_setup(self):
        trees = self.trees
        init_global = []
        
        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            init_global.append({
                "add_to_global_variable_list": [
                    {"name": "ciso_civil_institutions" },
                    {"target": f"flag:{root}"}
                ]
            })

        return {"ciso_init_civsoc_global": init_global}

    @handler(lambda c: c / "scripted_guis", "CISO_sguis.txt")
    def handle_sgui(self):
        trees = self.trees
        sgui_file = {}
        
        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            visible = ParadoxHelper.get_script_block(tree, "visible")
            
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

    @handler(lambda c: c / "scripted_triggers", "CISO_triggers.txt")
    def handle_triggers(self):
        trees = self.trees
        triggers_file = {}
        
        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            possible = ParadoxHelper.get_script_block(tree, "possible")
            visible = ParadoxHelper.get_script_block(tree, "visible")

            possible.extend(visible)

            triggers_file[f"{root}_creation_trigger"] = possible
        
        return triggers_file
class MeasureHandler(BaseHandler):

    @handler(lambda c: c / "scripted_effects", "CISO_measures_magic_utils.txt")
    def handle_magic(self):
        trees = self.trees
        magic_file = []

        with open(script_directory / "repetitemplate" / "repetitemplate-s1.txt") as f:
            magic_file.append(ParadoxParser(f.read()).parse())

        with open(script_directory / "repetitemplate" / "repetitemplate-p1.txt") as f:
            p1 = f.read()
        with open(script_directory / "repetitemplate" / "repetitemplate-p2.txt") as f:
            p2 = f.read()
            
        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            magic_file.append(ParadoxParser(p1.replace("<<root>>", root)).parse())
        
        with open(script_directory / "repetitemplate" / "repetitemplate-s1.txt") as f:
            magic_file.append(ParadoxParser(f.read()).parse())
        
        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            magic_file.append(ParadoxParser(p2.replace("<<root>>", root)).parse())

        return {"ciso_do_every_measure_with_ci": magic_file}

    @handler(lambda c: c / "institutions", "CISO_measures.txt")
    def handle_institution_icon(self):
        trees = self.trees
        institution_icon_file = {}
        
        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            icon = tree[root].get("icon", None)
            if icon:
                institution_icon_file[f"{root}_icon"] = [{
                    "icon": f"\"{icon}\""
                }]

        return institution_icon_file

    @handler(lambda c: c / "scripted_effects", "CISO_setup_measures.txt")
    def handle_setup(self):
        trees = self.trees
        init_global = []
        
        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            init_global.append({
                "add_to_global_variable_list": [
                    {"name": "ciso_society_measures" },
                    {"target": f"flag:{root}"}
                ]
            })

        return {"ciso_init_measures_global": init_global}

    @handler(lambda c: c / "scripted_effects", "CISO_measure_utils.txt")
    def handle_utils(self):
        trees = self.trees
        utils = []
        
        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            utils.append({
                "set_variable": [
                    {"name": f"ciso_{root}_ci_investment_var" },
                    {"value": f"0"}
                ]
            })

        return {"ciso_reset_all_measure_ci_invest": utils}

    @handler(lambda c: c / "script_values", "CISO_measure_values.txt")
    def handle_script_value(self):
        trees = self.trees
        script_value_file = {}
        avg_alr_invested = [{"value": "0"}]
        
        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            script_value_file[f"{root}_investment"] = [{
                "if": [
                    {
                        "limit": [
                            {"has_variable": f"{root}_investment_var"}
                        ]
                    },
                    {
                        "value": f"var:{root}_investment_var"
                    }
                ],
            },
            {
                "else": [
                    {
                        "value": "0"
                    }
                ]
            }]

        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            avg_alr_invested.append({
                "add": f"{root}_investment"
            })

        avg_alr_invested.append({
            "divide": {
                "value": len(trees)
            }
        })

        script_value_file["ciso_avg_already_allocated"] = avg_alr_invested
        return script_value_file

    @handler(lambda c: c / "scripted_guis", "CISO_sguis_measures.txt")
    def handle_sgui(self):
        trees = self.trees
        sgui_file = {}
        
        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            visible = ParadoxHelper.get_script_block(tree, "visible")
            
            sgui_file[f"{root}_conditions_effect"] = [
                {"scope": "state"},
                {
                    "is_shown": [{
                        "NOT": {
                            "is_target_in_variable_list": [
                                {"name": "ciso_society_measures"},
                                {"target": f"flag:{root}"}
                            ]
                        }
                    }] + visible
                },
                {
                    "effect": [{
                        "if": [
                            {"limit": [{
                                "NOT": [
                                    {"has_variable": f"{root}_investment_var"}
                                ]
                            }]},
                            {
                                "set_variable": [
                                    {"name": f"{root}_investment_var"},
                                    {"value": "0"}
                                ]
                            }
                        ]
                    },
                    {
                        "change_variable": [
                            {"name": f"{root}_investment_var"},
                            {"add": "50"}
                        ]
                    },
                    {
                        "add_to_variable_list": [
                            {"name": "ciso_society_measures"},
                            {"target": f"flag:{root}"}
                        ]
                    }
                    ]
                }
            ]
            sgui_file[f"{root}_increment_effect"] = self.generate_incrdecr_effect(
                root, increment="add", value="25"
            )
            sgui_file[f"{root}_decrement_effect"] = self.generate_incrdecr_effect(
                root, increment="subtract", value="25"
            )
            sgui_file[f"{root}_increment_alot_effect"] = self.generate_incrdecr_effect(
                root, increment="add", value="50"
            )
            sgui_file[f"{root}_decrement_alot_effect"] = self.generate_incrdecr_effect(
                root, increment="subtract", value="50"
            )
            sgui_file[f"{root}_increment_very_alot_effect"] = self.generate_incrdecr_effect(
                root, increment="add", value="100"
            )
            sgui_file[f"{root}_decrement_very_alot_effect"] = self.generate_incrdecr_effect(
                root, increment="subtract", value="100"
            )
            sgui_file[f"{root}_increment_alittle_effect"] = self.generate_incrdecr_effect(
                root, increment="add", value="10"
            )
            sgui_file[f"{root}_decrement_alittle_effect"] = self.generate_incrdecr_effect(
                root, increment="subtract", value="10"
            )
        
        return sgui_file

    @staticmethod
    def generate_incrdecr_effect(root, increment="add", value="100"):
        return [
            {"scope": "state"},
            {"effect": [
                {
                    "change_variable": [
                        {"name": f"{root}_investment_var"},
                        {increment: value}
                    ]
                },
                {
                    "clamp_variable": [
                        {"name": f"{root}_investment_var"},
                        {"min": "0"},
                        {"max": "100000000"}
                    ]
                }
            ]}
        ]
class Needs(BaseHandler):
    
    @handler(lambda c: c / "institutions", "CISO_needs.txt")
    def handle_institution_icon(self):
        trees = self.trees
        institution_icon_file = {}
        
        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            icon = tree[root].get("icon", None)
            if icon:
                institution_icon_file[f"{root}_icon"] = [{
                    "icon": f"\"{icon}\""
                }]

        return institution_icon_file

    @handler(lambda c: c / "scripted_effects", "CISO_setup_needs.txt")
    def handle_setup(self):
        trees = self.trees
        init_global = []
        
        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            init_global.append({
                "add_to_global_variable_list": [
                    {"name": "ciso_needs" },
                    {"target": f"flag:{root}"}
                ]
            })

        return {"ciso_init_needs_global": init_global}

    @handler(lambda c: c / "scripted_effects", "CISO_process_needs.txt")
    def handle_process(self):
        trees = self.trees
        process_file_monthly = []

        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            minv = tree[root].get("minimum", "999")
            process_file_monthly.append({
                "ciso_need_process_tooling_handle_needs": [
                    {"ne": root },
                    {"min":  minv }
                ]
            })

        return {
            "ciso_needs_process_monthly": process_file_monthly
        }

    @handler(lambda c: c / "script_values", "CISO_needs_values.txt")
    def handle_script_value(self):
        trees = self.trees
        script_value_file = {}
        
        for tree in trees:
            required_value = ParadoxHelper.get_script_block(tree, "required_value")
            root = ParadoxHelper.get_root(tree)
            script_value_file[f"{root}_fp"] = [{
                "value": f"modifier:state_{root}_fp"
            }]
            script_value_file[f"{root}_rfp"] = required_value

        return script_value_file

    @handler(lambda c: c / "scripted_guis", "CISO_sguis_needs.txt")
    def handle_sgui(self):
        trees = self.trees
        sgui_file = {}
        
        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            visible = ParadoxHelper.get_script_block(tree, "visible")
            
            sgui_file[f"{root}_conditions_effect"] = [
                {"scope": "state"},
                {
                    "is_shown": [{
                        "NOT": {
                            "is_target_in_variable_list": [
                                {"name": "ciso_needs"},
                                {"target": f"flag:{root}"}
                            ]
                        }
                    }] + visible
                }
            ]
        
        return sgui_file

    @handler(lambda c: c / "modifier_type_definitions", "CISO_needs_modtypes.txt")
    def handle_modtype(self):
        trees = self.trees
        modtype_file = {}

        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            modtype_file[f"state_{root}_fp"] = [
                {"decimals": "0"},
                {"color": "good"}
            ]

        return modtype_file



if __name__ == "__main__":
    ciso_common = script_directory / "ciso_common"
    civinsts = ciso_common / "civil_institutions"
    files = list(civinsts.glob("*.txt"))
    CivInstHandler(files)

    measures = ciso_common / "measures"
    measure_files = list(measures.glob("*.txt"))
    MeasureHandler(measure_files)

    needs = ciso_common / "needs"
    need_files = list(needs.glob("*.txt"))
    Needs(need_files)