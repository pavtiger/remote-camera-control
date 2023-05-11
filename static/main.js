const Http = new XMLHttpRequest();

const max_move_dist = 300;
let mouse_down = false;
let mouse_click_pos = [], mouse_pos = [];

const socket = io.connect(server_address);
socket.on('image', (image) => {
    const imageElem = document.getElementById('image');
    imageElem.src = `data:image/jpeg;base64,${image}`;
})
document.getElementById('image').ondragstart = function() { return false; };  // Disable image drag


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
        socket.emit("move", dy_ratio, dx_ratio);
    }
})

$('body').on('mousedown', function(event) {
    console.log(event.which);
    switch (event.which) {
        case 1:
            // Left mouse button
            mouse_click_pos = mouse_pos;
            mouse_down = true;
            break;
        case 2:
            // Middle mouse button
            socket.emit("reset");
            break;
        case 3:
            // Right mouse button
            break;
        default:
            console.log("You have a strange mouse. Received input not in range [1, 3]");
    }
});

$('body').on('mouseup', function(event) {
    mouse_down = false;
    socket.emit("stop");
});

