require('dotenv').config(); // Load environment variables
const express = require('express');
const session = require('express-session');
const passport = require('passport');
const passportSetup = require('./config/passport-setup'); // Import passport configuration
const authRoutes = require('./routes/auth'); // Import auth routes
const indexRoutes = require('./routes/index'); // Import index routes

const app = express();
const PORT = process.env.PORT || 3000;

// Session configuration
app.use(session({
    secret: process.env.SESSION_SECRET, // Required, should be in .env
    resave: false,
    saveUninitialized: false, // Set to false for login sessions
    // Add store configuration for production environments
}));

// Initialize Passport
app.use(passport.initialize());
app.use(passport.session());

// Set view engine
app.set('view engine', 'ejs');

// Static files
app.use(express.static('public'));

// Set up routes
app.use('/auth', authRoutes); // Mount auth routes
app.use('/', indexRoutes); // Mount index routes (including dashboard)

// Basic route (now handled by indexRoutes if at '/', but keep for fallback or remove)
app.get('/', (req, res) => {
    // res.send('Hello World!'); // Replace with rendering a home page later
    res.render('home', { user: req.user }); // Render home page view
});

// Start server
app.listen(PORT, () => {
    console.log(`Server listening on port ${PORT}`);
}); 