// الوضع الليلي والنهاري
function initTheme() {
  const savedTheme = localStorage.getItem('theme');
  if (savedTheme === 'night') {
    document.body.classList.add('night-mode');
  }
  
  const toggleBtn = document.createElement('button');
  toggleBtn.className = 'theme-toggle';
  toggleBtn.innerHTML = document.body.classList.contains('night-mode') ? '☀️ النهاري' : '🌙 الليلي';
  toggleBtn.onclick = () => {
    if (document.body.classList.contains('night-mode')) {
      document.body.classList.remove('night-mode');
      localStorage.setItem('theme', 'day');
      toggleBtn.innerHTML = '🌙 الليلي';
    } else {
      document.body.classList.add('night-mode');
      localStorage.setItem('theme', 'night');
      toggleBtn.innerHTML = '☀️ النهاري';
    }
  };
  document.body.prepend(toggleBtn);
}

// تشغيل الوضع الليلي عند تحميل الصفحة
initTheme();