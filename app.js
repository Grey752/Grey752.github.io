// 主题切换功能
const themeButtons = document.querySelectorAll('.theme-btn');
const body = document.body;

// 从本地存储加载主题
const savedTheme = localStorage.getItem('theme') || 'light';
body.setAttribute('data-theme', savedTheme);

themeButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        const selectedTheme = btn.dataset.theme;
        body.setAttribute('data-theme', selectedTheme);
        localStorage.setItem('theme', selectedTheme);
    });
});

// 文件上传功能
const uploadForm = document.getElementById('uploadForm');
if (uploadForm) {
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const fileInput = document.getElementById('fileInput');
        const formData = new FormData();

        Array.from(fileInput.files).forEach(file => {
            formData.append('files', file);
        });

        try {
            // 此处需要后端接口支持，目前仅演示前端逻辑
            alert('文件上传功能需要后端支持，请联系管理员配置服务器');
        } catch (error) {
            console.error('上传失败:', error);
        }
    });
}

// 动态生成下载列表
function renderFileList() {
    const fileItems = document.getElementById('fileItems');
    if (fileItems) {
        fileItems.innerHTML = `
            <div class="file-item">
                <span>demo.js</span>
                <a href="/programs/demo.js" download class="download-btn">下载</a>
            </div>
        `;
    }
}

// 初始化时渲染文件列表
window.addEventListener('DOMContentLoaded', renderFileList);

// 聊天室功能（待实现）
const chatContainer = document.querySelector('.chat-container');
if (chatContainer) {
    chatContainer.innerHTML = `
        <div class="chat-box">
            <div id="messages" class="messages"></div>
            <input type="text" id="messageInput" placeholder="输入消息...">
            <button onclick="sendMessage()">发送</button>
        </div>
    `;
}

// WebSocket连接
const socket = new WebSocket('ws://localhost:3000');
const messageInput = document.getElementById('messageInput');
const messagesDiv = document.getElementById('messages');

// 消息发送功能
function sendMessage() {
    if (messageInput.value.trim()) {
        socket.send(JSON.stringify({
            type: 'message',
            content: messageInput.value,
            timestamp: new Date().toLocaleTimeString()
        }));
        messageInput.value = '';
    }
}

// 接收服务器消息
socket.onmessage = function (event) {
    const msg = JSON.parse(event.data);
    const messageElement = document.createElement('div');
    messageElement.className = 'message';
    messageElement.innerHTML = `
        <span class="msg-time">${msg.timestamp}</span>
        <span class="msg-content">${msg.content}</span>
    `;
    messagesDiv.appendChild(messageElement);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
};

// 异常处理
socket.onerror = function (error) {
    console.error('WebSocket错误:', error);
    alert('无法连接到聊天服务器');
};

// 回车发送消息
messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});
    