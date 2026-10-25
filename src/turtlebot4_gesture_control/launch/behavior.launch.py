"""Start only the behavior controller; perception runs in its own Python venv."""
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    params = (Path(get_package_share_directory('turtlebot4_gesture_control'))
              / 'config/behavior.yaml')
    return LaunchDescription([Node(
        package='turtlebot4_gesture_control', executable='robot_behavior_node', output='screen',
        parameters=[str(params), {'use_sim_time': True}])])
