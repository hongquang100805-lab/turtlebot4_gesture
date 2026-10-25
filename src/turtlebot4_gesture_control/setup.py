from glob import glob

from setuptools import find_packages, setup

name = 'turtlebot4_gesture_control'
setup(
    name=name, version='0.1.0', packages=find_packages(exclude=['test']),
    data_files=[('share/ament_index/resource_index/packages', ['resource/' + name]),
                ('share/' + name, ['package.xml', 'README.md', 'VALIDATION.md']),
                ('share/' + name + '/launch', glob('launch/*.launch.py')),
                ('share/' + name + '/config', glob('config/*.yaml')),
                ('share/' + name + '/worlds', glob('worlds/*.sdf'))],
    scripts=['scripts/setup_gesture.sh'], install_requires=['setuptools'],
    extras_require={'test': ['pytest']},
    maintainer='lenovo', maintainer_email='hongquang100805@gmail.com', license='Apache-2.0',
    description='Webcam hand gesture interaction for TurtleBot 4',
    entry_points={'console_scripts': [
        'gesture_recognition_node = turtlebot4_gesture_control.gesture_recognition_node:main',
        'robot_behavior_node = turtlebot4_gesture_control.robot_behavior_node:main']})
