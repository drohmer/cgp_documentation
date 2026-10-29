#pragma once

#include "cgp/cgp.hpp"
#include "environment.hpp"

using cgp::mesh_drawable;

struct gui_parameters {
	bool display_frame = true;
	bool animate = true;
	float amplitude = 0.08f;               // sent as uniform "amplitude"
	cgp::vec3 wave_color = {0.2f, 0.5f, 0.9f}; // sent as uniform "wave_color"
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

	mesh_drawable global_frame;
	mesh_drawable surface;          // flat grid, displaced by the vertex shader
	opengl_shader_structure shader_wave;
	timer_basic timer;

	void mouse_move_event();
	void mouse_click_event();
	void keyboard_event();
	void idle_frame();
};
