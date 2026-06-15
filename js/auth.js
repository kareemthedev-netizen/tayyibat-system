document.addEventListener('DOMContentLoaded', function() {
    const authModal = document.getElementById('authModal');
    const loginModalBtn = document.getElementById('loginModalBtn');
    const closeBtn = document.querySelector('.close');
    const startBtn = document.getElementById('startJourneyBtn');
    const authScreen = document.getElementById('authScreen');
    const mainContent = document.getElementById('mainContent');
    const logoutBtn = document.getElementById('logoutBtn');
    
    if (loginModalBtn) {
        loginModalBtn.onclick = () => {
            if (authModal) authModal.style.display = 'block';
        };
    }
    if (closeBtn) {
        closeBtn.onclick = () => {
            if (authModal) authModal.style.display = 'none';
        };
    }
    window.onclick = (e) => {
        if (e.target === authModal) authModal.style.display = 'none';
    };
    
    const tabBtns = document.querySelectorAll('.tab-btn');
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const switchToRegister = document.getElementById('switchToRegister');
    const switchToLogin = document.getElementById('switchToLogin');
    
    if (tabBtns.length) {
        tabBtns.forEach(btn => {
            btn.onclick = () => {
                tabBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                if (btn.dataset.tab === 'login') {
                    if (loginForm) loginForm.classList.add('active');
                    if (registerForm) registerForm.classList.remove('active');
                } else {
                    if (loginForm) loginForm.classList.remove('active');
                    if (registerForm) registerForm.classList.add('active');
                }
            };
        });
    }
    if (switchToRegister) {
        switchToRegister.onclick = (e) => {
            e.preventDefault();
            const btn = document.querySelector('[data-tab="register"]');
            if (btn) btn.click();
        };
    }
    if (switchToLogin) {
        switchToLogin.onclick = (e) => {
            e.preventDefault();
            const btn = document.querySelector('[data-tab="login"]');
            if (btn) btn.click();
        };
    }
    
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = document.getElementById('loginEmail').value;
            const password = document.getElementById('loginPassword').value;
            try {
                await auth.signInWithEmailAndPassword(email, password);
                alert('تم تسجيل الدخول بنجاح');
                if (authModal) authModal.style.display = 'none';
            } catch (error) {
                alert('خطأ: ' + error.message);
            }
        });
    }
    
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('regName').value;
            const email = document.getElementById('regEmail').value;
            const password = document.getElementById('regPassword').value;
            const confirm = document.getElementById('regConfirmPassword').value;
            if (password !== confirm) {
                alert('كلمة المرور غير متطابقة');
                return;
            }
            if (password.length < 6) {
                alert('كلمة المرور 6 أحرف على الأقل');
                return;
            }
            try {
                const result = await auth.createUserWithEmailAndPassword(email, password);
                await db.collection('users').doc(result.user.uid).set({
                    username: username,
                    email: email,
                    createdAt: new Date(),
                    totalTests: 0
                });
                alert('تم إنشاء الحساب بنجاح');
                if (authModal) authModal.style.display = 'none';
            } catch (error) {
                alert('خطأ: ' + error.message);
            }
        });
    }
    
    if (startBtn) {
        startBtn.onclick = () => {
            if (auth.currentUser) {
                window.location.href = 'diagnosis.html';
            } else {
                if (authModal) authModal.style.display = 'block';
            }
        };
    }
    
    if (logoutBtn) {
        logoutBtn.onclick = async () => {
            await auth.signOut();
        };
    }
    
    auth.onAuthStateChanged((user) => {
        if (user) {
            if (authScreen && mainContent) {
                authScreen.style.display = 'none';
                mainContent.style.display = 'block';
            }
        } else {
            if (authScreen && mainContent) {
                authScreen.style.display = 'flex';
                mainContent.style.display = 'none';
            }
        }
    });
});