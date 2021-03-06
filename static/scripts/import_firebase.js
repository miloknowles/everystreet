import { initializeApp } from 'https://www.gstatic.com/firebasejs/9.6.5/firebase-app.js';

// https://stackoverflow.com/questions/5786851/define-a-global-variable-in-a-javascript-function
// Assign these variables to 'window' to make them global.
import { getDatabase } from 'https://www.gstatic.com/firebasejs/9.6.5/firebase-database.js';

window.firebaseApp = initializeApp({
  apiKey: "AIzaSyBZJ7d4Iz6i9q_E4Xq2f0bRIcg3uktGo1Q",
  // authDomain: "YOUR_APP.firebaseapp.com",
  databaseURL: "https://runningheatmap-a5864-default-rtdb.firebaseio.com/",
});

window.firebaseDatabase = getDatabase(firebaseApp);
