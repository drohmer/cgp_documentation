// Demo of the home page, section "A first look" (content/index.md): the three snippets shown
// next to their image. The code between the markers `// snippet:` and `// end` is the code
// of the page, character for character (tests/e2e/test_protos.py, check_snippets). The image
// of each snippet is captured from this demo (index.html#k shows snippet k) by
// tools/figures/first_look_captures.py. No asset.
#include "scene.hpp"
#ifdef __EMSCRIPTEN__
#include <emscripten.h>
#endif

using namespace cgp;

static char const* const snippet_names[] = { "Shapes", "Exploded cube", "Terrain" };

void scene_structure::initialize()
{
	camera_control.initialize(inputs, window);
	camera_control.set_rotation_axis_z();

#ifdef __EMSCRIPTEN__
	gui.snippet = emscripten_run_script_int("parseInt(window.location.hash.slice(1)) || 0");
	if (gui.snippet < 0 || gui.snippet > 2) gui.snippet = 0;
#endif

	// snippet: shapes - initialize
	sphere.initialize_data_on_gpu(mesh_primitive_sphere(0.5f));
	sphere.material.color = {1.0f, 0.6f, 0.4f};

	mesh torus_mesh = mesh_primitive_torus(0.6f, 0.15f);
	torus.initialize_data_on_gpu(torus_mesh);
	torus.model.translation = {1.4f, 0.0f, 0.0f};
	torus.material.color = {0.4f, 0.6f, 1.0f};
	// end

	// snippet: cube - initialize
	mesh cube = mesh_primitive_cube();
	for (int k = 0; k < cube.position.size(); ++k)
		cube.position[k] += 0.1f * cube.normal[k];

	cube_drawable.initialize_data_on_gpu(cube);
	cube_drawable.material.color = {1, 1, 0};
	// end

	// snippet: terrain - initialize
	mesh terrain = mesh_primitive_grid({-2,-2,0}, {2,-2,0},
	    {2,2,0}, {-2,2,0}, 150, 150);
	for (int k = 0; k < terrain.position.size(); ++k) {
		vec3& p = terrain.position[k];
		p.z = 0.8f * noise_perlin(0.5f * vec2{p.x, p.y}, 6);
	}
	terrain.normal_update();

	terrain_drawable.initialize_data_on_gpu(terrain);
	terrain_drawable.material.color = {0.5f, 0.8f, 0.4f};
	// end

	frame_camera();
}

// Camera of each snippet (not part of the snippets)
void scene_structure::frame_camera()
{
	if (gui.snippet == 0)
		camera_control.look_at({0.7f, -3.2f, 1.6f}, {0.7f, 0.0f, 0.0f});
	if (gui.snippet == 1)
		camera_control.look_at({2.2f, -1.8f, 1.6f}, {0.0f, 0.0f, 0.0f});
	if (gui.snippet == 2)
		camera_control.look_at({3.7f, -3.7f, 3.2f}, {0.0f, 0.0f, 0.0f});
	framed_snippet = gui.snippet;
}

void scene_structure::display_frame()
{
	environment.camera_view = camera_control.camera().matrix_view();
	environment.light = camera_control.camera_model.position();
	if (gui.snippet != framed_snippet)
		frame_camera();

	if (gui.snippet == 0) {
		// snippet: shapes - display_frame
		draw(sphere, environment);
		draw(torus, environment);
		// end
	}
	if (gui.snippet == 1) {
		// snippet: cube - display_frame
		draw(cube_drawable, environment);
		// end
	}
	if (gui.snippet == 2) {
		// snippet: terrain - display_frame
		draw(terrain_drawable, environment);
		// end
	}
}

void scene_structure::display_gui()
{
	ImGui::Combo("Snippet", &gui.snippet, snippet_names, IM_ARRAYSIZE(snippet_names));
}

void scene_structure::mouse_move_event()
{
	if (!inputs.keyboard.shift)
		camera_control.action_mouse_move();
}
void scene_structure::mouse_click_event() { camera_control.action_mouse_click(); }
void scene_structure::keyboard_event() { camera_control.action_keyboard(); }
void scene_structure::idle_frame() { camera_control.idle_frame(); }
void scene_structure::display_info() {}
