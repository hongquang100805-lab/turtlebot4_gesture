"""Official TurtleBot 4 simulation with the dock away from the gesture area."""

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription
from launch.actions import OpaqueFunction, SetLaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command
from launch_ros.actions import Node, SetParameter
from launch_ros.parameter_descriptions import ParameterValue
from turtlebot4_slam_nav.launch_helpers import simulator_actions


DOCK_X, DOCK_Y, DOCK_YAW = '6.0', '6.0', '3.141592'


def dock_description():
    """Use the official dock URDF with TF matching its Gazebo corner position."""
    share = Path(get_package_share_directory('irobot_create_description'))
    xacro = share / 'urdf/dock/standard_dock.urdf.xacro'
    return [
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             name='dock_state_publisher', parameters=[{
                 'use_sim_time': True, 'robot_description': ParameterValue(Command([
                     'xacro ', str(xacro), ' gazebo:=ignition namespace:=',
                     ' visualize_rays:=false']), value_type=str)}],
             remappings=[('robot_description', 'standard_dock_description'),
                         ('/tf', 'tf'), ('/tf_static', 'tf_static')]),
        Node(package='tf2_ros', executable='static_transform_publisher',
             name='tf_odom_std_dock_link_publisher', arguments=[
                 '--x', DOCK_X, '--y', DOCK_Y, '--z', '0', '--yaw', DOCK_YAW,
                 '--pitch', '0', '--roll', '0',
                 '--frame-id', 'odom', '--child-frame-id', 'std_dock_link'])]


def spawn_in_arena(context):
    """Reuse upstream robot launch; replace only dock spawn and dock publishers."""
    share = Path(get_package_share_directory('turtlebot4_gz_bringup'))
    source = PythonLaunchDescriptionSource(str(share / 'launch/turtlebot4_spawn.launch.py'))
    actions = []
    spawn_count = description_count = 0
    for action in source.get_launch_description(context).entities:
        if not isinstance(action, GroupAction):
            actions.append(action)
            continue
        children = []
        for child in action.get_sub_entities():
            if isinstance(child, Node) and child.node_executable == 'create':
                # Match literal arguments only; do not resolve ROS LocalSubstitution.
                literals = [getattr(s, 'text', '') for arg in child.cmd for s in arg]
                if 'standard_dock_description' in literals:
                    child = Node(package='ros_gz_sim', executable='create', output='screen',
                                 arguments=['-name', 'standard_dock', '-x', DOCK_X,
                                            '-y', DOCK_Y, '-z', '0', '-Y', DOCK_YAW,
                                            '-topic', 'standard_dock_description'])
                    spawn_count += 1
            if isinstance(child, IncludeLaunchDescription):
                # Expand the public source location without executing its actions.
                child.launch_description_source.get_launch_description(context)
                path = child.launch_description_source.location
                if Path(path).name == 'dock_description.launch.py':
                    children.extend(dock_description())
                    description_count += 1
                    continue
            children.append(child)
        # The upstream subentities already contain scope push/pop actions.
        actions.append(GroupAction(actions=children, scoped=False))
    if (spawn_count, description_count) != (1, 1):
        raise RuntimeError('Upstream TurtleBot spawn changed; inspect dock launch adaptation')
    return actions


def start(context):
    share = Path(get_package_share_directory('turtlebot4_gesture_control'))
    world = str((share / 'worlds/gesture_arena').resolve())
    return [SetParameter('use_sim_time', True), SetLaunchConfiguration('namespace', ''),
            SetLaunchConfiguration('world', 'gesture_arena'),
            SetLaunchConfiguration('model', 'standard'),
            SetLaunchConfiguration('use_sim_time', 'true')] + (
        simulator_actions(context, world, 'standard', 'ogre2')) + spawn_in_arena(context)


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('gazebo_gui', default_value='true', choices=['true', 'false']),
        DeclareLaunchArgument('gui_render_engine', default_value='ogre',
                              choices=['ogre2', 'ogre']), OpaqueFunction(function=start)])
