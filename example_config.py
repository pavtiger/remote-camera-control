interface = "wlan0"
port = 9002
servo_pins = [27, 17]
starting_angles = [1000, 1500]
camera_index = 0
resolution = [1280, 720]  # Width, height
step = [10, 10]  # Step distance for each moment (constant)
spill_threshold = 500  # Amount of time that is counted as error in http requests (ms)
control_mode = "drag"  # Either "joystick" or "drag"
server_ip_override = ""  # Override ip that is used on client's side to connect to remote server (leave empty not to engage or in format "http://x.x.x.x:port")

