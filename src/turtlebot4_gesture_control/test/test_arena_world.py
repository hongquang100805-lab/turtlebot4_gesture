"""The bridge namespace must match the SDF world, not an upstream default."""

import importlib.util
from pathlib import Path
import xml.etree.ElementTree as ET

from launch import LaunchContext
from launch.actions import GroupAction, SetLaunchConfiguration
from launch_ros.actions import Node


def test_bridge_world_matches_sdf():
    package = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location('arena', package / 'launch/arena.launch.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    context = LaunchContext()
    context.launch_configurations.update(gazebo_gui='false', gui_render_engine='ogre2')
    for action in module.start(context):
        if isinstance(action, SetLaunchConfiguration):
            action.execute(context)
    sdf_world = ET.parse(package / 'worlds/gesture_arena.sdf').getroot().find('world')
    assert context.launch_configurations['world'] == sdf_world.attrib['name']


def test_dock_spawn_and_tf_are_both_outside_demo_area():
    package = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location('arena', package / 'launch/arena.launch.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    nodes = []

    def collect(action):
        if isinstance(action, Node):
            nodes.append((action.node_executable,
                          [getattr(s, 'text', '') for arg in action.cmd for s in arg]))
        if isinstance(action, GroupAction):
            for child in action.get_sub_entities():
                collect(child)

    for action in module.spawn_in_arena(LaunchContext()):
        collect(action)
    dock = [args for exe, args in nodes
            if exe == 'create' and 'standard_dock_description' in args]
    tf = [args for exe, args in nodes
          if exe == 'static_transform_publisher' and 'std_dock_link' in args]
    assert len(dock) == len(tf) == 1
    assert dock[0][dock[0].index('-x') + 1] == tf[0][tf[0].index('--x') + 1] == '6.0'
    assert dock[0][dock[0].index('-y') + 1] == tf[0][tf[0].index('--y') + 1] == '6.0'
