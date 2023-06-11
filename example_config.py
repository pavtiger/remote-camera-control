# All options that apply to both axis are in order: [vertical, horizontal]
# And all quotes should be dublequote

# Networking
interface = "wlan0"
port = 9002
server_ip_override = ""  # Override ip that is used on client's side to connect to remote server (leave empty not to engage or in format "http://x.x.x.x:port")
cors_allowed_origins = ['http://192.168.1.159:9002', 'http://192.168.1.159:9003']

# Hardware
servo_pins = [27, 17]
starting_angles = [1000, 1500]
limits = [[500, 2500], [500, 2500]]  # Servo values in range [500, 2500]
mouse_sensitivity = 7 
keyboard_sensitivity = 13

# Video
camera_index = 0
video_encoding = 80
resolution = [1280, 720]  # Width, height

# Control
long_press_threshold = 300
control_mode = "drag"  # Either "joystick" or "drag"
mirror_video_axis = [False, False]
mirror_control_axis = [False, False]
axis_movements = [True, True]
