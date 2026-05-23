from .base_handler import BaseHandler, handler
from .paradox_lib import ParadoxHelper, ParadoxParser


class CivInstHandler(BaseHandler):

    @handler(lambda c: c / "script_values", "CISO_values.txt")
    def handle_values(self):
        trees = self.trees
        values_file = {}

        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            ms_weights = ParadoxHelper.get_script_block(tree, "measure_weights")
            alignment = [{"value": "0"}, {"save_temporary_scope_as": "alignment"}] + [
                {"owner": ParadoxHelper.get_script_block(tree, "alignment")}
            ]
            num_sites = [{"value": "0"}] + ParadoxHelper.get_script_block(tree, "num_sites")
            stance = ParadoxHelper.get_script_block(tree, "stance") + [
                {"subtract": [
                    {"value": "ciso_state_atmosphere_value"},
                    {"subtract": "50"},
                    {"divide": "50"},
                    {"round": True}
                ]}
            ]
            social_impact = ParadoxHelper.multi_replace_leaves(
                ParadoxHelper.get_script_block(tree, "social_impact"),
                [
                    ("organization", f"{root}_organization"),
                    ("size", f"{root}_population"),
                ]
            ) + [
                {"round": True}
            ]
            values_file[f"{root}_num_sites"] = num_sites
            values_file[f"{root}_alignment"] = alignment
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
                {"subtract": "devastation"},
                {"if": [
                    {"limit": [
                        {"ciso_ci_is_radical": {"ci": root}}
                    ]},
                    {
                        "add": "ciso_total_ci_attraction_num_out"
                    }
                ]},
                {"multiply": [
                    {"value": f"{root}_population"},
                    {"divide": "state_population"}
                ]},
                {"multiply": [
                    {"value": 100},
                    {"subtract": f"{root}_organization"},
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
                value = 0
                if = {
                    limit = {
                        has_variable = <<root>>_social_impact
                    }
                    value = var:<<root>>_social_impact
                }
                else = {
                    value = 150
                }
                multiply = {
                    value = var:<<root>>_atmospheric_si_modifier
                    add = 1
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
                    {"ciso_get_ci_attraction_num": [{"ci": root}]},
                    {"set_variable": [
                        {"name": f"{root}_population"},
                        {"value": "scope:ciso_total_ci_attraction_num_out"}
                    ]},
                    {"set_variable": [
                        {"name": f"{root}_social_impact"},
                        {"value": [
                            {"value": f"{root}_social_impact_base"},
                            {"subtract": f"{root}_social_impact"},
                            {"divide": "24"},
                            {"add": f"{root}_social_impact"}
                        ]}
                    ]},
                    {"set_variable": [
                        {"name": f"{root}_organization"},
                        {"value": [
                            {"value": f"{root}_organization"},
                            {"add": f"{root}_org_trend"}
                        ]}
                    ]}
                ]})

            process_file_monthly.append({
                "ciso_civsoc_process_tooling_handle_creation": [
                    {"ci": root}
                ]
            })

        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            process_file_monthly.append({
                "ciso_calculate_allocation": [{"ci": root}]
            })

        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            process_file_monthly.append({
                "ciso_calculate_atmosphere_stuff": [{"ci": root}]
            })

        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            process_file_monthly.append({
                "ciso_mv_atmosphere": [{"ci": root}]
            })

        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            process_file_monthly.append({
                "ciso_align_ci": [{"ci": root}]
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
                    {"name": "ciso_civil_institutions"},
                    {"target": f"flag:{root}"}
                ]
            })

        for tree in trees:
            root = ParadoxHelper.get_root(tree)
            if not "tammany" in root:
                init_global_orgset.append({
                    "set_variable": [
                        {"name": f"{root}_organization"},
                        {"value": 20}
                    ]
                })
            else:
                init_global_orgset.append({
                    "set_variable": [
                        {"name": f"{root}_organization"},
                        {"value": 80}
                    ]
                })

        return {
            "ciso_init_civsoc_global": init_global + [{
                "every_state": [
                    {"limit": [{"ciso_state_has_civil_society": "yes"}]}
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
            sgui_file[f"{root}_is_aggro"] = [
                {"scope": "state"},
                {"is_shown": [{f"{root}_is_aggro": "yes"}]},
            ]
            sgui_file[f"{root}_is_def"] = [
                {"scope": "state"},
                {"is_shown": [{f"{root}_is_def": "yes"}]},
            ]
            sgui_file[f"{root}_is_coop"] = [
                {"scope": "state"},
                {"is_shown": [{f"{root}_is_coop": "yes"}]},
            ]

            sgui_file[f"{root}_is_radical_trigger_sgui"] = [
                {"scope": "state"},
                {"is_shown": [{f"{root}_is_radical": "yes"}]}
            ]

            sgui_file[f"{root}_is_loyalist_trigger_sgui"] = [
                {"scope": "state"},
                {"is_shown": [{f"{root}_is_loyalist": "yes"}]}
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
