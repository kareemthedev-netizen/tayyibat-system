function saveToLocal(key, value) {
    localStorage.setItem(key, JSON.stringify(value));
}

function getFromLocal(key) {
    const item = localStorage.getItem(key);
    return item ? JSON.parse(item) : null;
}

console.log('🚀 موقع طبيب نفسك - نظام الطيبات');