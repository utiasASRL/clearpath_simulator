"""
Generic simulated platform service launch.

This is a parameterized version of a Clearpath-style platform service launch.

The included platform launch is also configurable. By default it preserves the
Clearpath behavior by including clearpath_common/launch/platform.launch.py.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    # Core robot instance arguments.
    namespace = LaunchConfiguration("namespace")
    setup_path = LaunchConfiguration("setup_path")
    use_sim_time = LaunchConfiguration("use_sim_time")

    # Included platform launch arguments.
    enable_ekf = LaunchConfiguration("enable_ekf")
    use_manipulation_controllers = LaunchConfiguration("use_manipulation_controllers")

    # Gazebo / Ignition model addressing.
    gz_model_prefix = ["/model/", namespace, "/robot"]

    # Config files derived from setup_path unless explicitly overridden.
    imu_filter = PathJoinSubstitution([setup_path, "platform", "config", "imu_filter.yaml"])
    imu_bridge_config = PathJoinSubstitution([setup_path, "sensors", "config", "imu_0.yaml"])

    launch_args = [
        DeclareLaunchArgument("namespace", description="ROS namespace for this robot instance.",),
        DeclareLaunchArgument("setup_path", description="Robot setup directory containing platform/config and sensors/config subdirectories.",),
        DeclareLaunchArgument("use_sim_time", default_value="true", description="Use simulation time for all nodes launched here.",),
        DeclareLaunchArgument("enable_ekf", default_value="true", description="Forwarded to the included platform launch file.",),
        DeclareLaunchArgument("use_manipulation_controllers", default_value="true", description="Forwarded to the included platform launch file.",),
    ]

    # Clearpath Common platform launch
    platform_launch_path = PathJoinSubstitution([FindPackageShare('clearpath_common'), "launch", 'platform.launch.py'])
    launch_platform = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(platform_launch_path),
        launch_arguments={
            "setup_path": setup_path,
            "use_sim_time": use_sim_time,
            "namespace": namespace,
            "enable_ekf": enable_ekf,
            "use_manipulation_controllers": use_manipulation_controllers,
        }.items(),
    )

    cmd_vel_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="cmd_vel_bridge",
        namespace=namespace,
        output="screen",
        arguments=[
            [namespace, "/cmd_vel@geometry_msgs/msg/Twist[ignition.msgs.Twist"],
            [*gz_model_prefix, "/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist"],
        ],
        remappings=[
            ([namespace, "/cmd_vel"], "cmd_vel"),
            ([*gz_model_prefix, "/cmd_vel"], "platform/cmd_vel_unstamped"),
        ],
        parameters=[{"use_sim_time": use_sim_time}],
    )

    odom_base_tf_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="odom_base_tf_bridge",
        namespace=namespace,
        output="screen",
        arguments=[
            [*gz_model_prefix, "/pose@tf2_msgs/msg/TFMessage[ignition.msgs.Pose_V"],
        ],
        remappings=[
            ([*gz_model_prefix, "/pose"], "tf"),
        ],
        parameters=[{"use_sim_time": use_sim_time}],
    )

    imu_0_gz_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="imu_0_gz_bridge",
        namespace=namespace,
        output="screen",
        parameters=[
            {
                "use_sim_time": use_sim_time,
                "config_file": imu_bridge_config,
            }
        ],
    )

    imu_filter_node = Node(
        package="imu_filter_madgwick",
        executable="imu_filter_madgwick_node",
        name="imu_filter_node",
        namespace=namespace,
        output="screen",
        remappings=[
            ("imu/data_raw", "sensors/imu_0/data_raw"),
            ("imu/mag", "sensors/imu_0/magnetic_field"),
            ("imu/data", "sensors/imu_0/data"),
            ("/tf", "tf"),
        ],
        parameters=[imu_filter],
    )

    # Create LaunchDescription
    ld = LaunchDescription()
    for launch_arg in launch_args:
        ld.add_action(launch_arg)
    ld.add_action(launch_platform)
    ld.add_action(cmd_vel_bridge)
    ld.add_action(odom_base_tf_bridge)
    ld.add_action(imu_0_gz_bridge)
    ld.add_action(imu_filter_node)
    return ld
