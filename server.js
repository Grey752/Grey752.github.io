const express = require('express');
const app = express();
const path = require('path');

// 定义文件下载的路由
app.get('/programs/:filename', (req, res) => {
    const filename = req.params.filename;
    const filePath = path.join(__dirname, 'programs', filename);
    res.download(filePath, (err) => {
        if (err) {
            console.error('下载出错:', err);
            res.status(404).send('文件未找到');
        }
    });
});

// 启动服务器
const port = 3000;
app.listen(port, () => {
    console.log(`服务器运行在端口 ${port}`);
});
    