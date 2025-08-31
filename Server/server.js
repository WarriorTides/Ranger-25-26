const WebSocket = require('ws');

const PORT = 8080;
const wss = new WebSocket.Server({ port: PORT });

console.log(`WebSocket server running on ws://localhost:${PORT}`);

let clients = [];

wss.on('connection', (ws) => {
    console.log('New client connected');
    clients.push(ws);

    ws.on('message', (message) => {
        console.log('Received:', message);

        // Broadcast message to all other clients
        clients.forEach(client => {
            if (client !== ws && client.readyState === WebSocket.OPEN) {
                client.send(message);
            }
        });
    });

    ws.on('close', () => {
        console.log('Client disconnected');
        clients = clients.filter(client => client !== ws);
    });
});
