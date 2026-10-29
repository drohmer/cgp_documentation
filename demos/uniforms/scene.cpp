// Demo of the Understand page "Shaders and uniforms" (content/understand/shaders-and-uniforms.md).
// A flat grid is displaced by a custom vertex shader (shaders/wave/). Three user uniforms,
// set in environment.uniform_generic, control it: time, amplitude and wave_color.
// No external asset.
#include "scene.hpp"

using namespace cgp;

void scene_structure::initialize()
{
	camera_control.initialize(inputs, window);
	camera_control.set_rotation_axis_z();
	camera_control.look_at({1.6f, -2.2f, 1.6f} /*eye*/, {-0.3f,-0.2f,0.15f} /*target*/, {0,0,1} /*up*/);

	// The default shader also receives "time", "amplitude", "wave_color": silence the warnings
	cgp_warning::max_warning = 0;

	global_frame.initialize_data_on_gpu(mesh_primitive_frame());

	// Load the custom shader (section 4 of the page)
	shader_wave.load(
		project::path + "shaders/wave/wave.vert.glsl",
		project::path + "shaders/wave/wave.frag.glsl");

	// A flat grid of 100 x 100 vertices: the shape is computed by the vertex shader
	mesh grid = mesh_primitive_grid({-1,-1,0}, {1,-1,0}, {1,1,0}, {-1,1,0}, 100, 100);
	surface.initialize_data_on_gpu(grid, shader_wave);
}

void scene_structure::display_frame()
{
	environment.camera_view = camera_control.camera().matrix_view();
	environment.light = camera_control.camera_model.position();

	if (gui.animate)
		timer.update();

	// User uniforms (section 3 of the page): the same value for every vertex of the draw call
	environment.uniform_generic.uniform_float["time"] = timer.t;
	environment.uniform_generic.uniform_float["amplitude"] = gui.amplitude;
	environment.uniform_generic.uniform_vec3["wave_color"] = gui.wave_color;

	if (gui.display_frame)
		draw(global_frame, environment);
	draw(surface, environment);
}

void scene_structure::display_gui()
{
	ImGui::Checkbox("Frame", &gui.display_frame);
	ImGui::Checkbox("Animate (time)", &gui.animate);
	ImGui::SliderFloat("amplitude", &gui.amplitude, 0.0f, 0.2f);
	ImGui::ColorEdit3("wave_color", &gui.wave_color[0]);
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
