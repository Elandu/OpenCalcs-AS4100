# SPDX-License-Identifier: AGPL-3.0-only
"""Bounded in-plane second-order elastic frame analysis for AS 4100 Appendix E."""

from math import isfinite, sqrt

from .frame_buckling import (
    _cholesky,
    _inverse_lower,
    _largest_symmetric_eigenvalue,
    _multiply,
    _transpose,
    assemble_frame_matrices,
)


def _reduced_scaled_matrix(matrix, free_dofs, scales):
    return [
        [
            matrix[row][column] * scales[row_index] * scales[column_index]
            for column_index, column in enumerate(free_dofs)
        ]
        for row_index, row in enumerate(free_dofs)
    ]


def _solve_cholesky(lower, right_hand_side):
    size = len(lower)
    forward = [0.0] * size
    for row in range(size):
        forward[row] = (
            right_hand_side[row]
            - sum(lower[row][column] * forward[column] for column in range(row))
        ) / lower[row][row]
    solution = [0.0] * size
    for row in range(size - 1, -1, -1):
        solution[row] = (
            forward[row]
            - sum(lower[column][row] * solution[column] for column in range(row + 1, size))
        ) / lower[row][row]
    return solution


def _member_loads_by_id(inputs):
    loads_by_member = {}
    for load in inputs["distributed_member_loads"]:
        loads_by_member.setdefault(load["member_id"], []).append(load)
    return loads_by_member


def _element_distributed_load_vector(member_loads, element):
    """Integrate consistent local nodal loads for piecewise-linear transverse loads."""
    local_load = [0.0] * 6
    element_start = element["start_fraction"]
    element_end = element["end_fraction"]
    element_fraction_length = element_end - element_start
    length = element["length_mm"]
    gauss_points = ((-sqrt(3.0 / 5.0), 5.0 / 9.0), (0.0, 8.0 / 9.0), (sqrt(3.0 / 5.0), 5.0 / 9.0))
    for member_load in member_loads:
        load_start = member_load["start_fraction"]
        load_end = member_load["end_fraction"]
        active_start = max(element_start, load_start)
        active_end = min(element_end, load_end)
        if active_end <= active_start:
            continue
        load_fraction_length = load_end - load_start
        for point, weight in gauss_points:
            fraction = (active_start + active_end) / 2 + point * (active_end - active_start) / 2
            local_fraction = (fraction - element_start) / element_fraction_length
            load_fraction = (fraction - load_start) / load_fraction_length
            # kN/m is numerically equal to N/mm for this mm-based element model.
            force = member_load["transverse_force_start_kn_per_m"] + load_fraction * (
                member_load["transverse_force_end_kn_per_m"]
                - member_load["transverse_force_start_kn_per_m"]
            )
            shape_functions = (
                1 - 3 * local_fraction**2 + 2 * local_fraction**3,
                length * (local_fraction - 2 * local_fraction**2 + local_fraction**3),
                3 * local_fraction**2 - 2 * local_fraction**3,
                length * (-(local_fraction**2) + local_fraction**3),
            )
            integration_weight = (
                length * (active_end - active_start) / element_fraction_length * weight / 2
            )
            for index, dof in enumerate((1, 2, 4, 5)):
                local_load[dof] += shape_functions[index] * force * integration_weight
    return local_load


def _frame_load_vector(inputs, assembly):
    load = [0.0] * (3 * len(assembly["coordinates"]))
    for action in inputs["joint_actions"]:
        offset = 3 * assembly["node_index"][action["joint_id"]]
        load[offset] += action["force_x_kn"] * 1000.0
        load[offset + 1] += action["force_y_kn"] * 1000.0
        load[offset + 2] += action["moment_knm"] * 1_000_000.0
    member_loads_by_id = _member_loads_by_id(inputs)
    for member, elements in zip(inputs["members"], assembly["member_elements"], strict=True):
        member_loads = member_loads_by_id.get(member["member_id"], [])
        for element in elements:
            local_load = _element_distributed_load_vector(member_loads, element)
            global_load = _multiply(
                _transpose(element["transform"]),
                [[value] for value in local_load],
            )
            for dof, values in zip(element["dofs"], global_load, strict=True):
                load[dof] += values[0]
    return load


def _support_reactions_and_equilibrium(inputs, assembly, displacement, load):
    tangent = [
        [elastic - geometric for elastic, geometric in zip(k_row, g_row, strict=True)]
        for k_row, g_row in zip(assembly["stiffness"], assembly["geometric"], strict=True)
    ]
    resisting = _multiply(tangent, [[value] for value in displacement])
    geometric_actions = _multiply(assembly["geometric"], [[value] for value in displacement])
    free_dofs = set(assembly["free_dofs"])
    joints_by_id = {joint["joint_id"]: joint for joint in inputs["joints"]}
    reactions = []
    for joint in inputs["joints"]:
        offset = 3 * assembly["node_index"][joint["joint_id"]]
        reaction = {
            "joint_id": joint["joint_id"],
            "force_x_kn": (resisting[offset][0] - load[offset]) / 1000.0
            if offset not in free_dofs
            else 0.0,
            "force_y_kn": (resisting[offset + 1][0] - load[offset + 1]) / 1000.0
            if offset + 1 not in free_dofs
            else 0.0,
            "moment_knm": (resisting[offset + 2][0] - load[offset + 2]) / 1_000_000.0
            if offset + 2 not in free_dofs
            else 0.0,
        }
        if joint["restrained_dofs"]:
            reactions.append(reaction)

    action_totals = {"force_x_kn": 0.0, "force_y_kn": 0.0, "moment_knm": 0.0}
    for joint_id, node in assembly["node_index"].items():
        offset = 3 * node
        x, y = assembly["coordinates"][joint_id]
        force_x = load[offset] / 1000.0
        force_y = load[offset + 1] / 1000.0
        moment = load[offset + 2] / 1_000_000.0
        action_totals["force_x_kn"] += force_x
        action_totals["force_y_kn"] += force_y
        action_totals["moment_knm"] += moment + (x * force_y - y * force_x) / 1000.0

    reaction_totals = {"force_x_kn": 0.0, "force_y_kn": 0.0, "moment_knm": 0.0}
    for reaction in reactions:
        joint = joints_by_id[reaction["joint_id"]]
        x = joint["x_mm"]
        y = joint["y_mm"]
        force_x = reaction["force_x_kn"]
        force_y = reaction["force_y_kn"]
        reaction_totals["force_x_kn"] += force_x
        reaction_totals["force_y_kn"] += force_y
        reaction_totals["moment_knm"] += (
            reaction["moment_knm"] + (x * force_y - y * force_x) / 1000.0
        )

    geometric_totals = {"force_x_kn": 0.0, "force_y_kn": 0.0, "moment_knm": 0.0}
    for joint_id, node in assembly["node_index"].items():
        offset = 3 * node
        x, y = assembly["coordinates"][joint_id]
        force_x = geometric_actions[offset][0] / 1000.0
        force_y = geometric_actions[offset + 1][0] / 1000.0
        moment = geometric_actions[offset + 2][0] / 1_000_000.0
        geometric_totals["force_x_kn"] += force_x
        geometric_totals["force_y_kn"] += force_y
        geometric_totals["moment_knm"] += moment + (x * force_y - y * force_x) / 1000.0

    residual = {
        name: action_totals[name] + reaction_totals[name] + geometric_totals[name]
        for name in action_totals
    }
    force_scale = max(
        1.0,
        abs(action_totals["force_x_kn"])
        + abs(action_totals["force_y_kn"])
        + abs(reaction_totals["force_x_kn"])
        + abs(reaction_totals["force_y_kn"])
        + abs(geometric_totals["force_x_kn"])
        + abs(geometric_totals["force_y_kn"]),
    )
    moment_scale = max(
        1.0,
        abs(action_totals["moment_knm"])
        + abs(reaction_totals["moment_knm"])
        + abs(geometric_totals["moment_knm"]),
    )
    tolerance = {"force_kn": 1e-8 * force_scale, "moment_knm": 1e-8 * moment_scale}
    equilibrium = {
        "applied_action_resultants": action_totals,
        "support_reaction_totals": reaction_totals,
        "geometric_stiffness_resultants": geometric_totals,
        "residual": residual,
        "numerical_tolerance": tolerance,
        "satisfied": abs(residual["force_x_kn"]) <= tolerance["force_kn"]
        and abs(residual["force_y_kn"]) <= tolerance["force_kn"]
        and abs(residual["moment_knm"]) <= tolerance["moment_knm"],
    }
    return reactions, equilibrium


def _buckling_factor(elastic, geometric):
    lower = _cholesky(elastic)
    inverse_lower = _inverse_lower(lower)
    transformed = _multiply(
        _multiply(inverse_lower, geometric),
        _transpose(inverse_lower),
    )
    for row in range(len(transformed)):
        for column in range(row):
            symmetric = (transformed[row][column] + transformed[column][row]) / 2.0
            transformed[row][column] = transformed[column][row] = symmetric
    eigenvalue = _largest_symmetric_eigenvalue(transformed)
    if not isfinite(eigenvalue):
        raise ValueError("The frame elastic buckling eigenvalue is not finite.")
    scale = max((abs(value) for row in transformed for value in row), default=0.0)
    if eigenvalue <= max(scale * 1e-11, 1e-18):
        return None
    return 1.0 / eigenvalue


def _member_end_moments(inputs, assembly, displacement):
    members = []
    member_loads_by_id = _member_loads_by_id(inputs)
    for member, elements in zip(inputs["members"], assembly["member_elements"], strict=True):
        member_loads = member_loads_by_id.get(member["member_id"], [])
        maximum = {"absolute_knm": -1.0, "signed_knm": 0.0, "element": None, "end": None}
        element_moments = []
        for element_index, element in enumerate(elements, start=1):
            global_displacements = [displacement[dof] for dof in element["dofs"]]
            local_displacements = _multiply(
                element["transform"], [[value] for value in global_displacements]
            )
            local_displacements = [row[0] for row in local_displacements]
            elastic_actions = _multiply(
                element["elastic"], [[value] for value in local_displacements]
            )
            geometric_actions = _multiply(
                element["geometric"],
                [[value] for value in local_displacements],
            )
            member_load_actions = _element_distributed_load_vector(member_loads, element)
            start_moment = (
                elastic_actions[2][0] - geometric_actions[2][0] - member_load_actions[2]
            ) / 1_000_000.0
            end_moment = (
                elastic_actions[5][0] - geometric_actions[5][0] - member_load_actions[5]
            ) / 1_000_000.0
            element_moments.append(
                {
                    "element_index": element_index,
                    "start_end_moment_knm": start_moment,
                    "end_end_moment_knm": end_moment,
                }
            )
            for end, value in (("start", start_moment), ("end", end_moment)):
                if abs(value) > maximum["absolute_knm"]:
                    maximum = {
                        "absolute_knm": abs(value),
                        "signed_knm": value,
                        "element": element_index,
                        "end": end,
                    }
        members.append(
            {
                "member_id": member["member_id"],
                "maximum_absolute_element_end_moment_knm": maximum["absolute_knm"],
                "governing_element_end_moment_knm": maximum["signed_knm"],
                "governing_element_index": maximum["element"],
                "governing_element_end": maximum["end"],
                "element_end_moments": element_moments,
            }
        )
    return members


def _solve_second_order_mesh(inputs, subdivisions):
    assembly = assemble_frame_matrices(inputs, subdivisions)
    free_dofs = assembly["free_dofs"]
    scales = assembly["scales"]
    elastic = _reduced_scaled_matrix(assembly["stiffness"], free_dofs, scales)
    geometric = _reduced_scaled_matrix(assembly["geometric"], free_dofs, scales)
    buckling_factor = _buckling_factor(elastic, geometric)
    if buckling_factor is not None and buckling_factor <= 1.0 + 1e-10:
        raise ValueError(
            "The supplied design load set reaches or exceeds the frame elastic buckling load; "
            "second-order equilibrium is not stable."
        )

    tangent = [
        [elastic[row][column] - geometric[row][column] for column in range(len(free_dofs))]
        for row in range(len(free_dofs))
    ]
    try:
        tangent_lower = _cholesky(tangent)
    except ValueError as exc:
        raise ValueError(
            "The second-order tangent stiffness is not positive definite; verify the load set "
            "and frame stability."
        ) from exc

    load = _frame_load_vector(inputs, assembly)
    right_hand_side = [load[dof] * scales[index] for index, dof in enumerate(free_dofs)]
    scaled_displacements = _solve_cholesky(tangent_lower, right_hand_side)
    displacement = [0.0] * len(load)
    for index, dof in enumerate(free_dofs):
        displacement[dof] = scales[index] * scaled_displacements[index]

    support_reactions, global_equilibrium = _support_reactions_and_equilibrium(
        inputs,
        assembly,
        displacement,
        load,
    )
    member_moments = _member_end_moments(inputs, assembly, displacement)
    joint_displacements = [
        {
            "joint_id": joint["joint_id"],
            "ux_mm": displacement[3 * assembly["node_index"][joint["joint_id"]]],
            "uy_mm": displacement[3 * assembly["node_index"][joint["joint_id"]] + 1],
            "rz_rad": displacement[3 * assembly["node_index"][joint["joint_id"]] + 2],
        }
        for joint in inputs["joints"]
    ]
    # Compare only physical model joints across meshes. Interior mesh nodes are
    # added during refinement, so their displacement vectors have different
    # lengths and cannot be compared component by component.
    displacement_response = [
        value
        for joint in joint_displacements
        for value in (
            joint["ux_mm"],
            joint["uy_mm"],
            joint["rz_rad"] * assembly["reference_length_mm"],
        )
    ]
    moment_response = [
        member["maximum_absolute_element_end_moment_knm"] for member in member_moments
    ]
    return {
        "mesh_subdivisions_per_member": subdivisions,
        "elastic_buckling_load_factor": buckling_factor,
        "member_moments": member_moments,
        "joint_displacements": joint_displacements,
        "support_reactions": support_reactions,
        "global_equilibrium": global_equilibrium,
        "displacement_response": displacement_response,
        "moment_response": moment_response,
    }


def _relative_change(current, previous):
    if not current:
        return 0.0
    scale = max((abs(value) for value in current), default=0.0)
    difference = max(abs(value - old) for value, old in zip(current, previous, strict=True))
    return difference / max(scale, 1e-9)


def _validate_frame_model(inputs):
    joint_ids = [joint["joint_id"] for joint in inputs["joints"]]
    member_ids = [member["member_id"] for member in inputs["members"]]
    action_ids = [action["joint_id"] for action in inputs["joint_actions"]]
    member_load_ids = [load["load_id"] for load in inputs["distributed_member_loads"]]
    if len(joint_ids) != len(set(joint_ids)):
        raise ValueError("Frame joint identifiers must be unique.")
    if len(member_ids) != len(set(member_ids)):
        raise ValueError("Frame member identifiers must be unique.")
    if len(action_ids) != len(set(action_ids)) or set(action_ids) != set(joint_ids):
        raise ValueError("Supply exactly one complete joint-action record for every frame joint.")
    if len(member_load_ids) != len(set(member_load_ids)):
        raise ValueError("Distributed member-load identifiers must be unique.")
    known_joints = set(joint_ids)
    if any(
        member["start_joint_id"] not in known_joints
        or member["end_joint_id"] not in known_joints
        or member["start_joint_id"] == member["end_joint_id"]
        for member in inputs["members"]
    ):
        raise ValueError("Every frame member must connect two distinct listed joints.")
    known_members = set(member_ids)
    for member_load in inputs["distributed_member_loads"]:
        if member_load["member_id"] not in known_members:
            raise ValueError("Every distributed member load must reference a listed frame member.")
        if not 0 <= member_load["start_fraction"] < member_load["end_fraction"] <= 1:
            raise ValueError(
                "Distributed member-load fractions must satisfy 0 <= start < end <= 1."
            )


def run_second_order_frame_analysis(inputs):
    """Solve the planar linearized second-order response for one assessed load set."""
    _validate_frame_model(inputs)

    mesh_results = []
    previous = None
    mesh_difference = None
    for subdivisions in (4, 8, 16, 32):
        current = _solve_second_order_mesh(inputs, subdivisions)
        if previous is not None:
            current_factor = current["elastic_buckling_load_factor"]
            previous_factor = previous["elastic_buckling_load_factor"]
            factor_change = (
                0.0
                if current_factor is None and previous_factor is None
                else float("inf")
                if current_factor is None or previous_factor is None
                else abs(current_factor - previous_factor) / max(current_factor, 1e-9)
            )
            changes = [
                _relative_change(
                    current["displacement_response"], previous["displacement_response"]
                ),
                _relative_change(current["moment_response"], previous["moment_response"]),
                factor_change,
            ]
            mesh_difference = max(changes)
            current["relative_difference_from_previous_mesh"] = mesh_difference
            mesh_results.append(current)
            if isfinite(mesh_difference) and mesh_difference <= 0.001:
                break
        else:
            current["relative_difference_from_previous_mesh"] = None
            mesh_results.append(current)
        previous = current
    else:
        raise ValueError(
            "Second-order frame response did not converge within 0.1% by 32 elements per "
            "member; refine the model or use an independently verified analysis."
        )

    refined = mesh_results[-1]
    return {
        "elastic_modulus_mpa": 200_000.0,
        "design_load_set_id": inputs["design_load_set_id"],
        "elastic_buckling_load_factor": refined["elastic_buckling_load_factor"],
        "relative_mesh_difference": mesh_difference,
        "mesh_results": [
            {
                "mesh_subdivisions_per_member": item["mesh_subdivisions_per_member"],
                "elastic_buckling_load_factor": item["elastic_buckling_load_factor"],
                "relative_difference_from_previous_mesh": item[
                    "relative_difference_from_previous_mesh"
                ],
            }
            for item in mesh_results
        ],
        "joint_displacements": refined["joint_displacements"],
        "support_reactions": refined["support_reactions"],
        "global_equilibrium": refined["global_equilibrium"],
        "member_moments": refined["member_moments"],
        "joint_actions": inputs["joint_actions"],
        "distributed_member_loads": inputs["distributed_member_loads"],
        "member_axial_force_pattern": [
            {
                "member_id": member["member_id"],
                "axial_force_profile_kn": (
                    member["axial_force_profile_kn"]
                    if "axial_force_profile_kn" in member
                    else [member["axial_force_kn"], member["axial_force_kn"]]
                ),
            }
            for member in inputs["members"]
        ],
    }
