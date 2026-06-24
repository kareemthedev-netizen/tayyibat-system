function initTheme() {
  const savedTheme = localStorage.getItem('theme');
  const body = document.body;
  
  if (savedTheme === 'night') {
    body.classList.add('night-mode');
  } else {
    body.classList.remove('night-mode');
  }
  
  // زر تبديل الوضع (يثبت في الزاوية)
  const toggleBtn = document.createElement('button');
  toggleBtn.className = 'theme-toggle';
  toggleBtn.innerHTML = body.classList.contains('night-mode') ? '☀️' : '🌙';
  toggleBtn.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        background: rgba(0,0,0,0.5);
        backdrop-filter: blur(10px);
        border: 1px solid #ffd700;
        border-radius: 50%;
        width: 45px;
        height: 45px;
        font-size: 1.2rem;
        cursor: pointer;
        color: #f5e6d3;
        transition: all 0.3s;
    `;
  
  toggleBtn.onclick = () => {
    if (document.body.classList.contains('night-mode')) {
      document.body.classList.remove('night-mode');
      localStorage.setItem('theme', 'day');
      toggleBtn.innerHTML = '🌙';
    } else {
      document.body.classList.add('night-mode');
      localStorage.setItem('theme', 'night');
      toggleBtn.innerHTML = '☀️';
    }
  };
  
  document.body.prepend(toggleBtn);
}

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
});