# Discovery through /rosapi/topics is not assumed to be available.
DEFAULT_TOPICS_LIST = '''
/aruco_detect/debug /aruco_detect/markers /aruco_detect/parameter_descriptions
/aruco_detect/parameter_updates /aruco_detect/visualization /aruco_map/debug
/aruco_map/image /aruco_map/map /aruco_map/parameter_descriptions
/aruco_map/parameter_updates /aruco_map/pose /aruco_map/visualization
/client_count /connected_clients /diagnostics /emergency /landing_target /led/state
/lt_marker /main_camera_nodelet_manager/bond /main_camera/camera_info
/main_camera/camera_markers /main_camera/image_raw /main_camera/image_raw_throttled
/main_camera/image_web_raw /mavlink/from /mavlink/gcs_ip /mavlink/to
/mavros/altitude /mavros/battery /mavros/distance_sensor/rangefinder
/mavros/distance_sensor/rangefinder_sub /mavros/estimator_status /mavros/extended_state
/mavros/global_position/compass_hdg /mavros/global_position/global
/mavros/global_position/gp_lp_offset /mavros/global_position/gp_origin
/mavros/global_position/local /mavros/global_position/raw/fix
/mavros/global_position/raw/gps_vel /mavros/global_position/raw/satellites
/mavros/global_position/rel_alt /mavros/global_position/set_gp_origin
/mavros/home_position/home /mavros/imu/data /mavros/imu/data_raw
/mavros/imu/diff_pressure /mavros/imu/mag /mavros/imu/static_pressure
/mavros/imu/temperature_baro /mavros/imu/temperature_imu
/mavros/local_position/accel /mavros/local_position/odom /mavros/local_position/pose
/mavros/local_position/pose_cov /mavros/local_position/velocity_body
/mavros/local_position/velocity_body_cov /mavros/local_position/velocity_local
/mavros/manual_control/control /mavros/manual_control/send /mavros/param/param_value
/mavros/px4flow/ground_distance /mavros/px4flow/raw/optical_flow_rad
/mavros/px4flow/raw/send /mavros/px4flow/temperature /mavros/rangefinder/rangefinder
/mavros/rc/in /mavros/rc/out /mavros/rc/override /mavros/setpoint_attitude/attitude
/mavros/setpoint_attitude/cmd_vel /mavros/setpoint_attitude/thrust
/mavros/setpoint_position/global /mavros/setpoint_position/global_to_local
/mavros/setpoint_position/local /mavros/setpoint_raw/attitude /mavros/setpoint_raw/global
/mavros/setpoint_raw/local /mavros/setpoint_raw/target_attitude
/mavros/setpoint_raw/target_global /mavros/setpoint_raw/target_local
/mavros/setpoint_velocity/cmd_vel /mavros/setpoint_velocity/cmd_vel_unstamped
/mavros/state /mavros/statustext/recv /mavros/statustext/send /mavros/sys_status
/mavros/time_reference /mavros/timesync_status /mavros/vision_pose/pose
/mavros/vision_pose/pose_cov /mavros/vision_speed/speed_twist_cov
/optical_flow/angular_velocity /optical_flow/debug /optical_flow/parameter_descriptions
/optical_flow/parameter_updates /optical_flow/shift /rangefinder/data /rangefinder/range
/rosout /rosout_agg /second_camera/camera_info
/second_camera/second_camera/detections_classes /second_camera/second_camera/face_annotated
/second_camera/second_camera/image_raw /simple_offboard/state /technic_blocks/block
/technic_blocks/error /technic_blocks/print /technic_blocks/prompt /technic_blocks/running
/tf /tf_static /track_markers /vehicle_marker /vpe_publisher/pose /wp_markers
'''.split()
