# SPDX-License-Identifier: AGPL-3.0-only
"""Iterative corotational elastic frame analysis for AS 4100 Appendix E."""

from math import atan2, isfinite, sqrt

from .frame_buckling import _cholesky, assemble_frame_matrices
from .second_order import (
    _element_distributed_load_vector,
    _frame_load_vector,
    _member_loads_by_id,
    _reduced_scaled_matrix,
    _relative_change,
    _solve_cholesky,
    _validate_frame_model,
)


def _corotational_element_response(element, member, displacement):
    dofs = element["dofs"]
    current_start = [
        element["reference_start"][axis] + displacement[dofs[axis]] for axis in range(2)
    ]
    current_end = [
        element["reference_end"][axis] + displacement[dofs[axis + 3]] for axis in range(2)
    ]
    delta_x = current_end[0] - current_start[0]
    delta_y = current_end[1] - current_start[1]
    current_length = sqrt(delta_x**2 + delta_y**2)
    reference_length = element["length_mm"]
    if not isfinite(current_length) or current_length <= 1e-9:
        raise ValueError("Iterative frame analysis produced a collapsed or invalid member element.")

    cosine = delta_x / current_length
    sine = delta_y / current_length
    chord_rotation = atan2(delta_y, delta_x) - element["reference_angle"]
    basic_deformation = [
        current_length - reference_length,
        displacement[dofs[2]] - chord_rotation,
        displacement[dofs[5]] - chord_rotation,
    ]

    elastic_modulus = 200_000.0
    area = member["area_mm2"]
    second_moment = member["second_moment_in_plane_mm4"]
    axial_stiffness = elastic_modulus * area / reference_length
    bending_scale = elastic_modulus * second_moment / reference_length
    basic_stiffness = [
        [axial_stiffness, 0.0, 0.0],
        [0.0, 4.0 * bending_scale, 2.0 * bending_scale],
        [0.0, 2.0 * bending_scale, 4.0 * bending_scale],
    ]
    basic_force = [
        sum(basic_stiffness[row][column] * basic_deformation[column] for column in range(3))
        for row in range(3)
    ]
    transformation = [
        [-cosine, -sine, 0.0, cosine, sine, 0.0],
        [
            -sine / current_length,
            cosine / current_length,
            1.0,
            sine / current_length,
            -cosine / current_length,
            0.0,
        ],
        [
            -sine / current_length,
            cosine / current_length,
            0.0,
            sine / current_length,
            -cosine / current_length,
            1.0,
        ],
    ]
    internal_force = [
        sum(transformation[row][column] * basic_force[row] for row in range(3))
        for column in range(6)
    ]
    tangent = [
        [
            sum(
                transformation[basic_row][row]
                * basic_stiffness[basic_row][basic_column]
                * transformation[basic_column][column]
                for basic_row in range(3)
                for basic_column in range(3)
            )
            for column in range(6)
        ]
        for row in range(6)
    ]

    length_hessian = (
        (sine**2 / current_length, -sine * cosine / current_length),
        (-sine * cosine / current_length, cosine**2 / current_length),
    )
    angle_hessian = (
        (
            2.0 * delta_x * delta_y / current_length**4,
            (delta_y**2 - delta_x**2) / current_length**4,
        ),
        (
            (delta_y**2 - delta_x**2) / current_length**4,
            -2.0 * delta_x * delta_y / current_length**4,
        ),
    )
    relative_translation = ((-1.0, 0.0, 0.0, 1.0, 0.0, 0.0), (0.0, -1.0, 0.0, 0.0, 1.0, 0.0))
    for row in range(6):
        for column in range(6):
            length_geometric = sum(
                relative_translation[axis][row]
                * length_hessian[axis][other_axis]
                * relative_translation[other_axis][column]
                for axis in range(2)
                for other_axis in range(2)
            )
            angle_geometric = sum(
                relative_translation[axis][row]
                * angle_hessian[axis][other_axis]
                * relative_translation[other_axis][column]
                for axis in range(2)
                for other_axis in range(2)
            )
            tangent[row][column] += (
                basic_force[0] * length_geometric
                - (basic_force[1] + basic_force[2]) * angle_geometric
            )

    return {
        "internal_force": internal_force,
        "tangent": tangent,
        "basic_force": basic_force,
    }


def _assemble_internal_state(inputs, assembly, displacement):
    dof_count = len(displacement)
    internal_force = [0.0] * dof_count
    tangent = [[0.0] * dof_count for _ in range(dof_count)]
    member_states = []
    for member, elements in zip(inputs["members"], assembly["member_elements"], strict=True):
        states = []
        for element in elements:
            state = _corotational_element_response(element, member, displacement)
            states.append(state)
            for local_row, global_row in enumerate(element["dofs"]):
                internal_force[global_row] += state["internal_force"][local_row]
                for local_column, global_column in enumerate(element["dofs"]):
                    tangent[global_row][global_column] += state["tangent"][local_row][local_column]
        member_states.append(states)
    return internal_force, tangent, member_states


def _scaled_residual_norm(residual, free_dofs, scales):
    return max(
        (abs(residual[dof] * scales[index]) for index, dof in enumerate(free_dofs)),
        default=0.0,
    )


def _newton_equilibrium_step(inputs, assembly, target_load, initial_displacement, load_scale):
    free_dofs = assembly["free_dofs"]
    scales = assembly["scales"]
    tolerance = 1e-8 * max(load_scale, 1.0)
    displacement = list(initial_displacement)

    for iteration in range(1, 61):
        internal, tangent, member_states = _assemble_internal_state(inputs, assembly, displacement)
        residual = [
            applied - resisting for applied, resisting in zip(target_load, internal, strict=True)
        ]
        residual_norm = _scaled_residual_norm(residual, free_dofs, scales)
        if residual_norm <= tolerance:
            reduced_tangent = _reduced_scaled_matrix(tangent, free_dofs, scales)
            try:
                _cholesky(reduced_tangent)
            except ValueError as exc:
                raise ValueError(
                    "The converged iterative frame tangent stiffness is not positive definite; "
                    "the design load set is unstable in this model."
                ) from exc
            return (
                displacement,
                iteration,
                residual_norm / max(load_scale, 1.0),
                internal,
                member_states,
            )

        reduced_tangent = _reduced_scaled_matrix(tangent, free_dofs, scales)
        try:
            lower = _cholesky(reduced_tangent)
        except ValueError as exc:
            raise ValueError(
                "The iterative frame tangent stiffness is not positive definite; the design "
                "load set is unstable in this model."
            ) from exc
        right_hand_side = [residual[dof] * scales[index] for index, dof in enumerate(free_dofs)]
        scaled_increment = _solve_cholesky(lower, right_hand_side)
        increment = [0.0] * len(target_load)
        for index, dof in enumerate(free_dofs):
            increment[dof] = scales[index] * scaled_increment[index]

        accepted = None
        for line_search_step in range(9):
            factor = 0.5**line_search_step
            trial = [
                value + factor * step for value, step in zip(displacement, increment, strict=True)
            ]
            trial_internal, _, _ = _assemble_internal_state(inputs, assembly, trial)
            trial_residual = [
                applied - resisting
                for applied, resisting in zip(target_load, trial_internal, strict=True)
            ]
            trial_norm = _scaled_residual_norm(trial_residual, free_dofs, scales)
            if trial_norm < residual_norm or trial_norm <= tolerance:
                accepted = trial
                break
        if accepted is None:
            raise ValueError(
                "Iterative second-order frame equilibrium did not converge under line search; "
                "refine the model or assess the design load set."
            )
        displacement = accepted

    raise ValueError(
        "Iterative second-order frame equilibrium did not converge within 60 Newton iterations."
    )


def _newton_solve(inputs, assembly, load):
    free_dofs = assembly["free_dofs"]
    scales = assembly["scales"]
    load_scale = max(
        (abs(load[dof] * scales[index]) for index, dof in enumerate(free_dofs)),
        default=0.0,
    )
    displacement = [0.0] * len(load)
    load_factor = 0.0
    load_step = 0.2
    minimum_step = 1.0 / 128.0
    total_iterations = 0
    load_steps = 0
    residual_relative = 0.0
    internal = [0.0] * len(load)
    member_states = []

    for _ in range(200):
        if load_factor >= 1.0:
            break
        target_factor = min(1.0, load_factor + load_step)
        target_load = [target_factor * value for value in load]
        try:
            (
                trial_displacement,
                iterations,
                residual_relative,
                trial_internal,
                trial_member_states,
            ) = _newton_equilibrium_step(
                inputs,
                assembly,
                target_load,
                displacement,
                load_scale,
            )
        except ValueError as exc:
            load_step /= 2.0
            if load_step < minimum_step:
                raise ValueError(
                    "The proportional design-load path loses a stable iterative equilibrium "
                    "before the full design load is reached."
                ) from exc
            continue
        displacement = trial_displacement
        internal = trial_internal
        member_states = trial_member_states
        total_iterations += iterations
        load_steps += 1
        load_factor = target_factor
        if iterations <= 5:
            load_step = min(load_step * 1.5, 0.25)
        elif iterations >= 12:
            load_step = max(load_step * 0.75, minimum_step)
    else:
        raise ValueError("The proportional design-load path exceeded 200 load increments.")

    if load_factor < 1.0:
        raise ValueError("The proportional design-load path did not reach the full design load.")
    return displacement, total_iterations, load_steps, residual_relative, internal, member_states


def _global_reactions_and_equilibrium(inputs, assembly, displacement, internal, load):
    free_dofs = set(assembly["free_dofs"])
    joints_by_id = {joint["joint_id"]: joint for joint in inputs["joints"]}
    reactions = []
    for joint in inputs["joints"]:
        node = assembly["node_index"][joint["joint_id"]]
        offset = 3 * node
        reaction = {
            "joint_id": joint["joint_id"],
            "force_x_kn": (internal[offset] - load[offset]) / 1000.0
            if offset not in free_dofs
            else 0.0,
            "force_y_kn": (internal[offset + 1] - load[offset + 1]) / 1000.0
            if offset + 1 not in free_dofs
            else 0.0,
            "moment_knm": (internal[offset + 2] - load[offset + 2]) / 1_000_000.0
            if offset + 2 not in free_dofs
            else 0.0,
        }
        if joint["restrained_dofs"]:
            reactions.append(reaction)

    applied = {"force_x_kn": 0.0, "force_y_kn": 0.0, "moment_knm": 0.0}
    for joint_id, node in assembly["node_index"].items():
        offset = 3 * node
        x0, y0 = assembly["coordinates"][joint_id]
        x = x0 + displacement[offset]
        y = y0 + displacement[offset + 1]
        force_x = load[offset] / 1000.0
        force_y = load[offset + 1] / 1000.0
        moment = load[offset + 2] / 1_000_000.0
        applied["force_x_kn"] += force_x
        applied["force_y_kn"] += force_y
        applied["moment_knm"] += moment + (x * force_y - y * force_x) / 1000.0

    support = {"force_x_kn": 0.0, "force_y_kn": 0.0, "moment_knm": 0.0}
    for reaction in reactions:
        joint = joints_by_id[reaction["joint_id"]]
        offset = 3 * assembly["node_index"][joint["joint_id"]]
        x = joint["x_mm"] + displacement[offset]
        y = joint["y_mm"] + displacement[offset + 1]
        force_x = reaction["force_x_kn"]
        force_y = reaction["force_y_kn"]
        support["force_x_kn"] += force_x
        support["force_y_kn"] += force_y
        support["moment_knm"] += reaction["moment_knm"] + (x * force_y - y * force_x) / 1000.0

    residual = {name: applied[name] + support[name] for name in applied}
    force_scale = max(
        1.0,
        abs(applied["force_x_kn"])
        + abs(applied["force_y_kn"])
        + abs(support["force_x_kn"])
        + abs(support["force_y_kn"]),
    )
    moment_scale = max(1.0, abs(applied["moment_knm"]) + abs(support["moment_knm"]))
    tolerance = {"force_kn": 1e-8 * force_scale, "moment_knm": 1e-8 * moment_scale}
    equilibrium = {
        "applied_action_resultants": applied,
        "support_reaction_resultants": support,
        "residual": residual,
        "numerical_tolerance": tolerance,
        "satisfied": abs(residual["force_x_kn"]) <= tolerance["force_kn"]
        and abs(residual["force_y_kn"]) <= tolerance["force_kn"]
        and abs(residual["moment_knm"]) <= tolerance["moment_knm"],
    }
    return reactions, equilibrium


def _member_results(inputs, assembly, member_states):
    members = []
    axial_forces = []
    loads_by_member = _member_loads_by_id(inputs)
    for member, elements, states in zip(
        inputs["members"], assembly["member_elements"], member_states, strict=True
    ):
        maximum = {"absolute_knm": -1.0, "signed_knm": 0.0, "element": None, "end": None}
        element_moments = []
        element_axial_forces = []
        member_loads = loads_by_member.get(member["member_id"], [])
        for element_index, (element, state) in enumerate(
            zip(elements, states, strict=True), start=1
        ):
            load_actions = _element_distributed_load_vector(member_loads, element)
            start_moment = (state["basic_force"][1] - load_actions[2]) / 1_000_000.0
            end_moment = (state["basic_force"][2] - load_actions[5]) / 1_000_000.0
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
            element_axial_forces.append(-state["basic_force"][0] / 1000.0)
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
        axial_forces.append(
            {"member_id": member["member_id"], "element_axial_compression_kn": element_axial_forces}
        )
    return members, axial_forces


def _solve_mesh(inputs, subdivisions):
    assembly_members = [
        {**member, "axial_force_profile_kn": [0.0, 0.0]} for member in inputs["members"]
    ]
    assembly_inputs = {**inputs, "members": assembly_members}
    assembly = assemble_frame_matrices(assembly_inputs, subdivisions)
    load = _frame_load_vector(inputs, assembly)
    (
        displacement,
        iterations,
        load_steps,
        residual_relative,
        internal,
        member_states,
    ) = _newton_solve(
        inputs,
        assembly,
        load,
    )
    reactions, equilibrium = _global_reactions_and_equilibrium(
        inputs,
        assembly,
        displacement,
        internal,
        load,
    )
    member_moments, axial_forces = _member_results(inputs, assembly, member_states)
    joint_displacements = [
        {
            "joint_id": joint["joint_id"],
            "ux_mm": displacement[3 * assembly["node_index"][joint["joint_id"]]],
            "uy_mm": displacement[3 * assembly["node_index"][joint["joint_id"]] + 1],
            "rz_rad": displacement[3 * assembly["node_index"][joint["joint_id"]] + 2],
        }
        for joint in inputs["joints"]
    ]
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
        "newton_iterations": iterations,
        "load_steps": load_steps,
        "nonlinear_residual_relative": residual_relative,
        "joint_displacements": joint_displacements,
        "support_reactions": reactions,
        "global_equilibrium": equilibrium,
        "member_moments": member_moments,
        "member_axial_forces": axial_forces,
        "displacement_response": displacement_response,
        "moment_response": moment_response,
    }


def run_iterative_second_order_frame_analysis(inputs):
    """Solve one in-plane elastic frame design load set with a corotational Newton method."""
    _validate_frame_model(inputs)
    mesh_results = []
    previous = None
    mesh_difference = None
    for subdivisions in (4, 8, 16, 32):
        current = _solve_mesh(inputs, subdivisions)
        if previous is not None:
            changes = [
                _relative_change(
                    current["displacement_response"], previous["displacement_response"]
                ),
                _relative_change(current["moment_response"], previous["moment_response"]),
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
            "Iterative second-order frame response did not converge within 0.1% by 32 elements "
            "per member; refine the model or use an independently verified analysis."
        )

    refined = mesh_results[-1]
    return {
        "elastic_modulus_mpa": 200_000.0,
        "design_load_set_id": inputs["design_load_set_id"],
        "relative_mesh_difference": mesh_difference,
        "mesh_results": [
            {
                "mesh_subdivisions_per_member": item["mesh_subdivisions_per_member"],
                "newton_iterations": item["newton_iterations"],
                "load_steps": item["load_steps"],
                "nonlinear_residual_relative": item["nonlinear_residual_relative"],
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
        "member_axial_forces": refined["member_axial_forces"],
        "distributed_member_loads": inputs["distributed_member_loads"],
        "nonlinear_residual_relative": refined["nonlinear_residual_relative"],
    }
