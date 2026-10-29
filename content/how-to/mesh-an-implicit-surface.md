---
title: Mesh an implicit surface with marching cubes
section: How-to
group: Shapes and meshes
order: 7
description: Sample a scalar function on a 3D grid and extract the triangle mesh of one of its isosurfaces with marching_cube.
---

# Mesh an implicit surface with marching cubes

**Goal**: display the smooth surface that surrounds two "blobs" (a sum of Gaussian
functions), and change its thickness with a slider.

> **Starting point**: the default project template (`src/scene.hpp`, `src/scene.cpp`, see
> [Your first scene](../get-started/first-scene.md)). It already declares the shapes `sphere`
> and `cylinder`, a `timer`, and the members `camera_control`, `environment` and `gui`: reuse
> them, do not declare them again. The first comment of each code block says in which file
> and where its lines go: *add* means insert them, *replace* means replace the whole function by the one shown.

<!-- demo: mesh-an-implicit-surface -->

## How it works

An implicit surface is the set of points p where a scalar function f(p) equals a given
*isovalue*. The marching cubes algorithm samples f on a regular 3D grid (the *domain*),
then builds triangles in each voxel where f crosses the isovalue. CGP provides the three
pieces: `spatial_domain_grid_3D` (where the samples are), `grid_3D<float>` (their values)
and `marching_cube` (the extraction, returning an ordinary `mesh`).

## 1. Write the scalar function

```cpp
// scene.cpp - add before initialize()
float blob(vec3 const& p, vec3 const& center)
{
    float const d = norm(p - center);
    return std::exp(-d * d);
}
float field_function(vec3 const& p)
{
    return blob(p, {-1,0,0}) + blob(p, {1,0,0});
}
```

## 2. Declare the data

```cpp
// scene.hpp - add in gui_parameters
float isovalue = 0.5f;
```

```cpp
// scene.hpp - add in scene_structure
spatial_domain_grid_3D domain;
grid_3D<float> field;
mesh_drawable implicit_surface;
curve_drawable domain_box;
```

## 3. Sample the field and extract the surface (once)

```cpp
// scene.cpp - add at the end of initialize()
// Box of size 5 x 3 x 3 centered at the origin, sampled with 50 x 50 x 50 points
domain = spatial_domain_grid_3D::from_center_length({0,0,0}, {5,3,3}, {50,50,50});

field.resize(domain.samples);
for (int kz = 0; kz < domain.samples.z; ++kz)
    for (int ky = 0; ky < domain.samples.y; ++ky)
        for (int kx = 0; kx < domain.samples.x; ++kx)
            field(kx, ky, kz) = field_function(domain.position({kx, ky, kz}));

implicit_surface.initialize_data_on_gpu(marching_cube(field, domain, gui.isovalue));
implicit_surface.material.color = { 1.0f, 0.7f, 0.5f };

// Optional: show the box of the domain
domain_box.display_type = curve_drawable_display_type::Segments;
domain_box.initialize_data_on_gpu(domain.export_segments_for_drawable_border());
```

## 4. Draw, and update the isovalue from the GUI

```cpp
// scene.cpp - add in display_frame(), before timer.update()
draw(implicit_surface, environment);
draw(domain_box, environment);
```

```cpp
// scene.cpp - add in display_gui()
if (ImGui::SliderFloat("Isovalue", &gui.isovalue, 0.05f, 1.5f)) {
    implicit_surface.clear();                                  // free the previous buffers
    implicit_surface.initialize_data_on_gpu(marching_cube(field, domain, gui.isovalue));
    implicit_surface.material.color = { 1.0f, 0.7f, 0.5f };   // reset by the new upload
}
```

The field is sampled once; only the extraction is repeated when the isovalue changes.

## Common pitfalls

- **Nothing is displayed**: the isovalue is outside the range of the field (here f is in
  [0,2]), or the surface lies outside the domain. Print a few values of the field.
- **The surface is cut by flat holes**: it crosses the border of the domain. Enlarge the
  domain (`length` argument of `from_center_length`).
- **The surface looks faceted or blobs merge too early**: the grid is too coarse for the
  details. Increase the number of samples (the cost grows as its cube: 100 x 100 x 100 is
  already 1 million evaluations).
- **The program stops on an assertion in `marching_cube`**: the field grid and the domain do not
  have the same size. Call `field.resize(domain.samples)` after each change of the domain.
- **Warning about a non-empty `mesh_drawable`**: `initialize_data_on_gpu` was called again
  without `clear()` first.
- **The surface turns white after a change of the isovalue**: `clear()` and
  `initialize_data_on_gpu` reset the material and the `model` transform. Set them again
  after the new upload.

## Variations

- Domain given by two corners: `spatial_domain_grid_3D::from_corners({-2,-2,-2}, {2,2,2}, {40,40,40})`.
- Show the voxels: `domain.export_segments_for_drawable_voxel()` gives the segments of all
  the grid cells (to draw as segments, on small grids only).
- Save the result: `mesh_save_file_obj("implicit_surface.obj", marching_cube(field, domain, gui.isovalue));`.
- Interactive editing of the function (moving blobs): the second form of `marching_cube`
  fills a `std::vector<vec3>` of positions without re-allocating, which you send to the
  GPU with `vbo_position.update`; this is what the dynamic example of the source does.

Source: EPITA Ani3D repository `epita_ani3d_lab_code-2027`, examples
`02_marching_cubes/01_marching_cube_simple` (scene.cpp and field_function.cpp) and
`02_marching_cubes/02_marching_cube_dynamic` (implicit_surface.cpp, interactive update).

## See also

- How-to: [Build a mesh by hand](build-a-mesh-by-hand.md), [Add GUI controls](add-gui-controls.md), [Draw curves, segments and trajectories](draw-curves-and-segments.md)
- Understand: [From CPU to GPU](../understand/cpu-to-gpu.md)
- Reference: [`grid_3D`](../reference/grid_3D.md), [`mesh`](../reference/mesh.md), [`mesh_drawable`](../reference/mesh_drawable.md), [`curve_drawable`](../reference/curve_drawable.md)
