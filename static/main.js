const HTTP = new XMLHttpRequest();


function httpGet(url) {
    let xmlHttp = new XMLHttpRequest();
    xmlHttp.open("GET", url, false); // false for synchronous request
    xmlHttp.send(null);
    return JSON.parse(xmlHttp.responseText);
}

function httpSend(url, body) {
    let xmlHttp = new XMLHttpRequest();
    xmlHttp.open("POST", url, false); // false for synchronous request
    xmlHttp.setRequestHeader("Content-Type", "text/json");
    xmlHttp.send(JSON.stringify(body));
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// For todays date;
Date.prototype.today = function () {
    return ((this.getDate() < 10)?"0":"") + this.getDate() +"."+(((this.getMonth()+1) < 10)?"0":"") + (this.getMonth()+1) +"."+ this.getFullYear();
}

// For the time now
Date.prototype.timeNow = function () {
     return ((this.getHours() < 10)?"0":"") + this.getHours() +"-"+ ((this.getMinutes() < 10)?"0":"") + this.getMinutes() +"-"+ ((this.getSeconds() < 10)?"0":"") + this.getSeconds();
}


const max_move_dist = 300;
let mouse_down = false;
let mouse_click_pos = [];
let last_mouse_pos = [];
let mouse_pos = [];
let pressed = { "up": false, "down": false, "left": false, "right": false }
let stop_stream = false;
document.getElementById("image").setAttribute("draggable", false);


const control_socket = io.connect(control_address);
const video_socket = io.connect(video_address);

control_socket.on("turn_off_lazer", () => {
    opt.lazer_on = false;
});

video_socket.on("image", (image) => {
    if (!stop_stream) {
        let imageElem = document.getElementById("image");
        imageElem.src = `data:image/jpeg;base64,${image}`;
    }
});

video_socket.on("send_snapshot", (image) => {
    stop_stream = true;
    let imageElem = document.getElementById("image");
    imageElem.src = `data:image/jpeg;base64,${image}`;

    if (opt.download_snapshot) {
        console.log("here");
        // Download base64 image
        var a = document.createElement("a");  // Create <a>
        a.href = "data:image/png;base64," + image;  // Image Base64 Goes here
        a.download = new Date().today() + "_" + new Date().timeNow() + ".png";
        document.body.appendChild(a);
        a.click();  // Downloaded file
        document.body.removeChild(a);
    }
});
document.getElementById("image").ondragstart = function() { return false; };  // Disable image drag


const Options = function() {
    // Retrieve options from server
    this.options = httpGet(control_address + "/options");

    this.pos_vert = 0;
    this.pos_hor = 0;

    this.servo_pins_vert = this.options["servo_pins"][0];
    this.servo_pins_hor = this.options["servo_pins"][1];

    this.starting_angles_vert = this.options["starting_angles"][0];
    this.starting_angles_hor = this.options["starting_angles"][1];

    this.limits_vert_start = this.options["limits"][0][0];
    this.limits_vert_end = this.options["limits"][0][1];
    this.limits_hor_start = this.options["limits"][1][0];
    this.limits_hor_end = this.options["limits"][1][1];

    this.mouse_sensitivity = this.options["mouse_sensitivity"];
    this.keyboard_sensitivity = this.options["keyboard_sensitivity"];

    this.camera_index = this.options["camera_index"];
    this.resolution = "[" + this.options["resolution"][0] + ", " + this.options["resolution"][1] + "]";
    this.hq_resolution = "[" + this.options["hq_resolution"][0] + ", " + this.options["hq_resolution"][1] + "]";
    this.video_encoding = this.options["video_encoding"];

    this.download_snapshot = true;
    this.lazer_on = false;

    this.control_mode = this.options["control_mode"];

    this.mirror_video_axis_vert = Boolean(this.options["mirror_video_axis"][0]);
    this.mirror_video_axis_hor = Boolean(this.options["mirror_video_axis"][1]);
    this.mirror_control_axis_vert = Boolean(this.options["mirror_control_axis"][0]);
    this.mirror_control_axis_hor = Boolean(this.options["mirror_control_axis"][1]);
    this.axis_movements_vert = Boolean(this.options["axis_movements"][0]);
    this.axis_movements_hor = Boolean(this.options["axis_movements"][1]);


    this.restart = function() {
        HTTP.open("post", control_address + "/restart");
        HTTP.send();
    }

    this.poweroff = function() {
        HTTP.open("POST", control_address + "/poweroff");
        HTTP.send();
    }

    this.flip_axis = function() {
        [this.servo_pins_vert, this.servo_pins_hor] = [this.servo_pins_hor, this.servo_pins_vert];
        for (var i in gui.__controllers) {
            gui.__controllers[i].updateDisplay();
        }

        HTTP.open("POST", control_address + "/change-servo_pins-[" + Math.round(this.servo_pins_vert) + ", " + Math.round(this.servo_pins_hor) + "]");
        HTTP.send();
    }

    this.snapshot = function() {
        video_socket.emit("snapshot");
    }
};


// Dat Gui controls setup
let opt = new Options();
gui = new dat.GUI({
    load: JSON,
    preset: "Flow",
    width: 500
});


let fPos = gui.addFolder("Current position");
let gPosVert = fPos.add(opt, "pos_vert", 500, 2500).name("Vertical").listen();
gPosVert.onChange(function(value) {
    control_socket.emit("set_pos", Math.round(value), Math.round(opt.pos_hor));
});
let gPosHor = fPos.add(opt, "pos_hor", 500, 2500).name("Horizontal").listen();
gPosHor.onChange(function(value) {
    control_socket.emit("set_pos", Math.round(opt.pos_vert), Math.round(value));
});
fPos.open();


let fServoPins = gui.addFolder("Servo pins");
let gServoPinsVert = fServoPins.add(opt, "servo_pins_vert").name("Vertical");
gServoPinsVert.onChange(function(value) {
    HTTP.open("POST", control_address + "/change-servo_pins-[" + Math.round(value).toString() + ", " + Math.round(opt.servo_pins_hor).toString() + "]");
    HTTP.send();
});
let gServoPinsHor = fServoPins.add(opt, "servo_pins_hor").name("Horizontal");
gServoPinsHor.onChange(function(value) {
    HTTP.open("POST", control_address + "/change-servo_pins-[" + Math.round(opt.servo_pins_vert).toString() + ", "  + Math.round(value).toString() + "]");
    HTTP.send();
});
fServoPins.add(opt, "restart").name("Apply");

gui.add(opt, "flip_axis").name("Flip axis");


let fStartingAngles = gui.addFolder("Servo starting angles");
let gStartingAnglesVert = fStartingAngles.add(opt, "starting_angles_vert", 500, 2500).name("Vertical");
gStartingAnglesVert.onChange(function(value) {
    HTTP.open("POST", control_address + "/change-starting_angles-[" + Math.round(value).toString() + ", " + Math.round(opt.starting_angles_hor).toString() + "]");
    HTTP.send();
});
let gStartingAnglesHor = fStartingAngles.add(opt, "starting_angles_hor", 500, 2500).name("Horizontal");
gStartingAnglesHor.onChange(function(value) {
    HTTP.open("POST", control_address + "/change-starting_angles-[" + Math.round(opt.starting_angles_vert).toString() + ", " + Math.round(value).toString() + "]");
    HTTP.send();
});

// let fLimits = gui.addFolder("Servo limits on each axis");
// let gLimitsVertStart = fLimits.add(opt, "limits_vert_start", 500, 2500).name("Vertical start");
// let gLimitsVertEnd = fLimits.add(opt, "limits_vert_end", 500, 2500).name("Vertical end");
// let gLimitsHorStart = fLimits.add(opt, "limits_hor_start", 500, 2500).name("Horizontal start");
// let gLimitsHorEnd = fLimits.add(opt, "limits_hor_end", 500, 2500).name("Horizontal end");


let fStep = gui.addFolder("Sensitivity (step distances)");
let gMouseSen = fStep.add(opt, "mouse_sensitivity", 1, 30).name("Mouse sensitivity");
gMouseSen.onChange(function(value) {
    HTTP.open("POST", control_address + "/change-mouse_sensitivity-" + Math.round(value).toString());
    HTTP.send();
});

let gKeySen = fStep.add(opt, "keyboard_sensitivity", 1, 30).name("Keyboard sensitivity");
gKeySen.onChange(function(value) {
    HTTP.open("POST", control_address + "/change-keyboard_sensitivity-" + Math.round(value).toString());
    HTTP.send();
});

fStep.open();


let fVideo = gui.addFolder("Video settings");
let available_cameras = httpGet(video_address + "/available_cameras");

let gCameraIndex = fVideo.add(opt, "camera_index", available_cameras).name("Camera index in system");
gCameraIndex.onChange(function(value) {
    video_socket.emit("options", "camera_index", Math.round(value));
});


let fFunctions = gui.addFolder("Additional functions");
fFunctions.add(opt, "snapshot").name("Take HQ snapshot");
fFunctions.add(opt, "download_snapshot").name("Download snapshot");
let gLazerOn = fFunctions.add(opt, "lazer_on").name("Turn on/off lazer").listen();

gLazerOn.onChange(function(value) {
    control_socket.emit("set_lazer", value);
});
fFunctions.open()


let gResolution = fVideo.add(opt, "resolution", ["[320, 240]", "[480, 360]", "[640, 360]", "[640, 480]", "[1056, 594]", "[1280, 720]", "[1920, 1080]"]).name("Video resolution");
gResolution.onChange(function(value) {
    video_socket.emit("options", "resolution", value);
});
let gHQResolution = fVideo.add(opt, "hq_resolution", ["[320, 240]", "[480, 360]", "[640, 360]", "[640, 480]", "[1056, 594]", "[1280, 720]", "[1920, 1080]"]).name("Snapshot resolution");
gHQResolution.onChange(function(value) {
    video_socket.emit("options", "hq_resolution", value);
});

let gVideoEncoding = fVideo.add(opt, "video_encoding", 0, 100).name("Video encoding");
gVideoEncoding.onChange(function(value) {
    video_socket.emit("options", "video_encoding", Math.round(value));
});
fVideo.open();


let gControlsMode = gui.add(opt, "control_mode", ["drag", "joystick"]).name("Control mode");
gControlsMode.onChange(function(value) {
    HTTP.open("POST", control_address + "/change-control_mode-\"" + value + "\"");
    HTTP.send();
});

let fMirrorVideo = gui.addFolder("Mirror video for axis");
let gMirrorVideoVert = fMirrorVideo.add(opt, "mirror_video_axis_vert").name("Mirror video vertically");
gMirrorVideoVert.onChange(function(value) {
    video_socket.emit("options", "mirror_video_axis", [value, opt.mirror_video_axis_hor]);
});
let gMirrorVideoHor = fMirrorVideo.add(opt, "mirror_video_axis_hor").name("Mirror video horizontally");
gMirrorVideoHor.onChange(function(value) {
    video_socket.emit("options", "mirror_video_axis", [opt.mirror_video_axis_vert, value])
});

let fMirrorControl = gui.addFolder("Mirror controls for axis");
let gMirrorControlVert = fMirrorControl.add(opt, "mirror_control_axis_vert").name("Mirror controls vertically");
gMirrorControlVert.onChange(function(value) {
    HTTP.open("POST", control_address + "/change-mirror_control_axis-[" + value + ", " + opt.mirror_control_axis_hor + "]");
    HTTP.send();
});
let gMirrorControlHor = fMirrorControl.add(opt, "mirror_control_axis_hor").name("Mirror controls horizontally");
gMirrorControlHor.onChange(function(value) {
    HTTP.open("POST", control_address + "/change-mirror_control_axis-[" + opt.mirror_video_axis_vert + ", " + value + "]");
    HTTP.send();
});

let fAxisMove = gui.addFolder("Allow movements for each axis");
let gAxisMoveVert = fAxisMove.add(opt, "axis_movements_vert").name("Allow vertical (up, down)  movements");
gAxisMoveVert.onChange(function(value) {
    HTTP.open("POST", control_address + "/change-axis_movements-[" + value + ", " + opt.axis_movements_hor + "]");
    HTTP.send();
});
let gAxisMoveHor = fAxisMove.add(opt, "axis_movements_hor").name("Allow horizontal (left, right) movements");
gAxisMoveHor.onChange(function(value) {
    HTTP.open("POST", control_address + "/change-axis_movements-[" + opt.axis_movements_vert + ", " + value + "]");
    HTTP.send();
});

gui.add(opt, "restart").name("Restart server");
let fPoweroff = gui.addFolder("Shutdown machine");
fPoweroff.add(opt, "poweroff").name("Shutdown machine");


// Update current position when recieved from server
control_socket.on("update_pos", (pos) => {
    opt.pos_vert = parseInt(pos[0], 10);
    opt.pos_hor = parseInt(pos[1], 10);
});


// Key down events
document.addEventListener("keydown", onDocumentKeyDown, false);
function onDocumentKeyDown(event) {
    if (event.repeat) { return }
    if (event.which === 27) {  // Esc
        stop_stream = false;

    } else if (!stop_stream) {
        if (event.which === 37) {  // Left
            if (!pressed["left"]) {
                control_socket.emit("left", true);
                pressed["left"] = true;
            }
        } else if (event.which === 39) {  // Right
            if (!pressed["right"]) {
                control_socket.emit("right", true);
                pressed["right"] = true;
            }
        } else if (event.which === 38) {  // Up
            if (!pressed["up"]) {
                control_socket.emit("up", true);
                pressed["up"] = true;
            }
        } else if (event.which === 40) {  // Down
            if (!pressed["down"]) {
                control_socket.emit("down", true);
                pressed["down"] = true;
            }
        }
    }
}


// Key up events
document.addEventListener("keyup", onDocumentKeyUp, false);
function onDocumentKeyUp(event) {
    if (stop_stream) return;
    if (event.which === 37) {  // Left
        control_socket.emit("left", false);
        pressed["left"] = false;
    } else if (event.which === 39) {  // Right
        control_socket.emit("right", false);
        pressed["right"] = false;
    } else if (event.which === 38) {  // Up
        control_socket.emit("up", false);
        pressed["up"] = false;
    } else if (event.which === 40) {  // Down
        control_socket.emit("down", 0);
        pressed["down"] = false;
    }
}

$("body").mousemove(function (e) {
    if (stop_stream) return;
    mouse_pos = [e.pageX, e.pageY];

    if (mouse_down) {
        if (opt.control_mode === "joystick") {
            let dx = mouse_pos[0] - mouse_click_pos[0];
            let dy = mouse_pos[1] - mouse_click_pos[1];

            let hyp = Math.sqrt(dx * dx + dy * dy);
            let dx_ratio = Math.min(1, dx / max_move_dist);
            let dy_ratio = Math.min(1, dy / max_move_dist);

            control_socket.emit("move", dy_ratio, dx_ratio);
        } else {
            let dx = mouse_pos[0] - last_mouse_pos[0];
            let dy = mouse_pos[1] - last_mouse_pos[1];

            control_socket.emit("move", dy, dx);
        }
    }
    last_mouse_pos = mouse_pos;
})

$('body').on('mousedown', function(event) {
    if (stop_stream) return;
    let option_elem = document.getElementsByClassName("dg main a")[0];
    if (option_elem.contains(event.target)) {
        return;  // This click is inside of options menu
    }
    switch (event.which) {
        case 1:
            // Left mouse button
            mouse_click_pos = mouse_pos;
            mouse_down = true;
            break;
        case 2:
            // Middle mouse button
            control_socket.emit("reset");
            break;
        case 3:
            // Right mouse button
            break;
        default:
            console.log("You have a strange mouse. Received input not in range [1, 3]");
    }
});


$('body').on('mouseup', function(event) {
    if (stop_stream) return;
    if (mouse_down) {
        // Send stop request
        control_socket.emit("stop");
    }
    mouse_down = false;
});

