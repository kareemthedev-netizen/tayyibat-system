const firebaseConfig = {
  apiKey: "AIzaSyBsXv68Rc9ppzVF57Qe2tkYM0kLK5ZjjZc",
  authDomain: "tayyibat-system.firebaseapp.com",
  projectId: "tayyibat-system",
  storageBucket: "tayyibat-system.firebasestorage.app",
  messagingSenderId: "679684759294",
  appId: "1:679684759294:web:024b5c6eaef793bcd70faf",
  measurementId: "G-BQ7PVH37SJ"
};

firebase.initializeApp(firebaseConfig);
const auth = firebase.auth();
const db = firebase.firestore();
const analytics = firebase.analytics();

console.log("✅ Firebase connected");