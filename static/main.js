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
        socket.emit('left', true);
    } else if (event.which === 39) {  // Right
        socket.emit('right', true);
    } else if (event.which === 38) {  // Up
        socket.emit("up", true);
    } else if (event.which === 40) {  // Down
        socket.emit("down", true);
    }
}


// Key up events
document.addEventListener("keyup", onDocumentKeyUp, false);
function onDocumentKeyUp(event) {
    if (event.which === 37) {  // Left
        socket.emit('left', false);
    } else if (event.which === 39) {  // Right
        socket.emit('right', false);
    } else if (event.which === 38) {  // Up
        socket.emit("up", false);
    } else if (event.which === 40) {  // Down
        socket.emit("down", false);
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

$('body').on('mousedown', function () {
    mouse_click_pos = mouse_pos;
    mouse_down = true;
});
$('body').on('mouseup', function () {
    mouse_down = false;
    socket.emit("stop");
});

