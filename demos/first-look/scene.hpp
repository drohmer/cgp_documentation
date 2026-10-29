#pragma once

#include "cgp/cgp.hpp"
#include "environment.hpp"

using cgp::mesh_drawable;

struct gui_parameters {
	int snippet = 0;   // 0: shapes, 1: exploded cube, 2: terrain
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

	// the drawables of the three snippets of the home page
	mesh_drawable sphere;
	mesh_drawable torus;
	mesh_drawable cube_drawable;
	mesh_drawable terrain_drawable;
	int framed_snippet = -1;

	void frame_camera();

	void mouse_move_event();
	void mouse_click_event();
	void keyboard_event();
	void idle_frame();
};
