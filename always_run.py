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
            if char in '{}=#\n\r\t ':
                break
            
            result.append(char)
            self.advance()
        
        return ''.join(result)
    
    def parse_comparison_or_value(self):
        """Parse a comparison expression (a > b) or a simple value."""
        # Save position in case we need to backtrack
        start_pos = self.pos
        
        # Parse first part
        first = self.parse_identifier()
        
        self.skip_whitespace()
        
        # Check if followed by comparison operator
        char = self.current_char()
        if char in '<>':
            operator = char
            self.advance()
            
            # Check for compound operators (<=, >=, etc.)
            if self.current_char() == '=':
                operator += self.current_char()
                self.advance()
            
            self.skip_whitespace()
            
            # Parse right side
            second = self.parse_identifier()
            
            # Return as a comparison expression string
            return f"{first}{operator}{second}"
        
        # Not a comparison, just return the first part
        return first
    
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
        
        # Unquoted identifier, number, or comparison expression
        return self.parse_comparison_or_value()
    
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
            
            # Parse key (might be a comparison expression)
            key = self.parse_comparison_or_value()
            
            if key is None:
                break
            
            self.skip_whitespace()
            
            # Check for assignment operator (only =)
            char = self.current_char()
            
            if char == '=':
                operator = char
                self.advance()
                
                # Check for compound operators (==)
                if self.current_char() == '=':
                    operator += self.current_char()
                    self.advance()
                
                self.skip_whitespace()
                
                # Parse the value after the operator
                value = self.parse_value()
                
                # Store as key-value pair
                items.append({'key': key, 'value': value, 'has_operator': True})
            
            else:
                # No operator - just a standalone key (or comparison expression)
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
    def __init__(self, indent_char='\t'):
        self.indent_char = indent_char
    
    def write(self, obj, indent_level=0):
        """
        Convert a JSON-like object to Paradox script format.
        
        Args:
            obj: The object to convert (dict, list, or primitive)
            indent_level: Current indentation level
            
        Returns:
            String in Paradox script format
        """
        if obj is None:
            return ""
        
        if isinstance(obj, dict):
            return self._write_dict(obj, indent_level)
        elif isinstance(obj, list):
            return self._write_list(obj, indent_level)
        else:
            return self._write_value(obj)
    
    def _write_dict(self, d, indent_level):
        """Write a dictionary as Paradox script."""
        lines = []
        indent = self.indent_char * indent_level
        
        for key, value in d.items():
            # Handle comparison operators - write them without '=' but with spaces around operators
            if self._is_comparison(key):
                formatted_key = self._format_comparison(key)
                lines.append(f"{indent}{formatted_key}")
                continue
            if isinstance(value, dict):
                # For nested dicts, write key = { ... }
                lines.append(f"{indent}{key} = {{")
                lines.append(self._write_dict(value, indent_level + 1))
                lines.append(f"{indent}}}")
            elif isinstance(value, list):
                # For lists, write key = { ... } (without extra braces)
                list_content = self._write_list(value, indent_level + 1)
                if list_content.strip():  # Only write if list has content
                    lines.append(f"{indent}{key} = {{")
                    lines.append(list_content)
                    lines.append(f"{indent}}}")
            else:
                # For simple values, write key = value
                lines.append(f"{indent}{key} = {self._write_value(value)}")
        
        return '\n'.join(lines)
    
    def _write_list(self, lst, indent_level):
        """Write a list as Paradox script."""
        lines = []
        indent = self.indent_char * indent_level
        
        for item in lst:
            if isinstance(item, dict):
                # For dict items in a list, write the dict content directly (no extra braces)
                dict_content = self._write_dict(item, indent_level)
                if dict_content.strip():
                    lines.append(dict_content)
            elif isinstance(item, list):
                # Nested lists are flattened - just process their contents
                nested_content = self._write_list(item, indent_level)
                if nested_content.strip():
                    lines.append(nested_content)
            else:
                # For simple values in a list
                lines.append(f"{indent}{self._write_value(item)}")
        
        return '\n'.join(lines)
    
    def _write_value(self, value):
        """Convert a value to its Paradox script representation."""
        if isinstance(value, bool):
            return "yes" if value else "no"
        elif isinstance(value, str):
            # Check if string needs quotes (contains spaces or special chars)
            if ' ' in value or any(c in value for c in ['=', '{', '}', '#']):
                return f'"{value}"'
            return value
        elif isinstance(value, (int, float)):
            return str(value)
        else:
            return str(value)
    
    def _is_comparison(self, key):
        """Check if a key is a comparison expression."""
        comparison_ops = ['>=', '<=', '!=', '>', '<', '=']
        return any(op in key for op in comparison_ops)
    
    def _format_comparison(self, key):
        """Add spaces around comparison operators."""
        # Order matters - check longer operators first
        comparison_ops = ['>=', '<=', '!=', '>', '<', '=']
        for op in comparison_ops:
            if op in key:
                parts = key.split(op, 1)
                return f"{parts[0].strip()} {op} {parts[1].strip()}"
        return key


class ParadoxHelper:
    @staticmethod
    def parse_file(filepath):
        """Parse a Paradox script file and return the tree structure."""
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        parser = ParadoxParser(content)
        return parser.parse()

    @staticmethod
    def replace_leaves(tree, old_str, new_str):
        """
        Replace all occurrences of old_str with new_str in all leaf values of the tree.
        
        Args:
            tree: The parsed tree structure (dict, list, or primitive)
            old_str: String to search for
            new_str: String to replace with
            
        Returns:
            A new tree with replacements applied
        """
        if isinstance(tree, dict):
            result = {}
            for key, value in tree.items():
                # Also check if the key itself contains the old_str
                new_key = key.replace(old_str, new_str) if (isinstance(key, str) and key.strip() == old_str) else key
                result[new_key] = ParadoxHelper.replace_leaves(value, old_str, new_str)
            return result
        elif isinstance(tree, list):
            return [ParadoxHelper.replace_leaves(item, old_str, new_str) for item in tree]
        elif isinstance(tree, str):
            if tree.strip() == old_str:
                return tree.replace(old_str, new_str)
            else:
                return tree
        else:
            # For non-string primitives (int, float, bool, None), return as-is
            return tree
    

    @staticmethod
    def multi_replace_leaves(tree, pairs):
        """
        Replace multiple string pairs in all leaf values of the tree.
        
        Args:
            tree: The parsed tree structure (dict, list, or primitive)
            pairs: List of (old_str, new_str) tuples
        Returns:
            A new tree with replacements applied
        """
        for old_str, new_str in pairs:
            tree = ParadoxHelper.replace_leaves(tree, old_str, new_str)
        return tree

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
            ms_weights = ParadoxHelper.get_script_block(tree, "measure_weights")
            stance = ParadoxHelper.get_script_block(tree, "stance")
            social_impact = ParadoxHelper.multi_replace_leaves(
                ParadoxHelper.get_script_block(tree, "social_impact"),
                [
                    ("organization", f"{root}_organization"),
                    ("size", f"{root}_population"),
                ]
            )

            values_file[f"{root}_social_impact_base"] = social_impact
            values_file[f"{root}_stance"] = stance
            values_file[f"{root}_population"] = ParadoxParser("""
                value = 0
                if = {
                    limit = {
                        has_variable = <<root>>_population
                    }
                    add = var:<<root>>_population
                }
            """.replace("<<root>>", root)).parse()
            values_file[f"{root}_organization"] = ParadoxParser("""
                value = 0
                if = {
                    limit = {
                        has_variable = <<root>>_organization
                    }
                    add = var:<<root>>_organization
                }
            """.replace("<<root>>", root)).parse()

            values_file[f"{root}_org_trend"] = [
                {"value": "0"},
                {"substract": "-0.1"},
                {"add": [
                    {"value": "ciso_total_unfulfilled_needs"},
                    {"divide": 10},
                ]},
                {"if": [
                    {"limit": [
                        {"ciso_ci_is_radical": { "ci": root }}
                    ]},
                    {
                        "add": "ciso_total_ci_attraction_num_out"
                    }
                ]},
                {"multiply": [
                    {"value": f"{root}_population" },
                    { "divide": "state_population" }
                ]},
                # higher org makes gains & losses slower
                {"multiply": [
                    {"value": 100},
                    {"subtract": f"{root}_organization" },
                    {"divide": 100},
                    {"min": 0.02}
                ]},
                {"multiply": 5}
            ]

            if ParadoxHelper.has_block(tree, "organization_trend_mult"):
                values_file[f"{root}_org_trend"].append({
                    "multiply": ParadoxHelper.get_script_block(tree, "organization_trend_mult")
                })

            values_file[f"{root}_ms_weights"] = [{
                "if": [
                {
                    "limit": [{
                        "NOT": [{
                            "exists": "scope:measure"
                        }]
                    }]
                },
                {
                    "scope:ms": [{
                        "save_temporary_scope_as": "measure"
                    }]
                }
                ]
            }] + ms_weights
            values_file[f"{root}_social_impact"] = ParadoxParser("""
                value = 100
                if = {
                    limit = {
                        has_variable = <<root>>_social_impact
                    }
                    value = var:<<root>>_social_impact
                    min = 100
                }
            """.replace("<<root>>", root)).parse()
            values_file[f"{root}_avg_sqrt_weight"] = ParadoxParser("""
                value = 0
                every_in_global_list = {
                    variable = ciso_society_measures
                    save_temporary_scope_as = measure
                    prev = {
                        add = {
                            value = <<root>>_ms_weights
                            if = {
                                limit = {
                                    <<root>>_ms_weights > 0
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
                                    <<root>>_ms_weights > 0
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
        process_file_size = []

        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            process_file_size.append({
                "if": [
                {"limit": [
                    {"is_target_in_variable_list": [
                        {"name": "ciso_civil_institutions"},
                        {"target": f"flag:{root}"}
                    ]}
                ]},
                {"ciso_get_ci_attraction_num": [ { "ci": root } ] },
                {"set_variable": [
                    {"name": f"{root}_population" },
                    {"value": "scope:ciso_total_ci_attraction_num_out" }
                ]},
                {"set_variable": [
                    {"name": f"{root}_social_impact" },
                    {"value": f"{root}_social_impact_base" }
                ]},
                {"set_variable": [
                    {"name": f"{root}_organization" },
                    {"value": [
                        {"value": f"{root}_organization" },
                        {"add": f"{root}_org_trend" }
                    ]}
                ]}
            ]})

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
        
        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            process_file_monthly.append({
                "ciso_calculate_atmosphere_stuff": [ { "ci": root } ]
            })


        return {
            "ciso_civsoc_process_monthly": [
                {"ciso_reset_all_measures_ci_invest": "yes"}
            ] + process_file_monthly,
            "ciso_update_ci_pop": process_file_size
        }

    @handler(lambda c: c / "scripted_effects", "CISO_setup.txt")
    def handle_setup(self):
        trees = self.trees
        init_global = []
        init_global_orgset = []
        
        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            init_global.append({
                "add_to_global_variable_list": [
                    {"name": "ciso_civil_institutions" },
                    {"target": f"flag:{root}"}
                ]
            })

        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            if not "tammany" in root:
                init_global_orgset.append({
                    "set_variable": [
                        {"name": f"{root}_organization" },
                        {"value": 20 }
                    ]
                })
            else:
                init_global_orgset.append({
                    "set_variable": [
                        {"name": f"{root}_organization" },
                        {"value": 80 }
                    ]
                })
        


        return {
            "ciso_init_civsoc_global": init_global + [{
                "every_state": [
                    {"limit": [ { "ciso_state_has_civil_society": "yes"}]}
                ] + init_global_orgset
            }]
        }

    @handler(lambda c: c / "scripted_guis", "CISO_sguis.txt")
    def handle_sgui(self):
        trees = self.trees
        sgui_file = {}
        
        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            visible = ParadoxHelper.get_script_block(tree, "visible")

            sgui_file[f"{root}_is_radical_trigger_sgui"] = [
                {"scope": "state"},
                {
                    "is_shown": [{ f"{root}_is_radical": "yes" }]
                }
            ]

            sgui_file[f"{root}_is_loyalist_trigger_sgui"] = [
                {"scope": "state"},
                {
                    "is_shown": [{ f"{root}_is_loyalist": "yes" }]
                }
            ]
            
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
            is_radical = ParadoxHelper.get_script_block(tree, "is_radical")
            is_loyalist = ParadoxHelper.get_script_block(tree, "is_loyalist")
            possible.extend(visible)

            triggers_file[f"{root}_creation_trigger"] = possible
            triggers_file[f"{root}_is_radical"] = is_radical
            triggers_file[f"{root}_is_loyalist"] = is_loyalist
            triggers_file[f"{root}_is_aggro"] = [
                {f"{root}_stance > 0": True}
            ]
            triggers_file[f"{root}_is_def"] = [
                {f"{root}_stance": 0}
            ]
            triggers_file[f"{root}_is_coop"] = [
                {f"{root}_stance < 0": True}
            ]
        
        return triggers_file

class MeasureHandler(BaseHandler):

    @handler(lambda c: c / "scripted_effects", "CISO_measures_magic_utils.txt")
    def handle_magic(self):
        trees = self.trees
        magic_file = []
        imagic_file = []

        with open(script_directory / "repetitemplate" / "repetitemplate-s1.txt") as f:
            magic_file.append(ParadoxParser(f.read()).parse())

        with open(script_directory / "repetitemplate" / "repetitemplate-p1.txt") as f:
            p1 = f.read()
        with open(script_directory / "repetitemplate" / "repetitemplate-p2.txt") as f:
            p2 = f.read()
        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            magic_file.append(ParadoxParser(p1.replace("<<root>>", root)).parse())
        
        with open(script_directory / "repetitemplate" / "repetitemplate-s2.txt") as f:
            magic_file.append(ParadoxParser(f.read()).parse())
        
        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            magic_file.append(ParadoxParser(p2.replace("<<root>>", root)).parse())


        # repitisimal
        with open(script_directory / "repetitemplate" / "repetisimal-s1.txt") as f:
            imagic_file.append(ParadoxParser(f.read()).parse())

        with open(script_directory / "repetitemplate" / "repetisimal-p1.txt") as f:
            p1 = f.read()

        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            imagic_file.append(ParadoxParser(p1.replace("<<root>>", root)).parse())
    
        with open(script_directory / "repetitemplate" / "repetisimal-s2.txt") as f:
            imagic_file.append(ParadoxParser(f.read()).parse())


        return {"ciso_do_every_measure_with_ci": magic_file, "ciso_calculate_atmosphere_stuff": imagic_file}

    @handler(lambda c: c / "scripted_effects", "CISO_measures_magic_values.txt")
    def handle_magic_values(self):
        trees = self.trees
        magic_file = [{"value": "0"}]

        with open(script_directory / "repetitemplate" / "repetinew-p1.txt") as f:
            p1 = f.read()

        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            magic_file.append({
                "every_scope_pop": ParadoxParser(p1.replace("<<root>>", root)).parse()
            })

        return {"ciso_get_ci_attraction_num": [
            {"save_scope_value_as": [
                {"name": "ciso_total_ci_attraction_num_out" },
                {"value": magic_file}
            ]}
        ]}

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

    @handler(lambda c: c / "scripted_effects", "CISO_measures_process.txt")
    def handle_process(self):
        trees = self.trees
        process_file_monthly = []
        process_file_halfyearly = []
        
        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            process_file_monthly.append({
                "ciso_apply_ms_effect": [
                    {"ms": root }
                ]
            })
            
        process_file_monthly.append({
            "if": [
                {"limit": [
                    {"owner": [{ "is_player": "yes"}]}
                ]},
                { "ciso_update_ci_pop": "yes" }
            ]
        })

        process_file_halfyearly.append({
            "ciso_update_ci_pop": "yes"
        })

        return {
            "ciso_measures_process_monthly": process_file_monthly,
            "ciso_measures_process_halfyearly": process_file_halfyearly
        }

    @handler(lambda c: c / "static_modifiers", "CISO_measure_modifiers.txt")
    def handle_modifiers(self):
        trees = self.trees
        modifiers_file = {}
        
        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            icon = tree[root].get("icon", None)
            effects = ParadoxHelper.get_script_block(tree, "modifier")
            if icon:
                modifiers_file[f"{root}_effect"] = [
                    {"icon": f"\"{icon}\""}
                ] + effects
            else:
                modifiers_file[f"{root}_effect"] = effects

        return modifiers_file


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
        reset = []
        calc = [
            {"set_local_variable": [
                {"name": "temp"},
                {"value": "ciso_total_government_investment"}
            ]},
            {"remove_building": "building_ciso_magic_building"},
            {"create_building": [
                {"building": "building_ciso_magic_building" },
                {"level": "local_var:temp" }
            ]}
        ]
        
        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            reset.extend([
                {
                "set_variable": [
                    {"name": f"{root}_ci_investment_var" },
                    {"value": f"0"}
                ]
                }
            ])

        with open(script_directory / "repetitemplate" / "repetires-p1.txt") as f:
            ip1 = f.read()
        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            reset.append(ParadoxParser(ip1.replace("<<root>>", root)).parse())

        return {
            "ciso_reset_all_measures_ci_invest": reset,
            "ciso_update_cost": calc
        }

    @handler(lambda c: c / "script_values", "CISO_measure_values.txt")
    def handle_script_value(self):
        trees = self.trees
        script_value_file = {}
        avg_alr_invested = [{"value": "0"}]
        total_gov_inv = [{"value": "0"}]
        
        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            attraction = ParadoxHelper.get_script_block(tree, "pop_weights")
            script_value_file[f"{root}_pop_weights"] = attraction
            script_value_file[f"{root}_efficiency"] = [
                {"value": "ciso_B"},
                {"divide": [
                    {"value": f"{root}_investment"},
                    {"add": "ciso_B"}
                ]}
            ]

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
                },
                {
                    "if": [
                        {
                            "limit": [
                                {"has_variable": f"{root}_ci_investment_var"}
                            ]
                        },
                        {
                            "add": f"var:{root}_ci_investment_var"
                        }
                    ],
                }
            ]

            script_value_file[f"{root}_investment_gov"] = [{
                "if": [
                    {
                        "limit": [
                            {"has_variable": f"{root}_investment_var"}
                        ]
                    },
                    {
                        "value": f"var:{root}_investment_var"
                    }
                ]
                },
                {
                    "else": [
                        {
                            "value": "0"
                        }
                    ]
                }
            ]

            total_gov_inv.append({
                "add": f"{root}_investment_gov"
            })

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

        script_value_file["ciso_total_government_investment"] = total_gov_inv
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
                    },
                    {"ciso_update_cost": "yes"},
                    {"ciso_apply_ms_effect": [
                        {"ms": root}
                    ]}
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
                    }]
                },
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
                },
                {"ciso_update_cost": "yes"},
                {"ciso_apply_ms_effect": [
                    {"ms": root}
                ]}
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
        unfulfilled_needs = [{"value": 0}]
        
        for tree in trees:
            required_value = ParadoxHelper.get_script_block(tree, "required_value")
            root = ParadoxHelper.get_root(tree)
            script_value_file[f"{root}_fp"] = [{
                "value": f"modifier:state_{root}_fp"
            }]
            script_value_file[f"{root}_rfp"] = required_value

            unfulfilled_needs.append({
                "if": [
                    {"limit": [{
                        "is_target_in_variable_list": [
                            {"name": "ciso_needs"},
                            {"target": f"flag:{root}"}
                        ]
                    }]},
                    {
                        "add": [
                            { "value": f"{root}_rfp" },
                            { "subtract": f"{root}_fp" },
                            { "min": 0 }
                        ]
                    }
                ]
            })

        script_value_file["ciso_total_unfulfilled_needs"] = unfulfilled_needs

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