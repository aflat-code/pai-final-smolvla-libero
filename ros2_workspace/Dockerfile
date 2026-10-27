FROM airobotbook/ros2-desktop-ai-robot-book-humble:latest

WORKDIR /workspace
COPY src ./src
RUN /bin/bash -lc "source /opt/ros/humble/setup.bash && colcon build --symlink-install"

ENV DISPLAY=:0
CMD ["/bin/bash", "-lc", "source /opt/ros/humble/setup.bash && source /workspace/install/setup.bash && ros2 launch pai_gazebo_demo demo.launch.py"]
