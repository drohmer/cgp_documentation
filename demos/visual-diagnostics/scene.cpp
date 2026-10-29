// Demo of the page "Troubleshooting and error messages" (content/get-started/troubleshooting.md),
// section "Symptoms without a message". Two textured spheres: the left one is correct, the
// right one shows the symptom chosen in the GUI (or by the URL: index.html#3 shows case 3).
// Asset: assets/checkerboard.png, from github.com/drohmer/csc43043ep-lab-code
// (05_shaders/a_shader_manipulation/assets/checkerboard.png).
#include "scene.hpp"
#ifdef __EMSCRIPTEN__
#include <emscripten.h>
#endif

using namespace cgp;

static char const* const symptom_names[] = {
	"None (both correct)", "Null normals", "Inverted normals", "No uv",
	"Normals not updated after a deformation", "Transparent shape drawn first" };

// Bumpy sphere: the vertices are moved along their normal
static void deform(mesh& m)
{
	for (int k = 0; k < m.position.size(); ++k) {
		vec3 const& p = m.position[k];
		m.position[k] += 0.25f * std::sin(5 * std::atan2(p.y, p.x)) * std::sin(4 * p.z) * m.normal[k];
	}
}

void scene_structure::build_shapes()
{
	symptom const s = symptom(gui.symptom);
	mesh reference = mesh_primitive_sphere(1.0f, {0,0,0}, 80, 40);
	mesh broken = reference;

	if (s == symptom::null_normals)
		broken.normal.fill({0,0,0});                        // e.g. a mesh built by hand without normals
	if (s == symptom::inverted_normals)
		for (vec3& n : broken.normal) n = -n;               // normals pointing inside
	if (s == symptom::no_uv)
		broken.uv.fill({0,0});                              // every vertex reads the same texel
	if (s == symptom::stale_normals) {
		deform(reference);
		reference.normal_update();                          // correct: normals recomputed
		deform(broken);                                     // symptom: normals of the sphere kept
	}

	// New shapes for a new case: these drawables are not copies, clear() is safe here
	if (built_symptom != -1) { left.clear(); right.clear(); }
	left.initialize_data_on_gpu(reference);
	right.initialize_data_on_gpu(broken);
	left.texture = checkerboard;
	right.texture = checkerboard;
	left.model.translation = {-1.3f, 0, 0};
	right.model.translation = {1.3f, 0, 0};
	built_symptom = gui.symptom;
}

void scene_structure::initialize()
{
	camera_control.initialize(inputs, window);
	camera_control.set_rotation_axis_z();
	camera_control.look_at({0.0f, -5.0f, 1.2f} /*eye*/, {0,0,0} /*target*/, {0,0,1} /*up*/);

#ifdef __EMSCRIPTEN__
	gui.symptom = emscripten_run_script_int("parseInt(window.location.hash.slice(1)) || 0");
	if (gui.symptom < 0 || gui.symptom > 5) gui.symptom = 0;
#endif

	checkerboard.load_and_initialize_texture_2d_on_gpu(project::path + "assets/checkerboard.png");

	// Two semi-transparent quads in front of the spheres
	mesh quad = mesh_primitive_quadrangle({-0.9f,0,-0.9f}, {0.9f,0,-0.9f}, {0.9f,0,0.9f}, {-0.9f,0,0.9f});
	glass_left.initialize_data_on_gpu(quad);
	glass_left.material.color = {0.2f, 0.5f, 0.9f};
	glass_left.material.alpha = 0.4f;
	glass_left.material.phong = {1, 0, 0, 1};
	glass_left.material.texture_settings.two_sided = true;
	glass_right = glass_left;                               // a copy: same buffers, own model
	glass_left.model.translation = {-1.3f, -1.4f, 0};
	glass_right.model.translation = {1.3f, -1.4f, 0};

	build_shapes();
}

void scene_structure::display_frame()
{
	environment.camera_view = camera_control.camera().matrix_view();
	environment.light = camera_control.camera_model.position();

	if (gui.symptom != built_symptom)
		build_shapes();
	bool const glass = symptom(gui.symptom) == symptom::transparency_order;

	if (glass) {
		// symptom: the transparent quad is drawn first, and writes its depth
		glEnable(GL_BLEND);
		glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
		draw(glass_right, environment);
		glDisable(GL_BLEND);
	}

	draw(left, environment);
	draw(right, environment);

	if (glass) {
		// correct: opaque shapes first, then the transparent one without writing its depth
		glEnable(GL_BLEND);
		glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
		glDepthMask(false);
		draw(glass_left, environment);
		glDepthMask(true);
		glDisable(GL_BLEND);
	}
}

void scene_structure::display_gui()
{
	ImGui::Text("Left: correct. Right: symptom.");
	ImGui::Combo("Symptom", &gui.symptom, symptom_names, IM_ARRAYSIZE(symptom_names));
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
