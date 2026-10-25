"""Reconnect a GUI client to the running arena without restarting physics."""

from pathlib import Path
from shlex import quote

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction, SetEnvironmentVariable
from launch.substitutions import EnvironmentVariable, LaunchConfiguration
from turtlebot4_slam_nav.launch_helpers import include


def start(context):
    bringup = Path(get_package_share_directory('turtlebot4_gz_bringup'))
    gui_plugins = Path(get_package_share_directory('turtlebot4_gz_gui_plugins')) / 'lib'
    create_plugins = Path(get_package_share_directory('irobot_create_gz_plugins')) / 'lib'
    resources = [str(Path(get_package_share_directory(name)).parent)
                 for name in ('turtlebot4_description', 'irobot_create_description')]
    engine = LaunchConfiguration('gui_render_engine').perform(context)
    config = bringup / 'gui/standard/gui.config'
    return [
        SetEnvironmentVariable('GZ_GUI_PLUGIN_PATH', [
            EnvironmentVariable('GZ_GUI_PLUGIN_PATH', default_value=''), ':',
            str(gui_plugins), ':', str(create_plugins)]),
        SetEnvironmentVariable('GZ_SIM_RESOURCE_PATH', [
            EnvironmentVariable('GZ_SIM_RESOURCE_PATH', default_value=''), ':',
            ':'.join(resources)]),
        include('ros_gz_sim', 'gz_sim.launch.py', {
            'on_exit_shutdown': 'false',
            'gz_args': f'-g -v 3 --render-engine-gui {engine} --gui-config {quote(str(config))}'})]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('gui_render_engine', default_value='ogre',
                              choices=['ogre', 'ogre2']),
        OpaqueFunction(function=start)])
