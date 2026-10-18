"""To chuc bon che do bang cac launch chinh thuc cua TurtleBot 4 Jazzy."""

from pathlib import Path
from shlex import quote

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription
from launch.actions import LogInfo, OpaqueFunction, SetEnvironmentVariable, SetLaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import EnvironmentVariable, LaunchConfiguration
from launch_ros.actions import Node, SetParameter
from nav2_common.launch import RewrittenYaml

from turtlebot4_slam_nav.map_utils import validate_map


def include(package, filename, arguments):
    """Nap launch cua package da cai."""
    path = Path(get_package_share_directory(package)) / 'launch' / filename
    return IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(path)), launch_arguments=arguments.items())


def default_map():
    """Uu tien ban do source, sau do ban do da cai vao share."""
    source = Path.home() / 'tb4_ws/src/turtlebot4_slam_nav/maps/map.yaml'
    installed = Path(get_package_share_directory('turtlebot4_slam_nav')) / 'maps/map.yaml'
    return str(source if source.exists() or not installed.exists() else installed)


def simulator_actions(context, world, model, engine):
    """Tai launch sim chinh thuc, chi bo sung co render engine cua Gazebo."""
    share = Path(get_package_share_directory('turtlebot4_gz_bringup'))
    source = PythonLaunchDescriptionSource(str(share / 'launch/sim.launch.py'))
    description = source.get_launch_description(context)
    actions = list(description.entities)
    includes = [i for i, action in enumerate(actions)
                if isinstance(action, IncludeLaunchDescription)]
    if len(includes) != 1:
        raise RuntimeError('Launch sim chinh thuc da thay doi; can kiem tra gz_sim include.')
    index = includes[0]
    gazebo = actions[index]
    local_share = Path(get_package_share_directory('turtlebot4_slam_nav'))
    world_file = world + '.sdf'
    if world == 'depot':
        world_file = str(local_share / 'worlds/depot_objects.sdf')
    actions.insert(index, SetEnvironmentVariable('GZ_SIM_RESOURCE_PATH', [
        EnvironmentVariable('GZ_SIM_RESOURCE_PATH', default_value=''),
        ':', str(local_share / 'models'),
    ]))
    index += 1
    gui_engine = LaunchConfiguration('gui_render_engine').perform(context)
    gui = LaunchConfiguration('gazebo_gui').perform(context) == 'true'
    # Giu resource path, GUI plugin path va clock bridge cua launch chinh thuc.
    # Co CLI nay ghi de engine ogre trong URDF ma khong sua mo hinh robot.
    actions[index] = GroupAction([IncludeLaunchDescription(
        gazebo.launch_description_source,
        launch_arguments={'on_exit_shutdown': 'true', 'gz_args': [
            quote(world_file), ' -r -v 3 --render-engine-server ', engine,
            ' -s',
        ]}.items())])
    if gui:
        # GUI la client cua cung server; crash GUI khong lam mat phien SLAM/Nav2.
        actions.insert(index + 1, GroupAction([IncludeLaunchDescription(
            gazebo.launch_description_source,
            launch_arguments={'on_exit_shutdown': 'false', 'gz_args': [
                '-g -v 3 --render-engine-gui ', gui_engine,
                ' --gui-config ', str(share / 'gui' / model / 'gui.config'),
            ]}.items())]))
    return actions


def launch_mode(context, mode):
    """Kiem tra map truoc khi bat simulator, chi bat thanh phan can thiet."""
    world = LaunchConfiguration('world').perform(context)
    engine = LaunchConfiguration('sensor_render_engine').perform(context)
    model = LaunchConfiguration('model').perform(context)
    rviz = LaunchConfiguration('rviz').perform(context) == 'true'
    map_path = None
    if mode in ('localization', 'navigation'):
        map_path, _ = validate_map(LaunchConfiguration('map').perform(context))

    # Tat cac thanh phan tuy chon trong simulator de tranh node trung ten.
    simulator_args = {
        'world': world, 'model': model, 'namespace': '',
        'use_sim_time': 'true', 'rviz': 'false',
        'slam': 'false', 'localization': 'false', 'nav2': 'false',
    }
    simulator_args.update({key: LaunchConfiguration(key) for key in ('x', 'y', 'z', 'yaw')})
    profile = str(Path(get_package_share_directory('turtlebot4_slam_nav'))
                  / 'config/fastdds_local.xml')
    actions = [
        SetEnvironmentVariable('RMW_IMPLEMENTATION', 'rmw_fastrtps_cpp'),
        SetEnvironmentVariable('ROS_AUTOMATIC_DISCOVERY_RANGE', 'SYSTEM_DEFAULT'),
        SetEnvironmentVariable('FASTRTPS_DEFAULT_PROFILES_FILE', profile),
        SetEnvironmentVariable('FASTDDS_DEFAULT_PROFILES_FILE', profile),
        SetParameter(name='use_sim_time', value=True),
        SetLaunchConfiguration('namespace', ''),
    ] + simulator_actions(context, world, model, engine) + [
        include('turtlebot4_gz_bringup', 'turtlebot4_spawn.launch.py', simulator_args),
    ]
    if mode == 'mapping':
        actions.append(include('turtlebot4_navigation', 'slam.launch.py', {
            'use_sim_time': 'true', 'namespace': '', 'sync': 'true',
        }))
    if map_path:
        setting = LaunchConfiguration('auto_initial_pose').perform(context)
        known_maps = [
            Path.home() / 'tb4_ws/src/turtlebot4_slam_nav/maps/depot_02.yaml',
            Path(get_package_share_directory('turtlebot4_slam_nav')) / 'maps/depot_02.yaml',
        ]
        known_start = (world == 'depot' and map_path.resolve() in
                       [path.resolve() for path in known_maps] and all(
                           float(LaunchConfiguration(key).perform(context)) == 0.0
                           for key in ('x', 'y', 'yaw')))
        automatic = setting == 'true' or (setting == 'auto' and known_start)
        params = RewrittenYaml(
            source_file=str(Path(get_package_share_directory('turtlebot4_navigation'))
                            / 'config/localization.yaml'),
            param_rewrites={
                'amcl.ros__parameters.set_initial_pose': str(automatic).lower(),
                **{f'amcl.ros__parameters.initial_pose.{key}': LaunchConfiguration(
                    f'initial_pose_{key}') for key in ('x', 'y', 'yaw')},
                'amcl.ros__parameters.initial_pose.z': '0.0',
            }, convert_types=True)
        actions.append(LogInfo(msg=(
            f'AMCL automatic initial pose: {automatic}; '
            'pose is in map coordinates (initial_pose_x/y/yaw).')))
        actions.append(include('turtlebot4_navigation', 'localization.launch.py', {
            'use_sim_time': 'true', 'namespace': '', 'map': str(map_path),
            'params': params,
        }))
    if mode == 'navigation':
        actions.append(include('turtlebot4_navigation', 'nav2.launch.py', {
            'use_sim_time': 'true', 'namespace': '',
        }))
    if rviz:
        share = Path(get_package_share_directory('turtlebot4_slam_nav'))
        config = share / 'rviz' / f'{mode}.rviz'
        actions.append(Node(
            package='rviz2', executable='rviz2', name='rviz2', output='screen',
            arguments=['-d', str(config)], parameters=[{'use_sim_time': True}]))
    actions.insert(0, LogInfo(msg=f'Che do {mode}; world={world}; use_sim_time=true'))
    return actions


def make_launch(mode):
    """Khai bao tham so chung; world va pose phai giong nhau giua cac che do."""
    args = [
        DeclareLaunchArgument('world', default_value='depot',
                              choices=['depot', 'maze', 'warehouse'],
                              description='Ten world chinh thuc (depot, maze, warehouse)'),
        DeclareLaunchArgument('sensor_render_engine', default_value='ogre2',
                              choices=['ogre2', 'ogre'],
                              description='Render engine sensor; ogre2 sua scan bi kep 0.164m'),
        DeclareLaunchArgument('gui_render_engine', default_value='ogre',
                              choices=['ogre2', 'ogre'], description='Render engine GUI Gazebo'),
        DeclareLaunchArgument('gazebo_gui', default_value='true', choices=['true', 'false'],
                              description='Mo GUI Gazebo; false chi chay server'),
        DeclareLaunchArgument('model', default_value='standard', choices=['standard', 'lite'],
                              description='Mo hinh TurtleBot 4'),
        DeclareLaunchArgument('rviz', default_value='true', choices=['true', 'false'],
                              description='Mo RViz2'),
    ]
    for key in ('x', 'y', 'z', 'yaw'):
        args.append(DeclareLaunchArgument(key, default_value='0.0',
                                          description=f'Toa do spawn {key}'))
    if mode in ('localization', 'navigation'):
        args.append(DeclareLaunchArgument('map', default_value=default_map(),
                                          description='Duong dan YAML ban do da tao bang SLAM'))
        args.append(DeclareLaunchArgument(
            'auto_initial_pose', default_value='auto', choices=['auto', 'true', 'false'],
            description='auto: tu dat pose cho depot_02 va spawn goc; true: luon tu dat'))
        for key in ('x', 'y', 'yaw'):
            args.append(DeclareLaunchArgument(
                f'initial_pose_{key}', default_value='0.0',
                description=f'AMCL initial pose {key} trong he map (yaw radian)'))
    return LaunchDescription(args + [OpaqueFunction(
        function=launch_mode, kwargs={'mode': mode})])
