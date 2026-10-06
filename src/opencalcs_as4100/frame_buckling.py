# SPDX-License-Identifier: AGPL-3.0-only
"""Bounded elastic in-plane frame buckling analysis for AS 4100 Clause 4.7.2(b)."""

from math import hypot, isfinite, sqrt

from .standards import ELASTIC_MODULUS_MPA


def _zeros(size):
    return [[0.0] * size for _ in range(size)]


def _multiply(left, right):
    rows = len(left)
    columns = len(right[0])
    output = _zeros(rows)
    for row in range(rows):
        for index, value in enumerate(left[row]):
            if value:
                for column in range(columns):
                    output[row][column] += value * right[index][column]
    return output


def _transpose(matrix):
    return [list(column) for column in zip(*matrix, strict=True)]


def _cholesky(matrix):
    size = len(matrix)
    lower = _zeros(size)
    scale = max(abs(matrix[index][index]) for index in range(size))
    if not isfinite(scale) or scale <= 0:
        raise ValueError("Frame elastic stiffness has no positive diagonal scale.")
    tolerance = scale * 1e-13
    for row in range(size):
        for column in range(row + 1):
            value = matrix[row][column] - sum(
                lower[row][index] * lower[column][index] for index in range(column)
            )
            if row == column:
                if not isfinite(value) or value <= tolerance:
                    raise ValueError(
                        "Frame elastic stiffness is singular or unstable; verify supports, "
                        "connectivity, and member properties."
                    )
                lower[row][column] = sqrt(value)
            else:
                lower[row][column] = value / lower[column][column]
    return lower


def _inverse_lower(lower):
    size = len(lower)
    inverse = _zeros(size)
    for column in range(size):
        for row in range(size):
            right_hand_side = 1.0 if row == column else 0.0
            inverse[row][column] = (
                right_hand_side
                - sum(lower[row][index] * inverse[index][column] for index in range(row))
            ) / lower[row][row]
    return inverse


def _largest_symmetric_eigenvalue(matrix):
    """Return the largest algebraic eigenvalue using cyclic Jacobi rotations."""
    size = len(matrix)
    values = [row[:] for row in matrix]
    scale = max((abs(value) for row in values for value in row), default=0.0)
    if not isfinite(scale) or scale == 0:
        return 0.0
    tolerance = scale * 2e-13
    converged = False
    for _ in range(80):
        largest_off_diagonal = max(
            (abs(values[row][column]) for row in range(size) for column in range(row + 1, size)),
            default=0.0,
        )
        if largest_off_diagonal <= tolerance:
            converged = True
            break
        for p in range(size - 1):
            for q in range(p + 1, size):
                off_diagonal = values[p][q]
                if abs(off_diagonal) <= tolerance:
                    continue
                tau = (values[q][q] - values[p][p]) / (2.0 * off_diagonal)
                tangent = (1.0 if tau >= 0 else -1.0) / (abs(tau) + hypot(1.0, tau))
                cosine = 1.0 / sqrt(1.0 + tangent * tangent)
                sine = tangent * cosine
                pp = values[p][p]
                qq = values[q][q]
                values[p][p] = pp - tangent * off_diagonal
                values[q][q] = qq + tangent * off_diagonal
                values[p][q] = values[q][p] = 0.0
                for index in range(size):
                    if index in (p, q):
                        continue
                    ip = values[index][p]
                    iq = values[index][q]
                    values[index][p] = values[p][index] = cosine * ip - sine * iq
                    values[index][q] = values[q][index] = sine * ip + cosine * iq
    if not converged:
        raise ValueError("Frame buckling eigenvalue solver did not converge.")
    return max(values[index][index] for index in range(size))


def _local_element_matrices(length, area, second_moment, axial_force_n):
    elastic = _zeros(6)
    axial = ELASTIC_MODULUS_MPA * area / length
    elastic[0][0] = elastic[3][3] = axial
    elastic[0][3] = elastic[3][0] = -axial

    bending_indices = (1, 2, 4, 5)
    bending = (
        (12.0, 6.0 * length, -12.0, 6.0 * length),
        (6.0 * length, 4.0 * length**2, -6.0 * length, 2.0 * length**2),
        (-12.0, -6.0 * length, 12.0, -6.0 * length),
        (6.0 * length, 2.0 * length**2, -6.0 * length, 4.0 * length**2),
    )
    bending_scale = ELASTIC_MODULUS_MPA * second_moment / length**3
    for row, global_row in enumerate(bending_indices):
        for column, global_column in enumerate(bending_indices):
            elastic[global_row][global_column] = bending_scale * bending[row][column]

    geometric = _zeros(6)
    geometric_shape = (
        (36.0, 3.0 * length, -36.0, 3.0 * length),
        (3.0 * length, 4.0 * length**2, -3.0 * length, -(length**2)),
        (-36.0, -3.0 * length, 36.0, -3.0 * length),
        (3.0 * length, -(length**2), -3.0 * length, 4.0 * length**2),
    )
    geometric_scale = axial_force_n / (30.0 * length)
    for row, global_row in enumerate(bending_indices):
        for column, global_column in enumerate(bending_indices):
            geometric[global_row][global_column] = geometric_scale * geometric_shape[row][column]
    return elastic, geometric


def _element_transform(cosine, sine):
    transform = _zeros(6)
    for offset in (0, 3):
        transform[offset][offset] = cosine
        transform[offset][offset + 1] = sine
        transform[offset + 1][offset] = -sine
        transform[offset + 1][offset + 1] = cosine
        transform[offset + 2][offset + 2] = 1.0
    return transform


def _connected_components(joints, members):
    adjacency = {joint["joint_id"]: set() for joint in joints}
    for member in members:
        start = member["start_joint_id"]
        end = member["end_joint_id"]
        adjacency[start].add(end)
        adjacency[end].add(start)
    reached = set()
    stack = [joints[0]["joint_id"]]
    while stack:
        joint_id = stack.pop()
        if joint_id in reached:
            continue
        reached.add(joint_id)
        stack.extend(adjacency[joint_id] - reached)
    return len(reached) == len(joints)


def _solve_mesh(d, subdivisions):
    joints = d["joints"]
    members = d["members"]
    coordinates = {joint["joint_id"]: (joint["x_mm"], joint["y_mm"]) for joint in joints}
    restraint_dofs = set()
    for joint_index, joint in enumerate(joints):
        for dof in joint["restrained_dofs"]:
            restraint_dofs.add(3 * joint_index + {"ux": 0, "uy": 1, "rz": 2}[dof])

    member_paths = []
    characteristic_lengths = []
    for member_index, member in enumerate(members):
        start = coordinates[member["start_joint_id"]]
        end = coordinates[member["end_joint_id"]]
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        physical_length = sqrt(dx * dx + dy * dy)
        if not isfinite(physical_length) or physical_length <= 1e-9:
            raise ValueError("Frame members must have finite, nonzero lengths.")
        characteristic_lengths.append(physical_length)
        path = [member["start_joint_id"]]
        for division in range(1, subdivisions):
            internal_id = ("__frame_mesh_joint__", member_index, division)
            fraction = division / subdivisions
            coordinates[internal_id] = (
                start[0] + fraction * dx,
                start[1] + fraction * dy,
            )
            path.append(internal_id)
        path.append(member["end_joint_id"])
        member_paths.append(path)

    node_ids = list(coordinates)
    node_index = {joint_id: index for index, joint_id in enumerate(node_ids)}
    free_dofs = [index for index in range(3 * len(node_ids)) if index not in restraint_dofs]
    if not free_dofs:
        raise ValueError("Frame buckling analysis requires unconstrained degrees of freedom.")
    if len(free_dofs) > 120:
        raise ValueError(
            "Frame buckling model exceeds 120 free degrees of freedom; split or bound the "
            "model before using this calculation."
        )

    stiffness = _zeros(3 * len(node_ids))
    geometric = _zeros(3 * len(node_ids))
    for member, path in zip(members, member_paths, strict=True):
        first = coordinates[member["start_joint_id"]]
        last = coordinates[member["end_joint_id"]]
        total_dx = last[0] - first[0]
        total_dy = last[1] - first[1]
        physical_length = sqrt(total_dx * total_dx + total_dy * total_dy)
        cosine = total_dx / physical_length
        sine = total_dy / physical_length
        transform = _element_transform(cosine, sine)
        transform_t = _transpose(transform)
        element_length = physical_length / subdivisions
        local_elastic, local_geometric = _local_element_matrices(
            element_length,
            member["area_mm2"],
            member["second_moment_in_plane_mm4"],
            member["axial_force_kn"] * 1000.0,
        )
        global_elastic = _multiply(_multiply(transform_t, local_elastic), transform)
        global_geometric = _multiply(_multiply(transform_t, local_geometric), transform)
        for path_start, path_end in zip(path[:-1], path[1:], strict=True):
            dofs = [
                *range(3 * node_index[path_start], 3 * node_index[path_start] + 3),
                *range(3 * node_index[path_end], 3 * node_index[path_end] + 3),
            ]
            for row, global_row in enumerate(dofs):
                for column, global_column in enumerate(dofs):
                    stiffness[global_row][global_column] += global_elastic[row][column]
                    geometric[global_row][global_column] += global_geometric[row][column]

    reference_length = sum(characteristic_lengths) / len(characteristic_lengths)
    scales = [1.0 if dof % 3 != 2 else 1.0 / reference_length for dof in free_dofs]
    reduced_stiffness = [
        [
            stiffness[row][column] * scales[row_index] * scales[column_index]
            for column_index, column in enumerate(free_dofs)
        ]
        for row_index, row in enumerate(free_dofs)
    ]
    reduced_geometric = [
        [
            geometric[row][column] * scales[row_index] * scales[column_index]
            for column_index, column in enumerate(free_dofs)
        ]
        for row_index, row in enumerate(free_dofs)
    ]

    lower = _cholesky(reduced_stiffness)
    inverse_lower = _inverse_lower(lower)
    transformed = _multiply(_multiply(inverse_lower, reduced_geometric), _transpose(inverse_lower))
    for row in range(len(transformed)):
        for column in range(row):
            symmetric = (transformed[row][column] + transformed[column][row]) / 2.0
            transformed[row][column] = transformed[column][row] = symmetric
    eigenvalue = _largest_symmetric_eigenvalue(transformed)
    scale = max((abs(value) for row in transformed for value in row), default=0.0)
    if not isfinite(eigenvalue) or eigenvalue <= max(scale * 1e-11, 1e-18):
        raise ValueError(
            "The supplied proportional member-force pattern has no positive elastic "
            "buckling eigenvalue."
        )
    return {
        "elastic_buckling_load_factor": 1.0 / eigenvalue,
        "mesh_subdivisions_per_member": subdivisions,
        "joint_count_including_mesh": len(node_ids),
        "free_degree_count": len(free_dofs),
    }


def run_frame_buckling(inputs):
    """Solve the lowest positive elastic buckling factor for a verified planar frame model."""
    joints = inputs["joints"]
    members = inputs["members"]
    joint_ids = [joint["joint_id"] for joint in joints]
    member_ids = [member["member_id"] for member in members]
    if len(joint_ids) != len(set(joint_ids)):
        raise ValueError("Frame joint identifiers must be unique.")
    if len(member_ids) != len(set(member_ids)):
        raise ValueError("Frame member identifiers must be unique.")
    known_joints = set(joint_ids)
    if any(
        member["start_joint_id"] not in known_joints
        or member["end_joint_id"] not in known_joints
        or member["start_joint_id"] == member["end_joint_id"]
        for member in members
    ):
        raise ValueError("Every frame member must connect two distinct listed joints.")
    if not _connected_components(joints, members):
        raise ValueError("Frame model must be one connected joint/member graph.")

    mesh_results = []
    previous = None
    mesh_difference = None
    for subdivisions in (4, 8, 16, 32):
        current = _solve_mesh(inputs, subdivisions)
        if previous is not None:
            mesh_difference = (
                abs(
                    current["elastic_buckling_load_factor"]
                    - previous["elastic_buckling_load_factor"]
                )
                / current["elastic_buckling_load_factor"]
            )
            current["relative_difference_from_previous_mesh"] = mesh_difference
            if isfinite(mesh_difference) and mesh_difference <= 0.001:
                mesh_results.append(current)
                break
        else:
            current["relative_difference_from_previous_mesh"] = None
        mesh_results.append(current)
        previous = current
    else:
        raise ValueError(
            "Frame buckling result did not converge within 0.1% by 32 elements per member; "
            "refine the model or use an independently verified analysis."
        )
    if len(mesh_results) == 1:
        raise ValueError("Frame buckling analysis requires at least two converged mesh results.")
    coarse = mesh_results[0]
    refined = mesh_results[-1]
    return {
        "elastic_modulus_mpa": ELASTIC_MODULUS_MPA,
        "design_load_set_id": inputs["design_load_set_id"],
        "lambda_c": refined["elastic_buckling_load_factor"],
        "elastic_buckling_load_factor": refined["elastic_buckling_load_factor"],
        "coarse_mesh_load_factor": coarse["elastic_buckling_load_factor"],
        "refined_mesh_load_factor": refined["elastic_buckling_load_factor"],
        "relative_mesh_difference": mesh_difference,
        "mesh_results": mesh_results,
        "coarse_mesh": coarse,
        "refined_mesh": refined,
        "member_count": len(members),
        "joint_count": len(joints),
        "restrained_degree_count": sum(len(joint["restrained_dofs"]) for joint in joints),
        "joints": [
            {
                "joint_id": joint["joint_id"],
                "x_mm": joint["x_mm"],
                "y_mm": joint["y_mm"],
                "restrained_dofs": joint["restrained_dofs"],
                "joint_geometry_verified": joint["joint_geometry_verified"],
                "restraint_assessment_verified": joint["restraint_assessment_verified"],
                "evidence_reference": joint["evidence_reference"],
            }
            for joint in joints
        ],
        "members": [
            {
                "member_id": member["member_id"],
                "start_joint_id": member["start_joint_id"],
                "end_joint_id": member["end_joint_id"],
                "area_mm2": member["area_mm2"],
                "second_moment_in_plane_mm4": member["second_moment_in_plane_mm4"],
                "axial_force_kn": member["axial_force_kn"],
                "prismatic_member_verified": member["prismatic_member_verified"],
                "geometry_verified": member["geometry_verified"],
                "section_properties_verified": member["section_properties_verified"],
                "axial_force_verified": member["axial_force_verified"],
                "evidence_reference": member["evidence_reference"],
            }
            for member in members
        ],
    }
