from .base_handler import BaseHandler, handler
from .paradox_lib import ParadoxHelper


class Needs(BaseHandler):

    @handler(lambda c: c / "static_modifiers", "CISO_needs_modifiers.txt")
    def handle_modifiers(self):
        trees = self.trees
        modifiers_file = {}

        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            icon = tree[root].get("icon", None)
            effects = ParadoxHelper.get_script_block(tree, "unfulfilled")
            if icon:
                modifiers_file[f"{root}_unfulfilled"] = [
                    {"icon": f"\"{icon}\""}
                ] + effects
            else:
                modifiers_file[f"{root}_unfulfilled"] = effects

        return modifiers_file

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
                    {"name": "ciso_needs"},
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
                    {"ne": root},
                    {"min": minv}
                ]
            })

        return {"ciso_needs_process_monthly": process_file_monthly}

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
                            {"value": f"{root}_rfp"},
                            {"subtract": f"{root}_fp"},
                            {"min": 0}
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
