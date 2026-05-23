import pathlib

from ..base_handler import BaseHandler, handler
from ..paradox_lib import ParadoxHelper, ParadoxParser

_here = pathlib.Path(__file__).resolve().parent
TMPL_DO_EVERY   = _here / "do_every_measure_with_ci"
TMPL_ATMOSPHERE = _here / "calculate_atmosphere_stuff"
TMPL_ATTRACTION = _here / "get_ci_attraction_num"
TMPL_RESET      = _here / "reset_measures_ci_invest"


class MeasureHandler(BaseHandler):

    @handler(lambda c: c / "scripted_effects", "CISO_measures_magic_utils.txt")
    def handle_magic(self):
        trees = self.trees
        magic_file = []
        imagic_file = []

        with open(TMPL_DO_EVERY / "singleton_pre.txt") as f:
            magic_file.append(ParadoxParser(f.read()).parse())

        with open(TMPL_DO_EVERY / "per_measure_pre.txt") as f:
            p1 = f.read()
        with open(TMPL_DO_EVERY / "per_measure_post.txt") as f:
            p2 = f.read()

        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            magic_file.append(ParadoxParser(p1.replace("<<root>>", root)).parse())

        with open(TMPL_DO_EVERY / "singleton_mid.txt") as f:
            magic_file.append(ParadoxParser(f.read()).parse())

        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            magic_file.append(ParadoxParser(p2.replace("<<root>>", root)).parse())

        with open(TMPL_ATMOSPHERE / "singleton_pre.txt") as f:
            imagic_file.append(ParadoxParser(f.read()).parse())

        with open(TMPL_ATMOSPHERE / "per_measure.txt") as f:
            p1 = f.read()

        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            imagic_file.append(ParadoxParser(p1.replace("<<root>>", root)).parse())

        with open(TMPL_ATMOSPHERE / "singleton_post.txt") as f:
            imagic_file.append(ParadoxParser(f.read()).parse())

        return {"ciso_do_every_measure_with_ci": magic_file, "ciso_calculate_atmosphere_stuff": imagic_file}

    @handler(lambda c: c / "scripted_effects", "CISO_measures_magic_values.txt")
    def handle_magic_values(self):
        trees = self.trees
        magic_file = [{"value": "0"}]

        with open(TMPL_ATTRACTION / "per_measure.txt") as f:
            p1 = f.read()

        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            magic_file.append({
                "every_scope_pop": ParadoxParser(p1.replace("<<root>>", root)).parse()
            })

        return {"ciso_get_ci_attraction_num": [
            {"save_scope_value_as": [
                {"name": "ciso_total_ci_attraction_num_out"},
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
                "ciso_apply_ms_effect": [{"ms": root}]
            })

        process_file_monthly.append({
            "if": [
                {"limit": [
                    {"owner": [{"is_player": "yes"}]}
                ]},
                {"ciso_update_ci_pop": "yes"}
            ]
        })

        process_file_halfyearly.append({
            "ciso_update_ci_pop": "yes"
        })

        process_file_monthly.append({
            "ciso_update_cost": True
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
                modifiers_file[f"{root}_effect"] = [{"icon": f"\"{icon}\""}] + effects
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
                    {"name": "ciso_society_measures"},
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
                {"value": [
                    {"value": "ciso_total_government_investment_w"},
                    {"add": "ciso_total_government_suppression"}
                ]}
            ]},
            {"remove_building": "building_ciso_magic_building"},
            {"create_building": [
                {"building": "building_ciso_magic_building"},
                {"level": "local_var:temp"}
            ]}
        ]

        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            reset.extend([{
                "set_variable": [
                    {"name": f"{root}_ci_investment_var"},
                    {"value": "0"}
                ]
            }])

        with open(TMPL_RESET / "per_measure.txt") as f:
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
        total_gov_sup = [{"value": "0"}]

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

            script_value_file[f"{root}_investment"] = [
                {"if": [
                    {"limit": [{"has_variable": f"{root}_investment_var"}]},
                    {"value": f"var:{root}_investment_var"}
                ]},
                {"else": [{"value": "0"}]},
                {"if": [
                    {"limit": [{"has_variable": f"{root}_ci_investment_var"}]},
                    {"add": f"var:{root}_ci_investment_var"}
                ]}
            ]

            script_value_file[f"{root}_investment_gov"] = [
                {"if": [
                    {"limit": [{"has_variable": f"{root}_investment_var"}]},
                    {"value": f"var:{root}_investment_var"}
                ]},
                {"else": [{"value": "0"}]}
            ]

            total_gov_inv.append({"add": f"{root}_investment_gov"})
            total_gov_sup.append([
                {"if": [
                    {"limit": [{"has_variable": f"{root}_is_suppressed"}]},
                    {"add": f"{root}_investment"}
                ]}
            ])

        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            avg_alr_invested.append({"add": f"{root}_investment"})

        avg_alr_invested.append({"divide": {"value": len(trees)}})

        script_value_file["ciso_total_government_investment"] = total_gov_inv
        script_value_file["ciso_total_government_suppression"] = total_gov_sup
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
                    "effect": [
                        {"if": [
                            {"limit": [{"NOT": [{"has_variable": f"{root}_investment_var"}]}]},
                            {"set_variable": [
                                {"name": f"{root}_investment_var"},
                                {"value": "0"}
                            ]}
                        ]},
                        {"change_variable": [
                            {"name": f"{root}_investment_var"},
                            {"add": "50"}
                        ]},
                        {"add_to_variable_list": [
                            {"name": "ciso_society_measures"},
                            {"target": f"flag:{root}"}
                        ]},
                        {"ciso_update_cost": "yes"},
                        {"ciso_apply_ms_effect": [{"ms": root}]}
                    ]
                }
            ]
            sgui_file[f"{root}_increment_effect"] = self.generate_incrdecr_effect(root, "add", "25")
            sgui_file[f"{root}_decrement_effect"] = self.generate_incrdecr_effect(root, "subtract", "25")
            sgui_file[f"{root}_increment_alot_effect"] = self.generate_incrdecr_effect(root, "add", "50")
            sgui_file[f"{root}_decrement_alot_effect"] = self.generate_incrdecr_effect(root, "subtract", "50")
            sgui_file[f"{root}_increment_very_alot_effect"] = self.generate_incrdecr_effect(root, "add", "100")
            sgui_file[f"{root}_decrement_very_alot_effect"] = self.generate_incrdecr_effect(root, "subtract", "100")
            sgui_file[f"{root}_increment_alittle_effect"] = self.generate_incrdecr_effect(root, "add", "10")
            sgui_file[f"{root}_decrement_alittle_effect"] = self.generate_incrdecr_effect(root, "subtract", "10")

            sgui_file[f"{root}_suppressed"] = [
                {"scope": "state"},
                {"is_shown": [{"has_variable": f"{root}_is_suppressed"}]},
                {"effect": [
                    {"if": [
                        {"limit": [{"has_variable": f"{root}_is_suppressed"}]},
                        {"remove_variable": f"{root}_is_suppressed"},
                        {"ciso_update_cost": "yes"}
                    ]},
                    {"else": [
                        {"set_variable": f"{root}_is_suppressed"},
                        {"ciso_update_cost": "yes"}
                    ]}
                ]}
            ]

        return sgui_file

    @staticmethod
    def generate_incrdecr_effect(root, increment="add", value="100"):
        return [
            {"scope": "state"},
            {"effect": [
                {"if": [
                    {"limit": [{"NOT": [{"has_variable": f"{root}_investment_var"}]}]},
                    {"set_variable": [
                        {"name": f"{root}_investment_var"},
                        {"value": "0"}
                    ]}
                ]},
                {"change_variable": [
                    {"name": f"{root}_investment_var"},
                    {increment: value}
                ]},
                {"clamp_variable": [
                    {"name": f"{root}_investment_var"},
                    {"min": "0"},
                    {"max": "100000000"}
                ]},
                {"ciso_update_cost": "yes"},
                {"ciso_apply_ms_effect": [{"ms": root}]}
            ]}
        ]
