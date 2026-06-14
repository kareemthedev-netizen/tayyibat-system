// نظام الليل والنهار
export function initTheme() {
  // التحقق من وجود تفضيل محفوظ
  const savedTheme = localStorage.getItem('theme');
  const body = document.body;
  
  if (savedTheme === 'night') {
    body.classList.add('night-mode');
  } else if (savedTheme === 'day') {
    body.classList.remove('night-mode');
  } else {
    // التحقق من تفضيل النظام
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      body.classList.add('night-mode');
      localStorage.setItem('theme', 'night');
    } else {
      localStorage.setItem('theme', 'day');
    }
  }
  
  // إضافة زر التبديل
  addThemeToggle();
}

function addThemeToggle() {
  const toggleBtn = document.createElement('button');
  toggleBtn.className = 'theme-toggle';
  toggleBtn.innerHTML = '<i class="fas fa-moon"></i> الوضع الليلي';
  toggleBtn.onclick = () => {
    const body = document.body;
    if (body.classList.contains('night-mode')) {
      body.classList.remove('night-mode');
      localStorage.setItem('theme', 'day');
      toggleBtn.innerHTML = '<i class="fas fa-moon"></i> الوضع الليلي';
    } else {
      body.classList.add('night-mode');
      localStorage.setItem('theme', 'night');
      toggleBtn.innerHTML = '<i class="fas fa-sun"></i> الوضع النهاري';
    }
  };
  document.body.prepend(toggleBtn);
}