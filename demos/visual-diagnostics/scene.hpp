#pragma once

#include "cgp/cgp.hpp"
#include "environment.hpp"

using cgp::mesh_drawable;

// The symptoms shown on the right shape (the left shape is always correct)
enum class symptom { none, null_normals, inverted_normals, no_uv, stale_normals, transparency_order };

struct gui_parameters {
	int symptom = 0;   // index in the enum symptom
};

struct scene_structure : cgp::scene_inputs_generic {

	void initialize();
	void display_frame();
	void display_gui();

	environment_structure environment;
	window_structure window;
	input_devices inputs;
	gui_parameters gui;

	void display_info();

	camera_controller_orbit_euler camera_control;
	camera_projection_perspective camera_projection;

	opengl_texture_image_structure checkerboard;
	mesh_drawable left;         // the correct shape
	mesh_drawable right;        // the same shape with the symptom
	mesh_drawable glass_left;   // semi-transparent quads (case transparency_order)
	mesh_drawable glass_right;
	int built_symptom = -1;     // symptom of the current buffers of left / right

	void build_shapes();

	void mouse_move_event();
	void mouse_click_event();
	void keyboard_event();
	void idle_frame();
};
