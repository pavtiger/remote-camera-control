# All options that apply to both axis are in order: [vertical, horizontal]

# Networking
interface = "wlan0"
port = 9002

# Hardware
servo_pins = [27, 17]
starting_angles = [1000, 1500]
limits = [[500, 2500], [500, 2500]]  # Servo values in range [500, 2500]
step = [10, 10]  # Step distance for each moment (constant)
big_step = [50, 50]

# Video
camera_index = 0
video_encoding = 80
resolution = [1280, 720]  # Width, height

# Control
spill_threshold = 100  # Amount of time that is counted as error in http requests (ms)
long_press_threshold = 300
control_mode = "drag"  # Either "joystick" or "drag"
server_ip_override = ""  # Override ip that is used on client's side to connect to remote server (leave empty not to engage or in format "http://x.x.x.x:port")
mirror_video_axis = [False, False]
mirror_mouse_axis = [False, False]
axis_movements = [True, True]
