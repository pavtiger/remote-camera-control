const Http = new XMLHttpRequest();


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


const max_move_dist = 300;
let mouse_down = false;
let mouse_click_pos = [], mouse_pos = [];

const socket = io.connect(server_address);
socket.on('image', (image) => {
    const imageElem = document.getElementById('image');
    imageElem.src = `data:image/jpeg;base64,${image}`;
})
document.getElementById('image').ondragstart = function() { return false; };  // Disable image drag


const Options = function () {
    // Retrieve options from server
    this.options = httpGet(server_address + '/options');

    this.servo_pins_vert = this.options["servo_pins"][0];
    this.servo_pins_hor = this.options["servo_pins"][1];

    this.starting_angles_vert = this.options["starting_angles"][0];
    this.starting_angles_hor = this.options["starting_angles"][1];

    this.limits_vert_start = this.options["limits"][0][0];
    this.limits_vert_end = this.options["limits"][0][1];
    this.limits_hor_start = this.options["limits"][1][0];
    this.limits_hor_end = this.options["limits"][1][1];

    this.step_vert = this.options["step"][0];
    this.step_hor = this.options["step"][1];

    this.camera_index = this.options["camera_index"];
    this.resolution_width = this.options["resolution"][0];
    this.resolution_height = this.options["resolution"][1];

    this.control_mode = this.options["control_mode"];

    this.mirror_video_axis_vert = this.options["mirror_video_axis"][0];
    this.mirror_video_axis_hor = this.options["mirror_video_axis"][1];
    this.mirror_control_axis_vert = this.options["mirror_control_axis"][0];
    this.mirror_control_axis_hor = this.options["mirror_control_axis"][1];
    this.axis_movements_vert = this.options["axis_movements"][0];
    this.axis_movements_hor = this.options["axis_movements"][1];
};


// Dat Gui controls setup
let opt = new Options();
gui = new dat.GUI({
    load: JSON,
    preset: "Flow",
    width: 500
});


let fServoPins = gui.addFolder("Servo pins");
let gServoPinsVert = fServoPins.add(opt, "servo_pins_vert").name("Vertical");
gServoPinsVert.onChange(function(value) {
    Http.open("POST", server_address + "/change-servo_pins-[" + Math.round(value.toString()) + ", " + Math.round(opt.servo_pins_hor.toString()) + "]");
    Http.send();
});
let gServoPinsHor = fServoPins.add(opt, "servo_pins_hor").name("Horizontal");
gServoPinsHor.onChange(function(value) {
    Http.open("POST", server_address + "/change-servo_pins-[" + Math.round(opt.servo_pins_vert.toString()) + ", "  + Math.round(value.toString()) + "]");
    Http.send();
});

let fStartingAngles = gui.addFolder("Servo starting angles");
let gStartingAnglesVert = fStartingAngles.add(opt, "starting_angles_vert", 500, 2500).name("Vertical");
gStartingAnglesVert.onChange(function(value) {
    Http.open("POST", server_address + "/change-starting_angles-[" + Math.round(value.toString()) + ", " + Math.round(opt.starting_angles_hor) + "]");
    Http.send();
});
let gStartingAnglesHor = fStartingAngles.add(opt, "starting_angles_hor", 500, 2500).name("Horizontal");
gStartingAnglesHor.onChange(function(value) {
    Http.open("POST", server_address + "/change-starting_angles-[" + Math.round(opt.starting_angles_vert) + ", " + Math.round(value.toString()) + "]");
    Http.send();
});

let fLimits = gui.addFolder("Servo limits on each axis");
let gLimitsVertStart = fLimits.add(opt, "limits_vert_start", 500, 2500).name("Vertical start");
let gLimitsVertEnd = fLimits.add(opt, "limits_vert_end", 500, 2500).name("Vertical end");
let gLimitsHorStart = fLimits.add(opt, "limits_hor_start", 500, 2500).name("Horizontal start");
let gLimitsHorEnd = fLimits.add(opt, "limits_hor_end", 500, 2500).name("Horizontal end");

let fStep = gui.addFolder("Servo step distances");
let gStepVert = fStep.add(opt, "step_vert", 0, 30).name("Vertical");
gStepVert.onChange(function(value) {
    Http.open("POST", server_address + "/change-step-[" + Math.round(value.toString()) + ", " + Math.round(opt.step_hor) + "]");
    Http.send();
});
let gStepHor = fStep.add(opt, "step_hor", 0, 30).name("Horizontal");
gStepHor.onChange(function(value) {
    Http.open("POST", server_address + "/change-step-[" + Math.round(opt.step_vert) + ", " + Math.round(value.toString()) + "]");
    Http.send();
});

let gCameraIndex = gui.add(opt, "camera_index").name("Camera index in system");
gCameraIndex.onChange(function(value) {
    Http.open("POST", server_address + "/change-camera_index-" + Math.round(value.toString()));
    Http.send();
});

let fResolution = gui.addFolder("Video resolution");
let gResolutionWidth = fResolution.add(opt, "resolution_width").name("Width");
gResolutionWidth.onChange(function(value) {
    Http.open("POST", server_address + "/change-resolution-[" + Math.round(value.toString()) + ", " + Math.round(opt.resolution_height) + "]");
    Http.send();
});
let gResolutionHeight = fResolution.add(opt, "resolution_height").name("Height");
gResolutionHeight.onChange(function(value) {
    Http.open("POST", server_address + "/change-resolution-[" + Math.round(opt.resolution_width) + ", " + Math.round(value.toString()) + "]");
    Http.send();
});

let gControlsMode = gui.add(opt, "control_mode", ["drag", "joystick"]).name("Control mode");

let fMirrorVideo = gui.addFolder("Mirror video for axis");
let gMirrorVideoVert = fMirrorVideo.add(opt, "mirror_video_axis_vert").name("Mirror video for axis");
let gMirrorVideoHor = fMirrorVideo.add(opt, "mirror_video_axis_hor").name("Mirror video for axis");

let fMirrorControl = gui.addFolder("Mirror controls for axis");
let gMirrorControlVert = fMirrorControl.add(opt, "mirror_control_axis_vert").name("Mirror controls for axis");
let gMirrorControlHor = fMirrorControl.add(opt, "mirror_control_axis_hor").name("Mirror controls for axis");

let fAxisMove = gui.addFolder("Allow movements for each axis");
let gAxisMoveVert = fAxisMove.add(opt, "axis_movements_vert").name("Allow movements for each axis");
let gAxisMoveHor = fAxisMove.add(opt, "axis_movements_hor").name("Allow movements for each axis");


// Key down events
document.addEventListener("keydown", onDocumentKeyDown, false);
function onDocumentKeyDown(event) {
    if (event.which === 37) {  // Left
        Http.open("POST", server_address + "/left_1");
        Http.send();
    } else if (event.which === 39) {  // Right
        Http.open("POST", server_address + "/right_1");
        Http.send();
    } else if (event.which === 38) {  // Up
        Http.open("POST", server_address + "/up_1");
        Http.send();
    } else if (event.which === 40) {  // Down
        Http.open("POST", server_address + "/down_1");
        Http.send();
    }
}


// Key up events
document.addEventListener("keyup", onDocumentKeyUp, false);
function onDocumentKeyUp(event) {
    if (event.which === 37) {  // Left
        Http.open("POST", server_address + "/left_0");
        Http.send();
    } else if (event.which === 39) {  // Right
        Http.open("POST", server_address + "/right_0");
        Http.send();
    } else if (event.which === 38) {  // Up
        Http.open("POST", server_address + "/up_0");
        Http.send();
    } else if (event.which === 40) {  // Down
        Http.open("POST", server_address + "/down_0");
        Http.send();
    }
}

$("body").mousemove(function(e) {
    mouse_pos = [e.pageX, e.pageY];

    if (mouse_down) {
        dx = mouse_pos[0] - mouse_click_pos[0];
        dy = mouse_pos[1] - mouse_click_pos[1];

        let hyp = Math.sqrt(dx * dx + dy * dy);
        let dx_ratio = Math.min(1, dx / max_move_dist);
        let dy_ratio = Math.min(1, dy / max_move_dist);
        Http.open("POST", server_address + "/move_" + dy_ratio + "_" + dx_ratio);
        Http.send();
    }
})

$('body').on('mousedown', function(event) {
    switch (event.which) {
        case 1:
            // Left mouse button
            mouse_click_pos = mouse_pos;
            mouse_down = true;
            break;
        case 2:
            // Middle mouse button
            Http.open("POST", server_address + "/reset");
            Http.send();
            break;
        case 3:
            // Right mouse button
            break;
        default:
            console.log("You have a strange mouse. Received input not in range [1, 3]");
    }
});

$('body').on('mouseup', function(event) {
    if (mouse_down) {
        // Send stop request
        Http.open("POST", server_address + "/stop");
        Http.send();
    }
    mouse_down = false;
});

