// 示例代码：颜色渐变动画
function colorShift() {
  const colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4'];
  let index = 0;
  
  setInterval(() => {
    document.body.style.backgroundColor = colors[index];
    index = (index + 1) % colors.length;
  }, 3000);
}

// 初始化函数
window.addEventListener('load', () => {
  colorShift();
  console.log('颜色渐变动画已启动！');
});