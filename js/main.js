// دوال مساعدة عامة
function saveToLocal(key, value) {
    localStorage.setItem(key, JSON.stringify(value));
}

function getFromLocal(key) {
    const item = localStorage.getItem(key);
    return item ? JSON.parse(item) : null;
}

function removeFromLocal(key) {
    localStorage.removeItem(key);
}

console.log('🚀 موقع طبيب نفسك - نظام الطيبات');
console.log('📅 تم التطوير بواسطة كريم عاطف - 2025');