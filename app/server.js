require('dotenv').config(); // Load environment variables
const express = require('express');
const session = require('express-session');
const passport = require('passport');
const passportSetup = require('./config/passport-setup'); // Import passport configuration
const authRoutes = require('./routes/auth'); // Import auth routes
const indexRoutes = require('./routes/index'); // Import index routes
const fetch = require('node-fetch'); // Use require for CommonJS
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// Session configuration
// IMPORTANT: Use a proper session store (like connect-redis, connect-mongo) for production
// IMPORTANT: Set a strong, secret key from environment variables
const SESSION_SECRET = process.env.SESSION_SECRET || 'some-very-strong-secret-key'; // TODO: Replace or set env var
app.use(session({
    secret: SESSION_SECRET,
    resave: false,
    saveUninitialized: false, // Don't create session until something stored
    cookie: {
        secure: process.env.NODE_ENV === 'production', // Use secure cookies in production (requires HTTPS)
        httpOnly: true,
        maxAge: 24 * 60 * 60 * 1000 // 24 hours
    }
}));

// Initialize Passport and restore authentication state, if any, from the session.
app.use(passport.initialize());
app.use(passport.session());

// Set view engine
app.set('view engine', 'ejs');

// Static files
app.use(express.static('public'));

// Set up routes
app.use('/auth', authRoutes); // Mount auth routes
app.use('/', indexRoutes); // Mount index routes (including dashboard)

// Middleware to parse plain text body (for the Google ID token)
app.use(express.text({ type: 'text/plain' }));

// Login Page Route (Root)
app.get('/', (req, res) => {
    if (req.isAuthenticated()) {
        // If already logged in, maybe redirect to terminal? Or show a logged-in home.
        res.redirect('/terminal'); // Redirect to terminal if session exists
    } else {
        // Serve the login page (modified index.html)
        res.sendFile(path.join(__dirname, 'public', 'index.html'));
    }
});

// Protected route simulation (for redirecting to ttyd)
// Nginx handles the actual proxy to ttyd for /terminal,
// but this route *could* exist to ensure auth before Nginx sees it,
// though it's simpler to let Nginx proxy and have ttyd be the destination.
// If we relied on this route, Nginx would proxy /terminal to this Node app,
// which would then internally redirect or proxy again - less efficient.
// Let's keep it simple: login flow ends with res.redirect('/terminal') in auth.js,
// and Nginx proxies /terminal directly to ttyd.

// --- Remove the old /auth POST endpoint --- 
// The functionality is now handled by passport-setup.js during the callback.

// Start server
app.listen(PORT, () => {
    console.log(`Server listening on port ${PORT}`);
}); 