from .base_handler import BaseHandler, handler
from .paradox_lib import ParadoxHelper


class AlignmentHandler(BaseHandler):

    @handler(lambda c: c / "scripted_effects", "CISO_alignment_setup.txt")
    def handle_alignment_setup(self):
        trees = self.trees
        init_global = []

        for tree in trees:
            for root in tree.keys():
                init_global.append({
                    "add_to_global_variable_list": [
                        {"name": "ciso_alignment"},
                        {"target": f"flag:{root}"}
                    ]
                })

        return {"ciso_init_alignment_global": init_global}

    @handler(lambda c: c / "modifier_type_definitions", "CISO_alignment_modifiers.txt")
    def handle_modifier_type(self):
        trees = self.trees
        init_global = []

        for tree in trees:
            for root in tree.keys():
                init_global.append({
                    f"{root}_attraction_mult": [
                        {"decimals": "0"},
                        {"percent": True},
                        {"color": "neutral"}
                    ]
                })

        return init_global

    @handler(lambda c: c / "static_modifiers", "CISO_alignment_static_modifiers.txt")
    def handle_static_modifiers(self):
        trees = self.trees
        modifiers_file = {}

        for tree in trees:
            for root in tree.keys():
                icon = tree[root].get("icon", None)
                if icon:
                    modifiers_file[f"{root}_boost_mod"] = [
                        {"icon": f"\"{icon}\""},
                        {f"{root}_attraction_mult": "1"}
                    ]
                else:
                    modifiers_file[f"{root}_boost_mod"] = [
                        {f"{root}_attraction_mult": "1"}
                    ]

        return modifiers_file

    @handler(lambda c: c / "scripted_effects", "CISO_alignment_process.txt")
    def handle_alignment_process(self):
        trees = self.trees
        process_file = []

        for tree in trees:
            for root in tree.keys():
                process_file.extend([
                    {"if": [
                        {"limit": [
                            {"scope:alignment": f"flag:{root}"}
                        ]},
                        {"ciso_align_ci_tool": [{"ci": "$ci$"}, {"modifier": f"{root}_boost_mod"}]}
                    ]}
                ])

        return {"ciso_apply_alignment": process_file}

    @handler(lambda l: l / "english", "CISO_alignment_l_english.yml", yml=True)
    def handle_alignment_loc(self):
        trees = self.trees
        loc_file = {}

        for tree in trees:
            for root in tree.keys():
                rootw = root.replace("ciso_al_", "").replace("_", " ")
                loc_file[f"{root}"] = rootw.title() + " Alignment"
                loc_file[f"{root}_boost_mod"] = rootw.title() + " Alignment"
                loc_file[f"{root}_attraction_mult"] = f"{rootw.title()} Alignment Attraction Multiplier"

        return loc_file
