# All options that apply to both axis are in order: [vertical, horizontal]

# Networking
interface = "wlan0"
port = 9002

# Hardware
servo_pins = [27, 17]
starting_angles = [1000, 1500]
limits = [[500, 2500], [500, 2500]]  # Servo values in range [500, 2500]
step = [10, 10]  # Step distance for each moment (constant)

# Video
camera_index = 0
video_encoding = 80
resolution = [1280, 720]  # Width, height

# Control
spill_threshold = 500  # Amount of time that is counted as error in http requests (ms)
control_mode = "drag"  # Either "joystick" or "drag"
mirror_video_axis = [False, False]
mirror_mouse_axis = [False, False]
axis_movements = [True, True]

